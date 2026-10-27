import os
os.environ.setdefault('QT_QPA_PLATFORM','offscreen')
import tempfile
import unittest
import importlib.util
if importlib.util.find_spec('PySide6') is None:
    raise unittest.SkipTest('Interface Qt opcional: instale requirements-qt.txt para estes testes.')
from dataclasses import replace
from pathlib import Path
from unittest.mock import patch
from PySide6.QtCore import Qt, QTimer, QEvent
from PySide6.QtTest import QTest
from PySide6.QtWidgets import (QApplication, QLineEdit, QDialogButtonBox, QTableWidget,
                               QMessageBox, QComboBox, QPlainTextEdit, QCheckBox, QFormLayout)
from app_qt import seed_demo
from horas_jogadas import i18n
from horas_jogadas.storage import Repositorio
from horas_jogadas.zerados import Conclusao, interpretar_txt
from horas_jogadas_qt.preview import prepare_preview, inventory
from horas_jogadas_qt.controller import Controller
from horas_jogadas_qt.theme import apply_theme
from horas_jogadas_qt.window import Window
from .test_data import Clock

APP=QApplication.instance() or QApplication([])


class UiTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory()
        self.source=Path(self.tmp.name)/'source'; self.source.mkdir(); seed_demo(self.source)
        self.before=inventory(self.source)
        self.folder=prepare_preview(self.source,Path(self.tmp.name)/'review')
        self.c=Controller(self.folder)
        i18n.definir_idioma('pt')
        apply_theme(APP)
        self.w=Window(self.c)
        self.w.show(); APP.processEvents()
        self.critical=patch.object(QMessageBox,'critical',return_value=QMessageBox.Ok).start()
        self.warning=patch.object(QMessageBox,'warning',return_value=QMessageBox.Ok).start()
        self.info=patch.object(QMessageBox,'information',return_value=QMessageBox.Ok).start()
        self.addCleanup(patch.stopall)

    def tearDown(self):
        self.w.timer.stop(); self.w.closing_allowed=True; self.w.close()
        APP.removeEventFilter(self.w)
        self.w.deleteLater()
        APP.sendPostedEvents(None,QEvent.DeferredDelete)
        APP.processEvents()
        self.assertEqual(inventory(self.source),self.before)
        i18n.definir_idioma('pt')
        self.tmp.cleanup()

    def dialog(self, callback, action):
        failures=[]
        def run():
            d=APP.activeModalWidget()
            try:
                callback(d)
            except Exception as error:
                failures.append(error)
                if d: d.reject()
        QTimer.singleShot(0,run)
        action()
        APP.processEvents()
        if failures: raise failures[0]

    def save_dialog(self,d):
        QTest.mouseClick(d.findChild(QDialogButtonBox).button(QDialogButtonBox.Save),Qt.LeftButton)
        if d.isVisible():
            d.reject()

    def test_all_pages_and_themes_render_in_both_languages(self):
        for language in ('pt','en'):
            i18n.definir_idioma(language)
            for theme in ('dark','violet','light'):
                apply_theme(APP,theme)
                for page in ('library','history','stats','completed','settings'):
                    with self.subTest(language=language,theme=theme,page=page):
                        self.w.navigate(page); APP.processEvents()
                        self.assertFalse(self.w.grab().isNull())
        self.assertEqual(self.critical.call_count,0)

    def test_scroll_resize_and_ticks_preserve_card_identity(self):
        identities={key:id(card) for key,card in self.w.cards.items()}
        first=next(iter(self.c.timers)); timer=self.c.timers[first]
        timer.clock=Clock(); timer.start()
        for width in (1240,840,1440,1000):
            self.w.resize(width,720); APP.processEvents()
            bar=self.w.library_scroll.verticalScrollBar()
            bar.setValue(bar.maximum()); self.w.tick(); APP.processEvents()
            self.assertEqual(identities,{key:id(card) for key,card in self.w.cards.items()})
        self.assertEqual(self.critical.call_count,0)

    def test_search_filter_sort_do_not_modify_saved_manual_order(self):
        ids=[g.id for g in self.c.repo.jogos]
        self.w.search.setText('celeste'); APP.processEvents()
        visible=[key for key,card in self.w.cards.items() if not card.isHidden()]
        self.assertEqual(len(visible),1)
        self.assertEqual(self.c.repo.jogo_por_id(visible[0]).nome,'Celeste')
        self.w.search.clear()
        self.w.order.setCurrentIndex(self.w.order.findData('nome'))
        self.assertEqual([g.id for g in self.c.repo.jogos],ids)
        self.assertEqual(self.critical.call_count,0)

    def test_add_game_and_timer_buttons_save_compatible_session(self):
        with patch('horas_jogadas_qt.window.QInputDialog.getText',return_value=('Novo jogo',True)):
            self.w.add_game()
        game=self.c.repo.jogos[0]; timer=self.c.timers[game.id]; timer.clock=Clock()
        QTest.mouseClick(self.w.cards[game.id].start,Qt.LeftButton)
        timer.clock.advance(15)
        QTest.mouseClick(self.w.cards[game.id].pause,Qt.LeftButton)
        self.assertTrue(timer.pausado)
        QTest.mouseClick(self.w.cards[game.id].stop,Qt.LeftButton)
        self.assertEqual(Repositorio(str(self.folder)).sessoes[-1].segundos,15)
        self.assertFalse(self.c.timers[game.id].pending)
        self.assertEqual(self.critical.call_count,0)

    def test_manual_session_dialog_saves_and_edit_keeps_id(self):
        self.w.navigate('history')
        before=len(self.c.repo.sessoes)
        def create(d):
            d.findChild(QLineEdit).setText('00:12:30')
            self.save_dialog(d)
        self.dialog(create,lambda:self.w.edit_session())
        self.assertEqual(len(self.c.repo.sessoes),before+1)
        session=self.c.repo.sessoes[-1]; sid=session.sessao_id
        def edit(d):
            d.findChild(QLineEdit).setText('00:13:00')
            self.save_dialog(d)
        self.dialog(edit,lambda:self.w.edit_session(session))
        self.assertEqual(self.c.repo.sessoes[-1].sessao_id,sid)
        self.assertEqual(self.c.repo.sessoes[-1].segundos,780)
        self.assertEqual(self.warning.call_count,0)
        self.assertEqual(self.critical.call_count,0)

    def test_completion_editor_preserves_notes_and_adds_dlc(self):
        self.w.navigate('completed')
        def fill(d):
            entries=d.findChildren(QLineEdit)
            # Spinboxes contain their own line edits; select fields by direct form rows.
            form=d.form
            form.itemAt(0,QFormLayout.ItemRole.FieldRole).widget().setText('Expansão teste')
            form.itemAt(1,QFormLayout.ItemRole.FieldRole).widget().setValue(2024)
            form.itemAt(2,QFormLayout.ItemRole.FieldRole).widget().setCurrentIndex(0)
            form.itemAt(4,QFormLayout.ItemRole.FieldRole).widget().setText('2h')
            form.itemAt(5,QFormLayout.ItemRole.FieldRole).widget().setText('30m')
            d.findChild(QCheckBox).setChecked(True)
            d.findChild(QPlainTextEdit).setPlainText('Não perder')
            self.save_dialog(d)
        self.dialog(fill,lambda:self.w.edit_completion())
        record=self.c.zerados.registros[-1]
        self.assertEqual(record.nome,'Expansão teste')
        self.assertTrue(record.dlc)
        self.assertEqual(record.segundos,7200)
        self.assertEqual(record.notas,'Não perder')
        self.assertEqual(self.warning.call_count,0)

    def test_import_review_ignores_invalid_unselected_lines_and_deduplicates(self):
        items=interpretar_txt('ZERADOS EM 2024\nJaneiro:\n-Jogo importado * 2h\n@dlc: sim\nlinha inválida')
        self.w.navigate('completed')
        before=len(self.c.zerados.registros)
        self.dialog(self.save_dialog,lambda:self.w.review_import(items))
        self.assertEqual(len(self.c.zerados.registros),before+1)
        self.assertTrue(self.c.zerados.registros[-1].dlc)
        self.dialog(self.save_dialog,lambda:self.w.review_import(items))
        self.assertEqual(len(self.c.zerados.registros),before+1)
        self.assertEqual(self.critical.call_count,0)

    def test_history_delete_undo_and_completion_undo(self):
        self.w.navigate('history')
        before=[s.to_dict() for s in self.c.repo.sessoes]
        self.w.history.selectRow(0)
        with patch.object(self.w,'confirm',return_value=True):
            self.w.delete_selected_session()
        self.assertEqual(len(self.c.repo.sessoes),len(before)-1)
        self.w.perform(self.c.undo_session)
        self.assertEqual([s.to_dict() for s in self.c.repo.sessoes],before)
        self.w.navigate('completed')
        record=self.c.zerados.registros[0]
        self.w.year=record.ano; self.w.refresh(); self.w.completed.selectRow(0)
        before_z=len(self.c.zerados.registros)
        with patch.object(self.w,'confirm',return_value=True): self.w.delete_completion()
        self.assertEqual(len(self.c.zerados.registros),before_z-1)
        self.w.undo_completion()
        self.assertEqual(len(self.c.zerados.registros),before_z)

    def test_close_cancel_keeps_timer_and_save_persists(self):
        game=self.c.repo.jogos[0]; timer=self.c.timers[game.id]; timer.clock=Clock(); timer.start(); timer.clock.advance(10)
        with patch.object(QMessageBox,'question',return_value=QMessageBox.Cancel):
            self.w.close()
        self.assertTrue(self.w.isVisible())
        self.assertTrue(timer.rodando)
        before=len(self.c.repo.sessoes)
        with patch.object(QMessageBox,'question',return_value=QMessageBox.Save):
            self.w.close()
        self.assertFalse(self.w.isVisible())
        self.assertEqual(len(Repositorio(str(self.folder)).sessoes),before+1)

    def test_settings_switch_language_without_resetting_active_timer(self):
        game=self.c.repo.jogos[0]; timer=self.c.timers[game.id]; timer.start()
        self.w.navigate('settings')
        self.w.save_settings('light','en')
        self.assertEqual(i18n.idioma_atual(),'en')
        self.assertTrue(self.c.timers[game.id].rodando)
        self.assertEqual(self.w.theme_name(),'light')
        self.assertEqual(self.critical.call_count,0)

    def test_escape_clears_search_and_moves_focus(self):
        self.w.search.setFocus(); self.w.search.setText('teste'); APP.processEvents()
        QTest.keyClick(self.w.search,Qt.Key_Escape); APP.processEvents()
        self.assertEqual(self.w.search.text(),'')
        self.assertFalse(self.w.search.hasFocus())

    def test_export_csv_and_txt_write_files_without_changing_records(self):
        before=[s.to_dict() for s in self.c.repo.sessoes]
        csv=Path(self.tmp.name)/'historico.csv'
        txt=Path(self.tmp.name)/'zerados.txt'
        with patch('horas_jogadas_qt.window.QFileDialog.getSaveFileName',return_value=(str(csv),'CSV')):
            self.w.export_csv()
        self.assertTrue(csv.read_text(encoding='utf-8-sig').startswith('Jogo;'))
        self.w.year=self.c.zerados.registros[0].ano
        with patch('horas_jogadas_qt.window.QFileDialog.getSaveFileName',return_value=(str(txt),'TXT')):
            self.w.export_txt()
        self.assertIn('ZERADOS EM',txt.read_text(encoding='utf-8'))
        self.assertEqual([s.to_dict() for s in self.c.repo.sessoes],before)

    def test_full_backup_action_and_restore_keep_original_source(self):
        self.w.backup_now()
        backups=list((self.folder/'full-backups').iterdir())
        self.assertEqual(len(backups),1)
        self.w.perform(lambda:self.c.add_game('Temporário'))
        self.assertEqual(len(self.w.c.repo.jogos),7)
        with patch('horas_jogadas_qt.window.QFileDialog.getExistingDirectory',return_value=str(backups[0])),patch.object(self.w,'confirm',return_value=True):
            self.w.restore_backup()
        self.assertEqual(len(self.w.c.repo.jogos),6)
        self.assertEqual(len(self.w.c.zerados.registros),4)
        self.assertEqual(self.critical.call_count,0)

    def test_unexpected_session_recovery_cancel_preserves_file(self):
        game=self.c.repo.jogos[0]
        timer=self.c.timers[game.id]; timer.clock=Clock(); timer.start(); timer.clock.advance(30)
        self.c.save_pending()
        pending=(self.folder/'em_andamento.json').read_bytes()
        self.w.pending_recovery=True
        with patch.object(QMessageBox,'question',return_value=QMessageBox.Cancel):
            self.assertFalse(self.w.recovery_prompt())
        self.assertEqual((self.folder/'em_andamento.json').read_bytes(),pending)

    def test_library_navigation_and_edit_preserve_search_filter_and_scroll(self):
        self.w.search.setText('Hollow')
        self.w.filter.setCurrentIndex(self.w.filter.findData('Jogando'))
        APP.processEvents()
        self.w.navigate('history'); APP.processEvents()
        self.w.navigate('library'); APP.processEvents()
        self.assertEqual(self.w.search.text(),'Hollow')
        self.assertEqual(self.w.filter.currentData(),'Jogando')
        visible=[key for key,card in self.w.cards.items() if not card.isHidden()]
        self.assertEqual(len(visible),1)
        key=visible[0]
        self.w.perform(lambda:self.c.repo.renomear_jogo(key,'Hollow Knight · revisado'))
        APP.processEvents()
        self.assertEqual(self.w.search.text(),'Hollow')
        self.assertFalse(self.w.cards[key].isHidden())
        self.w.search.clear(); self.w.filter.setCurrentIndex(0)
        self.w.resize(840,620); APP.processEvents()
        bar=self.w.library_scroll.verticalScrollBar()
        self.assertGreater(bar.maximum(),100)
        bar.setValue(150)
        previous=bar.value()
        self.w.navigate('completed'); APP.processEvents()
        self.w.navigate('library'); QTest.qWait(20); APP.processEvents()
        self.assertEqual(self.w.library_scroll.verticalScrollBar().value(),previous)
        self.assertEqual(self.critical.call_count,0)

    def test_history_selection_survives_refresh_and_round_trip(self):
        self.w.navigate('history'); APP.processEvents()
        self.w.history.selectRow(2)
        key=self.w.history_sessions[2].sessao_id
        self.w.navigate('completed'); APP.processEvents()
        self.w.navigate('history'); APP.processEvents()
        self.assertEqual(self.w.history_sessions[self.w.history.currentRow()].sessao_id,key)
        self.w.perform(lambda:self.c.repo.atualizar_sessao(key,self.w.history_sessions[2].jogo_id,
            self.w.history_sessions[2].jogo,600,self.w.history_sessions[2].data_dt))
        self.assertEqual(self.w.history_sessions[self.w.history.currentRow()].sessao_id,key)
        self.assertEqual(self.critical.call_count,0)

    def test_clicking_card_releases_search_focus_without_clearing_filter(self):
        self.w.search.setText('Hollow')
        self.w.search.setFocus(); APP.processEvents()
        key=next(key for key,card in self.w.cards.items() if not card.isHidden())
        QTest.mouseClick(self.w.cards[key],Qt.LeftButton)
        APP.processEvents()
        self.assertFalse(self.w.search.hasFocus())
        self.assertEqual(self.w.search.text(),'Hollow')
