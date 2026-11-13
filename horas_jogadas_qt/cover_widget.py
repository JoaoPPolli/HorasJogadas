"""Banner opcional: somente pintura de imagem local durante a rolagem."""
from PySide6.QtCore import Qt,QRectF,QSize
from PySide6.QtGui import QImage,QPainter,QPainterPath,QColor,QLinearGradient,QPalette
from PySide6.QtWidgets import QPushButton,QSizePolicy
from .texts import tr


class GameCover(QPushButton):
    def __init__(self,name,path=None,parent=None,*,fit='cover',height=132):
        super().__init__(parent)
        self.image=QImage(str(path)) if path else QImage()
        self.fit=fit
        self.setFixedHeight(height);self.setMinimumWidth(0)
        self.setSizePolicy(QSizePolicy.Expanding,QSizePolicy.Fixed)
        self.setCursor(Qt.PointingHandCursor);self.setToolTip(tr('covers_choose'))
        self.setAccessibleName(tr('covers_for').format(name=name));self.setObjectName('gameCover')
        self.setStyleSheet(f'QPushButton#gameCover {{ padding: 0px; min-height: {height}px; max-height: {height}px; border: none; }}')

    def sizeHint(self):return QSize(260,self.height())
    def minimumSizeHint(self):return QSize(0,self.height())

    def image_rect(self,rect=None):
        rect=rect if rect is not None else QRectF(self.rect()).adjusted(.5,.5,-.5,-.5)
        if self.image.isNull():return QRectF()
        ratio=(min if self.fit=='contain' else max)(rect.width()/self.image.width(),rect.height()/self.image.height())
        width,height=self.image.width()*ratio,self.image.height()*ratio
        return QRectF(rect.left()+(rect.width()-width)/2,rect.top()+(rect.height()-height)/2,width,height)

    def paintEvent(self,event):
        painter=QPainter(self);painter.setRenderHint(QPainter.Antialiasing);painter.setRenderHint(QPainter.SmoothPixmapTransform)
        rect=QRectF(self.rect()).adjusted(.5,.5,-.5,-.5)
        clip=QPainterPath();clip.addRoundedRect(rect,8,8);painter.setClipPath(clip)
        painter.fillRect(rect,self.palette().color(QPalette.Window) if self.fit=='contain' else QColor('#242735'))
        if not self.image.isNull():
            painter.drawImage(self.image_rect(rect),self.image)
        else:
            gradient=QLinearGradient(0,0,self.width(),self.height());gradient.setColorAt(0,QColor('#343448'));gradient.setColorAt(1,QColor('#22232c'))
            painter.fillRect(rect,gradient);painter.setPen(QColor('#bbb7d6'));painter.drawText(rect,Qt.AlignCenter,tr('covers_find'))
        if self.underMouse() or self.hasFocus():
            painter.fillRect(rect,QColor(0,0,0,40));painter.setClipping(False)
            painter.setPen(QColor('#b9b2ff'));painter.drawRoundedRect(rect,8,8)
