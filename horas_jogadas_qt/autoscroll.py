"""Rolagem vertical por botão central, sem hooks globais ou consultas do ponteiro."""
import math
import time
from shiboken6 import isValid
from PySide6.QtCore import QObject,QEvent,QPoint,QPointF,Qt,QTimer
from PySide6.QtGui import QColor,QCursor,QPainter,QPen,QPixmap,QPolygonF
from PySide6.QtWidgets import (QApplication,QWidget,QAbstractScrollArea,QAbstractItemView,
    QLineEdit,QTextEdit,QPlainTextEdit,QAbstractSpinBox,QComboBox,QScrollBar,QMenu)


def symbol(direction=0,ratio=1):
    pixmap=QPixmap(round(32*ratio),round(32*ratio));pixmap.setDevicePixelRatio(ratio);pixmap.fill(Qt.transparent)
    painter=QPainter(pixmap);painter.setRenderHint(QPainter.Antialiasing)
    painter.setPen(QPen(QColor('#17191c'),1.3));painter.setBrush(QColor('#ffffff'))
    painter.drawEllipse(QPointF(16,16),2.8,2.8)
    if direction<=0:painter.drawPolygon(QPolygonF([QPointF(16,4),QPointF(12,10),QPointF(20,10)]))
    if direction>=0:painter.drawPolygon(QPolygonF([QPointF(16,28),QPointF(12,22),QPointF(20,22)]))
    painter.end();return pixmap


class ScrollOverlay(QWidget):
    def __init__(self,window):
        super().__init__(window)
        self.setObjectName('autoScrollOverlay');self.setMouseTracking(True)
        self.setFocusPolicy(Qt.NoFocus);self.setAttribute(Qt.WA_NoSystemBackground)
        self.setGeometry(window.rect())


class AutoScroll(QObject):
    DEAD_ZONE=12

    def __init__(self,window):
        super().__init__(window)
        self.window=window;self.area=None;self.overlay=None;self.cancel_release=None;self.cancel_context=False
        self.timer=QTimer(self);self.timer.setInterval(16);self.timer.setTimerType(Qt.PreciseTimer)
        self.timer.timeout.connect(self.tick)
        QApplication.instance().installEventFilter(self)

    @property
    def active(self):return self.area is not None

    def owned(self,widget):
        while widget is not None:
            if widget is self.window:return True
            widget=widget.parentWidget()
        return False

    def scroll_area(self,widget,point):
        if not isinstance(widget,QWidget) or not self.owned(widget):return None
        # Um campo pode ignorar o clique em uma plataforma e propagá-lo ao pai.
        # Conserva o controle realmente sob o ponteiro mesmo nessa propagação.
        child=widget.childAt(widget.mapFromGlobal(point))
        if child is not None:widget=child
        current=widget
        while current is not None:
            # Mantém a colagem pelo botão central no Linux e o comportamento dos controles.
            if isinstance(current,(QLineEdit,QTextEdit,QPlainTextEdit,QAbstractSpinBox,QComboBox,QScrollBar,QMenu)):
                return None
            current=current.parentWidget()
        current=widget
        while current is not None:
            if isinstance(current,QAbstractScrollArea) and current.isEnabled():
                bar=current.verticalScrollBar()
                local=current.viewport().mapFromGlobal(point)
                if (bar.maximum()>bar.minimum() and current.verticalScrollBarPolicy()!=Qt.ScrollBarAlwaysOff
                        and current.viewport().rect().contains(local)):
                    return current
            current=current.parentWidget()
        return None

    def start(self,area,anchor):
        self.stop();self.area=area;self.anchor=QPoint(anchor);self.pointer=QPoint(anchor)
        self.awaiting_release=True;self.dragged=False;self.fraction=0.;self.last_tick=time.monotonic()
        self.overlay=ScrollOverlay(area.window())
        ratio=area.window().devicePixelRatioF()
        self.cursors={n:QCursor(symbol(n,ratio),16,16) for n in (-1,0,1)}
        self.overlay.setCursor(self.cursors[0]);self.overlay.show();self.overlay.raise_();self.timer.start()

    def stop(self):
        self.timer.stop();self.area=None;self.cancel_release=None;self.cancel_context=False
        overlay,self.overlay=self.overlay,None
        if overlay is not None and isValid(overlay):overlay.hide();overlay.deleteLater()

    def move(self,point):
        self.pointer=QPoint(point);offset=self.pointer-self.anchor
        if self.awaiting_release and offset.manhattanLength()>self.DEAD_ZONE:self.dragged=True
        direction=0 if abs(offset.y())<=self.DEAD_ZONE else (1 if offset.y()>0 else -1)
        if self.overlay is not None:self.overlay.setCursor(self.cursors[direction])

    def advance(self,seconds):
        if not self.active:return
        if not isValid(self.area) or not self.area.isVisible():self.stop();return
        offset=self.pointer.y()-self.anchor.y();distance=max(0,abs(offset)-self.DEAD_ZONE)
        if not distance:self.fraction=0.;return
        velocity=math.copysign(min(2400,distance**1.65*.7),offset)
        bar=self.area.verticalScrollBar()
        if isinstance(self.area,QAbstractItemView) and self.area.verticalScrollMode()==QAbstractItemView.ScrollPerItem:
            velocity*=bar.pageStep()/max(1,self.area.viewport().height())
        self.fraction+=velocity*seconds;step=int(self.fraction);self.fraction-=step
        bar.setValue(bar.value()+step)

    def tick(self):
        now=time.monotonic();elapsed=min(.05,now-self.last_tick);self.last_tick=now;self.advance(elapsed)

    def eventFilter(self,watched,event):
        kind=event.type()
        if self.active:
            if kind in (QEvent.MouseButtonPress,QEvent.MouseButtonDblClick):
                button=event.button();self.stop();self.cancel_release=button;self.cancel_context=button==Qt.RightButton
                return True
            if kind==QEvent.MouseButtonRelease and event.button()==Qt.MiddleButton:
                self.awaiting_release=False
                if self.dragged:self.stop()
                return True
            if kind==QEvent.MouseMove:
                self.move(event.globalPosition().toPoint());return True
            if kind==QEvent.KeyPress:
                self.stop();return event.key()==Qt.Key_Escape
            if kind==QEvent.Shortcut:self.stop();return False
            if kind==QEvent.Wheel:self.stop();return True
            if kind==QEvent.ApplicationDeactivate:
                self.stop()
            elif not isValid(self.area):self.stop()
            elif (kind in (QEvent.Hide,QEvent.WindowDeactivate,QEvent.Move,QEvent.Resize)
                    and watched is self.area.window()):self.stop()
            elif kind==QEvent.Hide and watched is self.area:self.stop()
            elif kind==QEvent.Leave and watched is self.overlay:self.stop()
        else:
            if kind==QEvent.MouseButtonRelease and event.button()==self.cancel_release:
                self.cancel_release=None;return True
            if kind==QEvent.ContextMenu and self.cancel_context:
                self.cancel_context=False;return True
            if kind in (QEvent.MouseButtonPress,QEvent.MouseButtonDblClick):
                self.cancel_release=None;self.cancel_context=False
                if event.button()==Qt.MiddleButton:
                    area=self.scroll_area(watched,event.globalPosition().toPoint())
                    if area is not None:
                        self.start(area,event.globalPosition().toPoint());return True
        return False
