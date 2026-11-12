"""Cálculo sem duplicação e persistência compatível do marco da platina."""
import json
import tempfile
import unittest
from dataclasses import replace
from pathlib import Path
from PySide6.QtCore import QTimer,QEvent
from PySide6.QtWidgets import QApplication,QLineEdit,QPushButton,QCheckBox,QDialogButtonBox
from horas_jogadas.zerados import Conclusao,RepositorioZerados
from horas_jogadas_qt.controller import Controller
from horas_jogadas_qt.window import Window
from horas_jogadas_qt.platinum import calculate_extra,matched_game,ExtraTimeError
APP=QApplication.instance() or QApplication([])

class PlatinumTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();self.addCleanup(self.tmp.cleanup);self.folder=Path(self.tmp.name)
        self.c=Controller(self.folder);self.game=self.c.add_game('Fallout 3');self.timer=self.c.timers[self.game.id]
        self.timer.adjust(20*3600+35*60);self.record=Conclusao('Fallout 3',2024,1,16*3600,platina_segundos=2*3600)
        self.c.zerados.guardar(self.record)
    def test_difference_repeated_click_and_finished_milestone(self):
        self.assertEqual(matched_game(self.c,self.record),self.game.id)
        for _ in range(2):self.assertEqual(calculate_extra(self.c,self.record,self.game.id,16*3600)['seconds'],4*3600+35*60)
        locked=replace(self.record,platina_segundos=4*3600+35*60,platina_concluida=True,jogo_id=self.game.id)
        self.c.zerados.guardar(locked);self.timer.adjust(3*3600)
        with self.assertRaisesRegex(ExtraTimeError,'platinum_locked'):calculate_extra(self.c,locked,self.game.id,16*3600)
        self.assertEqual(self.c.zerados.registros[0].platina_segundos,4*3600+35*60)
        restored=RepositorioZerados(str(self.folder)).registros[0];self.assertTrue(restored.platina_concluida);self.assertEqual(restored.jogo_id,self.game.id)
        data=json.loads((self.folder/'zerados.json').read_text());raw=data['registros'][0]
        self.assertNotIn('platina_concluida',raw);self.assertNotIn('jogo_id',raw)
        self.assertEqual(data['platinas_concluidas'],[self.record.id])
    def test_missing_counter_duration_low_total_and_multiple_playthroughs_are_safe(self):
        for game,base,error in [(None,10,'platinum_need_game'),(self.game.id,None,'platinum_need_duration'),(self.game.id,1000000,'platinum_less')]:
            with self.assertRaisesRegex(ExtraTimeError,error):calculate_extra(self.c,self.record,game,base)
        self.c.zerados.guardar(Conclusao('Fallout 3',2024,2,3600,jogo_id=self.game.id))
        with self.assertRaisesRegex(ExtraTimeError,'platinum_multiple'):calculate_extra(self.c,self.record,self.game.id,16*3600)
        self.assertEqual(self.c.zerados.registros[0].platina_segundos,7200)
    def test_legacy_record_loads_and_ambiguous_names_do_not_auto_link(self):
        data=json.loads((self.folder/'zerados.json').read_text());data.pop('platinas_concluidas');data.pop('jogos_vinculados')
        (self.folder/'zerados.json').write_text(json.dumps(data))
        legacy=RepositorioZerados(str(self.folder)).registros[0]
        self.assertFalse(legacy.platina_concluida);self.assertIsNone(legacy.jogo_id)
        other=self.c.add_game('Other');other.nome='Fallout 3';self.assertIsNone(matched_game(self.c,legacy))
    def test_native_button_fills_once_and_saves_only_completion(self):
        w=Window(self.c);w.timer.stop();w.show();errors=[]
        def interact():
            d=APP.activeModalWidget()
            try:
                extra=d.findChild(QLineEdit,'completionPlatinum');button=d.findChild(QPushButton,'calculatePlatinum');done=d.findChild(QCheckBox,'platinumDone')
                button.click();self.assertEqual(extra.text(),'4h35m00s')
                button.click();self.assertEqual(extra.text(),'4h35m00s')
                done.setChecked(True);self.assertFalse(button.isEnabled())
                d.findChild(QDialogButtonBox).button(QDialogButtonBox.Save).click()
            except BaseException as e:errors.append(e);d.reject()
        QTimer.singleShot(0,interact)
        try:
            w.edit_completion(self.record)
            if errors:raise errors[0]
            saved=self.c.zerados.registros[0];self.assertEqual(saved.segundos,16*3600);self.assertEqual(saved.platina_segundos,4*3600+35*60);self.assertTrue(saved.platina_concluida)
            self.assertEqual(int(self.timer.seconds()),20*3600+35*60);self.assertEqual(self.c.repo.sessoes,[])
        finally:
            w.closing_allowed=True;w.close();APP.removeEventFilter(w);w.deleteLater();APP.sendPostedEvents(None,QEvent.DeferredDelete);APP.processEvents()
