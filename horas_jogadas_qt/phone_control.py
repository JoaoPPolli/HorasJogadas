"""Controle pelo celular: conexão voluntária e operações na thread da interface."""
import hashlib
import ipaddress
import json
import secrets

from PySide6.QtCore import QObject, QTimer, Qt, QRectF
from PySide6.QtGui import QColor, QPainter, QPixmap
from PySide6.QtNetwork import QAbstractSocket, QNetworkInterface
from PySide6.QtWidgets import QApplication, QFrame, QVBoxLayout, QHBoxLayout, QComboBox, QLineEdit

from horas_jogadas import i18n
from horas_jogadas.i18n import t_status
from .remote_server import RemoteServer, RemoteError
from .release import VERSION
from .theme import PALETTES
from .texts import tr
from .widgets import label, button, row


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
        self.server = RemoteServer(self.snapshot, self.command, self)

    def invalidate(self):
        self.serial += 1

    def revision(self, game, timer):
        fields = (self.nonce, self.serial, game.id, game.nome, game.status, timer.rodando,
                  timer.acumulado, str(timer.inicio), timer.retomado, timer.mono, timer.pausa,
                  sorted((str(day), seconds) for day, seconds in timer.dias.items()))
        return hashlib.sha256(json.dumps(fields, ensure_ascii=False).encode()).hexdigest()

    def snapshot(self):
        w = self.window
        theme = w.theme_name()
        palette = dict(zip(('bg', 'side', 'card', 'border', 'text', 'muted', 'accent', 'on_accent'),
                           PALETTES.get(theme, PALETTES['dark'])))
        totals = w.c.repo.totais_por_jogo_id()
        games = []
        for game in w.c.repo.jogos:
            timer = w.c.timers[game.id]
            seconds = timer.seconds()
            games.append(dict(id=game.id, name=game.nome, status=game.status, status_label=t_status(game.status),
                              total_seconds=totals.get(game.id, 0) + seconds, seconds=seconds,
                              running=timer.rodando, paused=timer.pausado, pending=timer.pending,
                              revision=self.revision(game, timer)))
        return dict(theme=theme, language=i18n.idioma_atual(), palette=palette, version=VERSION,
                    games=games, active_count=sum(g['running'] for g in games),
                    pending_recovery=w.pending_recovery)

    def command(self, body):
        w = self.window
        if w.pending_recovery:
            raise RemoteError(409, 'recovery')
        if QApplication.activeModalWidget() is not None:
            raise RemoteError(409, 'busy')
        if not isinstance(body, dict) or set(body) - {'request_id', 'action', 'game_id', 'revision', 'name'}:
            raise RemoteError(400, 'invalid')
        action = body.get('action')
        if action not in ('start', 'pause', 'finish', 'add'):
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
            callback = (lambda: w.c.finish(key)) if action == 'finish' else getattr(timer, action)
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
        return {'ok': True, 'state': self.snapshot()}


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
            self.server.start(self.network.currentData())
        except (OSError, ValueError, RuntimeError):
            self.error.setText(tr('phone_failed'))
        self.update_status()

    def renew(self):
        self.server.regenerate_pairing()
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
