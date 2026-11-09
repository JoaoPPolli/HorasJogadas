"""Configuração e instruções do widget de transmissão no mesmo design do app."""
from PySide6.QtCore import QUrl
from PySide6.QtGui import QDesktopServices
from PySide6.QtWidgets import QFrame, QVBoxLayout, QFormLayout, QComboBox, QCheckBox, QLineEdit, QApplication
from .obs import read_options
from .texts import tr
from .widgets import label, button, row


class ObsCard(QFrame):
    def __init__(self, control):
        super().__init__()
        self.control = control
        self.setObjectName('card')
        box = QVBoxLayout(self); box.setContentsMargins(22,20,22,20); box.setSpacing(14)
        box.addWidget(label(tr('obs_title'), 'gameName'))
        box.addWidget(label(tr('obs_intro'), 'muted', True))
        options = read_options(control.window.c.folder)
        self.enabled = QCheckBox(tr('obs_enabled')); self.enabled.setObjectName('obsEnabled'); self.enabled.setChecked(options['enabled']); box.addWidget(self.enabled)
        form = QFormLayout(); form.setSpacing(12)
        self.game = QComboBox(); self.game.setObjectName('obsGame'); self.game.addItem(tr('obs_auto'), 'auto')
        for game in control.window.c.repo.jogos:self.game.addItem(game.nome, game.id)
        self.game.setCurrentIndex(max(0,self.game.findData(options['game'])))
        form.addRow(tr('obs_game'), self.game)
        self.scope = QComboBox(); self.scope.setObjectName('obsScope')
        for key in ('session','total'):self.scope.addItem(tr('obs_'+key), key)
        self.scope.setCurrentIndex(self.scope.findData(options['scope'])); form.addRow(tr('obs_time'), self.scope)
        self.style = QComboBox(); self.style.setObjectName('obsStyle')
        for key in ('minimal','arcade','digital'):self.style.addItem(tr('obs_'+key), key)
        self.style.setCurrentIndex(self.style.findData(options['style'])); form.addRow(tr('obs_style'), self.style)
        self.color = QLineEdit(options['color']); self.color.setObjectName('obsColor'); self.color.setMaxLength(7); self.color.setPlaceholderText('#ffffff'); form.addRow(tr('obs_color'), self.color)
        box.addLayout(form)
        self.show_name = QCheckBox(tr('obs_name')); self.show_name.setChecked(options['show_name']); box.addWidget(self.show_name)
        box.addWidget(button(tr('save'), self.save, 'primary'))
        self.address = QLineEdit(); self.address.setObjectName('obsAddress'); self.address.setReadOnly(True); self.address.setAccessibleName(tr('obs_url')); box.addWidget(self.address)
        self.copy = button(tr('obs_copy'), self.copy_url); self.preview = button(tr('obs_preview'), self.open_preview)
        box.addWidget(row(self.copy, self.preview, None))
        box.addWidget(label(tr('obs_instructions'), 'muted', True))
        self.message = label('', 'muted', True); box.addWidget(self.message)
        control.server.changed.connect(self.refresh)
        self.refresh()

    def refresh(self):
        url = self.control.url
        self.address.setText(url); self.copy.setEnabled(bool(url)); self.preview.setEnabled(bool(url))

    def save(self):
        try:
            self.control.save(dict(enabled=self.enabled.isChecked(), game=self.game.currentData(), scope=self.scope.currentData(), style=self.style.currentData(), color=self.color.text().strip(), show_name=self.show_name.isChecked()))
            self.message.setText(tr('obs_saved')); self.control.window.phone_control.invalidate()
        except (OSError, ValueError, RuntimeError):self.message.setText(tr('obs_failed'))
        self.refresh()

    def copy_url(self):
        QApplication.clipboard().setText(self.control.url); self.message.setText(tr('obs_copied'))

    def open_preview(self):
        if self.control.url:QDesktopServices.openUrl(QUrl(self.control.url))
