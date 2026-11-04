"""Operações do PC pelo controle conectado, sem diálogos bloqueantes remotos."""
import shutil
import sys
import tempfile
from datetime import datetime
from pathlib import Path

from PySide6.QtCore import QTimer, QUrl
from PySide6.QtGui import QDesktopServices

from horas_jogadas.constants import STATUS_OPCOES
from .backup import create_full, read_full
from .preview import prepare_preview
from .release import VERSION
from .remote_server import RemoteError
from .tasks import Task, Cancelled
from . import updates

GAME_ACTIONS = frozenset(('game_rename', 'game_status', 'game_move', 'timer_adjust',
                          'timer_count_pause', 'timer_discard', 'game_delete'))


class PhoneDesktop:
    actions = GAME_ACTIONS | frozenset(('device_revoke', 'device_revoke_all', 'pc_open_data',
                                       'pc_create_review', 'pending_recover', 'update_download',
                                       'update_install', 'update_cancel', 'library_order', 'control_disable'))

    def __init__(self, control):
        self.control = control
        self.release = None
        self.package = self.staged = self.work_dir = None
        self.task = None
        self.status, self.progress, self.error = 'idle', None, ''
        self.handed_off = False

    @property
    def w(self):return self.control.window

    def view(self, page, values):
        data = dict(current_version=VERSION,
                    available=dict(version=self.release.version, notes=self.release.notes) if self.release else None,
                    status=self.status, progress=self.progress, error=self.error,
                    can_install=bool(getattr(sys, 'frozen', False)), packaged=bool(getattr(sys, 'frozen', False)), busy=self.task is not None,
                    revision=self.control.workspace_revision())
        if page == 'job':
            return dict(status='running' if self.task else 'failed' if self.status == 'error' else 'done',
                        result=data, progress=self.progress or 0, total=100, error=self.error)
        return data

    def query(self, body):
        if self.task:raise RemoteError(409, 'busy')
        self.cleanup()
        self.release = None
        self.status = 'checking'
        def checked(release):
            self.release = release
            self.status = 'available' if release else 'latest'
        self.run(lambda cancel, progress: updates.check_release(), checked)
        return {'job_id': 'update'}

    def run(self, work, success):
        self.error, self.progress = '', None
        task = Task(self.w, work)
        self.task = task
        def failed(error):
            self.status = 'cancelled' if isinstance(error, Cancelled) else 'error'
            self.error = '' if isinstance(error, Cancelled) else str(error)[:1000]
        def settled():
            self.task = None
            if task.cancel.is_set():
                self.status = 'cancelled'
                self.cleanup()
            task.deleteLater()
        task.succeeded.connect(success)
        task.failed.connect(failed)
        task.progress.connect(lambda done, total: setattr(self, 'progress', min(100, int(done * 100 / total)) if total else 0))
        task.settled.connect(settled)
        task.start()

    def cleanup(self):
        if self.handed_off:return
        if self.staged and self.staged.parent.name.startswith('.horasjogadas-update-'):
            shutil.rmtree(self.staged.parent, ignore_errors=True)
        if self.work_dir:shutil.rmtree(self.work_dir, ignore_errors=True)
        self.package = self.staged = self.work_dir = None

    @staticmethod
    def confirmed(body):
        if body.get('confirmed') is not True:raise RemoteError(400, 'confirmation_required')

    def resolve_pending(self, body):
        c = self.w.c
        if any(t.pending for t in c.timers.values()) and body.get('pending') not in ('save', 'discard'):
            raise RemoteError(409, 'pending_required')
        for key, timer in c.timers.items():
            if not timer.pending:continue
            if body['pending'] == 'save':c.finish(key)
            else:timer.reset()
        c.save_pending()

    def execute(self, body):
        action = body['action']
        if action in GAME_ACTIONS:return self.game_action(body)
        if action == 'library_order':
            order = body.get('order')
            if order not in ('manual', 'nome', 'horas', 'recente'):raise RemoteError(400, 'invalid')
            with self.w.c.transaction():
                self.w.c.config['ordenacao'] = order
                self.w.c.repo.salvar_config(self.w.c.config)
        elif action == 'device_revoke':
            key = body.get('device_id')
            if not isinstance(key, str) or not self.control.trust_store.get(key):raise RemoteError(404, 'not_found')
            self.control.server.revoke_device(key)
        elif action == 'device_revoke_all':
            self.confirmed(body); self.control.server.revoke_all_devices()
        elif action == 'control_disable':
            self.confirmed(body)
            QTimer.singleShot(600, self.control.server.stop)
            return {'disconnecting': True}
        elif action == 'pc_open_data':
            if not QDesktopServices.openUrl(QUrl.fromLocalFile(str(self.w.c.folder))):raise RemoteError(503, 'unavailable')
        elif action == 'pc_create_review':
            self.confirmed(body)
            self.w.c.save_pending()
            target = self.w.c.folder.parent / ('HorasJogadas-Revisao-' + datetime.now().strftime('%Y%m%d-%H%M%S-%f'))
            prepare_preview(self.w.c.folder, target)
            return {'name': target.name, 'created': True}
        elif action == 'pending_recover':
            self.confirmed(body)
            if body.get('choice') not in ('save', 'discard'):raise RemoteError(400, 'invalid')
            read_full(create_full(self.w.c.folder))
            with self.w.c.transaction():
                if body['choice'] == 'save':self.w.c.recover()
                else:self.w.c.repo.limpar_andamento()
            self.w.pending_recovery = False
        elif action == 'update_download':
            if self.task:raise RemoteError(409, 'busy')
            if not getattr(sys, 'frozen', False):raise RemoteError(400, 'source_build')
            if self.release is None:raise RemoteError(400, 'invalid')
            root = updates.cache_directory(); root.mkdir(parents=True, exist_ok=True)
            self.work_dir = Path(tempfile.mkdtemp(prefix='v' + self.release.version + '-', dir=root))
            release, work_dir = self.release, self.work_dir
            self.status = 'downloading'
            def work(cancel, progress):
                package = updates.download(release, work_dir, cancel, progress)
                staged = updates.stage_linux(package, Path(sys.executable).resolve().parent, release.version) if sys.platform.startswith('linux') else None
                return package, staged
            def downloaded(result):
                self.package, self.staged = result
                self.status = 'ready'; self.progress = 100
            self.run(work, downloaded)
        elif action == 'update_cancel':
            if self.task:self.task.cancel.set()
            else:self.cleanup(); self.status = 'cancelled'
        elif action == 'update_install':
            self.confirmed(body)
            if self.task or not self.package:raise RemoteError(409, 'busy')
            if not getattr(sys, 'frozen', False):raise RemoteError(400, 'source_build')
            read_full(create_full(self.w.c.folder))
            with self.w.c.transaction():self.resolve_pending(body)
            read_full(create_full(self.w.c.folder))
            updates.launch_update(self.package, self.staged)
            self.handed_off = True; self.status = 'installing'
            self.w.closing_allowed = True
            QTimer.singleShot(1200, self.w.close)  # Envia o recibo HTTP antes de encerrar.
        else:raise RemoteError(400, 'invalid')
        return {}

    def game_action(self, body):
        c = self.w.c
        key = body.get('game_id')
        if not isinstance(key, str) or key not in c.timers:raise RemoteError(404, 'not_found')
        timer, game = c.timers[key], c.repo.jogo_por_id(key)
        if body.get('revision') != self.control.revision(game, timer):raise RemoteError(409, 'conflict')
        action = body['action']
        if action in ('game_delete', 'timer_discard'):
            self.confirmed(body)
            read_full(create_full(c.folder))
        with c.transaction():
            if action == 'game_rename':
                name = body.get('name')
                if not isinstance(name, str) or not name.strip() or len(name) > 200:raise RemoteError(400, 'invalid')
                c.repo.renomear_jogo(key, name)
            elif action == 'game_status':
                status = body.get('status')
                if status not in STATUS_OPCOES:raise RemoteError(400, 'invalid')
                c.set_status(key, status)
            elif action == 'game_move':
                position = body.get('position')
                if position not in ('top', 'bottom', 'before'):raise RemoteError(400, 'invalid')
                games = [g for g in c.repo.jogos if g.id != key]
                index = 0 if position == 'top' else len(games)
                if position == 'before':
                    index = next((i for i,g in enumerate(games) if g.id == body.get('before_id')), -1)
                    if index < 0:raise RemoteError(400, 'invalid')
                games.insert(index, game); c.repo.salvar_jogos(games)
            elif action == 'timer_adjust':
                seconds = body.get('seconds')
                if type(seconds) is not int or abs(seconds) > 2**31:raise RemoteError(400, 'invalid')
                timer.adjust(seconds)
            elif action == 'timer_count_pause':
                seconds = body.get('seconds')
                if seconds is not None and (type(seconds) is not int or not 0 < seconds <= 2**31):raise RemoteError(400, 'invalid')
                if not timer.pausado:raise RemoteError(409, 'conflict')
                timer.count_pause(seconds)
            elif action == 'timer_discard':timer.reset()
            elif action == 'game_delete':
                if timer.pending:
                    if body.get('pending') == 'save':c.finish(key)
                    elif body.get('pending') == 'discard':timer.reset()
                    else:raise RemoteError(409, 'pending_required')
                c.delete_game(key)
            c.save_pending()
        return {}
