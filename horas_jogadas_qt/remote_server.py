"""Controle HTTP restrito à rede local, executado no event loop do Qt.

O servidor não conhece repositórios nem cria threads: snapshot e comandos são
chamados na mesma thread dos widgets e dos cronômetros. Credenciais vivem somente
na memória desta execução e nunca entram em logs, URLs de requisições ou backups.
"""
import hashlib
import ipaddress
import json
import math
import secrets
import time
from collections import OrderedDict
from pathlib import Path

from PySide6.QtCore import QObject, Signal, QTimer
from PySide6.QtNetwork import QHostAddress, QTcpServer

PRIVATE_NETWORKS = tuple(ipaddress.ip_network(value) for value in
                         ('10.0.0.0/8', '172.16.0.0/12', '192.168.0.0/16', '127.0.0.0/8'))
ASSETS = Path(__file__).with_name('assets') / 'remote'
MAX_CONNECTIONS = 24
MAX_HEADER = 8192
MAX_BODY = 4096
SESSION_SECONDS = 12 * 3600
MAX_COMMANDS = 1024


class RemoteError(Exception):
    def __init__(self, status, code):
        super().__init__(code)
        self.status, self.code = status, code


def local_address(value):
    try:
        address = ipaddress.ip_address(value)
        if isinstance(address, ipaddress.IPv6Address):
            address = address.ipv4_mapped
        return address is not None and any(address in network for network in PRIVATE_NETWORKS)
    except ValueError:
        return False


