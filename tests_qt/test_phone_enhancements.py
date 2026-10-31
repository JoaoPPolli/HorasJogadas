"""Favoritos, imagens privadas, recibos e credenciais preservam a base existente."""
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from PySide6.QtCore import QBuffer, QIODevice, QEvent
from PySide6.QtGui import QImage, QColor
from PySide6.QtWidgets import QApplication, QPushButton
from horas_jogadas.storage import Repositorio
from horas_jogadas_qt import preferences
from horas_jogadas_qt.backup import create_full, read_full
from horas_jogadas_qt.controller import Controller
from horas_jogadas_qt.covers import CoverStore, normalize_image
from horas_jogadas_qt.phone_control import PhoneControlCard, PHONE_PORT
from horas_jogadas_qt.preview import inventory, prepare_preview
from horas_jogadas_qt.release import prepare_official_data
from horas_jogadas_qt.remote_server import RemoteError
from horas_jogadas_qt.window import Window
from .test_data import Clock

APP = QApplication.instance() or QApplication([])


class PhoneEnhancementsTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.folder = Path(self.tmp.name) / 'data'; self.folder.mkdir()
        repo = Repositorio(str(self.folder), config_legado='')
        self.key = repo.adicionar_jogo('Meu jogo no PS5').id
        self.c = Controller(self.folder)
        self.clock = Clock(); self.c.timers[self.key].clock = self.clock
        self.w = Window(self.c); self.w.timer.stop(); self.w.show(); APP.processEvents()
        self.phone = self.w.phone_control

    def tearDown(self):
        self.w.closing_allowed = True; self.w.close()
        APP.removeEventFilter(self.w); self.w.deleteLater()
        APP.sendPostedEvents(None, QEvent.DeferredDelete); APP.processEvents()

    def game(self):
        return next(g for g in self.phone.snapshot()['games'] if g['id'] == self.key)

    def command(self, action, **changes):
        return self.phone.command(dict(action=action, game_id=self.key, revision=self.game()['revision'], **changes))

    def test_favorites_persist_in_backup_without_modifying_timer_or_history(self):
        self.command('start'); self.clock.advance(17)
        timer = self.c.timers[self.key]
        self.command('favorite', enabled=True)
        self.assertTrue(self.game()['favorite']); self.assertIs(self.c.timers[self.key], timer)
        self.assertTrue(timer.rodando); self.assertEqual(timer.seconds(), 17)
        self.assertEqual(self.c.repo.sessoes, [])
        data = read_full(create_full(self.folder))
        self.assertIn(self.key, json.loads(data['.qt-preferences.json'])['phone_favorites'])
        self.command('favorite', enabled=False)
        self.assertFalse(self.game()['favorite'])

    def test_failed_favorite_rolls_back_preferences_and_stale_requests_are_rejected(self):
        stale = self.game()['revision']
        with patch.object(self.c, 'save_pending', side_effect=OSError('fake disk full')):
            with self.assertRaises(RemoteError) as error:
                self.command('favorite', enabled=True)
        self.assertEqual(error.exception.code, 'storage'); self.assertFalse(self.game()['favorite'])
        self.assertEqual(self.game()['revision'], stale)
        for enabled in (1, None, 'true'):
            with self.assertRaises(RemoteError): self.command('favorite', enabled=enabled)
        self.command('favorite', enabled=True)
        with self.assertRaises(RemoteError) as error:
            self.phone.command(dict(action='favorite', game_id=self.key, revision=stale, enabled=False))
        self.assertEqual(error.exception.code, 'conflict')

    def test_finish_summary_reports_seconds_actually_saved(self):
        self.command('start'); self.clock.advance(42)
        result = self.command('finish')
        self.assertEqual(result['summary'], dict(game='Meu jogo no PS5', seconds=42, total_seconds=42))
        self.assertEqual(Repositorio(str(self.folder), config_legado='').sessoes[-1].segundos, 42)

    def test_cached_images_follow_preferences_and_corrupt_files_are_not_exposed(self):
        image = QImage(48, 48, QImage.Format_ARGB32); image.fill(QColor('#6254ff'))
        buffer = QBuffer(); buffer.open(QIODevice.WriteOnly); image.save(buffer, 'PNG')
        for kind in ('cover', 'icon'):
            data = normalize_image(bytes(buffer.data()), kind)
            CoverStore(self.folder, kind).save_many([(self.key, data, {'source': 'synthetic-test'})])
        preferences.save(self.folder, covers_enabled=False, icons_enabled=False)
        self.assertEqual(self.game()['art'], {'cover': None, 'icon': None})
        with self.assertRaises(RemoteError): self.phone.media(self.key, 'cover')
        preferences.save(self.folder, covers_enabled=True, icons_enabled=True)
        for kind in ('cover', 'icon'):
            self.assertIn('?v=', self.game()['art'][kind])
            data, mime = self.phone.media(self.key, kind)
            self.assertTrue(mime.startswith('image/')); self.assertFalse(QImage.fromData(data).isNull())
        CoverStore(self.folder, 'icon').path(self.key).write_bytes(b'corrupt')
        with self.assertRaises(RemoteError): self.phone.media(self.key, 'icon')
        with self.assertRaises(RemoteError): self.phone.media('../private', 'icon')

    def test_credentials_never_enter_backups_or_review_and_revocation_is_visible(self):
        credentials = self.phone.trust_store.remember('Celular da sala')
        auth_path = self.folder / '.phone-devices.json'; before = auth_path.read_bytes()
        self.assertNotIn('.phone-devices.json', inventory(self.folder))
        self.assertNotIn('.phone-devices.json', read_full(create_full(self.folder)))
        backup = prepare_official_data(self.folder, version='99.0.0')
        self.assertFalse((backup / 'data' / '.phone-devices.json').exists())
        review = prepare_preview(self.folder, Path(self.tmp.name) / 'review')
        self.assertFalse((review / '.phone-devices.json').exists())
        self.assertEqual(auth_path.read_bytes(), before)
        card = PhoneControlCard(self.phone)
        revoke = card.findChild(QPushButton, 'phoneRevokeDevice')
        self.assertIsNotNone(revoke); revoke.click()
        self.assertIsNone(self.phone.trust_store.verify(credentials['remember_token']))
        card.deleteLater()

    def test_production_port_is_stable_and_library_export_contains_no_credentials(self):
        with patch('horas_jogadas_qt.phone_control.local_addresses', return_value=[('192.168.1.8', 'Wi-Fi')]):
            card = PhoneControlCard(self.phone)
        with patch.object(self.phone.server, 'start') as start:
            card.enable(); start.assert_called_once_with('192.168.1.8', PHONE_PORT)
        library = self.phone.library()
        self.assertEqual(library['format'], 'HorasJogadas-Library')
        self.assertEqual(library['games'], [{'id': self.key, 'name': 'Meu jogo no PS5'}])
        self.assertNotIn('token', library); card.deleteLater()
