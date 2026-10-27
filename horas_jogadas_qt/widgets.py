"""Widgets Qt com layout adaptável e pintura em buffer da própria Qt."""
import math
import hashlib
from PySide6.QtCore import Qt, QRect, QRectF, QSize, QPointF
from PySide6.QtGui import QColor, QPainter, QFont, QFontMetrics, QImage, QPainterPath
from PySide6.QtWidgets import (QApplication, QWidget, QLabel, QPushButton, QFrame, QVBoxLayout,
                              QHBoxLayout, QLayout, QDialog, QFormLayout, QDialogButtonBox,
                              QMessageBox, QTableWidget, QHeaderView, QAbstractItemView)
from .texts import tr


def label(text, name='', wrap=False):
    item = QLabel(text)
    item.setObjectName(name)
    item.setWordWrap(wrap)
    item.setTextFormat(Qt.PlainText)
    return item


def button(text, callback=None, name=''):
    item = QPushButton(text)
    item.setObjectName(name)
    item.setCursor(Qt.PointingHandCursor)
    if callback:
        item.clicked.connect(callback)
    return item


def row(*items):
    widget = QWidget()
    layout = QHBoxLayout(widget)
    layout.setContentsMargins(0, 0, 0, 0)
    layout.setSpacing(10)
    for item in items:
        if item is None:
            layout.addStretch()
        else:
            layout.addWidget(item)
    return widget


def metric(title, value, detail=''):
    card = QFrame()
    card.setObjectName('metricCard')
    box = QVBoxLayout(card)
    box.setContentsMargins(18, 16, 18, 16)
    box.setSpacing(7)
    box.addWidget(label(title, 'muted'))
    box.addWidget(label(value, 'metric'))
    if detail:
        box.addWidget(label(detail, 'muted', True))
    box.addStretch()
    return card


def table(headers):
    widget = QTableWidget(0, len(headers))
    widget.setHorizontalHeaderLabels(headers)
    widget.verticalHeader().hide()
    widget.setShowGrid(False)
    widget.setAlternatingRowColors(True)
    widget.setSelectionBehavior(QAbstractItemView.SelectRows)
    widget.setSelectionMode(QAbstractItemView.SingleSelection)
    widget.setEditTriggers(QAbstractItemView.NoEditTriggers)
    widget.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeToContents)
    widget.horizontalHeader().setDefaultAlignment(Qt.AlignLeft | Qt.AlignVCenter)
    widget.horizontalHeader().setStretchLastSection(False)
    widget.horizontalHeader().setSectionResizeMode(0, QHeaderView.Stretch)
    widget.verticalHeader().setDefaultSectionSize(50)
    widget.setCornerButtonEnabled(False)
    widget.setVerticalScrollMode(QAbstractItemView.ScrollPerPixel)
    return widget


class Form(QDialog):
    def __init__(self, parent, title):
        super().__init__(parent)
        self.setWindowTitle(title)
        self.setMinimumWidth(490)
        self.box = QVBoxLayout(self)
        self.box.setContentsMargins(24, 22, 24, 22)
        self.box.setSpacing(18)
        self.box.addWidget(label(title, 'gameName'))
        self.form = QFormLayout()
        self.form.setSpacing(12)
        self.box.addLayout(self.form)
        self.buttons = QDialogButtonBox(QDialogButtonBox.Save | QDialogButtonBox.Cancel)
        self.buttons.button(QDialogButtonBox.Save).setText(tr('save'))
        self.buttons.button(QDialogButtonBox.Save).setObjectName('primary')
        self.buttons.button(QDialogButtonBox.Cancel).setText(tr('cancel'))
        self.buttons.rejected.connect(self.reject)
        self.box.addWidget(self.buttons)

    def submit(self, callback):
        def save():
            try:
                if callback() is not False:
                    self.accept()
            except Exception as error:
                QMessageBox.warning(self, tr('error'), str(error))
        self.buttons.accepted.connect(save)