def unique_object(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            raise ValueError('Chave JSON duplicada')
        result[key] = value
    return result


def finite_number(text):
    value = float(text)
    if not math.isfinite(value):
        raise ValueError('Número JSON inválido')
    return value


def reject_constant(text):
    raise ValueError('Constante JSON inválida')


class RemoteServer(QObject):
    changed = Signal()

    def __init__(self, snapshot, command, parent=None):
        super().__init__(parent)
        self.snapshot, self.command = snapshot, command
        self.server = QTcpServer(self)
        self.server.setMaxPendingConnections(MAX_CONNECTIONS)
        self.server.newConnection.connect(self._accept)
        self._connections = {}
        self._sessions = {}
        self._attempts = []
        self._requests = []
        self._url = ''
        self._secret = ''
        self._code = ''
        self._pairing_deadline = 0
        self.maintenance = QTimer(self)
        self.maintenance.setInterval(1000)
        self.maintenance.timeout.connect(self._maintain)

    @property
    def running(self):
        return self.server.isListening()

    @property
    def url(self):
        return self._url if self.running else ''

    @property
    def pairing_url(self):
        return self.url + '/#pair=' + self._secret if self.running else ''

    @property
    def pairing_code(self):
        return self._code if self.running else ''

    @property
    def pairing_seconds(self):
        return max(0, math.ceil(self._pairing_deadline - time.monotonic())) if self.running else 0

    @property
    def client_count(self):
        self._expire_sessions()
        return len(self._sessions)

    def start(self, host, port=0):
        if self.running:
            raise ValueError('Controle remoto já está ativo')
        # Nunca escuta todas as interfaces, nomes DNS, redes públicas ou IPv6.
        if not isinstance(host, str):
            raise ValueError('Escolha um endereço IPv4 da rede local')
        try:
            address = ipaddress.IPv4Address(host)
        except ipaddress.AddressValueError as error:
            raise ValueError('Escolha um endereço IPv4 da rede local') from error
        if not local_address(str(address)):
            raise ValueError('Escolha um endereço IPv4 da rede local')
        if not isinstance(port, int) or isinstance(port, bool) or not 0 <= port <= 65535:
            raise ValueError('Porta inválida')
        if not self.server.listen(QHostAddress(str(address)), port):
            raise OSError(self.server.errorString())
        self._url = f'http://{address}:{self.server.serverPort()}'
        self.regenerate_pairing()
        self.maintenance.start()

    def stop(self):
        self.server.close()
        self.maintenance.stop()
        while self.server.hasPendingConnections():
            socket = self.server.nextPendingConnection()
            socket.abort()
            socket.deleteLater()
        for socket in list(self._connections):
            socket.abort()
            self._discard(socket)
        self._sessions.clear()
        self._attempts.clear()
        self._requests.clear()
        self._url = self._secret = self._code = ''
        self._pairing_deadline = 0
        self.changed.emit()

    def regenerate_pairing(self):
        if not self.running:
            return
        self._sessions.clear()
        self._secret = secrets.token_urlsafe(32)
        self._code = f'{secrets.randbelow(1000000):06d}'
        self._pairing_deadline = time.monotonic() + 300
        self._attempts.clear()
        self.changed.emit()

    def _expire_sessions(self):
        expired = [token for token, session in self._sessions.items() if session['expires'] <= time.monotonic()]
        for token in expired:
            del self._sessions[token]
        return bool(expired)

    def _maintain(self):
        if self._expire_sessions():
            self.changed.emit()
        self._attempts[:] = [(when, peer) for when, peer in self._attempts if time.monotonic() - when < 60]
        self._requests[:] = [(when, peer) for when, peer in self._requests if time.monotonic() - when < 10]

    def _accept(self):
        while self.server.hasPendingConnections():
            socket = self.server.nextPendingConnection()
            if len(self._connections) >= MAX_CONNECTIONS or not local_address(socket.peerAddress().toString()):
                socket.abort()
                socket.deleteLater()
                continue
            timer = QTimer(socket)
            socket.setReadBufferSize(MAX_HEADER + MAX_BODY + 5)
            timer.setSingleShot(True)
            timer.timeout.connect(lambda current=socket: current.abort())
            timer.start(7000)
            self._connections[socket] = {'data': bytearray(), 'timer': timer, 'responded': False}
            socket.readyRead.connect(lambda current=socket: self._read(current))
            socket.disconnected.connect(lambda current=socket: self._discard(current))

    def _discard(self, socket):
        if self._connections.pop(socket, None) is not None:
            socket.deleteLater()

    def _read(self, socket):
        connection = self._connections.get(socket)
        if not connection or connection['responded']:
            return
        connection['data'].extend(bytes(socket.readAll()))
        data = connection['data']
        boundary = data.find(b'\r\n\r\n')
        if boundary < 0:
            if len(data) > MAX_HEADER:
                self._respond(socket, 413, {'error': 'invalid'})
            return
        if boundary > MAX_HEADER or len(data) > MAX_HEADER + MAX_BODY + 4:
            self._respond(socket, 413, {'error': 'invalid'})
            return
        try:
            lines = data[:boundary].decode('ascii').split('\r\n')
            method, path, protocol = lines[0].split(' ')
            if protocol != 'HTTP/1.1' or method not in ('GET', 'POST'):
                raise RemoteError(405, 'invalid')
            headers = {}
            for line in lines[1:]:
                if not line or line[0].isspace() or ':' not in line:
                    raise RemoteError(400, 'invalid')
                name, value = line.split(':', 1)
                if not name or any(c not in "!#$%&'*+-.^_`|~0123456789abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ" for c in name):
                    raise RemoteError(400, 'invalid')
                name = name.lower()
                if name in headers or any(ord(c) < 32 and c != '\t' for c in value) or '\x7f' in value:
                    raise RemoteError(400, 'invalid')
                headers[name] = value.strip()
            if headers.get('host') != self._url.removeprefix('http://'):
                raise RemoteError(403, 'invalid')
            if 'transfer-encoding' in headers or 'expect' in headers:
                raise RemoteError(400, 'invalid')
            length_text = headers.get('content-length', '0')
            if not length_text.isascii() or not length_text.isdigit() or len(length_text) > 8:
                raise RemoteError(400, 'invalid')
            length = int(length_text)
            if length > MAX_BODY:
                raise RemoteError(413, 'invalid')
            if method == 'GET' and length:
                raise RemoteError(400, 'invalid')
            if method == 'POST':
                if headers.get('origin') != self._url:
                    raise RemoteError(403, 'invalid')
                if headers.get('content-type', '').lower() != 'application/json' or 'content-length' not in headers:
                    raise RemoteError(400, 'invalid')
            if len(data) - boundary - 4 < length:
                return
            if len(data) - boundary - 4 != length:
                raise RemoteError(400, 'invalid')
            now = time.monotonic()
            peer = socket.peerAddress().toString()
            self._requests[:] = [(when, source) for when, source in self._requests if now - when < 10]
            if len(self._requests) >= 240 or sum(source == peer for _, source in self._requests) >= 90:
                raise RemoteError(429, 'rate_limited')
            self._requests.append((now, peer))
            body = data[boundary + 4:]
            payload = json.loads(body, object_pairs_hook=unique_object, parse_float=finite_number,
                                 parse_constant=reject_constant) if body else {}
            if not isinstance(payload, dict):
                raise RemoteError(400, 'invalid')
            status, result, content_type = self._route(socket, method, path, headers, payload)
            self._respond(socket, status, result, content_type)
        except RemoteError as error:
            self._respond(socket, error.status, {'error': error.code})
        except (ValueError, UnicodeError):
            self._respond(socket, 400, {'error': 'invalid'})
        except Exception:
            # Não devolve exceções de arquivos, tokens ou dados pessoais ao cliente.
            self._respond(socket, 500, {'error': 'storage'})

    def _session(self, headers):
        self._expire_sessions()
        authorization = headers.get('authorization', '')
        if not authorization.startswith('Bearer '):
            raise RemoteError(401, 'unauthorized')
        token = authorization[7:]
        session = self._sessions.get(token)
        if session is None:
            raise RemoteError(401, 'unauthorized')
        return session

    def _route(self, socket, method, path, headers, payload):
        if method == 'GET' and path == '/icon.ico':
            return 200, Path(__file__).resolve().parent.parent.joinpath('icon.ico').read_bytes(), 'image/vnd.microsoft.icon'
        if method == 'GET' and path in ('/', '/app.css', '/app.js'):
            filename, mime = {'/': ('index.html', 'text/html; charset=utf-8'),
                              '/app.css': ('app.css', 'text/css; charset=utf-8'),
                              '/app.js': ('app.js', 'text/javascript; charset=utf-8')}[path]
            try:
                return 200, (ASSETS / filename).read_bytes(), mime
            except OSError as error:
                raise RemoteError(503, 'unavailable') from error
        if method == 'GET' and path == '/api/info':
            state = self.snapshot()
            return 200, {key: state[key] for key in ('theme', 'language', 'palette', 'version') if key in state}, None
        if method == 'POST' and path == '/api/pair':
            return 200, self._pair(socket.peerAddress().toString(), payload), None
        if method == 'GET' and path == '/api/state':
            self._session(headers)
            return 200, self.snapshot(), None
        if method == 'POST' and path == '/api/command':
            session = self._session(headers)
            return 200, self._command(session, payload), None
        if method == 'POST' and path == '/api/disconnect':
            self._session(headers)
            del self._sessions[headers['authorization'][7:]]
            self.changed.emit()
            return 200, {'ok': True}, None
        raise RemoteError(404, 'not_found')

    def _pair(self, peer, payload):
        now = time.monotonic()
        self._attempts[:] = [(when, source) for when, source in self._attempts if now - when < 60]
        if len(self._attempts) >= 20 or sum(source == peer for _, source in self._attempts) >= 6:
            raise RemoteError(429, 'rate_limited')
        if not self.pairing_seconds:
            raise RemoteError(410, 'pairing_expired')
        code, secret = payload.get('code', ''), payload.get('secret', '')
        valid = ((isinstance(code, str) and code.isascii() and len(code) == 6 and secrets.compare_digest(code, self._code))
                 or (isinstance(secret, str) and secret.isascii() and len(secret) <= 128 and secrets.compare_digest(secret, self._secret)))
        if not valid:
            self._attempts.append((now, peer))
            raise RemoteError(401, 'unauthorized')
        self._expire_sessions()
        if len(self._sessions) >= 6:
            raise RemoteError(409, 'busy')
        token = secrets.token_urlsafe(32)
        self._sessions[token] = {'expires': now + SESSION_SECONDS, 'commands': OrderedDict()}
        self.changed.emit()
        return {'token': token}

    def _command(self, session, payload):
        request_id = payload.get('request_id')
        if (not isinstance(request_id, str) or not 16 <= len(request_id) <= 100
                or any(not (c.isascii() and (c.isalnum() or c in '-_')) for c in request_id)):
            raise RemoteError(400, 'invalid')
        if payload.get('action') not in ('start', 'pause', 'finish', 'add'):
            raise RemoteError(400, 'invalid')
        digest = hashlib.sha256(json.dumps(payload, sort_keys=True, separators=(',', ':')).encode('utf-8')).hexdigest()
        commands = session['commands']
        if request_id in commands:
            old_digest, result, includes_state = commands[request_id]
            if old_digest != digest:
                raise RemoteError(409, 'conflict')
            return dict(result, state=self.snapshot()) if includes_state else dict(result)
        if len(commands) >= MAX_COMMANDS:
            # Não esquece IDs antigos, pois isso permitiria executar replays.
            session['expires'] = 0
            raise RemoteError(401, 'unauthorized')
        result = self.command(payload)
        # O estado pode conter uma biblioteca grande. Guarda apenas o recibo da
        # operação; uma repetição recebe o estado atual sem executar outra vez.
        commands[request_id] = (digest, {key: value for key, value in result.items() if key != 'state'}, 'state' in result)
        return result

    def _respond(self, socket, status, result, content_type=None):
        connection = self._connections.get(socket)
        if connection is None or connection['responded']:
            return
        body = result if isinstance(result, bytes) else json.dumps(result, ensure_ascii=False, allow_nan=False).encode('utf-8')
        connection['responded'] = True
        # Também limita clientes que deixam de ler a resposta, para não manter
        # sockets/bibliotecas enfileiradas indefinidamente no processo do app.
        connection['timer'].start(7000)
        content_type = content_type or 'application/json; charset=utf-8'
        reason = {200: 'OK', 400: 'Bad Request', 401: 'Unauthorized', 403: 'Forbidden', 404: 'Not Found',
                  405: 'Method Not Allowed', 409: 'Conflict', 410: 'Gone', 413: 'Payload Too Large',
                  429: 'Too Many Requests', 500: 'Internal Server Error', 503: 'Service Unavailable'}.get(status, 'Error')
        headers = (f'HTTP/1.1 {status} {reason}\r\nContent-Type: {content_type}\r\nContent-Length: {len(body)}\r\n'
                   "Cache-Control: no-store\r\nConnection: close\r\nX-Content-Type-Options: nosniff\r\n"
                   "Referrer-Policy: no-referrer\r\nX-Frame-Options: DENY\r\n"
                   "Content-Security-Policy: default-src 'none'; script-src 'self'; style-src 'self' 'unsafe-inline'; "
                   "connect-src 'self'; img-src 'self' data:; base-uri 'none'; form-action 'self'; frame-ancestors 'none'\r\n\r\n")
        socket.write(headers.encode('ascii') + body)
        socket.disconnectFromHost()
