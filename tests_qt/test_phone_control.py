"""Comandos do celular usam o mesmo domínio e preservam os registros existentes."""
import os
os.environ.setdefault('QT_QPA_PLATFORM', 'offscreen')
import tempfile
import unittest
from datetime import datetime
from pathlib import Path
from unittest.mock import PropertyMock, patch

from PySide6.QtCore import QEvent
from PySide6.QtWidgets import QApplication, QDialog, QMessageBox
from horas_jogadas import i18n
from horas_jogadas.storage import Repositorio
from horas_jogadas_qt.controller import Controller
from horas_jogadas_qt import preferences
from horas_jogadas_qt.phone_control import PhoneControlCard
from horas_jogadas_qt.preview import inventory, prepare_preview
from horas_jogadas_qt.remote_server import RemoteError
from horas_jogadas_qt.theme import PALETTES, apply_theme
from horas_jogadas_qt.window import Window
from .test_data import Clock

APP = QApplication.instance() or QApplication([])
CORE_FILES = ('cronometros.json', 'registros.json', 'em_andamento.json', 'config.json', 'zerados.json')


class PhoneControlTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        self.source = self.root / 'source'
        self.source.mkdir()
        repo = Repositorio(str(self.source), config_legado='')
        game = repo.adicionar_jogo('Jogo do console')
        repo.adicionar_sessao(game.id, game.nome, 120, None, datetime(2024, 1, 1, 20))
        self.before_source = inventory(self.source)
        self.folder = prepare_preview(self.source, self.root / 'review')
        self.c = Controller(self.folder)
        self.key = game.id
        self.clock = Clock()
        self.c.timers[self.key].clock = self.clock
        preferences.save(self.folder, theme='original')
        i18n.definir_idioma('pt')
        apply_theme(APP, 'original')
        self.w = Window(self.c)
        self.w.timer.stop()
        self.w.show()
        APP.processEvents()
        self.phone = self.w.phone_control
        self.critical = patch.object(QMessageBox, 'critical', return_value=QMessageBox.Ok).start()
        self.warning = patch.object(QMessageBox, 'warning', return_value=QMessageBox.Ok).start()
        self.addCleanup(patch.stopall)

    def tearDown(self):
        self.w.closing_allowed = True
        self.w.close()
        APP.removeEventFilter(self.w)
        self.w.deleteLater()
        APP.sendPostedEvents(None, QEvent.DeferredDelete)
        APP.processEvents()
        self.assertEqual(inventory(self.source), self.before_source, 'O controle remoto não pode escrever na origem da cópia')
        self.assertEqual(self.critical.call_count, 0, 'Erros remotos devem voltar ao celular, sem diálogos bloqueantes no PC')
        i18n.definir_idioma('pt')
        self.tmp.cleanup()

    def game_state(self):
        return next(g for g in self.phone.snapshot()['games'] if g['id'] == self.key)

    def command(self, action, **extra):
        body = {'action': action, 'game_id': self.key, 'revision': self.game_state()['revision']}
        body.update(extra)
        return self.phone.command(body)

    def assert_remote_error(self, callback, code):
        with self.assertRaises(RemoteError) as raised:
            callback()
        self.assertEqual(raised.exception.code, code)

    def core_bytes(self):
        return {name: (self.folder / name).read_bytes() if (self.folder / name).exists() else None for name in CORE_FILES}

    def test_snapshot_matches_theme_language_totals_and_has_no_pairing_credentials(self):
        state = self.phone.snapshot()
        self.assertEqual(state['language'], 'pt')
        self.assertEqual(state['theme'], 'original')
        self.assertEqual(state['palette']['accent'], PALETTES['original'][6])
        game = self.game_state()
        self.assertEqual(game['name'], 'Jogo do console')
        self.assertEqual(game['total_seconds'], 120)
        self.assertEqual(game['seconds'], 0)
        self.assertFalse(game['running'])
        self.assertFalse(game['pending'])
        self.assertFalse(state['pending_recovery'])
        for key in ('pairing_code', 'pairing_url', 'token', 'secret'):
            self.assertNotIn(key, state)

    def test_timer_revision_is_stable_while_ticking_and_changes_for_pc_actions(self):
        initial = self.game_state()['revision']
        self.w.timer_action(self.key, 'start')
        running = self.game_state()['revision']
        self.assertNotEqual(initial, running)
        self.clock.advance(15)
        self.assertEqual(self.game_state()['revision'], running)
        self.assertEqual(self.game_state()['seconds'], 15)
        self.w.timer_action(self.key, 'pause')
        self.assertNotEqual(self.game_state()['revision'], running)

    def test_start_pause_resume_and_finish_share_existing_timer_and_save_once(self):
        identity = id(self.c.timers[self.key])
        card_identity = id(self.w.cards[self.key])
        start = self.command('start')
        self.assertTrue(start['ok'])
        self.clock.advance(20)
        self.command('pause')
        self.assertTrue(self.c.timers[self.key].pausado)
        self.clock.advance(90)
        self.command('start')
        self.clock.advance(22)
        self.assertEqual(id(self.w.cards[self.key]), card_identity)
        finish_body = {'action': 'finish', 'game_id': self.key, 'revision': self.game_state()['revision']}
        self.phone.command(finish_body)
        self.assertEqual(id(self.c.timers[self.key]), identity)
        self.assertFalse(self.c.timers[self.key].pending)
        saved = Repositorio(str(self.folder), config_legado='').sessoes
        self.assertEqual([s.segundos for s in saved], [120, 42])
        self.assertEqual(self.game_state()['total_seconds'], 162)
        self.assert_remote_error(lambda: self.phone.command(finish_body), 'conflict')
        self.assertEqual(len(self.c.repo.sessoes), 2)

    def test_stale_phone_command_cannot_finish_a_new_session_started_on_pc(self):
        self.command('start')
        self.clock.advance(11)
        old = {'action': 'finish', 'game_id': self.key, 'revision': self.game_state()['revision']}
        self.w.timer_action(self.key, 'finish')
        self.w.timer_action(self.key, 'start')
        before = self.core_bytes()
        self.assert_remote_error(lambda: self.phone.command(old), 'conflict')
        self.assertTrue(self.c.timers[self.key].rodando)
        self.assertEqual(self.core_bytes(), before)

    def test_failed_finish_rolls_back_files_and_timer_without_blocking_dialog(self):
        self.command('start')
        self.clock.advance(27)
        before = self.core_bytes()
        revision = self.game_state()['revision']
        with patch.object(self.c, 'save_pending', side_effect=OSError('Disco cheio simulado')):
            self.assert_remote_error(lambda: self.command('finish'), 'storage')
        self.assertEqual(self.core_bytes(), before)
        self.assertEqual(self.game_state()['revision'], revision)
        self.assertTrue(self.c.timers[self.key].rodando)
        self.assertEqual(len(self.c.repo.sessoes), 1)
        self.assertFalse((self.folder / '.qt-transaction.json').exists())

    def test_add_game_uses_existing_name_validation_and_preserves_original_records(self):
        before_sessions = (self.folder / 'registros.json').read_bytes()
        result = self.phone.command({'action': 'add', 'name': '  Jogo   novo  '})
        self.assertTrue(result['ok'])
        self.assertEqual(self.c.repo.jogos[0].nome, 'Jogo novo')
        self.assertIn(self.c.repo.jogos[0].id, self.c.timers)
        for name in ('', '   ', 'jogo novo'):
            with self.subTest(name=name):
                self.assert_remote_error(lambda: self.phone.command({'action': 'add', 'name': name}), 'invalid')
        self.assertEqual((self.folder / 'registros.json').read_bytes(), before_sessions)
        self.assertEqual(len(self.c.repo.jogos), 2)

    def test_unknown_actions_fields_and_missing_game_do_not_mutate_data(self):
        before = self.core_bytes()
        requests = [
            {'action': 'delete', 'game_id': self.key},
            {'action': 'start', 'game_id': self.key},
            {'action': 'start', 'game_id': self.key, 'revision': self.game_state()['revision'], 'path': '/tmp/other'},
            {'action': 'add', 'name': 'Unwanted', 'extra': True},
        ]
        for body in requests:
            with self.subTest(body=body), self.assertRaises(RemoteError):
                self.phone.command(body)
        self.assertEqual(self.core_bytes(), before)
        self.assertEqual(len(self.c.repo.jogos), 1)
        self.assertFalse(self.c.timers[self.key].pending)

    def test_pending_recovery_and_modal_dialog_prevent_remote_changes(self):
        self.w.pending_recovery = True
        self.assert_remote_error(lambda: self.command('start'), 'recovery')
        self.w.pending_recovery = False
        dialog = QDialog(self.w)
        dialog.setModal(True)
        dialog.show()
        APP.processEvents()
        try:
            self.assert_remote_error(lambda: self.command('start'), 'busy')
        finally:
            dialog.reject()
            dialog.deleteLater()
            APP.processEvents()
        self.assertFalse(self.c.timers[self.key].pending)

    def test_settings_connection_is_off_by_default_and_survives_navigation_and_theme_change(self):
        self.assertFalse(self.phone.server.running)
        self.w.navigate('settings')
        APP.processEvents()
        self.assertIsNotNone(self.w.findChild(PhoneControlCard, 'phoneControlCard'))
        server = self.phone.server
        with patch.object(type(server), 'running', new_callable=PropertyMock, return_value=True):
            self.w.navigate('history')
            self.w.navigate('settings')
            self.w.save_settings('light', 'en')
            self.assertIs(self.w.phone_control, self.phone)
            self.assertIs(self.w.phone_control.server, server)
            self.assertTrue(server.running)
            state = self.phone.snapshot()
            self.assertEqual((state['theme'], state['language']), ('light', 'en'))
            self.assertEqual(state['palette']['bg'], PALETTES['light'][0])

    def test_cancelled_close_keeps_phone_available_and_accepted_close_stops_it(self):
        server = self.phone.server
        self.command('start')
        with patch.object(self.w, 'resolve_pending', return_value=False), patch.object(server, 'stop') as stop:
            self.assertFalse(self.w.close())
            stop.assert_not_called()
        with patch.object(server, 'stop') as stop:
            self.w.closing_allowed = True
            self.assertTrue(self.w.close())
            stop.assert_called_once()

    def test_packaged_phone_smoke_test_uses_real_http_and_preserves_existing_history(self):
        from horas_jogadas_qt.phone_self_test import run_phone_self_test
        evidence = run_phone_self_test(self.w, APP)
        self.assertEqual(evidence['phone_seconds_saved'], 3)
        for key in ('phone_disabled_by_default', 'phone_assets', 'phone_qr', 'phone_pairing',
                    'phone_commands', 'phone_replay_safe', 'phone_revocation', 'phone_shutdown'):
            self.assertTrue(evidence[key], key)
        self.assertFalse(self.phone.server.running)
        original = [s for s in self.c.repo.sessoes if s.jogo_id == self.key]
        self.assertEqual([s.segundos for s in original], [120])
