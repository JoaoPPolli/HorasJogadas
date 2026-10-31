"""Aparelhos opcionais e imagens privadas, sempre com perfis fictícios."""
import hashlib
import json
import os
import tempfile
import time
import unittest
from pathlib import Path
from unittest.mock import patch

from PySide6.QtCore import QEvent
from horas_jogadas_qt.remote_server import RemoteServer
from horas_jogadas_qt.trusted_devices import TrustStore, DEVICE_SECONDS, MAX_DEVICES
from . import test_remote_server as base


class TrustStoreTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.store = TrustStore(self.temporary.name)

    def test_explicit_remember_hash_only_metadata_and_private_file(self):
        self.assertEqual(self.store.list_devices(), [])
        self.assertFalse(self.store.path.exists())
        credentials = self.store.remember(' Meu\ncelular\t pessoal ')
        raw = self.store.path.read_text()
        self.assertNotIn(credentials['remember_token'], raw)
        self.assertIn(hashlib.sha256(credentials['remember_token'].encode()).hexdigest(), raw)
        metadata = self.store.verify(credentials['remember_token'])
        self.assertEqual(metadata['label'], 'Meu celular pessoal')
        self.assertEqual(metadata['id'], credentials['device_id'])
        self.assertEqual(metadata['expires_at'] - metadata['created_at'], DEVICE_SECONDS)
        self.assertNotIn('hash', self.store.list_devices()[0])
        if os.name != 'nt':
            self.assertEqual(self.store.path.stat().st_mode & 0o777, 0o600)
        self.assertEqual(TrustStore(self.temporary.name).verify(credentials['remember_token']), metadata)

    def test_expiration_revoke_one_and_revoke_all(self):
        first = self.store.remember('One')
        second = self.store.remember('Two')
        self.store.revoke(first['device_id'])
        self.assertIsNone(self.store.verify(first['remember_token']))
        self.assertIsNotNone(self.store.verify(second['remember_token']))
        with patch('horas_jogadas_qt.trusted_devices.time.time', return_value=time.time() + DEVICE_SECONDS + 1):
            self.assertEqual(self.store.list_devices(), [])
            self.assertIsNone(self.store.verify(second['remember_token']))
        self.store.revoke_all()
        self.assertEqual(self.store.list_devices(), [])

    def test_corrupt_and_oversized_file_fail_closed_without_implicit_overwrite(self):
        self.store.remember('One')
        for raw in ('{', '{"version":1,"version":1,"devices":[]}', ' ' * 65537,
                    '{"version":true,"devices":[]}'):
            self.store.path.write_text(raw)
            self.assertEqual(self.store.list_devices(), [])
            self.assertIsNone(self.store.verify('a' * 43))
            with self.assertRaises(ValueError):
                self.store.remember('New')
            self.assertEqual(self.store.path.read_text(), raw)
        self.store.revoke_all()
        self.assertEqual(self.store.list_devices(), [])

    def test_validation_limit_invalid_tokens_and_atomic_failure(self):
        credentials = [self.store.remember('Phone') for _ in range(MAX_DEVICES)]
        before = self.store.path.read_bytes()
        with self.assertRaises(ValueError):
            self.store.remember('Too many')
        for value in (None, [], '', 'é' * 43, 'a' * 100000, '\n' * 43):
            self.assertIsNone(self.store.verify(value))
        with patch('horas_jogadas_qt.trusted_devices.os.replace', side_effect=OSError('disk full')):
            with self.assertRaises(OSError):
                self.store.revoke(credentials[0]['device_id'])
        self.assertEqual(self.store.path.read_bytes(), before)
        self.assertEqual(list(Path(self.temporary.name).iterdir()), [self.store.path])


