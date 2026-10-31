"""Requisições reais ao servidor Qt, sem threads nem registros pessoais."""
import importlib.util
import json
import os
import tempfile
import threading
import time
import unittest
from pathlib import Path
from unittest.mock import patch

if importlib.util.find_spec('PySide6') is None:
    raise unittest.SkipTest('PySide6 necessário')
os.environ.setdefault('QT_QPA_PLATFORM', 'offscreen')
from PySide6.QtCore import QEvent
from PySide6.QtNetwork import QAbstractSocket, QTcpSocket
from PySide6.QtWidgets import QApplication
from horas_jogadas_qt.remote_server import RemoteServer, RemoteError, local_address, MAX_COMMANDS

APP = QApplication.instance() or QApplication([])


def pump_until(predicate, timeout=3):
    deadline = time.monotonic() + timeout
    while not predicate() and time.monotonic() < deadline:
        APP.processEvents()
        time.sleep(.001)
    APP.processEvents()
    return predicate()


class RemoteServerTests(unittest.TestCase):
    def setUp(self):
        self.calls = []
        self.thread_id = threading.get_ident()
        self.state = {'theme': 'original', 'language': 'pt', 'palette': ['#202024'], 'version': 'test',
                      'games': [{'id': '1', 'name': 'Jogo pessoal <script>', 'seconds': 4}],
                      'private_file_path': '/fake/profile'}
        def command(payload):
            self.assertEqual(threading.get_ident(), self.thread_id)
            self.calls.append(payload)
            return {'ok': True, 'state': self.state}
        self.server = RemoteServer(lambda: self.state, command)
        try:
            self.server.start('127.0.0.1')
        except OSError as error:
            self.skipTest('Sockets locais indisponíveis neste ambiente: ' + str(error))

    def tearDown(self):
        self.server.stop()
        self.server.deleteLater()
        APP.sendPostedEvents(None, QEvent.DeferredDelete)
        APP.processEvents()

    def raw(self, data):
        socket = QTcpSocket()
        socket.connectToHost('127.0.0.1', self.server.server.serverPort())
        self.assertTrue(socket.waitForConnected(1500), socket.errorString())
        socket.write(data)
        socket.flush()
        content = bytearray()
        def done():
            content.extend(bytes(socket.readAll()))
            return socket.state() == QAbstractSocket.UnconnectedState
        self.assertTrue(pump_until(done), 'Resposta HTTP não terminou')
        socket.deleteLater()
        headers, body = bytes(content).split(b'\r\n\r\n', 1)
        lines = headers.decode('ascii').split('\r\n')
        status = int(lines[0].split()[1])
        metadata = dict(line.split(': ', 1) for line in lines[1:])
        self.assertEqual(int(metadata['Content-Length']), len(body))
        return status, metadata, body

    def request(self, method='GET', path='/api/info', payload=None, token=None, overrides=None):
        body = json.dumps(payload).encode() if payload is not None else b''
        headers = {'Host': self.server.url.removeprefix('http://')}
        if method == 'POST':
            headers.update(Origin=self.server.url, **{'Content-Type': 'application/json', 'Content-Length': str(len(body))})
        if token:
            headers['Authorization'] = 'Bearer ' + token
        for name, value in (overrides or {}).items():
            if value is None:
                headers.pop(name, None)
            else:
                headers[name] = value
        data = method + ' ' + path + ' HTTP/1.1\r\n' + ''.join(k + ': ' + v + '\r\n' for k, v in headers.items())
        return self.raw(data.encode('ascii') + b'\r\n' + body)

    def pair(self, payload=None):
        status, _, body = self.request('POST', '/api/pair', payload or {'code': self.server.pairing_code})
        self.assertEqual(status, 200, body)
        return json.loads(body)['token']

    def test_disabled_lifecycle_bound_address_and_in_memory_revocation(self):
        self.assertTrue(self.server.running)
        self.assertRegex(self.server.pairing_code, r'^\d{6}$')
        self.assertIn('/#pair=', self.server.pairing_url)
        self.assertNotIn('?', self.server.pairing_url)
        self.assertGreater(self.server.pairing_seconds, 295)
        token = self.pair()
        self.assertEqual(self.server.client_count, 1)
        self.server.regenerate_pairing()
        self.assertEqual(self.server.client_count, 0)
        self.assertEqual(self.request(path='/api/state', token=token)[0], 401)
        self.assertFalse(self.calls)
        self.server.stop()
        self.assertFalse(self.server.running)
        self.assertEqual((self.server.url, self.server.pairing_url, self.server.pairing_code), ('', '', ''))
        self.assertEqual(self.server.client_count, 0)
        self.server.start('127.0.0.1')
        self.assertEqual(self.request(path='/api/state', token=token)[0], 401)

    def test_private_ipv4_only_no_public_wildcard_or_dns(self):
        for address in ('127.0.0.1', '10.1.2.3', '172.16.4.2', '192.168.1.12', '::ffff:127.0.0.1'):
            self.assertTrue(local_address(address), address)
        self.server.stop()
        for address in ('0.0.0.0', '8.8.8.8', '100.64.0.1', '169.254.1.1', 'localhost', '::1', None):
            with self.assertRaises(ValueError, msg=address):
                self.server.start(address)

    def test_public_info_does_not_expose_library_paths_or_credentials(self):
        status, headers, body = self.request()
        self.assertEqual(status, 200)
        self.assertEqual(set(json.loads(body)), {'theme', 'language', 'palette', 'version'})
        for value in (self.server._secret, self.server.pairing_code, 'Jogo pessoal', '/fake/profile'):
            self.assertNotIn(value.encode(), body)
        self.assertEqual(headers['Cache-Control'], 'no-store')
        self.assertEqual(headers['X-Frame-Options'], 'DENY')
        self.assertIn("frame-ancestors 'none'", headers['Content-Security-Policy'])
        self.assertNotIn('Access-Control-Allow-Origin', headers)
        self.assertEqual(self.request(path='/api/state')[0], 401)
        token = self.pair()
        status, _, body = self.request(path='/api/state', token=token)
        self.assertEqual(status, 200)
        self.assertEqual(json.loads(body), self.state)

    def test_qr_secret_pairing_and_pin_failures_expiry_and_throttle(self):
        token = self.pair({'secret': self.server._secret})
        self.assertEqual(self.request(path='/api/state', token=token)[0], 200)
        for _ in range(6):
            self.assertEqual(self.request('POST', '/api/pair', {'code': 'wrong'})[0], 401)
        self.assertEqual(self.request('POST', '/api/pair', {'code': self.server.pairing_code})[0], 429)
        self.server.regenerate_pairing()
        self.server._pairing_deadline = time.monotonic() - 1
        status, _, body = self.request('POST', '/api/pair', {'code': self.server.pairing_code})
        self.assertEqual((status, json.loads(body)['error']), (410, 'pairing_expired'))
        self.server.regenerate_pairing()
        self.assertEqual(self.request('POST', '/api/pair', {'code': '６６６６６６'})[0], 401)

    def test_expired_sessions_and_six_devices_bound(self):
        tokens = [self.pair() for _ in range(6)]
        self.assertEqual(self.server.client_count, 6)
        self.assertEqual(self.request('POST', '/api/pair', {'code': self.server.pairing_code})[0], 409)
        self.server._sessions[tokens[0]]['expires'] = 0
        self.assertEqual(self.request(path='/api/state', token=tokens[0])[0], 401)
        self.assertEqual(self.server.client_count, 5)
        self.pair()

    def test_disconnect_revokes_only_that_phone_and_releases_device_slot(self):
        one, two = self.pair(), self.pair()
        self.assertEqual(self.server.client_count, 2)
        self.assertEqual(self.request('POST', '/api/disconnect', {}, one, {'Origin': 'http://evil.example'})[0], 403)
        self.assertEqual(self.server.client_count, 2)
        status, _, body = self.request('POST', '/api/disconnect', {}, one)
        self.assertEqual((status, json.loads(body)), (200, {'ok': True}))
        self.assertEqual(self.server.client_count, 1)
        self.assertEqual(self.request(path='/api/state', token=one)[0], 401)
        self.assertEqual(self.request(path='/api/state', token=two)[0], 200)
        self.assertEqual(self.request('POST', '/api/disconnect', {})[0], 401)

    def test_same_origin_and_literal_host_protect_pair_and_commands(self):
        token = self.pair()
        for overrides in ({'Origin': None}, {'Origin': 'http://evil.example'}, {'Host': 'evil.example'},
                          {'Host': '127.0.0.1'}, {'Origin': 'null'}):
            self.assertEqual(self.request('POST', '/api/pair', {'code': self.server.pairing_code}, overrides=overrides)[0], 403)
            self.assertEqual(self.request('POST', '/api/command', {'request_id': 'x' * 20, 'action': 'start'}, token, overrides)[0], 403)
        self.assertEqual(self.request('POST', '/api/command', {'request_id': 'x' * 20, 'action': 'start'})[0], 401)
        self.assertFalse(self.calls)

    def test_commands_run_on_gui_thread_and_retries_do_not_mutate_twice(self):
        token = self.pair()
        payload = {'request_id': 'request-123456789012', 'action': 'finish', 'game_id': '1', 'revision': 'r1'}
        one = self.request('POST', '/api/command', payload, token)
        two = self.request('POST', '/api/command', payload, token)
        self.assertEqual((one[0], two[0]), (200, 200))
        self.assertEqual(one[2], two[2])
        self.assertEqual(len(self.calls), 1)
        self.state = dict(self.state, games=[{'id': '1', 'name': 'Título atualizado', 'seconds': 45}])
        retry = self.request('POST', '/api/command', payload, token)
        self.assertEqual(json.loads(retry[2])['state'], self.state)
        self.assertEqual(len(self.calls), 1)
        cached = self.server._sessions[token]['commands'][payload['request_id']]
        self.assertNotIn('state', cached[1])
        status, _, body = self.request('POST', '/api/command', dict(payload, action='start'), token)
        self.assertEqual((status, json.loads(body)['error']), (409, 'conflict'))
        self.assertEqual(len(self.calls), 1)

    def test_callback_failure_returns_code_without_exception_details(self):
        token = self.pair()
        payload = {'request_id': 'request-123456789012', 'action': 'start'}
        def unavailable(command):
            raise RemoteError(409, 'busy')
        self.server.command = unavailable
        self.assertEqual(self.request('POST', '/api/command', payload, token)[2], b'{"error": "busy"}')
        def storage_failure(command):
            raise OSError('/private/path and secret')
        self.server.command = storage_failure
        status, _, body = self.request('POST', '/api/command', payload, token)
        self.assertEqual(status, 500)
        self.assertEqual(json.loads(body), {'error': 'storage'})

    def test_only_exact_static_paths_and_packaged_icon(self):
        with tempfile.TemporaryDirectory() as temporary:
            assets = Path(temporary)
            for name in ('index.html', 'app.css', 'app.js'):
                (assets / name).write_text('fixture:' + name)
            with patch('horas_jogadas_qt.remote_server.ASSETS', assets):
                for path in ('/', '/app.css', '/app.js'):
                    status, _, body = self.request(path=path)
                    self.assertEqual(status, 200)
                    self.assertTrue(body.startswith(b'fixture:'))
                for path in ('/../icon.ico', '/%2e%2e/icon.ico', '/app.js?secret=x', '/config.json', '/#pair=x'):
                    self.assertEqual(self.request(path=path)[0], 404, path)
        status, headers, body = self.request(path='/icon.ico')
        self.assertEqual((status, headers['Content-Type']), (200, 'image/vnd.microsoft.icon'))
        self.assertTrue(body.startswith(b'\x00\x00\x01\x00'))

    def test_malformed_headers_transfer_encoding_duplicate_and_oversized_bodies(self):
        host = self.server.url.removeprefix('http://')
        for request in (
            'GET /api/info HTTP/1.1\r\nHost: ' + host + '\r\nHost: ' + host + '\r\n\r\n',
            'GET /api/info HTTP/1.1\r\nHost: ' + host + '\r\nTransfer-Encoding: chunked\r\n\r\n',
            'GET /api/info HTTP/1.1\r\nHost: ' + host + '\r\nContent-Length: -1\r\n\r\n',
            'GET /api/info HTTP/1.1\r\nHost: ' + host + '\r\nContent-Length: 1\r\n\r\nx',
            'GET /api/info HTTP/1.1\r\nHost : ' + host + '\r\n\r\n',
        ):
            self.assertEqual(self.raw(request.encode())[0], 400)
        self.assertEqual(self.request('POST', '/api/pair', {'x': 'a' * 5000})[0], 413)
        self.assertEqual(self.raw(b'GET / HTTP/1.1\r\nLong: ' + b'x' * 9000)[0], 413)
        self.assertEqual(self.request('OPTIONS', '/api/state')[0], 405)
        self.assertEqual(self.request('POST', '/api/pair', {'code': self.server.pairing_code}, overrides={'Content-Type': 'text/plain'})[0], 400)
        self.assertEqual(self.request('POST', '/api/pair', {'code': self.server.pairing_code}, overrides={'Content-Length': None})[0], 400)

    def test_connection_and_request_limits_do_not_leave_sockets_open(self):
        socket = QTcpSocket()
        socket.connectToHost('127.0.0.1', self.server.server.serverPort())
        self.assertTrue(socket.waitForConnected(1500))
        self.assertTrue(pump_until(lambda: len(self.server._connections) == 1))
        timer = next(iter(self.server._connections.values()))['timer']
        timer.start(5)
        self.assertTrue(pump_until(lambda: socket.state() == QAbstractSocket.UnconnectedState))
        self.assertTrue(pump_until(lambda: not self.server._connections))
        socket.deleteLater()
        self.server._requests = [(time.monotonic(), '127.0.0.1')] * 90
        self.assertEqual(self.request()[0], 429)

    def test_json_duplicate_keys_nonfinite_numbers_and_nonobjects_are_rejected(self):
        host = self.server.url.removeprefix('http://')
        for body in (b'{"code":"123456","code":"654321"}', b'{"value":NaN}', b'{"value":Infinity}',
                     b'{"value":-Infinity}', b'{"value":1e999}', b'{"nested":{"key":1,"key":2}}',
                     b'[]', b'null'):
            headers = (f'POST /api/pair HTTP/1.1\r\nHost: {host}\r\nOrigin: {self.server.url}\r\n'
                       f'Content-Type: application/json\r\nContent-Length: {len(body)}\r\n\r\n')
            self.assertEqual(self.raw(headers.encode() + body)[0], 400, body)
        self.assertEqual(self.server.client_count, 0)
        self.assertFalse(self.calls)

    def test_command_limit_expires_session_instead_of_forgetting_old_request_ids(self):
        token = self.pair()
        session = self.server._sessions[token]
        for index in range(MAX_COMMANDS):
            self.server._command(session, {'request_id': 'request-' + str(index).zfill(16), 'action': 'start'})
        with self.assertRaises(RemoteError) as error:
            self.server._command(session, {'request_id': 'one-more-request-1234', 'action': 'start'})
        self.assertEqual((error.exception.status, error.exception.code), (401, 'unauthorized'))
        self.assertEqual(len(self.calls), MAX_COMMANDS)
        self.assertEqual(self.server.client_count, 0)
        self.assertEqual(self.request(path='/api/state', token=token)[0], 401)
