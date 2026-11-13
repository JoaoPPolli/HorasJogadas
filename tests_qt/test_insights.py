"""Períodos, imagens compartilháveis e detalhes sem alterar registros."""
import tempfile
import unittest
from datetime import datetime
from pathlib import Path
from types import SimpleNamespace
from PySide6.QtWidgets import QApplication
from PySide6.QtCore import QTimer,QEvent
from PySide6.QtGui import QImage
from horas_jogadas_qt.controller import Controller
from horas_jogadas_qt.insights import recap,game_details
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
