"""Configurações, backups e artes do PC para o controle conectado do celular."""
import base64
import hashlib
import io
import json
import re
import secrets
import stat
import tempfile
import time
import zipfile
from pathlib import Path

from PySide6.QtCore import QObject
from PySide6.QtWidgets import QApplication
from horas_jogadas import i18n
from . import preferences
from .backup import create_full, read_full, restore_full, allowed, safe_path
from .controller import Controller
from .covers import CoverStore, normalize_image
from .remote_server import RemoteError
from .release import VERSION
from .tasks import Task, Cancelled
from .theme import PALETTES, apply_theme, translate_standard_controls

TRANSACTIONAL_ACTIONS = {'settings_save', 'art_local', 'art_remove'}
SPECIAL_ACTIONS = {'backup_create', 'backup_restore', 'backup_restore_local', 'legacy_restore', 'art_import', 'job_cancel', 'phone_import'}
ACTIONS = TRANSACTIONAL_ACTIONS | SPECIAL_ACTIONS
MAX_ZIP = 32 * 1024 * 1024
MAX_EXPANDED = 100 * 1024 * 1024
MAX_IMAGE = 10 * 1024 * 1024


def decode_data(value, maximum):
    if not isinstance(value, str) or len(value) > (maximum + 2) // 3 * 4:
        raise RemoteError(400, 'invalid')
    try:
        data = base64.b64decode(value, validate=True)
    except (ValueError, TypeError):
        raise RemoteError(400, 'invalid') from None
    if not data or len(data) > maximum:
        raise RemoteError(413, 'invalid')
    return data


def required_confirm(body):
    if body.get('confirmed') is not True:
        raise RemoteError(400, 'confirmation_required')


