"""Abertura/fechamento, controle manual e leitura real de processos isolados."""
import subprocess
import sys
import tempfile
import unittest
import time
import os
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch
from threading import Event
from PySide6.QtWidgets import QApplication
from horas_jogadas_qt.controller import Controller
from horas_jogadas_qt.window import Window
from horas_jogadas_qt.detection import save_profile,scan_processes
from horas_jogadas_qt import preferences
from .test_data import Clock
APP=QApplication.instance() or QApplication([])
class DetectionTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();self.addCleanup(self.tmp.cleanup);self.c=Controller(self.tmp.name)
        self.game=self.c.add_game('Process game');self.clock=Clock();self.c.timers[self.game.id].clock=self.clock
        self.w=Window(self.c);self.w.timer.stop();self.service=self.w.game_detection
    def tearDown(self):
        self.w.closing_allowed=True;self.w.close();APP.removeEventFilter(self.w);self.w.deleteLater();APP.processEvents()
    def sample(self,active=True,unknown=False):
        self.service.apply(dict(found={self.game.id:{(42,123)} if active else set()},unknown={self.game.id} if unknown else set(),conflicts=set()))
    def test_automatic_session_saves_once_after_confirmed_close(self):
        self.sample();self.clock.advance(37)
        self.assertTrue(self.c.timers[self.game.id].rodando)
        self.sample(False);self.assertEqual(len(self.c.repo.sessoes),0)
        self.sample(False);self.assertEqual(len(self.c.repo.sessoes),1)
        self.assertEqual(self.c.repo.sessoes[0].segundos,37)
        self.sample(False);self.assertEqual(len(self.c.repo.sessoes),1)
    def test_manual_pause_and_finish_are_not_overridden(self):
        self.sample();self.clock.advance(10);self.c.timers[self.game.id].pause();self.sample()
        self.assertFalse(self.c.timers[self.game.id].rodando)
        self.c.finish(self.game.id);self.sample();self.assertFalse(self.c.timers[self.game.id].rodando)
        self.sample(False);self.sample(False);self.sample();self.assertTrue(self.c.timers[self.game.id].rodando)
    def test_manually_started_session_and_unreadable_scan_are_preserved(self):
        self.c.timers[self.game.id].start();self.sample();self.clock.advance(12);self.sample(False);self.sample(False)
        self.assertTrue(self.c.timers[self.game.id].rodando);self.assertEqual(self.c.repo.sessoes,[])
        self.c.timers[self.game.id].reset();self.service.present.clear();self.sample();self.sample(False,True);self.sample(False,True)
        self.assertTrue(self.c.timers[self.game.id].rodando)
    def test_adjusting_owned_timer_keeps_automatic_finish(self):
        self.sample();self.clock.advance(10);self.c.timers[self.game.id].adjust(30)
        self.sample(False);self.sample(False)
        self.assertEqual(self.c.repo.sessoes[0].segundos,40)

    def test_other_profile_changes_and_reset_preserve_ownership(self):
        first={self.game.id:dict(executable='/game/first.exe',mode='path')}
        self.service.reconcile(first);self.sample();self.clock.advance(9)
        self.service.reconcile(dict(first,another=dict(executable='/game/other.exe',mode='path')))
        self.service.reset();self.sample(False);self.sample(False)
        self.assertEqual(self.c.repo.sessoes[0].segundos,9)

    def test_profile_is_opt_in_and_exact_duplicates_rejected(self):
        self.assertFalse(self.service.timer.isActive());self.assertEqual(self.service.configuration(),{})
        save_profile(self.w,self.game.id,True,str(Path(self.tmp.name)/'game.exe'),'path')
        self.assertTrue(preferences.read(self.c.folder)['detection_enabled'])
        other=self.c.add_game('Other')
        with self.assertRaises(ValueError):save_profile(self.w,other.id,True,str(Path(self.tmp.name)/'game.exe'),'path')
        preferences.save(self.c.folder,detection_enabled=False);self.assertEqual(self.service.configuration(),{})
    def test_wine_name_match_ignores_executable_arguments_for_other_apps(self):
        process=SimpleNamespace(info=dict(pid=42,name='wine64',exe='/usr/bin/wine64',create_time=123),cmdline=lambda:['wine64',r'C:\Games\Game.exe'])
        values={self.game.id:dict(executable='Game.exe',mode='name')}
        sample=scan_processes(values,{},Event(),iterator=lambda **kwargs:[process])
        self.assertEqual(sample['found'][self.game.id],{(42,123)})
        process.cmdline=lambda:['wine64',r'C:\Other.exe',r'C:\Games\Game.exe']
        self.assertFalse(scan_processes(values,{},Event(),iterator=lambda **kwargs:[process])['found'][self.game.id])
    def test_ambiguous_process_never_starts_two_timers(self):
        process=SimpleNamespace(info=dict(pid=42,name='Game.exe',exe='/games/Game.exe',create_time=123))
        values={key:dict(executable='Game.exe',mode='name') for key in [self.game.id,'other']}
        sample=scan_processes(values,{},Event(),iterator=lambda **kwargs:[process])
        self.assertEqual(sample['conflicts'],{self.game.id,'other'});self.service.apply(sample)
        self.assertFalse(self.c.timers[self.game.id].pending)
    def test_disabling_releases_ownership_without_stopping_timer(self):
        self.service.reconcile({self.game.id:dict(executable='/games/Game.exe',mode='path')});self.sample()
        self.service.reconcile({});self.sample(False);self.sample(False)
        self.assertTrue(self.c.timers[self.game.id].rodando);self.assertEqual(self.c.repo.sessoes,[])
    def test_save_failure_can_be_retried_without_duplicating_history(self):
        self.sample();self.clock.advance(11);self.sample(False)
        with patch.object(self.w,'perform',return_value=False):self.sample(False)
        self.assertTrue(self.service.failed);self.assertEqual(self.c.repo.sessoes,[])
        self.service.reset();self.sample(False)
        self.assertEqual(len(self.c.repo.sessoes),1);self.assertEqual(self.c.repo.sessoes[0].segundos,11)

    def test_real_process_open_close_is_saved(self):
        child=subprocess.Popen([sys.executable,'-c','import time;time.sleep(20)'])
        values={self.game.id:dict(executable=sys.executable,mode='path')}
        def only_child():
            sample=scan_processes(values,{},Event())
            sample['found'][self.game.id]={item for item in sample['found'][self.game.id] if item[0]==child.pid}
            return sample
        try:
            self.service.apply(only_child());self.assertTrue(self.c.timers[self.game.id].rodando)
            self.clock.advance(18);child.terminate();child.wait(timeout=5)
            self.service.apply(only_child());self.service.apply(only_child())
            self.assertEqual(self.c.repo.sessoes[0].segundos,18)
        finally:
            if child.poll() is None:child.terminate();child.wait(timeout=5)

    @unittest.skipUnless(sys.platform.startswith('linux'),'Linux exec lifecycle')
    def test_same_pid_executes_game_after_launcher(self):
        child=subprocess.Popen([sys.executable,'-c',"import os,time;time.sleep(1);os.execl('/bin/sleep','sleep','10')"])
        values={self.game.id:dict(executable='/bin/sleep',mode='path')}
        try:
            first=scan_processes(values,{},Event())
            self.assertNotIn(child.pid,{pid for pid,_ in first['found'][self.game.id]})
            end=time.monotonic()+5;found=False
            while time.monotonic()<end:
                sample=scan_processes(values,{},Event())
                if child.pid in {pid for pid,_ in sample['found'][self.game.id]}:found=True;break
                time.sleep(.05)
            self.assertTrue(found,'Launcher exec was hidden by cached process metadata')
        finally:
            if child.poll() is None:child.terminate();child.wait(timeout=5)

    def test_real_process_path_scan(self):
        child=subprocess.Popen([sys.executable,'-c','import time;time.sleep(20)'])
        try:
            values={self.game.id:dict(executable=sys.executable,mode='path')}
            sample=scan_processes(values,{},Event())
            self.assertIn(child.pid,{pid for pid,_ in sample['found'][self.game.id]})
        finally:child.terminate();child.wait(timeout=5)
