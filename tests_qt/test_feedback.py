"""Fluxos pedidos na revisão: mês, ano, ranking, identidade e edição de tempo."""
import unittest
from pathlib import Path
from unittest.mock import patch
from dataclasses import replace
from . import test_ui as _ui
from .test_data import Clock
from PySide6.QtCore import Qt, QPoint, QPointF
from PySide6.QtGui import QIcon, QWheelEvent
from PySide6.QtTest import QTest
from PySide6.QtWidgets import QLabel, QPushButton, QTableWidget
from horas_jogadas.zerados import Conclusao
from horas_jogadas_qt.completions_view import MONTH_ROLE, RECORD_ROLE

APP=_ui.APP


class FeedbackTests(unittest.TestCase):
    setUp=_ui.UiTests.setUp
    tearDown=_ui.UiTests.tearDown
    dialog=_ui.UiTests.dialog
    save_dialog=_ui.UiTests.save_dialog

    def key(self):
        return self.c.repo.jogos[0].id

    def test_month_headers_group_records_without_changing_ids(self):
        self.w.navigate('completed'); APP.processEvents()
        model=self.w.completed.model()
        headers=[model.index(i,0).data(MONTH_ROLE) for i in range(model.rowCount()) if model.index(i,0).data(MONTH_ROLE)]
        self.assertEqual(headers,['Janeiro','Fevereiro','Março'])
        self.assertEqual(model.rowCount(),len(self.c.zerados.registros)+3)
        for row,record in enumerate(self.w.completion_rows):
            self.w.completed.selectRow(row)
            self.assertEqual(self.w.selected(self.w.completed,self.w.completion_rows).id,record.id)
        for i in range(model.rowCount()):
            index=model.index(i,0)
            if index.data(MONTH_ROLE):
                self.assertFalse(model.flags(index)&Qt.ItemIsSelectable)

    def test_card_delete_and_undo_target_the_clicked_record_under_month_header(self):
        self.w.navigate('completed'); APP.processEvents()
        record=self.w.completion_rows[2]
        index=self.w.completed.model().index(self.w.completed.record_model.record_rows[2],0)
        self.w.completed.scrollTo(index); APP.processEvents()
        rect=self.w.completed.visualRect(index)
        delete_rect=next(rect for action,_,rect in self.w.completed.delegate.buttons(rect) if action=='delete')
        with patch.object(self.w,'confirm',return_value=True):
            QTest.mouseClick(self.w.completed.viewport(),Qt.LeftButton,pos=delete_rect.center())
        self.assertFalse(any(r.id==record.id for r in self.c.zerados.registros))
        self.w.undo_completion()
        restored=next(r for r in self.c.zerados.registros if r.id==record.id)
        self.assertEqual(restored,record)
        self.assertEqual(self.critical.call_count,0)

    def test_year_is_noneditable_popup_and_wheel_does_not_change_closed_picker(self):
        with self.c.transaction():
            self.c.zerados.guardar(Conclusao('Jogo antigo',2024,1,60))
        self.w.navigate('completed'); APP.processEvents()
        picker=self.w.year_picker
        self.assertFalse(picker.isEditable())
        self.assertIsNone(picker.lineEdit())
        picker.showPopup(); APP.processEvents()
        view=picker.view(); index=picker.model().index(picker.findData(2024),0)
        QTest.mouseClick(view.viewport(),Qt.LeftButton,pos=view.visualRect(index).center())
        APP.processEvents()
        self.assertEqual(self.w.year,2024)
        self.assertEqual([r.nome for r in self.w.completion_rows],['Jogo antigo'])
        picker=self.w.year_picker
        wheel=QWheelEvent(QPointF(15,15),QPointF(picker.mapToGlobal(QPoint(15,15))),QPoint(),QPoint(0,120),
                          Qt.NoButton,Qt.NoModifier,Qt.NoScrollPhase,False)
        APP.sendEvent(picker,wheel)
        self.assertEqual(self.w.year_picker.currentData(),2024)

    def test_brand_uses_original_application_icon(self):
        actual=self.w.findChild(QLabel,'appLogo').pixmap().toImage()
        expected=QIcon(str(Path(__file__).resolve().parent.parent/'icon.ico')).pixmap(36,36).toImage()
        self.assertFalse(actual.isNull())
        self.assertEqual(actual,expected)

    def test_stats_top_five_and_full_cards_have_filter_and_preserve_history_table(self):
        self.w.navigate('stats'); APP.processEvents()
        groups=self.w.top_ranking.groups
        self.assertEqual(len(groups),4)
        self.assertEqual(groups[0].nome,'Hollow Knight')
        self.assertEqual([g.total for g in groups],sorted([g.total for g in groups],reverse=True))
        self.assertIsNone(self.w.pages['stats'].findChild(QTableWidget))
        self.assertEqual(len(self.w.stat_group_cards),6)
        self.w.stats_status.setCurrentIndex(self.w.stats_status.findData('Jogando'))
        self.assertEqual(len(self.w.stat_group_cards),2)
        for key in self.w.stat_group_cards:
            self.assertEqual(self.c.repo.jogo_por_id(key).status,'Jogando')
        self.w.navigate('history')
        self.assertIsInstance(self.w.history,QTableWidget)

    def test_time_shortcuts_accumulate_and_save_an_hour(self):
        key=self.key()
        def fill(d):
            self.assertEqual([field.text() for field in d.fields],['0','0','0'])
            for minutes in (5,10,15,30):
                QTest.mouseClick(d.findChild(QPushButton,'add'+str(minutes)),Qt.LeftButton)
            self.assertEqual([field.text() for field in d.fields],['1','0','0'])
            self.save_dialog(d)
        self.dialog(fill,lambda:self.w.adjust_timer(key))
        self.assertEqual(self.c.timers[key].seconds(),3600)
        self.assertEqual(self.warning.call_count,0)
        self.assertEqual(self.critical.call_count,0)

    def test_signed_hours_minutes_seconds_and_negative_clamp(self):
        key=self.key()
        def add(d):
            for field,value in zip(d.fields,['1','2','3']): field.setText(value)
            self.save_dialog(d)
        self.dialog(add,lambda:self.w.adjust_timer(key))
        self.assertEqual(self.c.timers[key].seconds(),3723)
        def subtract(d):
            for field,value in zip(d.fields,['-2','0','0']): field.setText(value)
            self.save_dialog(d)
        self.dialog(subtract,lambda:self.w.adjust_timer(key))
        self.assertEqual(self.c.timers[key].seconds(),0)
        self.assertFalse(self.c.timers[key].pending)

    def test_paused_duration_is_available_and_adds_without_resuming(self):
        key=self.key(); timer=self.c.timers[key]; timer.clock=Clock()
        timer.start(); timer.clock.advance(20); timer.pause(); timer.clock.advance(75)
        def fill(d):
            self.assertIsNotNone(d.pause_label)
            QTest.mouseClick(d.use_pause,Qt.LeftButton)
            self.assertEqual([field.text() for field in d.fields],['0','1','15'])
            self.save_dialog(d)
        self.dialog(fill,lambda:self.w.adjust_timer(key))
        self.assertEqual(self.c.timers[key].seconds(),95)
        self.assertTrue(self.c.timers[key].pausado)
        self.assertEqual(sum(self.c.timers[key].dias.values()),95)

    def test_invalid_time_keeps_dialog_open_and_does_not_change_session(self):
        key=self.key()
        def invalid(d):
            d.fields[0].setText('-')
            self.save_dialog(d)
        self.dialog(invalid,lambda:self.w.adjust_timer(key))
        self.assertEqual(self.c.timers[key].seconds(),0)
        self.assertFalse(self.c.timers[key].pending)
        self.assertEqual(self.warning.call_count,1)
