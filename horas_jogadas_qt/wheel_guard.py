"""A roda rola conteúdo; escolhas e valores continuam sob controle explícito."""
from PySide6.QtCore import QObject,QEvent
from PySide6.QtGui import QWheelEvent
from PySide6.QtWidgets import QApplication,QWidget,QComboBox,QAbstractSpinBox,QAbstractScrollArea,QSlider,QDial


class WheelGuard(QObject):
    def eventFilter(self,watched,event):
        if event.type()!=QEvent.Wheel or not isinstance(watched,QWidget):return False
        current=watched;control=None
        while current is not None:
            if isinstance(current,(QComboBox,QAbstractSpinBox,QSlider,QDial)):
                control=current;break
            # A lista aberta é outra janela: nela a roda navega pelas opções,
            # sem confirmar uma escolha nem rolar a página que está atrás.
            if current.isWindow():break
            current=current.parentWidget()
        if control is None:return False
        parent=control.parentWidget()
        while parent is not None and not isinstance(parent,QAbstractScrollArea):parent=parent.parentWidget()
        if parent is not None:
            viewport=parent.viewport()
            forwarded=QWheelEvent(viewport.mapFromGlobal(event.globalPosition().toPoint()),event.globalPosition(),
                                  event.pixelDelta(),event.angleDelta(),event.buttons(),event.modifiers(),
                                  event.phase(),event.inverted(),event.source(),event.pointingDevice())
            QApplication.sendEvent(viewport,forwarded)
        event.accept()
        return True


def install(app):
    if not hasattr(app,'_horas_wheel_guard'):
        app._horas_wheel_guard=WheelGuard(app)
        app.installEventFilter(app._horas_wheel_guard)
