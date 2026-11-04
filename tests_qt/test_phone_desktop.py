"""Integração do controle completo com revisões, timers e atualização do PC."""
import json
import tempfile
import shutil
import time
import unittest
from pathlib import Path
from unittest.mock import patch

from PySide6.QtCore import QEvent
from PySide6.QtWidgets import QApplication
from app_qt import seed_demo
from horas_jogadas_qt.controller import Controller
from horas_jogadas_qt.window import Window
from horas_jogadas_qt.remote_server import RemoteError
from horas_jogadas_qt.updates import Release
from .test_data import Clock

APP = QApplication.instance() or QApplication([])


class PhoneDesktopTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory(); self.addCleanup(self.tmp.cleanup)
        self.folder = Path(self.tmp.name); seed_demo(self.folder)
        self.c = Controller(self.folder); self.w = Window(self.c)
        self.w.timer.stop(); self.w.show(); APP.processEvents()
        self.control = self.w.phone_control
        self.key = self.c.repo.jogos[0].id
        self.clock = Clock(); self.c.timers[self.key].clock = self.clock

    def tearDown(self):
        self.w.closing_allowed = True; self.w.close()
        APP.removeEventFilter(self.w); self.w.deleteLater()
        APP.sendPostedEvents(None, QEvent.DeferredDelete); APP.processEvents()

    def command(self, action, **values):
        body = dict(action=action, workspace_revision=self.control.workspace_revision(), **values)
        if action.startswith(('game_', 'timer_')):
            key = body.setdefault('game_id', self.key)
            body.setdefault('revision', self.control.revision(self.c.repo.jogo_por_id(key), self.c.timers[key]))
        return self.control.command(body)

    def test_seeded_profile_and_records_views_are_json_serializable(self):
        before = self.control.workspace_revision()
        json.dumps(self.control.snapshot())
        for page in ('history', 'stats', 'completed', 'settings', 'backups', 'devices', 'updates'):
            json.dumps(self.control.view(page, {}))
        self.assertEqual(before, self.control.workspace_revision())
        self.c.timers[self.key].start(); running = self.control.workspace_revision()
        self.clock.advance(10)
        self.assertEqual(running, self.control.workspace_revision())

    def test_game_rename_status_and_manual_order_use_pc_domain(self):
        self.command('game_rename', name='Novo nome — controle')
        self.assertEqual(self.c.repo.jogo_por_id(self.key).nome, 'Novo nome — controle')
        self.command('game_status', status='Zerado')
        self.assertEqual(self.c.repo.jogo_por_id(self.key).status, 'Zerado')
        self.command('game_move', position='bottom')
        self.assertEqual(self.c.repo.jogos[-1].id, self.key)
        self.command('library_order', order='recente')
        self.assertEqual(self.control.snapshot()['library_order'], 'recente')
        self.assertEqual(json.loads((self.folder/'config.json').read_text())['ordenacao'], 'recente')

    def test_timer_adjust_pause_and_pending_delete_keep_saved_history(self):
        timer = self.c.timers[self.key]; timer.start(); self.clock.advance(20); timer.pause()
        self.clock.advance(30)
        self.command('timer_adjust', seconds=300)
        self.assertTrue(timer.pausado); self.assertEqual(timer.seconds(), 320)
        self.command('timer_count_pause', seconds=10)
        self.assertTrue(timer.rodando); self.assertEqual(timer.seconds(), 330)
        before = len(self.c.repo.sessoes)
        with self.assertRaises(RemoteError):self.command('game_delete', confirmed=True)
        self.assertIn(self.key, self.c.timers)
        self.command('game_delete', confirmed=True, pending='save')
        self.assertNotIn(self.key, self.c.timers)
        self.assertEqual(len(self.c.repo.sessoes), before+1)
        self.assertEqual(self.c.repo.sessoes[-1].segundos, 330)

    def test_stale_workspace_or_timer_revision_never_overwrites_pc_change(self):
        body = dict(action='game_rename', game_id=self.key, name='Stale phone edit',
                    workspace_revision=self.control.workspace_revision(),
                    revision=self.control.revision(self.c.repo.jogo_por_id(self.key), self.c.timers[self.key]))
        self.w.perform(lambda:self.c.repo.renomear_jogo(self.key,'PC ganhou'), refresh=False)
        with self.assertRaises(RemoteError) as error:self.control.command(body)
        self.assertEqual(error.exception.code, 'conflict')
        self.assertEqual(self.c.repo.jogo_por_id(self.key).nome, 'PC ganhou')

    def test_record_delete_and_undo_share_desktop_stack_after_commit(self):
        record = self.c.zerados.registros[0]
        before = len(self.c.zerados.registros)
        self.command('completion_delete', id=record.id, confirmed=True)
        self.assertEqual(len(self.c.zerados.registros), before-1)
        self.assertTrue(self.control.view('completed', {'year':str(record.ano)})['can_undo'])
        self.command('completion_undo')
        self.assertEqual(len(self.c.zerados.registros), before)
        self.assertEqual(self.w.deleted_completions, [])

    def test_starting_network_job_does_not_invalidate_its_own_revision(self):
        before = self.control.workspace_revision()
        with patch.object(self.control.management, 'execute', return_value={'job_id':'synthetic'}):
            self.command('art_import', kind='cover', selected=[])
        self.assertEqual(before, self.control.workspace_revision())

    def test_source_build_cannot_launch_installer(self):
        with patch('horas_jogadas_qt.phone_desktop.sys.frozen', False, create=True):
            self.assertFalse(self.control.view('updates', {})['can_install'])
            with self.assertRaises(RemoteError) as error:self.command('update_download')
            self.assertEqual(error.exception.code, 'source_build')

    def test_pc_folder_and_isolated_review_copy_are_explicit_and_bounded(self):
        with patch('horas_jogadas_qt.phone_desktop.QDesktopServices.openUrl', return_value=True) as opened:
            self.command('pc_open_data')
            self.assertEqual(Path(opened.call_args.args[0].toLocalFile()), self.folder)
        with self.assertRaises(RemoteError):self.command('pc_create_review')
        result = self.command('pc_create_review', confirmed=True)
        target = self.folder.parent / result['name']
        self.addCleanup(lambda: shutil.rmtree(target, ignore_errors=True))
        self.assertTrue((target/'.horasjogadas-preview.json').is_file())
        self.assertTrue((target/'cronometros.json').is_file())
        self.assertNotEqual(target, self.folder)

    def test_pending_recovery_has_explicit_save_and_discard_choices(self):
        before = len(self.c.repo.sessoes)
        timer = self.c.timers[self.key]; timer.adjust(25); self.c.save_pending(); timer.reset()
        self.w.pending_recovery = True
        self.command('pending_recover', choice='save', confirmed=True)
        self.assertFalse(self.w.pending_recovery)
        self.assertEqual(len(self.c.repo.sessoes), before+1)
        self.assertEqual(self.c.repo.sessoes[-1].segundos, 25)
        self.assertFalse((self.folder/'em_andamento.json').exists())
        timer.adjust(15); self.c.save_pending(); timer.reset(); self.w.pending_recovery = True
        self.command('pending_recover', choice='discard', confirmed=True)
        self.assertEqual(len(self.c.repo.sessoes), before+1)
        self.assertFalse(self.w.pending_recovery)

    def test_update_check_runs_async_and_cannot_mutate_timers(self):
        release = Release('99.0.0','Synthetic notes','https://example.invalid',1,'https://example.invalid','test')
        timer = self.c.timers[self.key]; timer.start(); before = self.control.workspace_revision()
        with patch('horas_jogadas_qt.phone_desktop.updates.check_release', return_value=release):
            self.control.query({'query':'update_check'})
            deadline = time.monotonic()+5
            while self.control.desktop.task and time.monotonic()<deadline:
                APP.processEvents(); time.sleep(.001)
        self.assertIsNone(self.control.desktop.task)
        self.assertEqual(self.control.view('updates', {})['available']['version'], '99.0.0')
        self.assertEqual(before, self.control.workspace_revision()); self.assertTrue(timer.rodando)

    def test_update_install_requires_explicit_confirmation_and_saves_before_handoff(self):
        timer = self.c.timers[self.key]; timer.start(); self.clock.advance(12)
        self.control.desktop.package = self.folder/'fake-package'
        with patch('horas_jogadas_qt.phone_desktop.sys.frozen', True, create=True), \
             patch('horas_jogadas_qt.phone_desktop.updates.launch_update') as launch, \
             patch('horas_jogadas_qt.phone_desktop.QTimer.singleShot') as later:
            with self.assertRaises(RemoteError):self.command('update_install', pending='save')
            launch.assert_not_called()
            self.command('update_install', confirmed=True, pending='save')
            launch.assert_called_once(); later.assert_any_call(1200, self.w.close)
            self.assertEqual(sum(call.args[0] == 1200 for call in later.call_args_list), 1)
        self.assertFalse(timer.pending); self.assertEqual(self.c.repo.sessoes[-1].segundos, 12)
        self.assertTrue(self.control.desktop.handed_off)
