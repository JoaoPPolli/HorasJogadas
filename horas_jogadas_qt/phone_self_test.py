"""Autoteste HTTP do pacote, chamado somente com a janela de dados fictícios."""
import json
import secrets
import socket
import time
from urllib.parse import urlsplit

from horas_jogadas.storage import Repositorio
from .phone_control import qr_pixmap


class _Clock:
    def __init__(self):
        self.epoch, self.mono = time.time(), time.monotonic()

    def time(self):
        return self.epoch

    def monotonic(self):
        return self.mono

    def advance(self, seconds):
        self.epoch += seconds
        self.mono += seconds


def run_phone_self_test(window, app):
    """Exercita pacote, servidor e domínio sem sair da cópia de teste."""
    if window.mode != 'review':
        raise RuntimeError('O autoteste do celular exige uma cópia isolada')
    control = window.phone_control
    server = control.server
    if server.running:
        raise RuntimeError('Controle pelo celular não iniciou desativado')
    result = {'phone_disabled_by_default': True}
    server.start('127.0.0.1')
    try:
        location = urlsplit(server.url)

        def request(path, body=None, token=None):
            payload = b'' if body is None else json.dumps(body, ensure_ascii=False).encode('utf-8')
            method = 'GET' if body is None else 'POST'
            headers = [method + ' ' + path + ' HTTP/1.1', 'Host: ' + location.netloc,
                       'Connection: close']
            if body is not None:
                headers += ['Origin: ' + server.url, 'Content-Type: application/json',
                            'Content-Length: ' + str(len(payload))]
            if token:
                headers.append('Authorization: Bearer ' + token)
            with socket.create_connection((location.hostname, location.port), timeout=3) as connection:
                connection.sendall(('\r\n'.join(headers) + '\r\n\r\n').encode('ascii') + payload)
                connection.setblocking(False)
                received = bytearray()
                deadline = time.monotonic() + 5
                while time.monotonic() < deadline:
                    app.processEvents()
                    try:
                        chunk = connection.recv(65536)
                    except BlockingIOError:
                        time.sleep(.001)
                        continue
                    if not chunk:
                        break
                    received.extend(chunk)
                    if len(received) > 1024 * 1024:
                        raise RuntimeError('Resposta excessiva no autoteste do celular')
                else:
                    raise RuntimeError('O servidor local não respondeu ao autoteste')
            head, separator, response = bytes(received).partition(b'\r\n\r\n')
            if not separator:
                raise RuntimeError('Resposta HTTP incompleta no autoteste do celular')
            lines = head.decode('ascii').split('\r\n')
            status = int(lines[0].split()[1])
            response_headers = {key.lower(): value.strip() for key, value in
                                (line.split(':', 1) for line in lines[1:])}
            if len(response) != int(response_headers.get('content-length', -1)):
                raise RuntimeError('Corpo HTTP incompleto no autoteste do celular')
            return status, json.loads(response) if response_headers['content-type'].startswith('application/json') else response

        for path in ('/', '/app.css', '/app.js', '/icon.ico'):
            status, content = request(path)
            if status != 200 or not isinstance(content, bytes) or not content:
                raise RuntimeError('Página do controle pelo celular ausente do pacote: ' + path)
        result['phone_assets'] = True
        status, _ = request('/api/state')
        if status != 401:
            raise RuntimeError('O controle pelo celular permitiu acesso sem pareamento')
        if qr_pixmap(server.pairing_url).isNull():
            raise RuntimeError('QR Code do controle pelo celular ausente')
        result['phone_qr'] = True
        status, paired = request('/api/pair', {'code': server.pairing_code})
        if status != 200 or not paired.get('token'):
            raise RuntimeError('Pareamento local do celular falhou')
        token = paired['token']
        status, state = request('/api/state', token=token)
        if status != 200 or state['games'] != control.snapshot()['games']:
            raise RuntimeError('Estado remoto diverge do aplicativo')
        result['phone_pairing'] = True

        def command(body):
            body = dict(body, request_id=secrets.token_hex(16))
            status, response = request('/api/command', body, token)
            if status != 200 or not response.get('ok'):
                raise RuntimeError('Comando local do celular falhou: ' + str(response.get('error', status)))
            return body, response

        name = 'Console — autoteste ' + secrets.token_hex(4)
        command({'action': 'add', 'name': name})
        game = next(g for g in window.c.repo.jogos if g.nome == name)
        clock = _Clock()
        window.c.timers[game.id].clock = clock

        def action(kind):
            status, state = request('/api/state', token=token)
            if status != 200:
                raise RuntimeError('O celular perdeu o pareamento durante o teste')
            current = next(g for g in state['games'] if g['id'] == game.id)
            return command({'action': kind, 'game_id': game.id, 'revision': current['revision']})

        action('start')
        clock.advance(3)
        action('pause')
        clock.advance(90)
        action('start')
        completed_body, _ = action('finish')
        sessions = [s for s in Repositorio(str(window.c.folder), config_legado='').sessoes if s.jogo_id == game.id]
        if len(sessions) != 1 or sessions[0].segundos != 3 or window.c.timers[game.id].pending:
            raise RuntimeError('A sessão do celular não foi salva uma única vez com três segundos')
        status, replayed = request('/api/command', completed_body, token)
        if status != 200 or not replayed.get('ok') or len([s for s in window.c.repo.sessoes if s.jogo_id == game.id]) != 1:
            raise RuntimeError('Repetir a resposta do celular duplicou a sessão')
        result.update(phone_commands=True, phone_seconds_saved=3, phone_replay_safe=True)
        server.regenerate_pairing()
        status, _ = request('/api/state', token=token)
        if status != 401:
            raise RuntimeError('Novo código não revogou o acesso anterior do celular')
        result['phone_revocation'] = True
    finally:
        server.stop()
        app.processEvents()
    if server.running:
        raise RuntimeError('O controle pelo celular não encerrou após o autoteste')
    result['phone_shutdown'] = True
    return result
