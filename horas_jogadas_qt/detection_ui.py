"""Vínculo explícito ao jogo e controles de detecção no tema do aplicativo."""
import sys
from PySide6.QtWidgets import QFrame,QVBoxLayout,QComboBox,QLineEdit,QCheckBox,QFileDialog,QDialogButtonBox
from .widgets import label,button,row,Form
from .texts import tr
from . import preferences
from .detection import profiles,save_profile


def configure(window,key):
    game=window.c.repo.jogo_por_id(key)
    if game is None:return
    profile=profiles(window.c.folder).get(key,{})
    d=Form(window,tr('detect_title')+' · '+game.nome)
    enabled=QCheckBox(tr('detect_this'));enabled.setChecked(profile.get('enabled',False));enabled.setObjectName('detectGameEnabled')
    executable=QLineEdit(profile.get('executable',''));executable.setObjectName('detectExecutable')
    mode=QComboBox();mode.addItem(tr('detect_path'),'path');mode.addItem(tr('detect_name'),'name');mode.setCurrentIndex(max(0,mode.findData(profile.get('mode','path'))))
    def choose():
        path,_=QFileDialog.getOpenFileName(d,tr('detect_choose'),executable.text(),tr('detect_files') if sys.platform=='win32' else tr('detect_all_files'))
        if path:executable.setText(path)
    d.form.addRow('',enabled);d.form.addRow(tr('detect_executable'),row(executable,button(tr('detect_choose'),choose)))
    d.form.addRow(tr('detect_match'),mode);d.form.addRow('',label(tr('detect_help'),'muted',True))
    d.resize(660,380)
    def save():
        if window.perform(lambda:save_profile(window,key,enabled.isChecked(),executable.text(),mode.currentData()),refresh=False):
            window.game_detection.reset();window.notify(tr('detect_configured'));return True
        return False
    d.submit(save);d.exec()
    window.refresh()


class DetectionCard(QFrame):
    def __init__(self,window):
        super().__init__();self.setObjectName('card');box=QVBoxLayout(self);box.setContentsMargins(22,20,22,20);box.setSpacing(14)
        box.addWidget(label(tr('detect_title'),'gameName'));box.addWidget(label(tr('detect_intro'),'muted',True))
        toggle=QCheckBox(tr('detect_global'));toggle.setObjectName('detectGlobal');toggle.setChecked(bool(preferences.read(window.c.folder).get('detection_enabled',False)));box.addWidget(toggle)
        def save():
            if window.perform(lambda:preferences.save(window.c.folder,detection_enabled=toggle.isChecked()),refresh=False):window.game_detection.reset();window.notify(tr('done'))
        box.addWidget(button(tr('save'),save,'primary'))
        game=QComboBox()
        for item in window.c.repo.jogos:game.addItem(item.nome,item.id)
        open_button=button(tr('detect_configure'),lambda:configure(window,game.currentData()));open_button.setEnabled(bool(game.count()))
        box.addWidget(row(game,open_button));box.addWidget(label(tr('detect_help'),'muted',True))
