"""Interface de revisão em Qt; as telas são montadas antes de serem mostradas."""
import copy
import sys
import time
from dataclasses import replace
from datetime import date, datetime, timedelta
from pathlib import Path

from PySide6.QtCore import Qt, QTimer, QDateTime, QUrl, QEvent
from PySide6.QtGui import QIcon, QColor, QAction, QKeySequence, QShortcut, QDesktopServices
from PySide6.QtWidgets import (QApplication, QMainWindow, QWidget, QFrame, QVBoxLayout, QHBoxLayout,
    QStackedWidget, QScrollArea, QLineEdit, QComboBox, QMessageBox, QInputDialog, QMenu,
    QTableWidgetItem, QFileDialog, QDateTimeEdit, QSpinBox, QCheckBox, QPlainTextEdit, QDialog, QDialogButtonBox, QSizePolicy, QTableWidget)
from horas_jogadas import i18n, stats, exportacao, instancia, icone_barra
from horas_jogadas.constants import STATUS_OPCOES, ORDENACOES, INTERVALO_HEARTBEAT_S
from horas_jogadas.edicao_sessao import validar, LIMITE_CONFIRMACAO_S
from horas_jogadas.i18n import t, t_status
from horas_jogadas.utils import formatar_hhmmss, formatar_duracao, normalizar_texto
from horas_jogadas.zerados import (Conclusao, MESES, MESES_EN, ler_duracao, resumo_ano,
    duracao_texto, exportar_txt, interpretar_txt, ler_txt, ano_do_texto)
from .controller import Controller
from .preview import prepare_preview
from .backup import create_full, read_full, restore_full
from .texts import tr
from .theme import apply_theme, translate_standard_controls
from .widgets import label, button, row, metric, table, Form, CardLayout, Chart, GameAvatar, ElidedLabel, Ranking
from .completions_view import CompletionList, YearPicker
from .time_dialog import TimeDialog
from .icons import icon


class GameCard(QFrame):
    def __init__(self, window, key):
        super().__init__()
        self.owner, self.key = window, key
        self.setObjectName('gameCard')
        self.setMinimumWidth(310)
        box = QVBoxLayout(self)
        box.setContentsMargins(20, 18, 20, 18)
        box.setSpacing(11)
        game = window.c.repo.jogo_por_id(key)
        title = ElidedLabel(game.nome)
        self.status = label(t_status(game.status).upper(), 'statusPill')
        self.status.setProperty('status', game.status)
        self.status.setSizePolicy(QSizePolicy.Maximum, QSizePolicy.Fixed)
        identity = QWidget()
        identity_box = QVBoxLayout(identity)
        identity_box.setContentsMargins(0, 0, 0, 0)
        identity_box.setSpacing(3)
        identity_box.addWidget(title)
        identity_box.addWidget(self.status)
        more = button('', lambda: window.game_menu(key, more), 'quiet')
        more.setIcon(icon('more'))
        more.setToolTip(tr('actions'))
        more.setAccessibleName(tr('actions'))
        more.setFixedSize(30, 30)
        top = row(GameAvatar(game.nome), identity, more)
        top.layout().setStretch(1, 1)
        box.addWidget(top)
        box.addSpacing(6)
        box.addWidget(label(tr('session').upper(), 'eyebrow'))
        self.elapsed = label('00:00:00', 'timer')
        self.elapsed.setToolTip(tr('adjust'))
        self.elapsed.mouseDoubleClickEvent = lambda event: window.adjust_timer(key)
        box.addWidget(self.elapsed)
        self.state = label('', 'muted')
        box.addWidget(self.state)
        box.addSpacing(5)
        rule = QFrame(); rule.setObjectName('rule'); rule.setFixedHeight(1)
        box.addWidget(rule)
        self.total = label('', 'muted')
        box.addWidget(self.total)
        self.start = button(tr('start'), lambda: window.timer_action(key, 'start'), 'primary')
        foreground = QColor('#171a20' if self.palette().window().color().lightness() < 128 else '#ffffff')
        self.start.setIcon(icon('play', foreground=foreground))
        self.pause = button('', lambda: window.timer_action(key, 'pause'), 'iconButton')
        self.pause.setIcon(icon('pause'))
        self.pause.setFixedWidth(40)
        self.stop = button('', lambda: window.timer_action(key, 'finish'), 'iconButton')
        self.stop.setIcon(icon('stop'))
        self.stop.setFixedWidth(40)
        self.stop.setToolTip(tr('stop'))
        self.stop.setAccessibleName(tr('stop'))
        controls = row(self.start, self.pause, self.stop)
        controls.layout().setStretch(0, 1)
        box.addWidget(controls)
        self.update_timer()

    def update_timer(self):
        timer = self.owner.c.timers[self.key]
        self.elapsed.setText(formatar_hhmmss(timer.seconds()))
        total = self.owner.totals.get(self.key, 0) + timer.seconds()
        self.total.setText(f"{tr('total')} · {formatar_hhmmss(total, simplificado=True)}")
        state = 'playing' if timer.rodando else 'paused' if timer.pausado else 'ready'
        text = tr(state)
        if timer.pausado:
            text += ' · ' + formatar_hhmmss(max(0, time.time() - timer.pausa))
        self.state.setText(text)
        state_name = 'running' if timer.rodando else 'paused' if timer.pausado else 'muted'
        if self.state.objectName() != state_name:
            self.state.setObjectName(state_name)
            self.state.style().unpolish(self.state)
            self.state.style().polish(self.state)
        self.start.setText(tr('resume') if timer.pausado else tr('start'))
        self.start.setEnabled(not timer.rodando)
        self.pause.setAccessibleName(tr('count_pause') if timer.pausado else tr('pause'))
        self.pause.setToolTip(tr('count_pause') if timer.pausado else tr('pause'))
        self.pause.setEnabled(timer.rodando or timer.pausado)
        self.stop.setEnabled(timer.pending)
        if self.property('activity') != state:
            self.setProperty('activity', state)
            self.style().unpolish(self)
            self.style().polish(self)


