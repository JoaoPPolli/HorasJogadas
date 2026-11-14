"""A retrospectiva de Zerados usa a lista, preservando tempos e datas desconhecidos."""
import tempfile
import unittest
from datetime import datetime
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch
from PySide6.QtCore import QTimer,QEvent
from PySide6.QtGui import QImage
from PySide6.QtWidgets import QApplication,QPushButton,QComboBox
from horas_jogadas.zerados import Conclusao
from horas_jogadas_qt.controller import Controller
from horas_jogadas_qt.insights import completed_recap,completed_years,recap_filename
from horas_jogadas_qt.recap_image import png_bytes,save_png
from horas_jogadas_qt.preview import inventory
from horas_jogadas_qt.phone_insights import PhoneInsights
from horas_jogadas_qt.remote_server import RemoteError
APP=QApplication.instance() or QApplication([])


class CompletedRecapTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();self.addCleanup(self.tmp.cleanup);self.folder=Path(self.tmp.name)
        self.c=Controller(self.folder);game=self.c.add_game('Fora da lista')
        self.c.repo.adicionar_sessao(game.id,game.nome,90000,datetime(2023,1,1),datetime(2023,1,2,1))
        self.c.timers[game.id].adjust(5000)
        for r in [Conclusao('Aventura',2025,1,1000,1,200,platina_concluida=True),
                  Conclusao('Expansão sem campanha conhecida',2025,1,platina_segundos=100,dlc=True),
                  Conclusao('Experiência',2025,1,300,tipo='experiencia'),
                  Conclusao('Aventura',2025,2,500,2),Conclusao('Tempo zero conhecido',2025,3,0)]:
            self.c.zerados.guardar(r)
        self.api=PhoneInsights(SimpleNamespace(window=SimpleNamespace(c=self.c,theme_name=lambda:'original'),workspace_revision=lambda:'revision'))

    def test_period_totals_categories_replays_and_read_only(self):
        before=inventory(self.folder);data=completed_recap(self.c,2025)
        self.assertEqual((data['games'],data['dlcs'],data['experiences'],data['platinum_completed']),(3,1,1,1))
        self.assertEqual((data['total_seconds'],data['campaign_seconds'],data['platinum_seconds']),(2100,1800,300))
        self.assertEqual((data['records'],data['without_time']),(5,1))
        self.assertTrue(data['has_time']);self.assertEqual([i['count'] for i in data['timeline'][:3]],[2,1,1])
        self.assertEqual(sum(i['count'] for i in data['timeline']),4)
        self.assertEqual(sum(i['name']=='Aventura' for i in data['recent']),2)
        unknown=next(i for i in data['recent'] if i['dlc']);self.assertIsNone(unknown['day']);self.assertTrue(unknown['partial']);self.assertEqual(unknown['seconds'],100)
        january=completed_recap(self.c,2025,1)
        self.assertEqual((january['records'],january['games'],january['total_seconds']),(3,1,1600))
        self.assertNotIn(2023,completed_years(self.c));self.assertIn(2025,completed_years(self.c))
        self.assertEqual(inventory(self.folder),before)

    def test_zero_unknown_empty_and_validation(self):
        unknown=Conclusao('Sem tempo e sem dia',2024,1);self.c.zerados.guardar(unknown)
        data=completed_recap(self.c,2024,1)
        self.assertEqual(data['games'],1);self.assertFalse(data['has_time'])
        self.assertEqual(data['without_time'],1);self.assertIsNone(data['recent'][0]['seconds']);self.assertIsNone(data['recent'][0]['day'])
        zero=completed_recap(self.c,2025,3);self.assertTrue(zero['has_time']);self.assertEqual(zero['without_time'],0)
        empty=completed_recap(self.c,2020);self.assertEqual(empty['records'],0);self.assertFalse(empty['recent'])
        for year,month in [(True,1),(2025,True),(1899,0),(2025,-1),(2025,13)]:
            with self.assertRaises(ValueError):completed_recap(self.c,year,month)

    def test_standalone_list_without_library_timers_or_session_history(self):
        standalone=SimpleNamespace(zerados=self.c.zerados)
        data=completed_recap(standalone,2025)
        self.assertEqual((data['games'],data['total_seconds']),(3,2100))
        api=PhoneInsights(SimpleNamespace(window=SimpleNamespace(c=standalone),workspace_revision=lambda:'revision'))
        self.assertEqual(api.view('recap',dict(year='2025',source='completed'))['records'],5)

    def test_png_themes_languages_unknown_and_empty(self):
        self.c.zerados.guardar(Conclusao('Título muito longo '+('aventura '*35),2024,1))
        before=inventory(self.folder)
        for theme in ['original','dark','light','violet']:
            for language in ['pt','en']:
                for year,month in [(2025,0),(2025,1),(2024,1),(2020,0)]:
                    data=completed_recap(self.c,year,month);image=QImage.fromData(png_bytes(data,theme,language))
                    self.assertEqual((image.width(),image.height()),(1080,1350))
        self.assertEqual(recap_filename(data),'HorasJogadas-Zerados-2020-00.png')
        self.assertEqual(inventory(self.folder),before)

    def test_phone_scope_survives_preview_export_and_rejects_invalid_source(self):
        values=dict(year='2025',month='1',source='completed');before=inventory(self.folder)
        data=self.api.view('recap',values);self.assertEqual(data['source'],'completed');self.assertEqual(data['total_seconds'],1600)
        preview=self.api.preview(values);self.assertEqual(preview['records'],3)
        raw,mime,name=self.api.export(values)
        self.assertEqual(raw,png_bytes(data));self.assertEqual(mime,'image/png');self.assertEqual(name,'HorasJogadas-Zerados-2025-01.png')
        self.assertEqual(name,preview['filename']);self.assertEqual(inventory(self.folder),before)
        for bad in [dict(values,source=None),dict(values,source='unknown'),dict(values,source=[]),dict(values,game_id='anything')]:
            for call in [lambda:self.api.view('recap',bad),lambda:self.api.preview(bad),lambda:self.api.export(bad)]:
                with self.assertRaises(RemoteError):call()

    def test_native_completed_button_uses_selected_year_and_exports_period(self):
        from horas_jogadas_qt.window import Window
        w=Window(self.c);w.timer.stop();w.year=2025;w.navigate('completed');w.show();errors=[]
        try:
            with patch('horas_jogadas_qt.insights_ui.save_png',wraps=save_png) as save,patch('horas_jogadas_qt.insights_ui.QFileDialog.getSaveFileName',return_value=(str(self.folder/'zerados.png'),'PNG')) as choose:
                def inspect():
                    dialog=APP.activeModalWidget()
                    try:
                        self.assertEqual(dialog.property('recapSource'),'completed')
                        self.assertEqual(dialog.findChild(QComboBox,'recapYear').currentData(),2025)
                        month=dialog.findChild(QComboBox,'recapMonth');month.setCurrentIndex(month.findData(1))
                        dialog.findChild(QPushButton,'recapExport').click()
                        data=save.call_args.args[1];self.assertEqual(data['source'],'completed')
                        self.assertEqual((data['year'],data['month'],data['total_seconds']),(2025,1,1600))
                        self.assertEqual(choose.call_args.args[2],'HorasJogadas-Zerados-2025-01.png')
                        self.assertFalse(QImage(str(self.folder/'zerados.png')).isNull())
                    except BaseException as error:errors.append(error)
                    finally:dialog.reject()
                QTimer.singleShot(0,inspect);w.findChild(QPushButton,'completedRecap').click()
                if errors:raise errors[0]
        finally:
            w.closing_allowed=True;w.close();APP.removeEventFilter(w);w.deleteLater();APP.sendPostedEvents(None,QEvent.DeferredDelete);APP.processEvents()
