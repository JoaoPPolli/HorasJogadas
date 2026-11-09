"""Widget OBS local e somente leitura, independente do controle pelo celular."""
import re
import secrets
from pathlib import Path
from urllib.parse import urlsplit
from PySide6.QtCore import QObject
from .remote_server import RemoteServer, RemoteError
from .desktop import write_if_changed
from . import preferences
from horas_jogadas import i18n

PORT = 48968
ASSETS = Path(__file__).with_name('assets') / 'obs'
DEFAULTS = dict(enabled=False, game='auto', scope='session', style='arcade', color='#e8cba7', show_name=False)


def read_options(folder):
    value = preferences.read(folder).get('obs', {})
    try:return validate(value)
    except ValueError:return dict(DEFAULTS)


def validate(value):
    if not isinstance(value, dict):raise ValueError('Invalid OBS options')
    result = dict(DEFAULTS, **{k:v for k,v in value.items() if k in DEFAULTS})
    if type(result['enabled']) is not bool or type(result['show_name']) is not bool:raise ValueError('Invalid boolean')
    if result['scope'] not in ('session', 'total') or result['style'] not in ('arcade', 'minimal', 'digital'):raise ValueError('Invalid style')
    if not isinstance(result['game'], str) or len(result['game']) > 128:raise ValueError('Invalid game')
    if not isinstance(result['color'], str) or not re.fullmatch(r'#[a-fA-F0-9]{6}', result['color']):raise ValueError('Invalid color')
    return result


class ObsServer(RemoteServer):
    def __init__(self, owner):
        super().__init__(owner.snapshot, lambda body: {}, owner)
        self.owner = owner

    def start(self):
        super().start('127.0.0.1', PORT)

    def _route(self, socket, method, path, headers, payload):
        if method != 'GET':raise RemoteError(405, 'read_only')
        origin = headers.get('origin')
        if origin and origin != self.url:raise RemoteError(403, 'invalid')
        if path == '/state':
            supplied = headers.get('authorization', '')
            if not self.owner.key or not secrets.compare_digest(supplied, 'Bearer ' + self.owner.key):raise RemoteError(401, 'unauthorized')
            return 200, self.owner.snapshot(), None
        files = {'/': ('index.html', 'text/html; charset=utf-8'), '/obs.css': ('obs.css', 'text/css; charset=utf-8'), '/obs.js': ('obs.js', 'text/javascript; charset=utf-8')}
        if path not in files:raise RemoteError(404, 'not_found')
        filename, mime = files[path]
        return 200, (ASSETS / filename).read_bytes(), mime


class ObsControl(QObject):
    def __init__(self, window):
        super().__init__(window)
        self.window = window
        self.key = ''
        self.last_game = None
        self.server = ObsServer(self)

    @property
    def url(self):
        return self.server.url + '/#key=' + self.key if self.server.running else ''

    def enable(self):
        path = self.window.c.folder / '.obs-key'
        if path.exists():
            key = path.read_text(encoding='ascii').strip()
            if not re.fullmatch(r'[a-f0-9]{64}', key):raise ValueError('Invalid OBS key')
        else:
            key = secrets.token_hex(32)
            write_if_changed(path, key.encode('ascii'))
        self.key = key
        if not self.server.running:self.server.start()

    def auto_start(self):
        if self.window.mode == 'release' and read_options(self.window.c.folder)['enabled']:
            try:self.enable()
            except (OSError, ValueError, RuntimeError):
                from .texts import tr
                self.window.notify(tr('obs_failed'))

    def save(self, options):
        options = validate(options)
        before = self.server.running
        if options['enabled']:self.enable()
        try:preferences.save(self.window.c.folder, obs=options)
        except Exception:
            if not before:self.server.stop()
            raise
        if not options['enabled']:self.server.stop()

    def snapshot(self):
        c = self.window.c
        options = read_options(c.folder)
        key = options['game']
        if key == 'auto':
            active = [g.id for g in c.repo.jogos if c.timers[g.id].rodando]
            paused = [g.id for g in c.repo.jogos if c.timers[g.id].pending]
            if active:self.last_game = max(active, key=lambda k:c.timers[k].retomado)
            elif paused and self.last_game not in paused:self.last_game = paused[0]
            key = self.last_game
        game = c.repo.jogo_por_id(key) if key in c.timers else None
        timer = c.timers.get(key)
        seconds = int(timer.seconds()) if timer else 0
        if game and options['scope'] == 'total':seconds += c.repo.totais_por_jogo_id().get(key, 0)
        return dict(seconds=seconds, name=game.nome if game and options['show_name'] else '',
                    paused=bool(timer and timer.pausado), style=options['style'], color=options['color'],
                    language=i18n.idioma_atual(), visible=not self.window.pending_recovery)
