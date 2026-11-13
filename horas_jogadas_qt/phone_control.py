"""Controle pelo celular: conexão voluntária e operações na thread da interface."""
import hashlib
import ipaddress
import json
import secrets
from dataclasses import asdict

from PySide6.QtCore import QObject, QTimer, Qt, QRectF, QUrl
from PySide6.QtGui import QColor, QPainter, QPixmap, QDesktopServices
from PySide6.QtNetwork import QAbstractSocket, QNetworkInterface
from PySide6.QtWidgets import QApplication, QFrame, QVBoxLayout, QHBoxLayout, QComboBox, QLineEdit, QDialog

from horas_jogadas import i18n
from horas_jogadas.i18n import t_status
from .remote_server import RemoteServer, RemoteError
from .release import VERSION
from .theme import PALETTES
from .texts import tr
from .widgets import label, button, row
from . import preferences
from .trusted_devices import TrustStore

COMPANION_URL = 'https://joaoppolli.github.io/HorasJogadas/celular/'
PHONE_PORT = 48967


def local_addresses():
    """Endereços IPv4 privados das interfaces ativas; sem sondar a internet."""
    networks = [ipaddress.ip_network(s) for s in ('10.0.0.0/8', '172.16.0.0/12', '192.168.0.0/16')]
    result = []
    for interface in QNetworkInterface.allInterfaces():
        flags = interface.flags()
        if not flags & QNetworkInterface.IsUp or not flags & QNetworkInterface.IsRunning or flags & QNetworkInterface.IsLoopBack:
            continue
        for entry in interface.addressEntries():
            address = entry.ip()
            if address.protocol() == QAbstractSocket.IPv4Protocol:
                value = address.toString()
                if any(ipaddress.ip_address(value) in network for network in networks):
                    priority = 0 if interface.type() in (QNetworkInterface.Wifi, QNetworkInterface.Ethernet) else 1
                    result.append((priority, value, interface.humanReadableName()))
    return [(value, name) for _, value, name in sorted(set(result))]


