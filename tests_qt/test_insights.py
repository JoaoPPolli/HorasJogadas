"""Períodos, imagens compartilháveis e detalhes sem alterar registros."""
import tempfile
import unittest
from datetime import datetime
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch
from PySide6.QtWidgets import QApplication
from PySide6.QtCore import QTimer,QEvent
from PySide6.QtGui import QImage
from horas_jogadas_qt.controller import Controller
from horas_jogadas_qt.insights import recap,game_details,available_years,recap_filename
from horas_jogadas_qt.recap_image import png_bytes,save_png
from horas_jogadas_qt.preview import inventory
from horas_jogadas.zerados import Conclusao
APP=QApplication.instance() or QApplication([])
class InsightsTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();self.addCleanup(self.tmp.cleanup);self.folder=Path(self.tmp.name)
        self.c=Controller(self.folder);self.game=self.c.add_game('Jogo muito legal')
        self.c.repo.adicionar_sessao(self.game.id,self.game.nome,7200,datetime(2024,12,31,23),datetime(2025,1,1,1))
        self.c.repo.adicionar_sessao(None,'Jogo antigo',1800,datetime(2025,1,5,13),datetime(2025,1,5,13,30))
        self.c.zerados.guardar(Conclusao(self.game.nome,2025,1,3600,jogo_id=self.game.id,platina_segundos=600,platina_concluida=True))
    def test_recap_splits_periods_and_never_double_counts_completion_hours(self):
        before=inventory(self.folder)
        self.assertEqual(recap(self.c,2024)['total_seconds'],3600)
        data=recap(self.c,2025,1)
        self.assertEqual(data['total_seconds'],5400);self.assertEqual(data['sessions'],2);self.assertEqual(data['games'],2);self.assertEqual(data['completed'],1)
        self.assertEqual(data['days'],2);self.assertEqual(recap(self.c,2025,2)['total_seconds'],0)
        self.assertEqual(inventory(self.folder),before)
    def test_details_keep_linked_completion_and_live_time_separate(self):
        self.c.timers[self.game.id].adjust(20)
        data=game_details(self.c,self.game.id)
        self.assertEqual(data['saved_seconds'],7200);self.assertEqual(data['total_seconds'],7220)
        self.assertEqual(data['session_count'],1);self.assertEqual(data['completions'][0]['platinum_seconds'],600)
        self.assertTrue(data['completions'][0]['platinum_completed'])
    def test_png_all_themes_empty_and_populated(self):
        for theme in ['original','dark','light','violet']:
            for year in [2025,2020]:
                image=QImage.fromData(png_bytes(recap(self.c,year),theme,'en'))
                self.assertFalse(image.isNull());self.assertEqual((image.width(),image.height()),(1080,1350))
        path=self.folder/'shared.png';save_png(path,recap(self.c,2025));self.assertFalse(QImage(str(path)).isNull())
    def test_phone_views_and_png_validate_period(self):
        from horas_jogadas_qt.phone_insights import PhoneInsights
        from horas_jogadas_qt.remote_server import RemoteError
        control=SimpleNamespace(window=SimpleNamespace(c=self.c,theme_name=lambda:'original'),workspace_revision=lambda:'revision')
        api=PhoneInsights(control)
        self.assertEqual(api.view('game',{'id':self.game.id})['id'],self.game.id)
        self.assertEqual(api.view('recap',{'year':'2025','month':'1'})['total_seconds'],5400)
        data,mime,name=api.export({'year':'2025','month':'1'});self.assertEqual(mime,'image/png');self.assertFalse(QImage.fromData(data).isNull())
        with self.assertRaises(RemoteError):api.view('recap',{'year':2025,'month':1.9})

    def test_native_game_page_timer_and_recap_dialog(self):
        from horas_jogadas_qt.window import Window
        from horas_jogadas_qt.insights_ui import show_recap
        from .test_data import Clock
        clock=Clock();self.c.timers[self.game.id].clock=clock
        w=Window(self.c);w.timer.stop();w.show()
        try:
            w.show_game(self.game.id);self.assertEqual(w.page,'game');self.assertEqual(w.detail_card.key,self.game.id)
            w.timer_action(self.game.id,'start');clock.advance(14);w.timer_action(self.game.id,'finish')
            self.assertEqual(game_details(self.c,self.game.id)['session_count'],2)
            errors=[]
            def inspect():
                dialog=APP.activeModalWidget()
                try:
                    from PySide6.QtWidgets import QLabel
                    self.assertFalse(dialog.findChild(QLabel,'recapPreview').pixmap().isNull())
                except BaseException as e:errors.append(e)
                dialog.reject()
            QTimer.singleShot(0,inspect);show_recap(w)
            if errors:raise errors[0]
        finally:
            w.closing_allowed=True;w.close();APP.removeEventFilter(w);w.deleteLater();APP.sendPostedEvents(None,QEvent.DeferredDelete);APP.processEvents()

    def test_period_validation(self):
        for year,month in [(2025,13),(True,1),(2025,-1)]:
            with self.assertRaises(ValueError):recap(self.c,year,month)

    def test_individual_filters_ids_completions_years_and_live_time(self):
        other=self.c.add_game(self.game.nome+' 2')
        other.nome=self.game.nome # Simula títulos iguais com IDs distintos em dados antigos.
        self.c.repo.adicionar_sessao(other.id,other.nome,9000,datetime(2023,5,1,10),datetime(2023,5,1,12,30))
        self.c.repo.adicionar_sessao(other.id,other.nome,600,datetime(2025,1,2,10),datetime(2025,1,2,10,10))
        self.c.repo.adicionar_sessao(None,self.game.nome,300,datetime(2025,1,2,11),datetime(2025,1,2,11,5))
        self.c.zerados.guardar(Conclusao(other.nome,2025,1,9000,jogo_id=other.id))
        self.c.timers[self.game.id].adjust(500)
        before=inventory(self.folder);data=recap(self.c,2025,1,self.game.id)
        self.assertEqual(data['game'],dict(id=self.game.id,name=self.game.nome))
        self.assertEqual(data['total_seconds'],3600);self.assertEqual(data['sessions'],1)
        self.assertEqual(data['average_seconds'],3600);self.assertEqual(data['longest_seconds'],3600)
        self.assertEqual(data['days'],1);self.assertEqual(data['completed'],1)
        self.assertEqual([item['id'] for item in data['top']],[self.game.id])
        self.assertEqual(len(data['timeline']),31);self.assertEqual(data['timeline'][0]['seconds'],3600)
        self.assertEqual(sum(item['seconds'] for item in data['timeline']),3600)
        self.assertNotIn(2023,available_years(self.c,self.game.id));self.assertIn(2024,available_years(self.c,self.game.id))
        self.assertEqual(inventory(self.folder),before)

    def test_individual_year_month_boundaries_empty_and_leap_day(self):
        key=self.game.id
        self.c.repo.adicionar_sessao(key,self.game.nome,7200,datetime(2024,2,29,23),datetime(2024,3,1,1))
        year=recap(self.c,2024,game_id=key);feb=recap(self.c,2024,2,key);march=recap(self.c,2024,3,key)
        self.assertEqual(len(year['timeline']),12);self.assertEqual(year['timeline'][1]['seconds'],3600)
        self.assertEqual(year['timeline'][2]['seconds'],3600);self.assertEqual(year['timeline'][11]['seconds'],3600)
        self.assertEqual(len(feb['timeline']),29);self.assertEqual(feb['timeline'][-1]['seconds'],3600)
        self.assertEqual(march['timeline'][0]['seconds'],3600)
        empty=recap(self.c,2020,game_id=key)
        for field in ['total_seconds','sessions','average_seconds','longest_seconds','days']:self.assertEqual(empty[field],0)
        self.assertTrue(all(item['seconds']==0 for item in empty['timeline']))
        for invalid in ['',False,'missing']:
            with self.assertRaises(ValueError):recap(self.c,2025,game_id=invalid)

    def test_individual_png_themes_languages_long_titles_and_safe_filename(self):
        self.game.nome='Jogo / Com: nome? muito comprido '+('e aventuras '*16)
        before=inventory(self.folder)
        for language in ['pt','en']:
            for theme in ['original','dark','light','violet']:
                for year,month in [(2025,0),(2025,1),(2020,2)]:
                    data=recap(self.c,year,month,self.game.id);raw=png_bytes(data,theme,language)
                    image=QImage.fromData(raw);self.assertEqual((image.width(),image.height()),(1080,1350))
                    self.assertNotEqual(raw,png_bytes(recap(self.c,year,month),theme,language))
        filename=recap_filename(data)
        self.assertTrue(filename.startswith('HorasJogadas-Jogo - Com- nome-'))
        self.assertFalse(any(c in filename for c in '<>:"/\\|?*'));self.assertLess(len(filename),120)
        self.game.nome='🎮'*80
        self.assertLess(len(recap_filename(recap(self.c,2025,game_id=self.game.id)).encode('utf-8')),200)
        self.assertEqual(inventory(self.folder),before)

    def test_phone_individual_view_preview_and_export_keep_scope(self):
        from horas_jogadas_qt.phone_insights import PhoneInsights
        from horas_jogadas_qt.remote_server import RemoteError
        api=PhoneInsights(SimpleNamespace(window=SimpleNamespace(c=self.c,theme_name=lambda:'original'),workspace_revision=lambda:'revision'))
        values=dict(year='2025',month='1',game_id=self.game.id)
        data=api.view('recap',values);self.assertEqual(data['total_seconds'],3600)
        preview=api.preview(values);self.assertEqual(preview['game']['id'],self.game.id)
        raw,mime,name=api.export(values)
        self.assertEqual(name,preview['filename']);self.assertIn(self.game.nome,name)
        self.assertEqual(raw,png_bytes(data,'original'));self.assertEqual(mime,'image/png')
        self.assertEqual(api.view('recap',dict(year='2025',month='1'))['total_seconds'],5400)
        for invalid in ['',None,True,'missing']:
            bad=dict(values,game_id=invalid)
            for call in [lambda:api.view('recap',bad),lambda:api.preview(bad),lambda:api.export(bad)]:
                with self.assertRaises(RemoteError):call()

    def test_native_individual_button_preview_period_and_export(self):
        from PySide6.QtWidgets import QComboBox,QPushButton
        from horas_jogadas_qt.window import Window
        w=Window(self.c);w.timer.stop();w.show();errors=[]
        try:
            w.show_game(self.game.id)
            with patch('horas_jogadas_qt.insights_ui.recap',wraps=recap) as query,patch('horas_jogadas_qt.insights_ui.save_png',wraps=save_png) as save,patch('horas_jogadas_qt.insights_ui.QFileDialog.getSaveFileName',return_value=(str(self.folder/'individual.png'),'PNG')) as chooser:
                def inspect():
                    dialog=APP.activeModalWidget()
                    try:
                        self.assertEqual(dialog.property('gameId'),self.game.id)
                        year=dialog.findChild(QComboBox,'recapYear');year.setCurrentIndex(year.findData(2025))
                        month=dialog.findChild(QComboBox,'recapMonth');month.setCurrentIndex(month.findData(1))
                        self.assertEqual(query.call_args.args[-1],self.game.id)
                        dialog.findChild(QPushButton,'recapExport').click()
                        self.assertEqual(save.call_args.args[1]['total_seconds'],3600)
                        self.assertEqual(save.call_args.args[1]['game']['id'],self.game.id)
                        self.assertIn(self.game.nome,chooser.call_args.args[2])
                        self.assertFalse(QImage(str(self.folder/'individual.png')).isNull())
                    except BaseException as error:errors.append(error)
                    finally:dialog.reject()
                QTimer.singleShot(0,inspect);w.findChild(QPushButton,'gameRecap').click()
                if errors:raise errors[0]
        finally:
            w.closing_allowed=True;w.close();APP.removeEventFilter(w);w.deleteLater();APP.sendPostedEvents(None,QEvent.DeferredDelete);APP.processEvents()
