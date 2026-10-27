"""Widgets Qt com layout adaptável e pintura em buffer da própria Qt."""
import math
from PySide6.QtCore import Qt, QRect, QSize, QPointF
from PySide6.QtGui import QColor, QPainter, QFont
from PySide6.QtWidgets import (QWidget, QLabel, QPushButton, QFrame, QVBoxLayout,
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
    card.setObjectName('card')
    box = QVBoxLayout(card)
    box.setContentsMargins(18, 16, 18, 16)
    box.setSpacing(7)
    box.addWidget(label(title, 'muted'))
    box.addWidget(label(value, 'metric'))
    if detail:
        box.addWidget(label(detail, 'muted', True))
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
    widget.horizontalHeader().setStretchLastSection(True)
    widget.verticalHeader().setDefaultSectionSize(46)
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
        n = max(1, len(self.data))
        slot = (self.width() - 24) / n
        maximum = max((seconds for _, seconds in self.data), default=0) or 1
        baseline = self.height() - 30
        painter.setFont(QFont('Segoe UI', 9))
        for index, (name, seconds) in enumerate(self.data):
            x = 12 + slot * index
            width = min(48, slot * .5)
            height = (baseline - 30) * seconds / maximum
            painter.setPen(Qt.NoPen)
            color = QColor('#8599b0'); color.setAlpha(240 if index == n - 1 else 160)
            painter.setBrush(color)
            if seconds:
                painter.drawRoundedRect(QRect(int(x + (slot - width) / 2), int(baseline - height), int(width), int(height)), 4, 4)
            painter.setPen(muted)
            painter.drawText(QRect(int(x), baseline + 8, int(slot), 20), Qt.AlignCenter, str(name))
            if seconds:
                painter.drawText(QRect(int(x), int(baseline - height - 24), int(slot), 20), Qt.AlignCenter, f'{seconds / 3600:.1f}h')
        painter.end()
