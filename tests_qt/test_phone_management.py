"""Connected-phone management validates files and preserves existing PC records."""
import base64
import io
import json
import tempfile
import time
import unittest
import zipfile
from pathlib import Path
from unittest.mock import patch

from PySide6.QtCore import QObject
from PySide6.QtGui import QImage, QColor
from PySide6.QtCore import QBuffer, QIODevice
from PySide6.QtWidgets import QApplication, QWidget
from horas_jogadas_qt import preferences
from horas_jogadas_qt.controller import Controller
from horas_jogadas_qt.covers import Candidate, CoverStore
from horas_jogadas_qt.phone_management import PhoneManagement, TRANSACTIONAL_ACTIONS
from horas_jogadas_qt.remote_server import RemoteError
from horas_jogadas_qt.preview import inventory
from horas_jogadas_qt.trusted_devices import TrustStore

APP = QApplication.instance() or QApplication([])


class Window(QWidget):
    def __init__(self, folder):
        super().__init__(); self.c = Controller(folder); self.page = 'library'; self.pending_recovery = False
    def theme_name(self): return preferences.read(self.c.folder).get('theme', 'dark')
    def refresh(self): pass
    def update_activity(self): pass


class Control(QObject):
    def __init__(self, window):
        super().__init__(window); self.window = window; self.serial = 0
    def workspace_revision(self): return str(self.serial)
    def invalidate(self): self.serial += 1
    def snapshot(self): return {}


class ManagementTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory(); self.addCleanup(self.temporary.cleanup)
        self.folder = Path(self.temporary.name)
        self.w = Window(self.folder)
        self.control = Control(self.w); self.manager = PhoneManagement(self.control)
        self.game = self.w.c.add_game('Keep my game')
        self.w.c.timers[self.game.id].adjust(42)
        self.w.c.finish(self.game.id)
        self.before = (self.folder / 'registros.json').read_bytes()
        self.addCleanup(self.w.deleteLater)

    def execute(self, **body):
        if body['action'] in TRANSACTIONAL_ACTIONS:
            with self.w.c.transaction(): return self.manager.execute(body)
        return self.manager.execute(body)

    def preview(self, data):
        return self.manager.query(dict(query='backup_restore_preview', data=base64.b64encode(data).decode()))

    def test_fresh_backup_preserves_unrecovered_sessions(self):
        timer = self.w.c.timers[self.game.id]
        timer.adjust(15); self.w.c.save_pending()
        pending_file = self.folder / 'em_andamento.json'
        before = pending_file.read_bytes()
        timer.reset(); self.w.pending_recovery = True
        with self.assertRaises(RemoteError) as error:
            self.manager.export('full_backup')
        self.assertEqual(error.exception.code, 'recovery')
        self.assertEqual(pending_file.read_bytes(), before)
        self.assertTrue(self.w.c.repo.carregar_andamento())

    def wait_job(self, job_id):
        deadline = time.monotonic() + 5
        while time.monotonic() < deadline:
            APP.processEvents()
            state = self.manager.view('job', {'id': job_id})
            if state['status'] != 'running': return state
            time.sleep(.001)
        self.fail('Network task did not settle')

    def image(self):
        image = QImage(30, 30, QImage.Format_ARGB32); image.fill(QColor('#6755ff'))
        buffer = QBuffer(); buffer.open(QIODevice.WriteOnly); image.save(buffer, 'PNG')
        return bytes(buffer.data())

    def test_settings_validate_and_transaction_rolls_back(self):
        self.execute(action='settings_save', theme='light', language='en', covers_enabled=True)
        self.assertEqual(self.manager.view('settings')['theme'], 'light')
        self.assertEqual(self.w.c.config['idioma'], 'en')
        with self.assertRaises(RemoteError): self.execute(action='settings_save', theme='other')
        before = (self.folder / '.qt-preferences.json').read_bytes()
        with patch.object(self.w.c.repo, 'salvar_config', side_effect=OSError('fake disk')):
            with self.assertRaises(OSError): self.execute(action='settings_save', language='pt', theme='original')
        self.assertEqual((self.folder / '.qt-preferences.json').read_bytes(), before)
        self.assertEqual((self.folder / 'registros.json').read_bytes(), self.before)

    def test_local_art_is_normalized_and_removal_preserves_records(self):
        self.execute(action='art_local', game_id=self.game.id, kind='icon', data=base64.b64encode(self.image()).decode())
        image = QImage(str(CoverStore(self.folder, 'icon').path(self.game.id)))
        self.assertFalse(image.isNull()); self.assertTrue(image.hasAlphaChannel())
        with self.assertRaises(RemoteError): self.execute(action='art_local', game_id='../private', kind='icon', data='AAAA')
        with self.assertRaises(RemoteError): self.execute(action='art_local', game_id=self.game.id, kind='script', data='AAAA')
        self.execute(action='art_remove', game_id=self.game.id, kind='icon')
        self.assertIsNone(CoverStore(self.folder, 'icon').path(self.game.id))
        self.assertEqual((self.folder / 'registros.json').read_bytes(), self.before)

    def test_full_backup_export_omits_credentials_and_roundtrip_has_verified_preview(self):
        TrustStore(self.folder).remember('Private device')
        data, mime, filename = self.manager.export('full_backup')
        self.assertEqual(mime, 'application/zip'); self.assertTrue(filename.endswith('.zip'))
        with zipfile.ZipFile(io.BytesIO(data)) as archive:
            self.assertNotIn('.phone-devices.json', archive.namelist())
            self.assertIn('manifest.json', archive.namelist())
        preview = self.preview(data)
        self.assertEqual(preview['games'], 1); self.assertEqual(preview['sessions'], 1)
        self.w.c.add_game('Added after backup')
        response = self.execute(action='backup_restore', ticket=preview['ticket'], confirmed=True)
        self.assertTrue(response['restored']); self.assertEqual(len(self.w.c.repo.jogos), 1)
        self.assertEqual(self.w.c.repo.sessoes[0].segundos, 42)
        self.assertTrue(TrustStore(self.folder).list_devices())

    def test_zip_traversal_duplicates_hash_tampering_and_expiry_are_rejected(self):
        def archive(values):
            output = io.BytesIO()
            with zipfile.ZipFile(output, 'w') as stream:
                for name, content in values: stream.writestr(name, content)
            return output.getvalue()
        for values in ([('../escape', b'x')], [('manifest.json', b'{}'), ('.phone-devices.json', b'{}')],
                       [('manifest.json', json.dumps({'registros.json': '0'*64})), ('registros.json', b'[]')],
                       [('manifest.json', b'{}'), ('manifest.json', b'{}')]):
            with self.subTest(values=values):
                with self.assertRaises(RemoteError): self.preview(archive(values))
        data, _, _ = self.manager.export('full_backup')
        preview = self.preview(data)
        self.manager.tickets[preview['ticket']]['expires'] = 0
        with self.assertRaises(RemoteError): self.execute(action='backup_restore', ticket=preview['ticket'], confirmed=True)
        self.assertEqual((self.folder / 'registros.json').read_bytes(), self.before)
        self.assertFalse((self.folder.parent / 'escape').exists())

    def test_restore_requires_explicit_pending_decision_and_backup_recovery(self):
        self.w.c.timers[self.game.id].start(); self.w.c.save_pending()
        data, _, _ = self.manager.export('full_backup')
        preview = self.preview(data)
        self.assertTrue(preview['has_pending'])
        with self.assertRaises(RemoteError) as error:
            self.execute(action='backup_restore', ticket=preview['ticket'], confirmed=True)
        self.assertEqual(error.exception.code, 'pending_required')
        with self.assertRaises(RemoteError) as error:
            self.execute(action='backup_restore', ticket=preview['ticket'], confirmed=True, pending='save')
        self.assertEqual(error.exception.code, 'recovery_required')
        self.execute(action='backup_restore', ticket=preview['ticket'], confirmed=True, pending='save', recovery='discard')
        self.assertFalse(self.w.c.repo.carregar_andamento())
        self.assertFalse(any(timer.pending for timer in self.w.c.timers.values()))

    def test_failed_restore_rolls_back_original_files_and_controller(self):
        data, _, _ = self.manager.export('full_backup'); preview = self.preview(data)
        old = self.w.c
        def broken_restore(folder, path):
            (Path(folder)/'registros.json').write_text('[]')
            raise OSError('fake disk error')
        with patch('horas_jogadas_qt.phone_management.restore_full', side_effect=broken_restore):
            with self.assertRaises(OSError): self.execute(action='backup_restore', ticket=preview['ticket'], confirmed=True)
        self.assertIs(self.w.c, old)
        self.assertEqual((self.folder / 'registros.json').read_bytes(), self.before)

    def test_art_search_and_import_are_async_issued_candidates_only(self):
        candidate = Candidate(123, 'Matched game', 'https://shared.fastly.steamstatic.com/store_item_assets/steam/apps/123/header.jpg', .99)
        with patch('horas_jogadas_qt.artwork_sources.search_artwork', return_value=[candidate]):
            started = self.manager.query(dict(query='art_search', kind='icon', source='Steam', titles=[dict(game_id=self.game.id, title='Matched game')]))
            result = self.wait_job(started['job_id'])
        self.assertEqual(result['status'], 'complete')
        candidate_id = result['result']['games'][0]['candidates'][0]['id']
        with self.assertRaises(RemoteError): self.execute(action='art_import', kind='icon', job_id=started['job_id'], selected=[dict(game_id=self.game.id, candidate_id='arbitrary-url')])
        with patch('horas_jogadas_qt.artwork_sources.download_artwork', return_value=self.image()):
            imported = self.execute(action='art_import', kind='icon', job_id=started['job_id'], selected=[dict(game_id=self.game.id, candidate_id=candidate_id)])
            job = self.wait_job(imported['job_id'])
        self.assertEqual(job['status'], 'complete'); self.assertEqual(job['result']['imported'], 1)
        self.assertTrue(CoverStore(self.folder, 'icon').path(self.game.id).is_file())
        self.assertEqual((self.folder / 'registros.json').read_bytes(), self.before)

    def test_art_download_conflict_does_not_write_image_index(self):
        candidate = Candidate(123, 'Matched game', 'https://shared.fastly.steamstatic.com/store_item_assets/steam/apps/123/header.jpg', .99)
        self.manager.candidates['test'] = {'choice': dict(candidate=candidate, game_id=self.game.id, kind='icon')}
        with patch('horas_jogadas_qt.artwork_sources.download_artwork', return_value=self.image()):
            imported = self.execute(action='art_import', kind='icon', job_id='test', selected=[dict(game_id=self.game.id, candidate_id='choice')])
            self.control.invalidate()
            job = self.wait_job(imported['job_id'])
        self.assertEqual(job['status'], 'failed'); self.assertEqual(job['error'], 'conflict')
        self.assertIsNone(CoverStore(self.folder, 'icon').path(self.game.id))