def qr_pixmap(value, pixels=196):
    import qrcode
    qr = qrcode.QRCode(error_correction=qrcode.constants.ERROR_CORRECT_M, border=4)
    qr.add_data(value); qr.make(fit=True)
    matrix = qr.get_matrix()
    scale = max(1, pixels // len(matrix))
    pixmap = QPixmap(len(matrix) * scale, len(matrix) * scale)
    pixmap.fill(Qt.white)
    painter = QPainter(pixmap)
    painter.setPen(Qt.NoPen); painter.setBrush(QColor('#101215'))
    for y, cells in enumerate(matrix):
        for x, filled in enumerate(cells):
            if filled:
                painter.drawRect(QRectF(x * scale, y * scale, scale, scale))
    painter.end()
    return pixmap


class PhoneControl(QObject):
    def __init__(self, window):
        super().__init__(window)
        self.window = window
        self.serial = 0
        self.nonce = secrets.token_hex(16)
        self.trust_store = TrustStore(window.c.folder)
        from .phone_records import PhoneRecords
        from .phone_management import PhoneManagement
        from .phone_desktop import PhoneDesktop
        self.records = PhoneRecords(self)
        self.management = PhoneManagement(self)
        self.desktop = PhoneDesktop(self)
        from .phone_insights import PhoneInsights
        self.insights = PhoneInsights(self)
        self.actions = frozenset(('start', 'pause', 'finish', 'add', 'favorite')) | self.records.actions | self.management.TRANSACTIONAL_ACTIONS | self.management.SPECIAL_ACTIONS | self.desktop.actions
        self.server = RemoteServer(self.snapshot, self.command, self,
                                   trust_store=self.trust_store, media=self.media, library=self.library,
                                   view=self.view, query=self.query, export=self.export, actions=self.actions)

    def auto_start(self, attempt=0):
        if self.window.mode != 'release' or self.server.running or not preferences.read(self.window.c.folder).get('phone_auto_start', False):
            return
        addresses = [address for address, _ in local_addresses()]
        preferred = preferences.read(self.window.c.folder).get('phone_host')
        address = preferred if preferred in addresses else addresses[0] if addresses else None
        if address:
            try:
                self.server.start(address, PHONE_PORT)
                return
            except (OSError, ValueError, RuntimeError):pass
        if attempt < 19:
            QTimer.singleShot(3000, self, lambda: self.auto_start(attempt + 1))
        else:self.window.notify(tr('phone_failed'))

    def invalidate(self):
        self.serial += 1

    def revision(self, game, timer):
        fields = (self.nonce, self.serial, game.id, game.nome, game.status, timer.rodando,
                  timer.acumulado, str(timer.inicio), timer.retomado, timer.mono, timer.pausa,
                  sorted((str(day), seconds) for day, seconds in timer.dias.items()))
        return hashlib.sha256(json.dumps(fields, ensure_ascii=False).encode()).hexdigest()

    def workspace_revision(self):
        c = self.window.c
        fields = [self.nonce, self.serial, c.config, preferences.read(c.folder),
                  [g.to_dict() for g in c.repo.jogos], [s.to_dict() for s in c.repo.sessoes],
                  [asdict(r) for r in c.zerados.registros],
                  [self.revision(g, c.timers[g.id]) for g in c.repo.jogos]]
        return hashlib.sha256(json.dumps(fields, sort_keys=True, ensure_ascii=False).encode()).hexdigest()

    def view(self, page, values):
        if page in ('game','recap'):return self.insights.view(page,values)
        if page in ('history', 'stats', 'completed'):
            return self.records.view(page, values)
        if page == 'updates' or page == 'job' and values.get('id') == 'update':
            return self.desktop.view(page, values)
        return self.management.view(page, values)

    def query(self, body):
        if not isinstance(body, dict):raise RemoteError(400, 'invalid')
        if body.get('query') == 'recap_preview':return self.insights.preview(body)
        if body.get('query') == 'completion_extra':
            self.ensure_ready()
            return self.records.preview_extra(body)
        if body.get('query') == 'completion_import':
            return self.records.preview_import(body.get('text'), body.get('year'))
        if body.get('query') == 'update_check':
            self.ensure_ready()
            return self.desktop.query(body)
        return self.management.query(body)

    def export(self, kind, values):
        if kind == 'recap_png':return self.insights.export(values)
        if kind == 'full_backup' and not values.get('id'):
            self.ensure_ready()
        if kind in ('history_csv', 'summary_csv', 'completions_txt'):
            return self.records.export(kind, values)
        return self.management.export(kind, values)

    def ensure_ready(self, action=''):
        if self.window.pending_recovery and action != 'pending_recover':
            raise RemoteError(409, 'recovery')
        if QApplication.activeModalWidget() is not None:
            raise RemoteError(409, 'busy')

    def refresh_desktop(self):
        w = self.window
        w.totals = w.c.repo.totais_por_jogo_id()
        try:
            w.refresh()
            w.update_activity()
        except Exception:
            import logging
            logging.getLogger('horas_jogadas').exception('Falha ao redesenhar após comando do celular')

    def desktop_command(self, body):
        action = body.get('action')
        self.ensure_ready(action)
        if body.get('workspace_revision') != self.workspace_revision():
            raise RemoteError(409, 'conflict')
        if action in self.desktop.actions:
            result = self.desktop.execute(body)
        elif action in self.records.actions:
            if self.records.needs_backup(action):
                from .backup import create_full, read_full
                read_full(create_full(self.window.c.folder))
            with self.window.c.transaction():
                result = self.records.execute(body)
            self.records.after_commit(body, result)
        elif action in self.management.TRANSACTIONAL_ACTIONS:
            with self.window.c.transaction():
                result = self.management.execute(body)
            if action == 'settings_save':self.management.apply_ui()
        elif action in self.management.SPECIAL_ACTIONS:
            result = self.management.execute(body)
            if action in ('backup_restore', 'backup_restore_local', 'legacy_restore'):
                self.management.apply_ui()
        else:
            raise RemoteError(400, 'invalid')
        if action not in ('art_import', 'job_cancel', 'update_download', 'update_cancel', 'pc_open_data', 'pc_create_review', 'backup_create'):
            self.invalidate()
        self.refresh_desktop()
        return dict(result or {}, ok=True, state=self.snapshot())

    def snapshot(self):
        w = self.window
        theme = w.theme_name()
        palette = dict(zip(('bg', 'side', 'card', 'border', 'text', 'muted', 'accent', 'on_accent'),
                           PALETTES.get(theme, PALETTES['dark'])))
        totals = w.c.repo.totais_por_jogo_id()
        from horas_jogadas.stats import ultima_sessao_por_jogo_id
        latest = ultima_sessao_por_jogo_id(w.c.repo.sessoes)
        prefs = preferences.read(w.c.folder)
        favorites = prefs.get('phone_favorites', [])
        favorites = set(value for value in favorites if isinstance(value, str)) if isinstance(favorites, list) else set()
        covers, icons = bool(prefs.get('covers_enabled', False)), bool(prefs.get('icons_enabled', True))
        from .covers import CoverStore
        stores = {'cover': CoverStore(w.c.folder), 'icon': CoverStore(w.c.folder, 'icon')}
        games = []
        for game in w.c.repo.jogos:
            timer = w.c.timers[game.id]
            seconds = timer.seconds()
            art = {}
            for kind, enabled in (('cover', covers), ('icon', icons)):
                path = stores[kind].path(game.id) if enabled else None
                art[kind] = f'/api/art/{kind}/{game.id}?v={path.stem}' if path else None
            games.append(dict(id=game.id, name=game.nome, status=game.status, status_label=t_status(game.status),
                              total_seconds=totals.get(game.id, 0) + seconds, seconds=seconds,
                              running=timer.rodando, paused=timer.pausado, pending=timer.pending,
                              revision=self.revision(game, timer), favorite=game.id in favorites, art=art,
                              pause_seconds=max(0, int(timer.clock.time()-timer.pausa)) if timer.pausado else 0))
            games[-1]['last_played'] = latest[game.id].isoformat() if game.id in latest else None
        return dict(theme=theme, language=i18n.idioma_atual(), palette=palette, version=VERSION,
                    games=games, active_count=sum(g['running'] for g in games),
                    pending_recovery=w.pending_recovery, covers_enabled=covers, icons_enabled=icons,
                    companion_url=COMPANION_URL, workspace_revision=self.workspace_revision(),
                    library_order=w.c.config.get('ordenacao', 'manual'))

    def media(self, game_id, kind):
        from .backup import safe_path
        from .covers import CoverStore
        w = self.window
        prefs = preferences.read(w.c.folder)
        enabled = prefs.get('covers_enabled', False) if kind == 'cover' else prefs.get('icons_enabled', True)
        if kind not in ('cover', 'icon') or not enabled or game_id not in w.c.timers:
            raise RemoteError(404, 'not_found')
        path = CoverStore(w.c.folder, kind).path(game_id)
        if path is None or not safe_path(w.c.folder, path):
            raise RemoteError(404, 'not_found')
        with path.open('rb') as stream:
            data = stream.read(10 * 1024 * 1024 + 1)
        signature = b'\x89PNG\r\n\x1a\n' if kind == 'icon' else b'\xff\xd8\xff'
        if len(data) > 10 * 1024 * 1024 or not data.startswith(signature) or hashlib.sha256(data).hexdigest() != path.stem:
            raise RemoteError(404, 'not_found')
        return data, 'image/png' if kind == 'icon' else 'image/jpeg'

    def library(self):
        from .phone_import import export_library
        return json.loads(export_library(self.window.c, self.window.theme_name(), i18n.idioma_atual()))

    def command(self, body):
        w = self.window
        if isinstance(body, dict) and body.get('action') not in ('start', 'pause', 'finish', 'add', 'favorite'):
            try:
                return self.desktop_command(body)
            except RemoteError:raise
            except (ValueError, TypeError, KeyError):raise RemoteError(400, 'invalid') from None
            except Exception:raise RemoteError(500, 'storage') from None
        if w.pending_recovery:
            raise RemoteError(409, 'recovery')
        if QApplication.activeModalWidget() is not None:
            raise RemoteError(409, 'busy')
        if not isinstance(body, dict) or set(body) - {'request_id', 'action', 'game_id', 'revision', 'name', 'enabled', 'workspace_revision'}:
            raise RemoteError(400, 'invalid')
        action = body.get('action')
        if action not in ('start', 'pause', 'finish', 'add', 'favorite'):
            raise RemoteError(400, 'invalid')
        if action == 'add':
            name = body.get('name')
            if not isinstance(name, str) or not name.strip() or len(name) > 200:
                raise RemoteError(400, 'invalid')
            callback = lambda: w.c.add_game(name)
        else:
            key = body.get('game_id')
            if not isinstance(key, str) or key not in w.c.timers:
                raise RemoteError(404, 'not_found')
            game, timer = w.c.repo.jogo_por_id(key), w.c.timers[key]
            if not isinstance(body.get('revision'), str) or body['revision'] != self.revision(game, timer):
                raise RemoteError(409, 'conflict')
            if action == 'pause' and not timer.rodando or action == 'finish' and not timer.pending:
                raise RemoteError(409, 'conflict')
            if action == 'favorite':
                if not isinstance(body.get('enabled'), bool):
                    raise RemoteError(400, 'invalid')
                def callback():
                    favorites = preferences.read(w.c.folder).get('phone_favorites', [])
                    favorites = {value for value in favorites if isinstance(value, str) and value in w.c.timers} if isinstance(favorites, list) else set()
                    if body['enabled']:
                        favorites.add(key)
                    else:
                        favorites.discard(key)
                    preferences.save(w.c.folder, phone_favorites=sorted(favorites))
            else:
                callback = (lambda: w.c.finish(key)) if action == 'finish' else getattr(timer, action)
        before_sessions = {s.sessao_id for s in w.c.repo.sessoes} if action == 'finish' else set()
        try:
            with w.c.transaction():
                callback()
                w.c.save_pending()
        except ValueError:
            raise RemoteError(400, 'invalid') from None
        except Exception:
            raise RemoteError(500, 'storage') from None
        self.invalidate()
        w.totals = w.c.repo.totais_por_jogo_id()
        try:
            if action == 'add' or (action == 'finish' and w.page in ('history', 'stats')):
                w.refresh()
            elif w.page == 'library':
                for card in w.cards.values():
                    card.update_timer()
                w.reorder_cards()
            w.update_activity()
        except Exception:
            # O comando já foi salvo: uma falha de desenho não pode informar
            # falha e levar o celular a enviar uma segunda adição de jogo.
            import logging
            logging.getLogger('horas_jogadas').exception('Falha ao atualizar a interface após comando do celular')
        result = {'ok': True, 'state': self.snapshot()}
        if action == 'finish':
            saved = next((s for s in reversed(w.c.repo.sessoes) if s.sessao_id not in before_sessions), None)
            result['summary'] = dict(game=game.nome, seconds=saved.segundos if saved else 0,
                                     total_seconds=w.c.repo.totais_por_jogo_id().get(key, 0))
        return result


class PhoneControlCard(QFrame):
    def __init__(self, control, parent=None):
        super().__init__(parent)
        self.control, self.server = control, control.server
        self.setObjectName('phoneControlCard')
        # Usa a mesma superfície, margens e hierarquia dos outros cartões.
        self.setProperty('phoneCard', True)
        box = QVBoxLayout(self); box.setContentsMargins(22, 20, 22, 20); box.setSpacing(14)
        box.addWidget(label(tr('phone_title'), 'gameName'))
        box.addWidget(label(tr('phone_intro'), 'muted', True))
        self.status = label('', 'badge'); box.addWidget(self.status)
        self.network = QComboBox(); self.network.setAccessibleName(tr('phone_network'))
        self.refresh_button = button(tr('phone_refresh'), self.find_networks)
        self.network_row = row(self.network, self.refresh_button)
        self.network_row.layout().setStretch(0, 1)
        box.addWidget(self.network_row)
        self.start_button = button(tr('phone_enable'), self.enable, 'primary')
        box.addWidget(self.start_button)
        self.help = label('', 'muted', True); box.addWidget(self.help)
        self.details = QFrame(); details_box = QHBoxLayout(self.details)
        details_box.setContentsMargins(0, 0, 0, 0); details_box.setSpacing(20)
        self.qr = label(''); self.qr.setFixedSize(196, 196); self.qr.setAlignment(Qt.AlignCenter)
        self.qr.setAccessibleName(tr('phone_qr'))
        details_box.addWidget(self.qr, 0, Qt.AlignTop)
        instructions = QVBoxLayout(); instructions.setSpacing(10)
        instructions.addWidget(label(tr('phone_scan'), '', True))
        self.url = QLineEdit(); self.url.setReadOnly(True); self.url.setAccessibleName(tr('phone_address'))
        instructions.addWidget(self.url)
        instructions.addWidget(button(tr('phone_copy'), self.copy_address))
        instructions.addWidget(label(tr('phone_manual'), 'muted', True))
        self.code = label('', 'timer'); self.code.setTextInteractionFlags(Qt.TextSelectableByMouse)
        instructions.addWidget(self.code)
        self.expires = label('', 'muted', True); instructions.addWidget(self.expires)
        instructions.addStretch(); details_box.addLayout(instructions, 1)
        box.addWidget(self.details)
        self.clients = label('', 'muted', True); box.addWidget(self.clients)
        self.renew_button = button(tr('phone_renew'), self.renew)
        self.stop_button = button(tr('phone_disable'), self.server.stop, 'danger')
        self.actions = row(self.renew_button, self.stop_button, None); box.addWidget(self.actions)
        self.devices = QFrame(); self.devices_box = QVBoxLayout(self.devices)
        self.devices_box.setContentsMargins(0, 0, 0, 0); self.devices_box.setSpacing(8)
        box.addWidget(self.devices); self.last_devices = None
        box.addWidget(label(tr('phone_local_help'), 'muted', True))
        self.error = label('', 'muted', True); box.addWidget(self.error)
        self.server.changed.connect(self.update_status)
        self.timer = QTimer(self); self.timer.setInterval(1000); self.timer.timeout.connect(self.update_status)
        self.timer.start(); self.last_qr = None
        self.find_networks(); self.update_status()

    def find_networks(self):
        previous = self.network.currentData()
        self.network.clear()
        for address, name in local_addresses():
            self.network.addItem(f'{name} · {address}', address)
        if previous:
            self.network.setCurrentIndex(max(0, self.network.findData(previous)))
        self.update_status()

    def enable(self):
        self.error.clear()
        try:
            self.server.start(self.network.currentData(), PHONE_PORT)
            preferences.save(self.control.window.c.folder, phone_host=self.network.currentData())
        except (OSError, ValueError, RuntimeError):
            self.error.setText(tr('phone_failed'))
        self.update_status()

    def renew(self):
        try:
            self.server.regenerate_pairing()
            self.error.clear()
        except (OSError, ValueError):
            self.error.setText(tr('phone_device_failed'))
        self.update_status()

    def revoke_device(self, device_id):
        try:
            self.server.revoke_device(device_id)
            self.error.clear()
        except (OSError, ValueError):
            self.error.setText(tr('phone_device_failed'))
        self.update_status()

    def copy_address(self):
        QApplication.clipboard().setText(self.server.url)
        self.control.window.notify(tr('phone_copied'))

    def update_status(self):
        enabled = self.server.running
        self.status.setText(tr('phone_on') if enabled else tr('phone_off'))
        self.network_row.setVisible(not enabled); self.start_button.setVisible(not enabled)
        self.start_button.setEnabled(self.network.count() > 0)
        self.help.setText(tr('phone_connected_help') if enabled else tr('phone_disabled_help') if self.network.count() else tr('phone_no_network'))
        self.details.setVisible(enabled); self.actions.setVisible(enabled); self.clients.setVisible(enabled)
        devices = self.server.remembered_devices
        signature = [(d.get('id'), d.get('label'), d.get('expires_at')) for d in devices]
        if signature != self.last_devices:
            while self.devices_box.count():
                child = self.devices_box.takeAt(0).widget()
                if child:
                    child.deleteLater()
            if devices:
                self.devices_box.addWidget(label(tr('phone_remembered'), 'gameName'))
                for device in devices:
                    revoke = button(tr('phone_revoke'), lambda checked=False, key=device['id']: self.revoke_device(key))
                    revoke.setObjectName('phoneRevokeDevice')
                    self.devices_box.addWidget(row(label(device['label'], '', True), None, revoke))
            self.last_devices = signature
        self.devices.setVisible(bool(devices))
        if enabled:
            self.url.setText(self.server.url)
            seconds = self.server.pairing_seconds
            self.code.setText(self.server.pairing_code if seconds > 0 else '— — —')
            self.expires.setText(tr('phone_expires').format(time=f'{seconds // 60:02d}:{seconds % 60:02d}') if seconds > 0 else tr('phone_expired'))
            self.clients.setText(tr('phone_clients').format(n=self.server.client_count))
            qr = self.server.pairing_url if seconds > 0 else None
            if qr != self.last_qr:
                self.qr.setPixmap(qr_pixmap(qr) if qr else QPixmap())
                self.last_qr = qr


class PhoneOfflineCard(QFrame):
    def __init__(self, window):
        super().__init__()
        self.setObjectName('phoneControlCard')
        box = QVBoxLayout(self); box.setContentsMargins(22, 20, 22, 20); box.setSpacing(14)
        box.addWidget(label(tr('phone_offline_title'), 'gameName'))
        box.addWidget(label(tr('phone_offline_intro'), 'muted', True))
        companion = button(tr('phone_companion'), self.open_companion, 'primary')
        companion.setObjectName('phoneCompanion'); box.addWidget(companion)
        import_button = button(tr('phone_import'), window.phone_import_sessions)
        import_button.setObjectName('phoneImport')
        export_button = button(tr('phone_export_library'), window.phone_export_library)
        export_button.setObjectName('phoneExportLibrary')
        box.addWidget(row(import_button, export_button))
        box.addWidget(label(tr('phone_offline_help'), 'muted', True))

    def open_companion(self):
        dialog = QDialog(self); dialog.setWindowTitle(tr('phone_offline_title'))
        dialog.setMinimumWidth(360)
        box = QVBoxLayout(dialog); box.setContentsMargins(24, 24, 24, 24); box.setSpacing(14)
        box.addWidget(label(tr('phone_companion_scan'), '', True))
        qr = label(''); qr.setPixmap(qr_pixmap(COMPANION_URL, 220)); qr.setAlignment(Qt.AlignCenter)
        box.addWidget(qr)
        address = QLineEdit(COMPANION_URL); address.setReadOnly(True); box.addWidget(address)
        box.addWidget(button(tr('phone_copy_link'), lambda: QApplication.clipboard().setText(COMPANION_URL)))
        box.addWidget(button(tr('phone_open_site'), lambda: QDesktopServices.openUrl(QUrl(COMPANION_URL))))
        box.addWidget(label(tr('phone_install_help'), 'muted', True))
        box.addWidget(button(tr('phone_close'), dialog.accept))
        dialog.exec(); dialog.deleteLater()