class CardLayout(QLayout):
    """Reposiciona widgets existentes; não destrói cartões na rolagem ou resize."""
    def __init__(self, parent):
        super().__init__(parent)
        self.items = []
        self.setContentsMargins(0, 0, 0, 0)
        self.setSpacing(16)

    def addItem(self, item):
        self.items.append(item)

    def count(self):
        return len(self.items)

    def itemAt(self, i):
        return self.items[i] if 0 <= i < len(self.items) else None

    def takeAt(self, i):
        return self.items.pop(i) if 0 <= i < len(self.items) else None

    def expandingDirections(self):
        return Qt.Horizontal

    def hasHeightForWidth(self):
        return True

    def visible(self):
        return [item for item in self.items if not item.widget().isHidden()]

    def heightForWidth(self, width):
        items = self.visible()
        cols = max(1, int((width + self.spacing()) / (310 + self.spacing())))
        height = max((i.sizeHint().height() for i in items), default=0)
        return max(0, math.ceil(len(items) / cols) * (height + self.spacing()) - self.spacing())

    def minimumSize(self):
        return QSize(310, 0)

    def sizeHint(self):
        return QSize(650, self.heightForWidth(650))

    def setGeometry(self, rect):
        super().setGeometry(rect)
        items = self.visible()
        cols = max(1, int((rect.width() + self.spacing()) / (310 + self.spacing())))
        width = (rect.width() - (cols - 1) * self.spacing()) // cols
        height = max((i.sizeHint().height() for i in items), default=0)
        for index, item in enumerate(items):
            item.setGeometry(QRect(rect.x() + (index % cols) * (width + self.spacing()),
                                   rect.y() + (index // cols) * (height + self.spacing()), width, height))


class Chart(QWidget):
    def __init__(self, data, parent=None):
        super().__init__(parent)
        self.data = data
        self.setMinimumHeight(210)

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        text = self.palette().windowText().color()
        muted = QColor(text); muted.setAlpha(150)
        painter.setFont(QFont('Segoe UI', 9))
        maximum = max((seconds for _, seconds in self.data), default=0)
        if maximum <= 0:
            painter.setPen(muted)
            painter.drawText(self.rect(), Qt.AlignCenter, tr('empty_chart'))
            painter.end()
            return
        left, right = 48, self.width() - 12
        top, baseline = 24, self.height() - 32
        grid = QColor(text); grid.setAlpha(25)
        for fraction in (0, .5, 1):
            y = baseline - (baseline - top) * fraction
            painter.setPen(grid)
            painter.drawLine(left, int(y), right, int(y))
            painter.setPen(muted)
            painter.drawText(QRect(0, int(y) - 10, left - 10, 20), Qt.AlignRight | Qt.AlignVCenter,
                             f'{maximum * fraction / 3600:.0f}h')
        n = max(1, len(self.data)); slot = (right - left) / n
        latest = max((i for i, (_, seconds) in enumerate(self.data) if seconds), default=0)
        for index, (name, seconds) in enumerate(self.data):
            x = left + slot * index
            width = min(44, slot * .46)
            height = (baseline - top) * seconds / maximum
            painter.setPen(Qt.NoPen)
            original = QApplication.instance().property('horasTheme') == 'original'
            color = QColor(QApplication.palette().link().color()) if original else QColor(text)
            color.setAlpha((220 if index == latest else 150) if original else (180 if index == latest else 75))
            painter.setBrush(color)
            if seconds:
                painter.drawRoundedRect(QRect(int(x + (slot - width) / 2), int(baseline - height), int(width), max(2, int(height))), 4, 4)
            painter.setPen(muted)
            painter.drawText(QRect(int(x), baseline + 8, int(slot), 20), Qt.AlignCenter, str(name))
            if seconds:
                painter.drawText(QRect(int(x), int(baseline - height - 23), int(slot), 20), Qt.AlignCenter,
                                 f'{seconds / 3600:.1f}h')
        painter.end()


class GameAvatar(QPushButton):
    def __init__(self, name, parent=None, path=None):
        super().__init__(parent)
        self.name = name
        self.image = QImage(str(path)) if path else QImage()
        self.setObjectName('gameAvatar')
        self.setStyleSheet('QPushButton#gameAvatar { padding: 0; min-height: 42px; max-height: 42px; min-width: 42px; max-width: 42px; border: none; }')
        self.setFixedSize(42, 42)
        self.setAccessibleName(tr('game_icons_for').format(name=name))
        self.setToolTip(tr('game_icons_choose'))
        self.setCursor(Qt.PointingHandCursor)

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        hue = int.from_bytes(hashlib.sha256(self.name.encode('utf-8')).digest()[:2], 'big') / 65535
        dark = self.palette().window().color().lightness() < 128
        background = QColor.fromHslF(hue, .16, .22 if dark else .90)
        foreground = QColor.fromHslF(hue, .25, .77 if dark else .28)
        painter.setBrush(background); painter.setPen(Qt.NoPen)
        painter.drawRoundedRect(QRect(0, 0, 42, 42), 10, 10)
        if not self.image.isNull():
            painter.setRenderHint(QPainter.SmoothPixmapTransform)
            clip=QPainterPath();clip.addRoundedRect(QRectF(self.rect()),10,10);painter.setClipPath(clip)
            size=self.image.size().scaled(self.size(),Qt.KeepAspectRatio)
            target=QRectF((42-size.width())/2,(42-size.height())/2,size.width(),size.height())
            painter.drawImage(target,self.image);painter.setClipping(False)
        else:
            initials = ''.join(word[0] for word in self.name.split()[:2]).upper()
            painter.setFont(QFont('Segoe UI', 11, QFont.DemiBold)); painter.setPen(foreground)
            painter.drawText(self.rect(), Qt.AlignCenter, initials)
        if self.hasFocus():
            painter.setBrush(Qt.NoBrush);painter.setPen(self.palette().highlight().color())
            painter.drawRoundedRect(QRectF(self.rect()).adjusted(1,1,-1,-1),9,9)
        painter.end()


class ElidedLabel(QWidget):
    """Mantém o título em uma linha sem permitir que nomes longos alarguem o cartão."""
    def __init__(self, text, parent=None):
        super().__init__(parent)
        self.text = text
        self.setMinimumWidth(0)
        self.setFixedHeight(25)
        self.setToolTip(text)
        self.setAccessibleName(text)

    def sizeHint(self):
        return QSize(120, 25)

    def paintEvent(self, event):
        painter = QPainter(self)
        font = QFont('Segoe UI', 11, QFont.DemiBold)
        painter.setFont(font); painter.setPen(self.palette().windowText().color())
        text = QFontMetrics(font).elidedText(self.text, Qt.ElideRight, self.width())
        painter.drawText(self.rect(), Qt.AlignVCenter | Qt.AlignLeft, text)
        painter.end()


class Ranking(QWidget):
    """Top 5 com barras proporcionais, nomes e duração, como no dashboard original."""
    def __init__(self, groups, parent=None):
        super().__init__(parent)
        self.groups = groups
        self.row_height = 32
        self.setMinimumHeight(max(55,len(groups)*self.row_height))
        self.setAccessibleName(tr('top'))
        self.setMouseTracking(True)

    def paintEvent(self,event):
        from horas_jogadas.utils import formatar_hhmmss
        painter=QPainter(self); painter.setRenderHint(QPainter.Antialiasing)
        foreground=self.palette().windowText().color()
        muted=QColor(foreground); muted.setAlpha(140)
        painter.setFont(QFont('Segoe UI',10))
        if not self.groups:
            painter.setPen(muted)
            painter.drawText(self.rect(),Qt.AlignCenter,tr('no_playtime'))
            painter.end(); return
        maximum=max(group.total for group in self.groups) or 1
        metrics=painter.fontMetrics()
        # Mesmo arranjo do gráfico original: nome | barra de horas | duração.
        # Não há trilho nem valor-alvo: todas as barras representam tempo, não conclusão.
        name_width=int(min(max(max(metrics.horizontalAdvance(g.nome) for g in self.groups)+16,120),self.width()*.4))
        duration_width=max(metrics.horizontalAdvance(formatar_hhmmss(g.total,simplificado=True)) for g in self.groups)+12
        plot_width=max(1,self.width()-name_width-duration_width-8)
        fill=QColor(QApplication.palette().link().color()) if QApplication.instance().property('horasTheme') == 'original' else QColor('#7567f0' if self.palette().window().color().lightness()<128 else '#6250d8')
        for index,group in enumerate(self.groups):
            top=index*self.row_height
            painter.setPen(foreground)
            painter.drawText(QRect(0,top,name_width-14,self.row_height),Qt.AlignLeft|Qt.AlignVCenter,
                             metrics.elidedText(group.nome,Qt.ElideRight,name_width-14))
            width=max(2,int(plot_width*group.total/maximum))
            bar=QRect(name_width,top+(self.row_height-14)//2,width,14)
            painter.setPen(Qt.NoPen); painter.setBrush(fill)
            painter.drawRect(bar)
            painter.setPen(muted)
            painter.drawText(QRect(bar.right()+8,top,duration_width,self.row_height),Qt.AlignLeft|Qt.AlignVCenter,
                             formatar_hhmmss(group.total,simplificado=True))
        painter.end()

    def mouseMoveEvent(self,event):
        from horas_jogadas.utils import formatar_hhmmss
        index=int(event.position().y()//self.row_height)
        if 0<=index<len(self.groups):
            group=self.groups[index]
            self.setToolTip(group.nome+' · '+formatar_hhmmss(group.total,simplificado=True))
        super().mouseMoveEvent(event)
