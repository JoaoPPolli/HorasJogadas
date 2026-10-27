"""Ícones vetoriais pequenos, consistentes em Windows, Linux e escalas HiDPI."""
from PySide6.QtCore import Qt, QRectF, QPointF
from PySide6.QtGui import QIcon, QPixmap, QPainter, QPen, QColor, QPainterPath
from PySide6.QtWidgets import QApplication


def icon(name, size=20, foreground=None):
    result = QIcon()
    palette = QApplication.palette()
    for mode, color in [(QIcon.Normal, foreground or palette.buttonText().color()),
                        (QIcon.Disabled, QColor('#626d79')),
                        (QIcon.Active, palette.windowText().color())]:
        # Renderiza em 2x sem depender de fontes de símbolos instaladas.
        pixmap = QPixmap(size * 2, size * 2)
        pixmap.fill(Qt.transparent)
        painter = QPainter(pixmap)
        painter.setRenderHint(QPainter.Antialiasing)
        painter.scale(size / 12, size / 12)
        painter.setPen(QPen(color, 1.6, Qt.SolidLine, Qt.RoundCap, Qt.RoundJoin))
        painter.setBrush(Qt.NoBrush)
        if name == 'library':
            for x, y in ((4,4),(14,4),(4,14),(14,14)):
                painter.drawRoundedRect(QRectF(x,y,6,6),1.2,1.2)
        elif name in ('history','clock'):
            painter.drawEllipse(QRectF(3,3,18,18))
            painter.drawPolyline([QPointF(12,7),QPointF(12,12),QPointF(16,14)])
        elif name == 'stats':
            for x, y in ((5,14),(11,9),(17,4)):
                painter.drawRoundedRect(QRectF(x,y,3,20-y),.7,.7)
        elif name == 'completed':
            painter.drawRoundedRect(QRectF(7,3,10,11),2,2)
            painter.drawPolyline([QPointF(7,5),QPointF(3,5),QPointF(3,9),QPointF(7,11)])
            painter.drawPolyline([QPointF(17,5),QPointF(21,5),QPointF(21,9),QPointF(17,11)])
            painter.drawLine(12,14,12,20); painter.drawLine(8,21,16,21)
        elif name == 'settings':
            painter.drawEllipse(QRectF(5,5,14,14)); painter.drawEllipse(QRectF(9,9,6,6))
            for x1,y1,x2,y2 in ((12,2,12,5),(12,19,12,22),(2,12,5,12),(19,12,22,12),
                                   (5,5,7,7),(17,17,19,19),(5,19,7,17),(17,7,19,5)):
                painter.drawLine(x1,y1,x2,y2)
        elif name == 'search':
            painter.drawEllipse(QRectF(4,4,12,12)); painter.drawLine(15,15,21,21)
        elif name == 'plus':
            painter.drawLine(12,5,12,19); painter.drawLine(5,12,19,12)
        elif name == 'play':
            painter.setBrush(color); painter.setPen(Qt.NoPen)
            path=QPainterPath(); path.moveTo(8,5); path.lineTo(19,12); path.lineTo(8,19); path.closeSubpath()
            painter.drawPath(path)
        elif name == 'pause':
            painter.setBrush(color); painter.setPen(Qt.NoPen)
            painter.drawRoundedRect(QRectF(6,5,4,14),1,1); painter.drawRoundedRect(QRectF(14,5,4,14),1,1)
        elif name == 'stop':
            painter.setBrush(color); painter.setPen(Qt.NoPen); painter.drawRoundedRect(QRectF(6,6,12,12),2,2)
        elif name == 'more':
            painter.setBrush(color); painter.setPen(Qt.NoPen)
            for x in (5,12,19): painter.drawEllipse(QRectF(x-1,11,2,2))
        elif name == 'shield':
            path=QPainterPath(); path.moveTo(12,3); path.lineTo(20,6); path.lineTo(19,14)
            path.quadTo(17,19,12,22); path.quadTo(7,19,5,14); path.lineTo(4,6); path.closeSubpath()
            painter.drawPath(path)
            painter.drawPolyline([QPointF(8,12),QPointF(11,15),QPointF(16,9)])
        painter.end()
        pixmap.setDevicePixelRatio(2)
        result.addPixmap(pixmap, mode)
    return result