class Window(QMainWindow):
    def __init__(self, controller, lock=None):
        super().__init__()
        self.c, self.lock = controller, lock
        self.page = 'library'
        self.view_states = {}
        self.displayed_page = None
        self.totals = self.c.repo.totais_por_jogo_id()
        self.year = date.today().year
        self.period = '7d'
        self.stats_filter = None
        self.cards = {}
        self.pending_recovery = bool(self.c.repo.carregar_andamento())
        self.closing_allowed = False
        self.last_heartbeat, self.last_backup = time.monotonic(), time.monotonic()
        self.setWindowTitle('HorasJogadas · ' + tr('review'))
        self.setMinimumSize(840, 620)
        self.resize(1240, 820)
        self.build_shell()
        self.navigate('library')
        self.shortcut = QShortcut(QKeySequence.Find, self)
        self.shortcut.activated.connect(self.focus_search)
        QApplication.instance().installEventFilter(self)
        self.timer = QTimer(self)
        self.timer.setInterval(1000)
        self.timer.timeout.connect(self.tick)
        self.timer.start()
        self.overlay = icone_barra.SobreposicaoBarra(lambda: int(self.winId()), lambda s: t('icone.' + s), icone_barra.criar_backend())
        self.statusBar().showMessage(tr('library_hint'))
        self.statusBar().setToolTip(str(self.c.folder))

    def build_shell(self):
        root = QWidget()
        layout = QHBoxLayout(root)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)
        sidebar = QFrame()
        sidebar.setObjectName('sidebar')
        sidebar.setFixedWidth(206)
        nav = QVBoxLayout(sidebar)
        nav.setContentsMargins(18, 26, 18, 20)
        nav.setSpacing(8)
        logo = label('', 'appLogo')
        app_icon = QIcon(str(Path(__file__).resolve().parent.parent / 'icon.ico'))
        logo.setPixmap(app_icon.pixmap(36,36))
        logo.setAlignment(Qt.AlignCenter)
        logo.setAccessibleName('HorasJogadas')
        logo.setFixedSize(40,40)
        brand = QWidget(); brand_box = QVBoxLayout(brand)
        brand_box.setContentsMargins(0,0,0,0); brand_box.setSpacing(3)
        brand_box.addWidget(label('HorasJogadas', 'brand'))
        hint = label(tr('brand_hint'), 'muted'); hint.setStyleSheet('font-size: 10px;')
        brand_box.addWidget(hint)
        nav.addWidget(row(logo, brand))
        nav.addSpacing(24)
        nav.addWidget(label(tr('space'), 'section'))
        self.nav_buttons = {}
        for name, glyph in [('library','▤'), ('history','◷'), ('stats','▥'), ('completed','◇')]:
            item = button(tr(name), lambda checked=False, page=name: self.navigate(page), 'nav')
            item.setIcon(icon(name))
            item.setCheckable(True)
            nav.addWidget(item)
            self.nav_buttons[name] = item
        nav.addStretch()
        self.side_activity = label(tr('no_active'), 'muted', True)
        self.side_activity.setStyleSheet('font-size: 11px; padding: 0 10px;')
        nav.addWidget(self.side_activity)
        nav.addSpacing(12)
        review = label(tr('separate'), 'reviewBadge')
        review.setToolTip(tr('copy')); nav.addWidget(review)
        settings = button(tr('settings'), lambda: self.navigate('settings'), 'nav')
        settings.setIcon(icon('settings'))
        settings.setCheckable(True)
        nav.addWidget(settings)
        self.nav_buttons['settings'] = settings
        layout.addWidget(sidebar)
        main = QWidget()
        self.main = QVBoxLayout(main)
        self.main.setContentsMargins(30, 24, 30, 24)
        self.main.setSpacing(20)
        self.title = label('', 'title')
        self.subtitle = label('', 'subtitle')
        heading = QWidget(); heading_box = QVBoxLayout(heading)
        heading_box.setContentsMargins(0,0,0,0); heading_box.setSpacing(6)
        heading_box.addWidget(self.title); heading_box.addWidget(self.subtitle)
        self.main.addWidget(heading)
        self.stack = QStackedWidget()
        self.pages = {}
        self.main.addWidget(self.stack, 1)
        layout.addWidget(main, 1)
        self.setCentralWidget(root)

    def navigate(self, page):
        self.page = page
        for key, item in self.nav_buttons.items():
            item.setChecked(key == page)
        self.title.setText(tr(page))
        self.subtitle.setText(tr('subtitle') if page == 'library' else tr('independent') if page == 'completed' else '')
        self.subtitle.setVisible(page in ('library', 'completed'))
        self.refresh()

    def remember_view(self):
        page = self.displayed_page
        current = self.stack.currentWidget()
        if current is None or current is not self.pages.get(page):
            return
        state = {}
        if page == 'library':
            state = {'search': self.search.text(), 'status': self.filter.currentData(),
                     'scroll': self.library_scroll.verticalScrollBar().value()}
        else:
            if isinstance(current, QScrollArea):
                state['scroll'] = current.verticalScrollBar().value()
            grid = self.completed if page == 'completed' else current.findChild(QTableWidget)
            if grid is not None:
                state['table_scroll'] = grid.verticalScrollBar().value()
                index = grid.currentRow()
                state['row'] = index
                values = self.table_values(page)
                if 0 <= index < len(values):
                    state['selected'] = self.record_key(page, values[index])
        self.view_states[page] = state

    def table_values(self, page):
        return {'history': getattr(self, 'history_sessions', []),
                'completed': getattr(self, 'completion_rows', []),
                'stats': getattr(self, 'stat_groups', [])}.get(page, [])

    @staticmethod
    def record_key(page, value):
        return value.sessao_id if page == 'history' else value.id if page == 'completed' else value.chave

    def restore_view(self, widget):
        state = self.view_states.get(self.page, {})
        bar = None
        if self.page == 'library':
            self.search.setText(state.get('search', ''))
            self.filter.setCurrentIndex(max(0, self.filter.findData(state.get('status'))))
            bar = self.library_scroll.verticalScrollBar()
        elif isinstance(widget, QScrollArea):
            bar = widget.verticalScrollBar()
        if bar is not None:
            QTimer.singleShot(0, widget, lambda: bar.setValue(state.get('scroll', 0)))
        grid = self.completed if self.page == 'completed' else widget.findChild(QTableWidget)
        values = self.table_values(self.page)
        if grid is not None and values:
            selected = state.get('selected')
            index = next((i for i, value in enumerate(values) if self.record_key(self.page, value) == selected),
                         max(0, min(state.get('row', 0), len(values) - 1)))
            grid.selectRow(index)
            QTimer.singleShot(0, widget, lambda: grid.verticalScrollBar().setValue(state.get('table_scroll', 0)))

    def refresh(self, preserve_view=True):
        if preserve_view:
            self.remember_view()
        old = self.pages.get(self.page)
        widget = getattr(self, 'build_' + self.page)()
        self.pages[self.page] = widget
        self.stack.addWidget(widget)
        self.stack.setCurrentWidget(widget)
        self.restore_view(widget)
        self.displayed_page = self.page
        self.update_activity()
        if old:
            self.stack.removeWidget(old)
            old.deleteLater()

    def perform(self, action, refresh=True):
        try:
            with self.c.transaction():
                action()
            self.totals = self.c.repo.totais_por_jogo_id()
            if refresh:
                self.refresh()
            return True
        except Exception as error:
            QMessageBox.critical(self, tr('error'), str(error))
            if refresh:
                self.refresh()
            return False

    def confirm(self, message):
        return QMessageBox.question(self, tr('confirm'), message,
            QMessageBox.Yes | QMessageBox.No, QMessageBox.No) == QMessageBox.Yes

    def notify(self, message):
        self.statusBar().showMessage(message, 12000)

    def eventFilter(self, watched, event):
        if (event.type() == QEvent.MouseButtonPress and self.page == 'library'
                and isinstance(watched, QWidget) and watched.window() is self
                and hasattr(self, 'search') and self.search.hasFocus()
                and not isinstance(watched, (QLineEdit, QComboBox, QSpinBox, QDateTimeEdit))):
            self.search.clearFocus()
        return super().eventFilter(watched, event)

    def focus_search(self):
        if self.page != 'library':
            self.navigate('library')
        self.search.setFocus()
        self.search.selectAll()

    def build_library(self):
        widget = QWidget()
        box = QVBoxLayout(widget); box.setContentsMargins(0,0,0,0); box.setSpacing(16)
        self.search = QLineEdit()
        self.search.setPlaceholderText(tr('search'))
        self.search.setClearButtonEnabled(True)
        self.search.addAction(icon('search'), QLineEdit.LeadingPosition)
        self.search.setAccessibleName(tr('search'))
        self.search_escape = QShortcut(QKeySequence(Qt.Key_Escape), self.search)
        self.search_escape.setContext(Qt.WidgetShortcut)
        self.search_escape.activated.connect(lambda: (self.search.clear(), self.search.clearFocus()))
        self.filter = QComboBox()
        self.filter.setToolTip(tr('status'))
        self.filter.setAccessibleName(tr('status'))
        self.filter.addItem(tr('all'), None)
        for status in STATUS_OPCOES:
            self.filter.addItem(t_status(status), status)
        self.order = QComboBox()
        for key in ORDENACOES:
            self.order.addItem(t('ord.' + key), key)
        self.order.setCurrentIndex(max(0, self.order.findData(self.c.config.get('ordenacao', 'manual'))))
        add = button(tr('add'), self.add_game, 'primary')
        box.addWidget(row(self.search, self.filter, self.order, add))
        self.library_count = label('', 'muted')
        box.addWidget(self.library_count)
        self.library_scroll = QScrollArea()
        self.library_scroll.setWidgetResizable(True)
        self.library_scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.library_host = QWidget()
        self.card_layout = CardLayout(self.library_host)
        self.cards = {}
        for game in self.c.repo.jogos:
            card = GameCard(self, game.id)
            self.cards[game.id] = card
            self.card_layout.addWidget(card)
        self.library_scroll.setWidget(self.library_host)
        box.addWidget(self.library_scroll, 1)
        self.empty = label(tr('empty') + '\n\n' + tr('empty_hint'), 'muted', True)
        self.empty.setAlignment(Qt.AlignCenter)
        box.addWidget(self.empty, 1)
        self.search.textChanged.connect(self.filter_library)
        self.filter.currentIndexChanged.connect(self.filter_library)
        self.order.currentIndexChanged.connect(self.sort_library)
        self.filter_library()
        return widget

    def filter_library(self):
        term, status = normalizar_texto(self.search.text()), self.filter.currentData()
        count = 0
        for key, card in self.cards.items():
            game = self.c.repo.jogo_por_id(key)
            visible = (not term or term in normalizar_texto(game.nome)) and (not status or game.status == status)
            card.setVisible(visible)
            count += bool(visible)
        self.library_count.setText((tr('one_game') if count == 1 else tr('all_count').format(n=count))
                                   if count == len(self.cards) else tr('result_count').format(n=count, total=len(self.cards)))
        self.card_layout.invalidate()
        self.library_host.updateGeometry()
        self.empty.setVisible(count == 0)
        self.empty.setText(tr('nothing') if self.c.repo.jogos else tr('empty') + '\n\n' + tr('empty_hint'))
        self.library_scroll.setVisible(count > 0)
        self.reorder_cards()

    def sort_library(self):
        key = self.order.currentData()
        if self.perform(lambda: self.save_order(key), refresh=False):
            self.reorder_cards()

    def save_order(self, key):
        self.c.config['ordenacao'] = key
        self.c.repo.salvar_config(self.c.config)

    def reorder_cards(self):
        order = self.order.currentData()
        games = list(self.c.repo.jogos)
        if order == 'nome':
            games.sort(key=lambda g: normalizar_texto(g.nome))
        elif order == 'horas':
            totals = self.c.repo.totais_por_jogo_id()
            games.sort(key=lambda g: totals.get(g.id, 0) + self.c.timers[g.id].seconds(), reverse=True)
        elif order == 'recente':
            latest = stats.ultima_sessao_por_jogo_id(self.c.repo.sessoes)
            games.sort(key=lambda g: latest.get(g.id, datetime.min), reverse=True)
        by_key = {item.widget().key: item for item in self.card_layout.items}
        self.card_layout.items[:] = [by_key[g.id] for g in games]
        self.card_layout.invalidate()
        self.library_host.updateGeometry()

    def add_game(self):
        name, ok = QInputDialog.getText(self, tr('add'), tr('name'))
        if ok and self.perform(lambda: self.c.add_game(name), refresh=False):
            # Um jogo recém-adicionado deve aparecer mesmo se havia uma busca ativa.
            self.search.blockSignals(True); self.filter.blockSignals(True)
            self.search.clear(); self.filter.setCurrentIndex(0)
            self.search.blockSignals(False); self.filter.blockSignals(False)
            self.library_scroll.verticalScrollBar().setValue(0)
            self.refresh()

    def timer_action(self, key, action):
        timer = self.c.timers[key]
        if action == 'pause' and timer.pausado:
            text, ok = QInputDialog.getText(self, tr('count_pause'), tr('pause_minutes'))
            if not ok:
                return
            try:
                minutes = None if not text.strip() else float(text.replace(',', '.'))
                if minutes is not None and minutes <= 0:
                    raise ValueError(tr('duration'))
            except ValueError as error:
                QMessageBox.warning(self, tr('error'), str(error)); return
            callback = lambda: timer.count_pause(None if minutes is None else minutes * 60)
        elif action == 'finish':
            callback = lambda: self.c.finish(key)
        else:
            callback = getattr(timer, action)
        def apply():
            callback()
            self.c.save_pending()
        if self.perform(apply, refresh=False):
            if self.page == 'library':
                self.cards[key].update_timer()
                self.reorder_cards()
            self.update_activity()

    def adjust_timer(self, key):
        TimeDialog(self,key).exec()

    def game_menu(self, key, anchor):
        game = self.c.repo.jogo_por_id(key)
        menu = QMenu(self)
        menu.addAction(tr('rename'), lambda: self.rename_game(key))
        statuses = menu.addMenu(tr('status'))
        for status in STATUS_OPCOES:
            action = statuses.addAction(t_status(status), lambda checked=False, s=status: self.change_status(key, s))
            action.setCheckable(True); action.setChecked(game.status == status)
        menu.addAction(tr('adjust'), lambda: self.adjust_timer(key))
        pause_action = menu.addAction(tr('count_pause'), lambda: self.timer_action(key,'pause'))
        pause_action.setEnabled(self.c.timers[key].pausado)
        menu.addSeparator()
        for end, text in [(False,'move_top'), (True,'move_end')]:
            action = menu.addAction(tr(text), lambda checked=False, bottom=end: self.move_game(key,bottom))
            action.setEnabled(self.order.currentData() == 'manual')
        menu.addSeparator()
        discard = menu.addAction(tr('discard'), lambda: self.discard_timer(key))
        discard.setEnabled(self.c.timers[key].pending)
        menu.addAction(tr('delete'), lambda: self.delete_game(key))
        menu.exec(anchor.mapToGlobal(anchor.rect().bottomLeft()))

    def rename_game(self, key):
        name, ok = QInputDialog.getText(self,tr('rename'),tr('name'),text=self.c.repo.jogo_por_id(key).nome)
        if ok:
            self.perform(lambda: self.c.repo.renomear_jogo(key,name))

    def change_status(self, key, status):
        if self.perform(lambda: self.c.set_status(key,status)) and status == 'Zerado':
            self.notify(tr('complete_undo'))

    def move_game(self, key, bottom):
        def apply():
            game = self.c.repo.jogo_por_id(key)
            games = [g for g in self.c.repo.jogos if g.id != key]
            games.insert(len(games) if bottom else 0, game)
            self.c.repo.salvar_jogos(games)
        self.perform(apply)

    def discard_timer(self, key):
        if self.confirm(tr('discard') + '?'):
            self.perform(lambda: (self.c.timers[key].reset(), self.c.save_pending()))

    def delete_game(self, key):
        if not self.confirm(tr('confirm_delete')):
            return
        if not self.resolve_pending([key]):
            return
        self.perform(lambda: self.c.delete_game(key))

    def selected(self, widget, values):
        index = widget.currentRow()
        return values[index] if 0 <= index < len(values) else None

    def fill_table(self, widget, rows):
        widget.setUpdatesEnabled(False)
        try:
            widget.setRowCount(len(rows))
            for r, values in enumerate(rows):
                for col, value in enumerate(values):
                    item = QTableWidgetItem(str(value))
                    item.setToolTip(str(value))
                    widget.setItem(r,col,item)
        finally:
            widget.setUpdatesEnabled(True)

    def build_history(self):
        widget = QWidget(); box = QVBoxLayout(widget); box.setContentsMargins(0,0,0,0)
        self.history = table([tr('game'),tr('duration_col'),tr('end')])
        self.history_sessions = list(reversed(self.c.repo.sessoes))
        self.fill_table(self.history, [(s.jogo, s.tempo + ('  ⚠' if s.segundos > 43200 else ''), s.data) for s in self.history_sessions])
        edit = self.edit_selected_session
        self.history.doubleClicked.connect(lambda index: edit())
        undo = button(tr('undo'), lambda: self.perform(self.c.undo_session))
        undo.setEnabled(bool(self.c.undo))
        box.addWidget(row(button('+ '+tr('add_session'),lambda: self.edit_session(), 'primary'),
            button(tr('export_csv'),lambda: self.export_csv(False)), None, undo))
        box.addWidget(self.history,1)
        box.addWidget(row(button(tr('edit'),edit),button(tr('delete'),self.delete_selected_session),None,
                          button(tr('clear'),self.clear_history,'danger')))
        return widget

    def edit_selected_session(self):
        session = self.selected(self.history, self.history_sessions)
        if session:
            self.edit_session(session)

    def edit_session(self, session=None):
        d = Form(self, tr('edit') if session else tr('add_session'))
        game = QComboBox()
        for g in self.c.repo.jogos:
            game.addItem(g.nome,g.id)
        if session and game.findData(session.jogo_id) < 0:
            game.addItem(session.jogo,session.jogo_id)
        if session:
            game.setCurrentIndex(max(0,game.findData(session.jogo_id)))
        if not game.count():
            QMessageBox.warning(self,tr('warning'),tr('add')); return
        duration = QLineEdit(formatar_hhmmss(session.segundos) if session else '')
        duration.setPlaceholderText('01:30:00')
        end = QDateTimeEdit(); end.setCalendarPopup(True)
        end.setDisplayFormat('yyyy-MM-dd HH:mm:ss')
        end.setDateTime(QDateTime(session.data_dt if session and session.data_dt else datetime.now()))
        d.form.addRow(tr('game'),game); d.form.addRow(tr('duration'),duration); d.form.addRow(tr('end'),end)
        def save():
            seconds = ler_duracao(duration.text())
            if seconds is None:
                raise ValueError(tr('duration'))
            h, rest = divmod(seconds,3600)
            finish, seconds = validar(end.dateTime().toString('yyyy-MM-dd HH:mm:ss'),str(h),str(rest//60),str(rest%60),datetime.now())
            if seconds > LIMITE_CONFIRMACAO_S and not self.confirm(t('sessao.confirma_longa',tempo=formatar_hhmmss(seconds))):
                return False
            key, name = game.currentData(),game.currentText()
            def change():
                if session:
                    self.c.repo.atualizar_sessao(session.sessao_id,key,name,seconds,finish)
                else:
                    self.c.repo.adicionar_sessao(key,name,seconds,finish-timedelta(seconds=seconds),finish)
            return self.perform(change)
        d.submit(save); d.exec()

    def delete_selected_session(self):
        session = self.selected(self.history,self.history_sessions)
        if session and self.confirm(tr('confirm_delete')):
            self.perform(lambda: self.c.delete_session(session))

    def clear_history(self):
        if self.confirm(tr('confirm_clear')):
            def change():
                create_full(self.c.folder)
                self.c.repo.limpar_sessoes()
                self.c.undo.clear()
            self.perform(change)

    def export_csv(self, summary=False):
        path,_ = QFileDialog.getSaveFileName(self,tr('export_csv'),'horas_jogadas.csv','CSV (*.csv)')
        if path:
            try:
                function = exportacao.exportar_resumo if summary else exportacao.exportar_historico
                function(path,self.c.repo.jogos,self.c.repo.sessoes)
                self.notify(tr('done'))
            except OSError as error:
                QMessageBox.critical(self,tr('error'),str(error))

    def build_stats(self):
        scroll = QScrollArea(); scroll.setWidgetResizable(True)
        host=QWidget(); box=QVBoxLayout(host); box.setContentsMargins(0,0,12,0); box.setSpacing(18)
        groups=stats.agrupar_por_jogo(self.c.repo.jogos,self.c.repo.sessoes)
        summary=stats.resumo_geral(groups,self.c.repo.sessoes)
        current,best=stats.sequencias(self.c.repo.sessoes)
        box.addWidget(row(metric(tr('hours'),formatar_duracao(summary.total_segundos)),
                          metric(tr('sessions'),str(summary.total_sessoes)),
                          metric(tr('average'),formatar_duracao(summary.media_sessao))))
        longest=summary.sessao_mais_longa
        longest_box=metric(tr('longest'),formatar_duracao(longest.segundos) if longest else '—',longest.jogo if longest else '')
        if longest:
            longest_box.layout().addWidget(button(tr('edit'),lambda: self.edit_session(longest)))
        box.addWidget(row(longest_box,metric(tr('streak'),f'{current} '+tr('days')),
                          metric(tr('best_streak'),f'{best} '+tr('days'))))
        periods=QComboBox()
        for key in ('7d','8s','6m'):
            periods.addItem(tr(key),key)
        periods.setCurrentIndex(periods.findData(self.period))
        periods.currentIndexChanged.connect(lambda: self.change_period(periods.currentData()))
        box.addWidget(row(label(tr('period'),'gameName'),None,periods))
        data=stats.horas_por_periodo(self.c.repo.sessoes,self.period,
            dias_semana=i18n.lista('dias_semana'),meses_nomes=i18n.lista('meses'),formato_semana=t('fmt.semana'))
        box.addWidget(Chart(data))
        top_card=QFrame(); top_card.setObjectName('card')
        top_box=QVBoxLayout(top_card); top_box.setContentsMargins(20,18,20,18); top_box.setSpacing(14)
        top_box.addWidget(label(tr('top_five'),'gameName'))
        self.top_ranking=Ranking(stats.top_jogos(groups,5))
        top_box.addWidget(self.top_ranking)
        box.addWidget(top_card)
        self.stats_status=QComboBox(); self.stats_status.setAccessibleName(tr('status'))
        self.stats_status.addItem(tr('all'),None)
        for status in STATUS_OPCOES:
            self.stats_status.addItem(t_status(status),status)
        self.stats_status.setCurrentIndex(max(0,self.stats_status.findData(self.stats_filter)))
        self.stats_status.currentIndexChanged.connect(lambda:self.change_stats_filter(self.stats_status.currentData()))
        box.addWidget(row(label(tr('games'),'gameName'),None,self.stats_status))
        self.stat_groups=list(groups)  # O domínio já ordena pela sessão mais recente, como no app atual.
        self.stat_group_cards={}
        for group in self.stat_groups:
            if self.stats_filter is not None and group.status!=self.stats_filter:
                continue
            card=QFrame(); card.setObjectName('card')
            content=QVBoxLayout(card); content.setContentsMargins(18,16,18,16); content.setSpacing(7)
            title=ElidedLabel(group.nome)
            status=label(t_status(group.status) if group.status else '—','statusPill')
            status.setProperty('status',group.status or '')
            status.setSizePolicy(QSizePolicy.Maximum,QSizePolicy.Fixed)
            heading=row(title,status); heading.layout().setStretch(0,1)
            content.addWidget(heading)
            sessions=t('dash.sessao_um') if group.sessoes==1 else t('dash.sessoes',n=group.sessoes)
            content.addWidget(label(tr('total')+' · '+formatar_hhmmss(group.total)+' · '+sessions,'muted'))
            first=group.primeira.strftime(t('fmt.data')) if group.primeira else '—'
            last=group.ultima.strftime(t('fmt.data_hora')) if group.ultima else '—'
            dates=QWidget(); dates.setSizePolicy(QSizePolicy.Preferred,QSizePolicy.Maximum)
            dates_box=QVBoxLayout(dates); dates_box.setContentsMargins(0,0,0,0); dates_box.setSpacing(4)
            dates_box.setAlignment(Qt.AlignTop)
            dates_box.addWidget(label(t('dash.primeira',data=first),'muted'))
            dates_box.addWidget(label(t('dash.ultima',data=last),'muted'))
            if group.sessoes:
                remove=button(tr('delete_history'),lambda checked=False,key=group.chave:self.delete_group_by_key(key),'danger')
                content.addWidget(row(dates,None,remove))
            else:
                content.addWidget(dates)
            self.stat_group_cards[group.chave]=card
            box.addWidget(card)
        box.addWidget(row(button(tr('export_summary'),lambda:self.export_csv(True)),None))
        scroll.setWidget(host)
        return scroll

    def change_period(self,key):
        self.period=key; self.refresh()

    def change_stats_filter(self,status):
        self.stats_filter=status; self.refresh()

    def delete_group_by_key(self,key):
        group=next((group for group in self.stat_groups if group.chave==key),None)
        if group and self.confirm(t('dash.excluir_registros',nome=group.nome)):
            self.perform(lambda:(create_full(self.c.folder),self.c.repo.remover_sessoes_do_grupo(group.chave)))

    def build_completed(self):
        widget=QWidget(); box=QVBoxLayout(widget); box.setContentsMargins(0,0,0,0); box.setSpacing(16)
        self.year_picker=YearPicker({date.today().year,self.year} | {record.ano for record in self.c.zerados.registros},self.year)
        year=self.year_picker
        year.currentIndexChanged.connect(lambda:self.change_year(year.currentData()))
        box.addWidget(row(label(tr('year')),year,None,
            button(tr('import_txt'),self.import_txt),button(tr('export_txt'),self.export_txt),
            button('+ '+tr('new_record'),lambda:self.edit_completion(), 'primary')))
        summary=resumo_ano(self.c.zerados.registros,self.year)
        known=any(r.segundos is not None or r.platina_segundos is not None for r in self.c.zerados.registros if r.ano==self.year)
        box.addWidget(row(metric(tr('base_games'),str(summary.jogos_zerados)),metric(tr('dlcs'),str(summary.dlcs_zeradas)),
            metric(tr('hours'),duracao_texto(summary.segundos_registrados) if known else '—'),
            metric(tr('platinum'),duracao_texto(summary.platina_segundos) if known else '—')))
        box.addWidget(label(f"{summary.registros} {tr('records')} · {summary.sem_tempo} {tr('no_time')}",'muted'))
        self.completion_rows=sorted([r for r in self.c.zerados.registros if r.ano==self.year],key=lambda r:(r.mes,r.dia or 0,r.nome))
        self.completed=CompletionList(self.completion_rows)
        self.completed.doubleClicked.connect(lambda _:self.edit_selected_completion())
        self.completed.delegate.actionRequested.connect(self.completion_action)
        box.addWidget(self.completed,1)
        undo=button(tr('undo'),self.undo_completion)
        undo.setEnabled(bool(getattr(self,'deleted_completions',[])))
        box.addWidget(row(button(tr('edit'),self.edit_selected_completion),button(tr('new_play'),self.new_play),
                          button(tr('delete'),self.delete_completion),None,undo))
        return widget

    def change_year(self,year):
        self.year=year
        self.view_states.pop('completed',None)
        self.refresh(preserve_view=False)
        self.completed.verticalScrollBar().setValue(0)

    def completion_action(self,action,key):
        index=next((i for i,record in enumerate(self.completion_rows) if record.id==key),None)
        if index is None:
            return
        self.completed.selectRow(index)
        if action=='edit':
            self.edit_selected_completion()
        elif action=='new_play':
            self.new_play()
        elif action=='delete':
            self.delete_completion()

    def edit_selected_completion(self):
        record=self.selected(self.completed,self.completion_rows)
        if record:
            self.edit_completion(record)

    def edit_completion(self, record=None, save_callback=None):
        record=record or Conclusao('', self.year, min(date.today().month,12))
        d=Form(self,tr('edit') if record.nome else tr('new_record'))
        name=QLineEdit(record.nome)
        year=QSpinBox(); year.setRange(1900,9999); year.setValue(record.ano)
        month=QComboBox(); month.addItems(MESES_EN if i18n.idioma_atual()=='en' else MESES); month.setCurrentIndex(record.mes-1)
        day=QSpinBox(); day.setRange(0,31); day.setSpecialValueText('—'); day.setValue(record.dia or 0)
        duration=QLineEdit(duracao_texto(record.segundos)); duration.setPlaceholderText(tr('unknown'))
        extra=QLineEdit(duracao_texto(record.platina_segundos)); extra.setPlaceholderText(tr('unknown'))
        kind=QComboBox(); kind.addItem(tr('completion'),'zerado'); kind.addItem(tr('experience'),'experiencia'); kind.setCurrentIndex(1 if record.tipo=='experiencia' else 0)
        dlc=QCheckBox(tr('dlc')); dlc.setChecked(record.dlc)
        notes=QPlainTextEdit(record.notas); notes.setMaximumHeight(100)
        for title,field in [('name',name),('year',year),('month',month),('day',day),('duration',duration),
                            ('platinum',extra),('type',kind)]:
            d.form.addRow(tr(title),field)
        d.form.addRow('',dlc); d.form.addRow(tr('notes'),notes)
        def save():
            new=replace(record,nome=name.text().strip(),ano=year.value(),mes=month.currentIndex()+1,dia=day.value() or None,
                segundos=ler_duracao(duration.text()),platina_segundos=ler_duracao(extra.text()),
                tipo=kind.currentData(),dlc=dlc.isChecked(),notas=notes.toPlainText().strip()).validar()
            if save_callback:
                save_callback(new)
                return True
            def save_record():
                self.c.zerados.guardar(new)
                self.year=new.ano
            return self.perform(save_record)
        d.submit(save); d.exec()

    def new_play(self):
        record=self.selected(self.completed,self.completion_rows)
        if record:
            from horas_jogadas.models import novo_id
            today=date.today()
            self.edit_completion(replace(record,id=novo_id(),ano=today.year,mes=today.month,dia=None,
                                         segundos=None,platina_segundos=None,notas='',origem='manual'))

    def delete_completion(self):
        record=self.selected(self.completed,self.completion_rows)
        if record and self.confirm(tr('confirm_delete')):
            if self.perform(lambda:self.c.zerados.excluir(record.id),refresh=False):
                if not hasattr(self,'deleted_completions'):
                    self.deleted_completions=[]
                self.deleted_completions.append(record)
                self.refresh()

    def undo_completion(self):
        if getattr(self,'deleted_completions',[]):
            record=self.deleted_completions[-1]
            if self.perform(lambda:self.c.zerados.guardar(record),refresh=False):
                self.deleted_completions.pop(); self.refresh()

    def export_txt(self):
        path,_=QFileDialog.getSaveFileName(self,tr('export_txt'),f'zerados-{self.year}.txt','TXT (*.txt)')
        if path:
            try:
                from horas_jogadas_qt.files import write_text_atomic
                write_text_atomic(path,exportar_txt(self.c.zerados.registros,self.year))
                self.notify(tr('done'))
            except OSError as error:
                QMessageBox.warning(self,tr('error'),str(error))

    def import_txt(self):
        paths,_=QFileDialog.getOpenFileNames(self,tr('import_txt'),'','TXT (*.txt)')
        if not paths:
            return
        items=[]
        try:
            for path in paths:
                text=ler_txt(path)
                default=ano_do_texto(text)
                if default is None:
                    import re
                    match=re.search(r'\b(19\d{2}|20\d{2})\b',Path(path).stem)
                    if match:
                        default=int(match[1])
                    else:
                        default,ok=QInputDialog.getInt(self,tr('year'),Path(path).name,self.year,1900,9999)
                        if not ok:
                            return
                items.extend(interpretar_txt(text,default))
        except (OSError,ValueError) as error:
            QMessageBox.warning(self,tr('error'),str(error)); return
        self.review_import(items)

    def review_import(self,items):
        d=Form(self,tr('import_txt')); d.resize(1000,650)
        d.form.addRow(label(tr('import_review'),'muted',True))
        preview=table([tr('selected'),tr('line'),tr('name'),tr('issue')])
        d.form.addRow(preview)
        def update():
            self.fill_table(preview,[( '',item.texto,item.registro.nome if item.registro else '—',item.aviso) for item in items])
            for index,item in enumerate(items):
                check=preview.item(index,0)
                check.setFlags(Qt.ItemIsEnabled | (Qt.ItemIsUserCheckable if item.registro and not item.aviso else Qt.NoItemFlags))
                check.setCheckState(Qt.Checked if item.selecionado and not item.aviso else Qt.Unchecked)
        def edit():
            index=preview.currentRow()
            if index<0:
                return
            for row_index,item in enumerate(items):
                item.selecionado=preview.item(row_index,0).checkState()==Qt.Checked
            item=items[index]
            initial=item.registro or Conclusao(item.texto.strip('- '),self.year,1)
            def save(record):
                item.registro=record; item.aviso=''; item.selecionado=True; update()
            self.edit_completion(initial,save)
        preview.doubleClicked.connect(lambda _:edit())
        d.form.addRow(button(tr('edit'),edit))
        def save():
            selected=[item.registro for index,item in enumerate(items)
                if preview.item(index,0).checkState()==Qt.Checked and item.registro and not item.aviso]
            return self.perform(lambda:self.c.zerados.importar(selected))
        d.buttons.button(QDialogButtonBox.Save).setText(tr('import'))
        d.submit(save); update(); d.exec()

    def build_settings(self):
        scroll=QScrollArea(); scroll.setWidgetResizable(True)
        host=QWidget(); box=QVBoxLayout(host); box.setContentsMargins(0,0,12,0); box.setSpacing(20)
        appearance=QFrame(); appearance.setObjectName('card'); form=QVBoxLayout(appearance)
        form.setContentsMargins(22,20,22,20); form.setSpacing(14)
        form.addWidget(label(tr('theme'),'gameName'))
        theme=QComboBox()
        for key in ('dark','violet','light'):
            theme.addItem(tr(key),key)
        theme.setCurrentIndex(max(0,theme.findData(self.theme_name())))
        language=QComboBox(); language.addItem('Português (Brasil)','pt'); language.addItem('English','en')
        language.setCurrentIndex(language.findData(i18n.idioma_atual()))
        form.addWidget(row(label(tr('theme')),theme,None,label(tr('language')),language))
        form.addWidget(button(tr('save'),lambda:self.save_settings(theme.currentData(),language.currentData()),'primary'))
        box.addWidget(appearance)
        data=QFrame(); data.setObjectName('card'); data_box=QVBoxLayout(data); data_box.setContentsMargins(22,20,22,20); data_box.setSpacing(12)
        data_box.addWidget(label(tr('data'),'gameName'))
        data_box.addWidget(label(str(self.c.folder),'muted',True))
        data_box.addWidget(label(tr('copy_help'),'muted',True))
        data_box.addWidget(row(button(tr('open_folder'),lambda:QDesktopServices.openUrl(QUrl.fromLocalFile(str(self.c.folder)))),
                              button(tr('copy_data'),self.new_review),None))
        data_box.addWidget(row(button(tr('export_csv'),lambda:self.export_csv(False)),
                              button(tr('export_summary'),lambda:self.export_csv(True)),None))
        box.addWidget(data)
        backup_card=QFrame(); backup_card.setObjectName('card'); backups_box=QVBoxLayout(backup_card); backups_box.setContentsMargins(22,20,22,20); backups_box.setSpacing(12)
        backups_box.addWidget(label(tr('backups'),'gameName'))
        backups_box.addWidget(label(tr('backup_help'),'muted',True))
        backups_box.addWidget(row(button(tr('backup_now'),self.backup_now,'primary'),button(tr('restore'),self.restore_backup),
                                 button(tr('restore_legacy'),self.restore_legacy)))
        box.addWidget(backup_card)
        box.addWidget(label(tr('about'),'muted'))
        box.addWidget(label(tr('updates'),'muted',True))
        box.addStretch(); scroll.setWidget(host)
        return scroll

    def theme_name(self):
        import json
        try:
            return json.loads((self.c.folder/'.qt-preferences.json').read_text(encoding='utf-8')).get('theme','dark')
        except (ValueError,OSError):
            return 'dark'

    def save_settings(self,theme,language):
        from horas_jogadas.storage import escrever_json_atomico
        def save():
            self.c.config['idioma']=language
            self.c.repo.salvar_config(self.c.config)
            escrever_json_atomico(str(self.c.folder/'.qt-preferences.json'),{'theme':theme})
        if self.perform(save,False):
            i18n.definir_idioma(language)
            apply_theme(QApplication.instance(),theme)
            translate_standard_controls(QApplication.instance(),language)
            old=self.centralWidget(); self.build_shell(); old.deleteLater()
            self.setWindowTitle('HorasJogadas · '+tr('review'))
            self.navigate('settings')

    def new_review(self):
        source=QFileDialog.getExistingDirectory(self,tr('copy_data'))
        if not source or not self.confirm(tr('copy_help')):
            return
        target=self.c.folder.parent/('HorasJogadas-Revisao-'+datetime.now().strftime('%Y%m%d-%H%M%S-%f'))
        try:
            prepare_preview(source,target)
            QMessageBox.information(self,tr('done'),tr('snapshot')+'\n'+str(target)+'\n\npython app_qt.py --review-dir "'+str(target)+'" --source "'+str(Path(source).resolve())+'"')
        except Exception as error:
            QMessageBox.warning(self,tr('error'),str(error))

    def backup_now(self):
        try:
            self.c.save_pending()
            target=create_full(self.c.folder)
            QMessageBox.information(self,tr('done'),str(target))
        except Exception as error:
            QMessageBox.warning(self,tr('error'),str(error))

    def reload_data(self):
        self.c=Controller(self.c.folder)
        self.totals=self.c.repo.totais_por_jogo_id()
        self.pending_recovery=bool(self.c.repo.carregar_andamento())
        if self.pending_recovery:
            self.recovery_prompt()
        self.refresh()

    def restore_backup(self):
        path=QFileDialog.getExistingDirectory(self,tr('restore'),str(self.c.folder/'full-backups'))
        if not path:
            return
        try:
            read_full(path)
        except Exception as error:
            QMessageBox.warning(self,tr('error'),str(error)); return
        if not self.confirm(tr('restore')+'?') or not self.resolve_pending():
            return
        def apply():
            create_full(self.c.folder)
            restore_full(self.c.folder,path)
        if self.perform(apply,False):
            self.reload_data()

    def restore_legacy(self):
        backups=self.c.repo.listar_backups()
        choices=[f'{b.momento:%Y-%m-%d %H:%M} · {b.tipo} · {b.jogos} / {b.sessoes}' for b in backups]
        if not choices:
            QMessageBox.information(self,tr('backups'),t('bk.vazio')); return
        text,ok=QInputDialog.getItem(self,tr('restore_legacy'),tr('backups'),choices,0,False)
        if not ok or not self.confirm(tr('restore')+'?\n'+tr('independent')) or not self.resolve_pending():
            return
        def apply():
            create_full(self.c.folder)
            self.c.repo.restaurar_backup(backups[choices.index(text)])
        if self.perform(apply,False):
            self.reload_data()

    def recovery_prompt(self):
        if not self.pending_recovery:
            return True
        result=QMessageBox.question(self,tr('warning'),tr('recover'),QMessageBox.Yes|QMessageBox.No|QMessageBox.Cancel,QMessageBox.Cancel)
        if result==QMessageBox.Cancel:
            self.closing_allowed=True
            self.close()
            return False
        if not self.perform(self.c.recover if result==QMessageBox.Yes else self.c.repo.limpar_andamento,False):
            self.closing_allowed=True; self.close(); return False
        self.pending_recovery=False
        self.refresh()
        return True

    def resolve_pending(self,keys=None):
        keys=[k for k in (list(self.c.timers) if keys is None else keys) if self.c.timers[k].pending]
        if not keys:
            return True
        response=QMessageBox.question(self,tr('warning'),tr('pending'),
            QMessageBox.Save|QMessageBox.Discard|QMessageBox.Cancel,QMessageBox.Cancel)
        if response==QMessageBox.Cancel:
            return False
        def apply():
            for key in keys:
                if response==QMessageBox.Save:
                    self.c.finish(key)
                else:
                    self.c.timers[key].reset()
            self.c.save_pending()
        return self.perform(apply,False)

    def update_activity(self):
        running = sum(timer.rodando for timer in self.c.timers.values())
        paused = sum(timer.pausado for timer in self.c.timers.values())
        text = tr('active_count').format(n=running) if running else ''
        if paused:
            text += (' · ' if text else '') + tr('paused_count').format(n=paused)
        self.side_activity.setText(text or tr('no_active'))

    def tick(self):
        if self.pending_recovery:
            return
        try:
            if self.page=='library':
                for key,card in self.cards.items():
                    if self.c.timers[key].pending:
                        card.update_timer()
            self.update_activity()
            self.overlay.definir(icone_barra.estado_do_icone(self.c.timers.values()))
            if instancia.consumir_sinal(str(self.c.folder)):
                self.showNormal(); self.raise_(); self.activateWindow()
            now=time.monotonic()
            if now-self.last_heartbeat>=INTERVALO_HEARTBEAT_S:
                self.c.save_pending(); self.last_heartbeat=now
            if now-self.last_backup>=300:
                self.c.repo.backup_diario(); self.last_backup=now
        except Exception as error:
            self.timer.stop()
            QMessageBox.critical(self,tr('error'),str(error))
            self.timer.start()

    def closeEvent(self,event):
        if self.closing_allowed or self.pending_recovery:
            event.accept()
        elif self.resolve_pending():
            try:
                self.c.repo.limpar_andamento()
                event.accept()
            except OSError as error:
                QMessageBox.critical(self,tr('error'),str(error)); event.ignore()
        else:
            event.ignore()