class RememberedServerTests(unittest.TestCase):
    raw = base.RemoteServerTests.raw
    request = base.RemoteServerTests.request
    pair = base.RemoteServerTests.pair

    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.store = TrustStore(self.temporary.name)
        self.state = {'theme': 'dark', 'language': 'pt', 'version': 'test', 'palette': {},
                      'games': [], 'companion_url': 'https://example.test/celular/'}
        self.library = {'format': 'HorasJogadas-Library', 'version': 1, 'games': []}
        def media(game_id, kind):
            return (b'image fixture', 'image/png') if game_id == 'game-id' else None
        self.server = RemoteServer(lambda: self.state, lambda body: {'ok': True},
                                   trust_store=self.store, media=media, library=lambda: self.library)
        try:
            self.server.start('127.0.0.1')
        except OSError as error:
            self.temporary.cleanup()
            self.skipTest('Sockets locais indisponíveis: ' + str(error))

    def tearDown(self):
        self.server.stop(); self.server.deleteLater()
        base.APP.sendPostedEvents(None, QEvent.DeferredDelete); base.APP.processEvents()
        self.temporary.cleanup()

    def remembered_pair(self):
        status, _, body = self.request('POST', '/api/pair',
            {'code': self.server.pairing_code, 'remember': True, 'device_name': 'Meu celular'})
        self.assertEqual(status, 200, body)
        return json.loads(body)

    def test_pair_is_ephemeral_by_default_and_remember_requires_opt_in(self):
        self.pair()
        self.assertFalse(self.store.path.exists())
        self.assertEqual(self.server.remembered_devices, [])
        credentials = self.remembered_pair()
        self.assertEqual(len(self.server.remembered_devices), 1)
        self.assertNotIn(credentials['remember_token'], self.store.path.read_text())
        self.assertEqual(self.request(path='/api/state', token=credentials['token'])[0], 200)
        self.assertEqual(self.request('POST', '/api/pair', {'code': self.server.pairing_code, 'remember': 'yes'})[0], 400)

    def test_resume_survives_server_restart_and_expired_pin_but_stop_remains_disabled(self):
        credentials = self.remembered_pair()
        self.server.stop()
        self.assertFalse(self.server.running)
        self.assertEqual(len(self.store.list_devices()), 1)
        self.server.start('127.0.0.1')
        self.server._pairing_deadline = time.monotonic() - 1
        status, _, body = self.request('POST', '/api/resume', {'remember_token': credentials['remember_token']})
        self.assertEqual(status, 200, body)
        resumed = json.loads(body)
        self.assertEqual(resumed['device_id'], credentials['device_id'])
        self.assertNotEqual(resumed['token'], credentials['token'])
        self.assertEqual(self.request(path='/api/state', token=credentials['token'])[0], 401)
        self.assertEqual(self.request(path='/api/state', token=resumed['token'])[0], 200)
        self.assertEqual(self.request('POST', '/api/resume', {'remember_token': credentials['remember_token']}, overrides={'Origin': 'http://evil.test'})[0], 403)

    def test_resume_shares_same_device_session_across_tabs_without_extending_expiry(self):
        credentials = self.remembered_pair()
        expires = self.server._sessions[credentials['token']]['expires']
        for _ in range(8):
            status, _, body = self.request('POST', '/api/resume', {'remember_token': credentials['remember_token']})
            self.assertEqual(status, 200)
            self.assertEqual(json.loads(body)['token'], credentials['token'])
            self.assertEqual(self.request(path='/api/state', token=credentials['token'])[0], 200)
        self.assertEqual(self.server.client_count, 1)
        self.assertEqual(self.server._sessions[credentials['token']]['expires'], expires)
        self.assertEqual(len(self.server.remembered_devices), 1)
        for _ in range(6):
            self.assertEqual(self.request('POST', '/api/resume', {'remember_token': 'bad'})[0], 401)
        self.assertEqual(self.request('POST', '/api/resume', {'remember_token': credentials['remember_token']})[0], 429)

    def test_qr_session_can_opt_in_later_and_disconnect_revokes_remembered_access(self):
        token = self.pair({'secret': self.server._secret})
        status, _, body = self.request('POST', '/api/remember', {'device_name': 'Phone after QR'}, token)
        self.assertEqual(status, 200, body)
        credentials = json.loads(body)
        self.assertEqual(len(self.server.remembered_devices), 1)
        self.assertEqual(self.request('POST', '/api/remember', {}, token)[0], 409)
        self.assertEqual(self.request('POST', '/api/disconnect', {}, token)[0], 200)
        self.assertEqual(self.server.remembered_devices, [])
        self.assertEqual(self.request('POST', '/api/resume', {'remember_token': credentials['remember_token']})[0], 401)
        self.assertEqual(self.request(path='/api/state', token=token)[0], 401)

    def test_individual_and_all_revocation_invalidate_current_and_future_tokens(self):
        first, second = self.remembered_pair(), self.remembered_pair()
        self.server.revoke_device(first['device_id'])
        self.assertEqual(self.request(path='/api/state', token=first['token'])[0], 401)
        self.assertEqual(self.request(path='/api/state', token=second['token'])[0], 200)
        self.server.regenerate_pairing()
        self.assertEqual(self.server.remembered_devices, [])
        self.assertEqual(self.request(path='/api/state', token=second['token'])[0], 401)
        self.assertEqual(self.request('POST', '/api/resume', {'remember_token': second['remember_token']})[0], 401)

    def test_tamper_expiry_and_failed_store_write_never_create_authorization(self):
        credentials = self.remembered_pair()
        self.store.path.write_text('{broken')
        self.assertEqual(self.request(path='/api/state', token=credentials['token'])[0], 401)
        self.assertEqual(self.request('POST', '/api/resume', {'remember_token': credentials['remember_token']})[0], 401)
        self.store.revoke_all()
        before = self.server.client_count
        with patch('horas_jogadas_qt.trusted_devices.os.replace', side_effect=OSError('write failed')):
            self.assertEqual(self.request('POST', '/api/pair', {'code': self.server.pairing_code, 'remember': True})[0], 500)
        self.assertEqual(self.server.client_count, before)

    def test_media_and_library_are_authenticated_exact_and_never_take_token_in_url(self):
        self.assertEqual(self.request(path='/api/library')[0], 401)
        self.assertEqual(self.request(path='/api/art/icon/game-id')[0], 401)
        token = self.pair()
        status, headers, body = self.request(path='/api/art/icon/game-id?v=' + 'a' * 64, token=token)
        self.assertEqual((status, headers['Content-Type'], body), (200, 'image/png', b'image fixture'))
        self.assertIn('blob:', headers['Content-Security-Policy'])
        for path in ('/api/art/icon/../../config.json', '/api/art/icon/%2e%2e', '/api/art/other/game-id',
                     '/api/art/icon/game-id?token=' + token, '/api/art/icon/game-id?v=x', '/api/art/icon/unknown'):
            self.assertEqual(self.request(path=path, token=token)[0], 404, path)
        status, _, body = self.request(path='/api/library', token=token)
        self.assertEqual((status, json.loads(body)), (200, self.library))
        self.server.media = lambda *args: (b'bad', 'text/html')
        self.assertEqual(self.request(path='/api/art/icon/game-id', token=token)[0], 404)
        public = json.loads(self.request()[2])
        self.assertEqual(public['companion_url'], self.state['companion_url'])
        self.assertNotIn('games', public)
