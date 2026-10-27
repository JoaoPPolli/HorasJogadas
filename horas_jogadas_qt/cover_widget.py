"""Banner opcional: somente pintura de imagem local durante a rolagem."""
from PySide6.QtCore import Qt,QRectF,QSize
from PySide6.QtGui import QImage,QPainter,QPainterPath,QColor,QLinearGradient
from PySide6.QtWidgets import QPushButton,QSizePolicy
from .texts import tr


class GameCover(QPushButton):
    def __init__(self,name,path=None,parent=None):
        super().__init__(parent)
        self.image=QImage(str(path)) if path else QImage()
        self.setFixedHeight(132);self.setMinimumWidth(0)
        self.setSizePolicy(QSizePolicy.Expanding,QSizePolicy.Fixed)
        self.setCursor(Qt.PointingHandCursor);self.setToolTip(tr('covers_choose'))
        self.setAccessibleName(tr('covers_for').format(name=name));self.setObjectName('gameCover')
        self.setStyleSheet('QPushButton#gameCover { padding: 0px; min-height: 132px; max-height: 132px; border: none; }')

    def sizeHint(self):return QSize(260,132)
    def minimumSizeHint(self):return QSize(0,132)

    def paintEvent(self,event):
        painter=QPainter(self);painter.setRenderHint(QPainter.Antialiasing);painter.setRenderHint(QPainter.SmoothPixmapTransform)
        rect=QRectF(self.rect()).adjusted(.5,.5,-.5,-.5)
        clip=QPainterPath();clip.addRoundedRect(rect,8,8);painter.setClipPath(clip)
        painter.fillRect(rect,QColor('#242735'))
        if not self.image.isNull():
            scale=max(rect.width()/self.image.width(),rect.height()/self.image.height())
            width,height=self.image.width()*scale,self.image.height()*scale
            painter.drawImage(QRectF((rect.width()-width)/2,(rect.height()-height)/2,width,height),self.image)
        else:
            gradient=QLinearGradient(0,0,self.width(),self.height());gradient.setColorAt(0,QColor('#343448'));gradient.setColorAt(1,QColor('#22232c'))
            painter.fillRect(rect,gradient);painter.setPen(QColor('#bbb7d6'));painter.drawText(rect,Qt.AlignCenter,tr('covers_find'))
        if self.underMouse() or self.hasFocus():
            painter.fillRect(rect,QColor(0,0,0,40));painter.setClipping(False)
            painter.setPen(QColor('#b9b2ff'));painter.drawRoundedRect(rect,8,8)