class PhoneManagement(QObject):
    TRANSACTIONAL_ACTIONS = TRANSACTIONAL_ACTIONS
    SPECIAL_ACTIONS = SPECIAL_ACTIONS

    def __init__(self, control):
        super().__init__(control)
        self.control = control
        self.jobs = {}
        self.tickets = {}
        self.candidates = {}

    @property
    def w(self):
        return self.control.window

    def _revision(self):
        return self.control.workspace_revision()

    def _expire(self):
        now = time.monotonic()
        for key, ticket in list(self.tickets.items()):
            if ticket['expires'] < now:
                if ticket.get('temporary'): ticket['temporary'].cleanup()
                del self.tickets[key]
        for key, job in list(self.jobs.items()):
            if job['status'] != 'running' and job['expires'] < now:
                del self.jobs[key]
                self.candidates.pop(key, None)

    def _full_backup(self, key):
        if not isinstance(key, str) or not re.fullmatch(r'[0-9-]{8,40}', key):
            raise RemoteError(404, 'not_found')
        path = self.w.c.folder / 'full-backups' / key
        if not path.is_dir() or not safe_path(self.w.c.folder, path):
            raise RemoteError(404, 'not_found')
        read_full(path)
        return path

    def _legacy(self):
        result = {}
        for info in self.w.c.repo.listar_backups():
            path = Path(info.caminho)
            if safe_path(self.w.c.folder, path):
                identifier = hashlib.sha256(str(path.relative_to(self.w.c.folder)).encode()).hexdigest()[:24]
                result[identifier] = info
        return result

    def view(self, page, query=None):
        query = query or {}
        self._expire()
        if page == 'settings':
            prefs = preferences.read(self.w.c.folder)
            return dict(theme=self.w.theme_name(), language=i18n.idioma_atual(),
                        check_updates=bool(prefs.get('check_updates', True)),
                        covers_enabled=bool(prefs.get('covers_enabled', False)),
                        icons_enabled=bool(prefs.get('icons_enabled', True)), revision=self._revision())
        if page == 'devices':
            return dict(devices=self.control.server.remembered_devices, revision=self._revision())
        if page == 'backups':
            full = []
            root = self.w.c.folder / 'full-backups'
            if root.is_dir() and safe_path(self.w.c.folder, root):
                for path in sorted(root.iterdir(), reverse=True)[:200]:
                    try:
                        if not path.is_dir() or not safe_path(self.w.c.folder, path): continue
                        manifest = path / 'manifest.json'
                        if not safe_path(self.w.c.folder, manifest) or manifest.stat().st_size > 1024*1024:continue
                        payload = json.loads(manifest.read_text(encoding='utf-8'))
                        if not isinstance(payload, dict) or not all(allowed(name) and isinstance(digest, str) and re.fullmatch(r'[a-f0-9]{64}', digest) for name,digest in payload.items()):continue
                        # A lista usa metadados; todos os bytes serão verificados
                        # ao baixar/restaurar, sem reler centenas de capas aqui.
                        full.append(dict(id=path.name, created=path.name, files=len(payload)))
                    except (OSError, ValueError):
                        continue
            legacy = [dict(id=key, created=info.momento.isoformat(), games=info.jogos,
                           sessions=info.sessoes, type=info.tipo) for key, info in self._legacy().items()]
            return dict(full=full, legacy=legacy, revision=self._revision())
        if page == 'artwork':
            covers, icons = CoverStore(self.w.c.folder), CoverStore(self.w.c.folder, 'icon')
            return dict(games=[dict(id=g.id, name=g.nome, has_cover=bool(covers.path(g.id)),
                                    has_icon=bool(icons.path(g.id))) for g in self.w.c.repo.jogos],
                        sources=dict(cover=['Steam', 'GOG', 'Wikipedia'], icon=['Steam', 'GOG']), revision=self._revision())
        if page == 'job':
            job = self.jobs.get(query.get('id'))
            if not job: raise RemoteError(404, 'not_found')
            return {key: value for key, value in job.items() if key not in ('task', 'expires')}
        if page == 'updates':
            import sys
            return dict(version=VERSION, packaged=bool(getattr(sys, 'frozen', False)))
        raise RemoteError(404, 'not_found')

    def _start_job(self, work, apply=None):
        self._expire()
        if sum(job['status'] == 'running' for job in self.jobs.values()) >= 2 or len(self.jobs) >= 32:
            raise RemoteError(409, 'busy')
        identifier = secrets.token_hex(16)
        job = dict(id=identifier, status='running', progress=dict(done=0, total=0), result=None,
                   expires=time.monotonic() + 600)
        self.jobs[identifier] = job
        task = Task(self.w, work)
        job['task'] = task
        task.progress.connect(lambda done, total: job.update(progress=dict(done=done, total=total)))
        def succeeded(result):
            try:
                if task.cancel.is_set():
                    job.update(status='cancelled'); return
                value = apply(result, identifier) if apply else result
                job.update(status='complete', result=value, expires=time.monotonic() + 600)
            except RemoteError as error:
                job.update(status='failed', error=error.code)
            except Exception:
                job.update(status='failed', error='storage')
        def failed(error):
            job.update(status='cancelled' if isinstance(error, Cancelled) else 'failed', error='cancelled' if isinstance(error, Cancelled) else 'unavailable')
        task.succeeded.connect(succeeded); task.failed.connect(failed)
        def settled():
            job.pop('task', None)
            task.deleteLater()
        task.settled.connect(settled)
        task.start()
        return dict(job_id=identifier)

    def _ticket(self, temporary=None, **details):
        self._expire()
        if len(self.tickets) >= 8:
            if temporary: temporary.cleanup()
            raise RemoteError(409, 'busy')
        identifier = secrets.token_hex(24)
        self.tickets[identifier] = dict(expires=time.monotonic() + 300, temporary=temporary, **details)
        return identifier

    def query(self, body):
        self._expire()
        kind = body.get('query')
        if kind == 'backup_restore_preview':
            data = decode_data(body.get('data'), MAX_ZIP)
            temporary = tempfile.TemporaryDirectory(prefix='horas-phone-restore-')
            path = Path(temporary.name)
            try:
                with zipfile.ZipFile(io.BytesIO(data)) as archive:
                    infos = archive.infolist()
                    if not infos or len(infos) > 2000 or sum(info.file_size for info in infos) > MAX_EXPANDED:
                        raise ValueError('Invalid size')
                    names = set()
                    for info in infos:
                        name = info.filename
                        mode = info.external_attr >> 16
                        if (name in names or name not in ('manifest.json',) and not allowed(name)
                                or info.is_dir() or info.flag_bits & 1 or stat.S_ISLNK(mode)
                                or info.file_size < 0 or info.file_size > MAX_EXPANDED):
                            raise ValueError('Invalid archive')
                        names.add(name)
                        target = path / name; target.parent.mkdir(parents=True, exist_ok=True)
                        with archive.open(info) as source:
                            content = source.read(info.file_size + 1)
                        if len(content) != info.file_size: raise ValueError('Invalid archive')
                        target.write_bytes(content)
                payload = read_full(path)
                # Loading legacy data may migrate files. Validate on a separate
                # copy so the signed payload and its manifest remain untouched.
                for filename, content in payload.items():
                    if filename.endswith('.json'):
                        value = json.loads(content)
                        expected = list if filename in ('cronometros.json', 'registros.json', 'em_andamento.json') else dict
                        if not isinstance(value, expected): raise ValueError('Invalid core JSON')
                with tempfile.TemporaryDirectory(prefix='horas-phone-validate-') as validation:
                    validation_path = Path(validation)
                    for filename, content in payload.items():
                        target = validation_path / filename; target.parent.mkdir(parents=True, exist_ok=True); target.write_bytes(content)
                    check = Controller(validation_path)
                    counts = dict(games=len(check.repo.jogos), sessions=len(check.repo.sessoes),
                                  completions=len(check.zerados.registros), has_pending=bool(check.repo.carregar_andamento()))
                ticket = self._ticket(temporary, path=path, type='backup')
                return dict(ticket=ticket, files=len(payload), **counts)
            except Exception:
                temporary.cleanup()
                raise RemoteError(400, 'invalid') from None
        if kind == 'phone_import_preview':
            from .phone_import import parse_mobile, suggested_destination
            records = parse_mobile(decode_data(body.get('data'), 1024 * 1024))
            ticket = self._ticket(records=records, type='phone')
            existing = {s.sessao_id for s in self.w.c.repo.sessoes}
            return dict(ticket=ticket, records=[dict(index=i, name=r.game, seconds=r.seconds,
                start=r.started_at.isoformat(), end=r.ended_at.isoformat(), duplicate=r.session_id in existing,
                destination_id=suggested_destination(self.w.c, r)) for i, r in enumerate(records)])
        if kind == 'art_search':
            from .artwork_sources import search_artwork
            image_kind = self._kind(body)
            source = body.get('source')
            if source in ('all', '', None): source = None
            available = ('Steam', 'GOG', 'Wikipedia') if image_kind == 'cover' else ('Steam', 'GOG')
            if source is not None and source not in available: raise RemoteError(400, 'invalid')
            titles = body.get('titles')
            if not isinstance(titles, list) or not 1 <= len(titles) <= 100: raise RemoteError(400, 'invalid')
            cleaned = []
            for title in titles:
                if not isinstance(title, dict) or title.get('game_id') not in self.w.c.timers or not isinstance(title.get('title'), str) or not 1 <= len(title['title'].strip()) <= 200:
                    raise RemoteError(400, 'invalid')
                cleaned.append((title['game_id'], title['title'].strip()))
            def work(cancel, progress):
                games = []
                for index, (game_id, title) in enumerate(cleaned):
                    if cancel.is_set(): raise Cancelled()
                    candidates = search_artwork(title, source=source, kind=image_kind, cancel=cancel)
                    games.append((game_id, title, list(candidates)[:15]))
                    progress(index + 1, len(cleaned))
                return games
            def apply(result, identifier):
                stored = {}
                games = []
                for game_id, title, candidates in result:
                    values = []
                    for candidate in candidates:
                        key = secrets.token_hex(16)
                        stored[key] = dict(candidate=candidate, game_id=game_id, kind=image_kind)
                        values.append(dict(id=key, name=candidate.name, source=candidate.source,
                                           score=candidate.score, page_url=candidate.page))
                    games.append(dict(game_id=game_id, title=title, candidates=values))
                self.candidates[identifier] = stored
                return dict(games=games)
            return self._start_job(work, apply)
        if kind == 'art_preview':
            selected = self._candidate(body.get('job_id'), body.get('candidate_id'))
            from .artwork_sources import download_artwork
            return self._start_job(lambda cancel, progress: dict(data=base64.b64encode(
                download_artwork(selected['candidate'], cancel, kind=selected['kind'])).decode('ascii'),
                mime='image/png' if selected['kind'] == 'icon' else 'image/jpeg'))
        raise RemoteError(400, 'invalid')

    @staticmethod
    def _kind(body):
        kind = body.get('kind')
        if kind not in ('cover', 'icon'): raise RemoteError(400, 'invalid')
        return kind

    def _candidate(self, job_id, candidate_id):
        self._expire()
        value = self.candidates.get(job_id, {}).get(candidate_id)
        if value is None: raise RemoteError(404, 'not_found')
        return value

    def _backup_now(self):
        if self.w.pending_recovery:
            raise RemoteError(409, 'recovery')
        self.w.c.save_pending()
        path = create_full(self.w.c.folder); read_full(path)
        return path

    def _resolve_pending(self, body):
        pending = [t for t in self.w.c.timers.values() if t.pending]
        if pending and body.get('pending') not in ('save', 'discard'):
            raise RemoteError(409, 'pending_required')
        for key, timer in self.w.c.timers.items():
            if not timer.pending: continue
            if body['pending'] == 'save': self.w.c.finish(key)
            else: timer.reset()
        self.w.c.save_pending()

    def _restore(self, body, path=None, legacy=None):
        required_confirm(body)
        controller = self.w.c
        if any(t.pending for t in controller.timers.values()) and body.get('pending') not in ('save', 'discard'):
            raise RemoteError(409, 'pending_required')
        if path is not None:
            data = read_full(path)
            if json.loads(data.get('em_andamento.json', b'[]')) and body.get('recovery') not in ('save', 'discard'):
                raise RemoteError(409, 'recovery_required')
        before = self._backup_now()
        with controller.transaction():
            self._resolve_pending(body)
            if legacy is not None: controller.repo.restaurar_backup(legacy)
            else: restore_full(controller.folder, path)
            replacement = Controller(controller.folder)
            if replacement.repo.carregar_andamento():
                if body.get('recovery') == 'save': replacement.recover()
                else: replacement.repo.limpar_andamento()
        self.w.c = replacement
        self.w.pending_recovery = False
        self.control.invalidate()
        self._refresh()
        return dict(restored=True, previous_backup=before.name)

    def execute(self, body):
        action = body.get('action')
        if action == 'settings_save':
            changes = {}
            if 'theme' in body:
                if body['theme'] not in PALETTES: raise RemoteError(400, 'invalid')
                changes['theme'] = body['theme']
            if 'language' in body:
                if body['language'] not in ('pt', 'en'): raise RemoteError(400, 'invalid')
                self.w.c.config['idioma'] = body['language']
                self.w.c.repo.salvar_config(self.w.c.config)
            for key in ('check_updates', 'covers_enabled', 'icons_enabled'):
                if key in body:
                    if type(body[key]) is not bool: raise RemoteError(400, 'invalid')
                    changes[key] = body[key]
            preferences.save(self.w.c.folder, **changes)
            return dict(saved=True)
        if action in ('art_local', 'art_remove'):
            kind = self._kind(body)
            game_id = body.get('game_id')
            if game_id not in self.w.c.timers: raise RemoteError(404, 'not_found')
            store = CoverStore(self.w.c.folder, kind)
            if action == 'art_remove': store.remove(game_id)
            else: store.save_many([(game_id, normalize_image(decode_data(body.get('data'), MAX_IMAGE), kind), {'source': 'local'})])
            return dict(saved=True)
        if action == 'backup_create':
            return dict(id=self._backup_now().name)
        if action in ('backup_restore', 'backup_restore_local'):
            if action == 'backup_restore':
                self._expire(); ticket = self.tickets.get(body.get('ticket'))
                if ticket is None or ticket.get('type') != 'backup': raise RemoteError(409, 'expired')
                path = ticket['path']
            else: path = self._full_backup(body.get('id'))
            return self._restore(body, path=path)
        if action == 'legacy_restore':
            legacy = self._legacy().get(body.get('id'))
            if not legacy: raise RemoteError(404, 'not_found')
            return self._restore(body, legacy=legacy)
        if action == 'phone_import':
            from dataclasses import replace
            from .phone_import import import_mobile
            self._expire(); ticket = self.tickets.get(body.get('ticket'))
            if ticket is None or ticket.get('type') != 'phone': raise RemoteError(409, 'expired')
            indices, destinations = body.get('selected'), body.get('destinations', {})
            if not isinstance(indices, list) or not isinstance(destinations, dict) or not indices or any(type(i) is not int or not 0 <= i < len(ticket['records']) for i in indices) or len(set(indices)) != len(indices):
                raise RemoteError(400, 'invalid')
            records = [replace(ticket['records'][i], destination_id=destinations.get(str(i), '')) for i in indices]
            result = import_mobile(self.w.c, records)
            self.control.invalidate(); self._refresh()
            return {key: value for key, value in result.items() if key != 'backup'}
        if action == 'art_import':
            kind = self._kind(body)
            records = body.get('selected')
            if not isinstance(records, list) or not 1 <= len(records) <= 100: raise RemoteError(400, 'invalid')
            chosen = []
            for item in records:
                if not isinstance(item, dict): raise RemoteError(400, 'invalid')
                candidate = self._candidate(body.get('job_id'), item.get('candidate_id'))
                if candidate['kind'] != kind or candidate['game_id'] != item.get('game_id') or item.get('game_id') not in self.w.c.timers:
                    raise RemoteError(400, 'invalid')
                chosen.append((item['game_id'], candidate['candidate']))
            revision = self._revision()
            from .artwork_sources import download_artwork
            def work(cancel, progress):
                result = []; total_bytes = 0
                for i, (game_id, candidate) in enumerate(chosen):
                    image = download_artwork(candidate, cancel, kind=kind)
                    total_bytes += len(image)
                    if total_bytes > MAX_ZIP: raise ValueError('Artwork import too large')
                    result.append((game_id, image, dict(source=candidate.source, page=candidate.page, app_id=candidate.app_id)))
                    progress(i + 1, len(chosen))
                return result
            def apply(result, identifier):
                if revision != self._revision(): raise RemoteError(409, 'conflict')
                if QApplication.activeModalWidget() is not None: raise RemoteError(409, 'busy')
                with self.w.c.transaction():
                    CoverStore(self.w.c.folder, kind).save_many(result)
                self.control.invalidate(); self._refresh()
                return dict(imported=len(result))
            return self._start_job(work, apply)
        if action == 'job_cancel':
            job = self.jobs.get(body.get('job_id'))
            if not job: raise RemoteError(404, 'not_found')
            task = job.get('task')
            if task is not None:
                task.cancel.set()
            else:
                self.jobs.pop(body.get('job_id'), None)
                self.candidates.pop(body.get('job_id'), None)
            return dict(cancelled=True)
        raise RemoteError(400, 'invalid')

    def apply_ui(self):
        apply_theme(QApplication.instance(), self.w.theme_name())
        i18n.definir_idioma(self.w.c.config['idioma'])
        translate_standard_controls(QApplication.instance(), self.w.c.config['idioma'])
        old = self.w.centralWidget()
        page = self.w.page
        self.w.build_shell()
        if old: old.deleteLater()
        self.w.navigate(page)

    def _refresh(self):
        self.w.totals = self.w.c.repo.totais_por_jogo_id()
        self.w.refresh()
        self.w.update_activity()

    def export(self, kind, query=None):
        if kind != 'full_backup': raise RemoteError(404, 'not_found')
        query = query or {}
        path = self._full_backup(query['id']) if query.get('id') else self._backup_now()
        data = read_full(path)
        result = io.BytesIO()
        with zipfile.ZipFile(result, 'w', zipfile.ZIP_DEFLATED) as archive:
            archive.writestr('manifest.json', json.dumps({name: hashlib.sha256(content).hexdigest() for name, content in data.items()}))
            for name, content in data.items(): archive.writestr(name, content)
        if len(result.getbuffer()) > MAX_ZIP: raise RemoteError(413, 'invalid')
        return result.getvalue(), 'application/zip', 'HorasJogadas-backup-' + path.name + '.zip'
