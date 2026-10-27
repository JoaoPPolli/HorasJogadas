"""Ajuste de tempo com os mesmos campos, atalhos e tratamento de pausa do app atual."""
from PySide6.QtCore import Qt, QTimer
from PySide6.QtGui import QIntValidator
from PySide6.QtWidgets import QWidget, QVBoxLayout, QLineEdit, QDialogButtonBox
from horas_jogadas.constants import PAUSA_ATALHOS_MIN
from horas_jogadas.i18n import t
from horas_jogadas.utils import formatar_hhmmss
from .texts import tr
from .widgets import Form, row, label, button


class TimeDialog(Form):
    def __init__(self, window, key):
        game = window.c.repo.jogo_por_id(key)
        super().__init__(window,t('tempo.titulo'))
        self.window_owner, self.key = window,key
        self.setMinimumWidth(450)
        self.box.itemAt(0).widget().setText(t('tempo.adicionar',nome=game.nome))
        self.box.itemAt(0).widget().setWordWrap(True)
        self.fields = []
        columns = []
        for name,title in [('hours',t('tempo.horas')),('minutes',t('tempo.minutos')),('seconds',t('tempo.segundos'))]:
            column = QWidget(); layout = QVBoxLayout(column); layout.setContentsMargins(0,0,0,0)
            heading = label(title,'muted'); heading.setAlignment(Qt.AlignCenter)
            field = QLineEdit('0'); field.setObjectName(name)
            field.setValidator(QIntValidator(-2147483647,2147483647,field))
            field.setAlignment(Qt.AlignCenter); field.setAccessibleName(title)
            layout.addWidget(heading); layout.addWidget(field)
            columns.append(column); self.fields.append(field)
        self.form.addRow(row(*columns))
        shortcuts = []
        for minutes in PAUSA_ATALHOS_MIN:
            shortcut = button(t('tempo.atalho',n=minutes),lambda checked=False,m=minutes:self.add_minutes(m))
            shortcut.setObjectName('add'+str(minutes))
            shortcuts.append(shortcut)
        self.form.addRow(row(*shortcuts))
        self.pause_label = None
        if window.c.timers[key].pausado:
            self.pause_label = label('','muted')
            self.use_pause = button(t('tempo.usar'),self.use_paused_duration)
            self.use_pause.setObjectName('usePause')
            self.form.addRow(row(self.pause_label,None,self.use_pause))
            self.pause_tick = QTimer(self); self.pause_tick.setInterval(1000)
            self.pause_tick.timeout.connect(self.update_pause); self.pause_tick.start()
            self.update_pause()
        self.form.addRow(label(t('tempo.negativo'),'muted'))
        self.buttons.button(QDialogButtonBox.Save).setText(t('btn.confirmar'))
        self.submit(self.save_adjustment)

    def read_seconds(self):
        try:
            hours,minutes,seconds = [int(field.text()) for field in self.fields]
        except ValueError:
            raise ValueError(t('tempo.invalido')) from None
        return hours*3600+minutes*60+seconds

    def set_seconds(self,total):
        sign = -1 if total<0 else 1
        hours,remainder = divmod(abs(total),3600)
        for field,value in zip(self.fields,(hours,remainder//60,remainder%60)):
            field.setText(str(sign*value))

    def add_minutes(self,minutes):
        try:
            self.set_seconds(self.read_seconds()+minutes*60)
        except ValueError as error:
            from PySide6.QtWidgets import QMessageBox
            QMessageBox.warning(self,tr('error'),str(error))

    def pause_seconds(self):
        timer = self.window_owner.c.timers[self.key]
        return max(0,int(timer.clock.time()-timer.pausa)) if timer.pausado else 0

    def update_pause(self):
        paused = self.window_owner.c.timers[self.key].pausado
        self.pause_label.setText(t('card.pausado_ha',tempo=formatar_hhmmss(self.pause_seconds())))
        self.use_pause.setEnabled(paused)

    def use_paused_duration(self):
        self.set_seconds(self.pause_seconds())

    def save_adjustment(self):
        delta = self.read_seconds()
        def apply():
            self.window_owner.c.timers[self.key].adjust(delta)
            self.window_owner.c.save_pending()
        return self.window_owner.perform(apply)
