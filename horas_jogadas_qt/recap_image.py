"""Imagem compartilhável gerada localmente, sem fontes ou serviços de rede."""
from PySide6.QtCore import Qt,QRectF,QBuffer,QIODevice,QSaveFile
from PySide6.QtGui import QImage,QPainter,QColor,QFont,QLinearGradient,QFontMetrics
from .theme import PALETTES
from horas_jogadas.zerados import MESES,MESES_EN


def render(data,theme='original',language='pt'):
    en=language=='en';bg,side,card,border,ink,muted,accent,on_accent=PALETTES.get(theme,PALETTES['original'])
    image=QImage(1080,1350,QImage.Format_ARGB32);image.fill(QColor(bg));p=QPainter(image);p.setRenderHint(QPainter.Antialiasing)
    gradient=QLinearGradient(0,0,1080,1000);gradient.setColorAt(0,QColor(side));gradient.setColorAt(1,QColor(bg));p.fillRect(image.rect(),gradient)
    def text(x,y,w,h,value,size=22,color=ink,bold=False):
        p.setPen(QColor(color));p.setFont(QFont('Sans Serif',size,QFont.Bold if bold else QFont.Normal))
        value=QFontMetrics(p.font()).elidedText(str(value),Qt.ElideRight,int(w));p.drawText(QRectF(x,y,w,h),Qt.AlignLeft|Qt.AlignVCenter,value)
    def rect(x,y,w,h,color,r=22):p.setPen(Qt.NoPen);p.setBrush(QColor(color));p.drawRoundedRect(QRectF(x,y,w,h),r,r)
    rect(64,62,12,42,accent,4);text(96,56,800,50,'HORASJOGADAS',26,bold=True)
    text(64,147,950,40,'YOUR GAMING RECAP' if en else 'SUA RETROSPECTIVA',16,muted,True)
    period=str(data['year']) if not data['month'] else (MESES_EN if en else MESES)[data['month']-1]+' '+str(data['year'])
    text(64,196,950,70,period,42,bold=True)
    total=data['total_seconds'];text(64,297,950,110,f'{total//3600}h {total%3600//60:02d}m',70,accent,True)
    text(68,414,940,40,'of stories, challenges and good games.' if en else 'de histórias, desafios e boas partidas.',21,muted)
    labels=['GAMES','SESSIONS','COMPLETED','ACTIVE DAYS'] if en else ['JOGOS','SESSÕES','ZERADOS','DIAS JOGADOS']
    for i,value in enumerate([data['games'],data['sessions'],data['completed'],data['days']]):
        x=64+i*242;rect(x,504,224,140,card);text(x+20,519,190,57,value,32,bold=True);text(x+20,584,190,38,labels[i],12,muted,True)
    text(64,699,950,50,'YOUR MOST PLAYED' if en else 'OS QUE MAIS MARCARAM',23,bold=True)
    maximum=data['top'][0]['seconds'] if data['top'] else 1
    for i,item in enumerate(data['top']):
        y=776+i*82;text(64,y,48,35,f'{i+1:02}',17,muted);text(126,y,655,35,item['name'],20,bold=True)
        text(807,y,215,35,f"{item['seconds']//3600}h {item['seconds']%3600//60:02d}m",18,muted)
        rect(126,y+49,max(3,890*item['seconds']/maximum),6,accent,3)
    if not data['top']:text(64,800,950,70,'Your next adventure starts here.' if en else 'Sua próxima aventura começa aqui.',24,muted)
    p.setPen(QColor(border));p.drawLine(64,1232,1016,1232)
    text(64,1254,950,35,'Saved sessions • generated on your device' if en else 'Sessões salvas • gerado no seu dispositivo',15,muted)
    text(64,1291,950,30,'HorasJogadas • '+('Every game counts.' if en else 'Cada partida conta.'),13,muted)
    p.end();return image


def png_bytes(data,theme='original',language='pt'):
    buffer=QBuffer();buffer.open(QIODevice.WriteOnly)
    if not render(data,theme,language).save(buffer,'PNG'):raise OSError('PNG export failed')
    return bytes(buffer.data())


def save_png(path,data,theme='original',language='pt'):
    content=png_bytes(data,theme,language);file=QSaveFile(str(path))
    if not file.open(QIODevice.WriteOnly) or file.write(content)!=len(content) or not file.commit():raise OSError(file.errorString())
