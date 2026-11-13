"""Imagem compartilhável gerada localmente, sem fontes ou serviços de rede."""
from PySide6.QtCore import Qt,QRectF,QBuffer,QIODevice,QSaveFile
from PySide6.QtGui import QImage,QPainter,QColor,QFont,QLinearGradient,QFontMetrics
from .theme import PALETTES
from horas_jogadas.zerados import MESES,MESES_EN


def render(data,theme='original',language='pt'):
    en=language=='en';bg,side,card,border,ink,muted,accent,on_accent=PALETTES.get(theme,PALETTES['original'])
    image=QImage(1080,1350,QImage.Format_ARGB32);image.fill(QColor(bg));p=QPainter(image);p.setRenderHint(QPainter.Antialiasing)
    gradient=QLinearGradient(0,0,1080,1000);gradient.setColorAt(0,QColor(side));gradient.setColorAt(1,QColor(bg));p.fillRect(image.rect(),gradient)
    def text(x,y,w,h,value,size=22,color=ink,bold=False,align=Qt.AlignLeft):
        p.setPen(QColor(color));p.setFont(QFont('Sans Serif',size,QFont.Bold if bold else QFont.Normal))
        value=QFontMetrics(p.font()).elidedText(str(value),Qt.ElideRight,int(w));p.drawText(QRectF(x,y,w,h),align|Qt.AlignVCenter,value)
    def rect(x,y,w,h,color,r=22):p.setPen(Qt.NoPen);p.setBrush(QColor(color));p.drawRoundedRect(QRectF(x,y,w,h),r,r)
    rect(64,62,12,42,accent,4);text(96,56,800,50,'HORASJOGADAS',26,bold=True)
    period=str(data['year']) if not data['month'] else (MESES_EN if en else MESES)[data['month']-1]+' '+str(data['year'])
    def duration(seconds):return f'{seconds//3600}h {seconds%3600//60:02d}m' if seconds>=3600 else f'{seconds//60}m {seconds%60:02d}s'
    if data.get('game'):
        text(64,147,950,40,'YOUR GAME RECAP' if en else 'SUA HISTÓRIA NESTE JOGO',16,muted,True)
        # Até duas linhas para o título, inclusive nomes longos sem espaços.
        title=data['game']['name'];font=QFont('Sans Serif',34,QFont.Bold);metrics=QFontMetrics(font)
        cut=0
        while cut<len(title) and metrics.horizontalAdvance(title[:cut+1])<=950:cut+=1
        if cut<len(title):
            space=title.rfind(' ',0,cut+1)
            if space>cut//2:cut=space
            text(64,196,950,57,title[:cut],34,bold=True);text(64,253,950,57,title[cut:].lstrip(),34,bold=True)
        else:text(64,196,950,114,title,34,bold=True)
        text(64,320,950,38,period,22,muted)
        text(64,365,950,100,duration(data['total_seconds']),64,accent,True)
        text(68,467,940,38,'Saved playtime in this period' if en else 'Tempo salvo neste período',20,muted)
        labels=['SESSIONS','ACTIVE DAYS','AVG / SESSION','LONGEST SESSION'] if en else ['SESSÕES','DIAS JOGADOS','MÉDIA / SESSÃO','MAIOR SESSÃO']
        values=[data['sessions'],data['days'],duration(data['average_seconds']),duration(data['longest_seconds'])]
        for i,value in enumerate(values):
            x=64+i*242;rect(x,542,224,140,card);text(x+20,557,184,57,value,27,bold=True);text(x+20,622,184,38,labels[i],11,muted,True)
        text(64,717,950,45,'YOUR PLAYTIME OVER TIME' if en else 'SEU TEMPO AO LONGO DO PERÍODO',22,bold=True)
        text(64,766,950,35,('Hours per day' if en else 'Horas por dia') if data['month'] else ('Hours per month' if en else 'Horas por mês'),17,muted)
        rect(64,820,952,280,card)
        timeline=data['timeline'];maximum=max((item['seconds'] for item in timeline),default=0)
        if maximum:
            text(90,838,890,34,('Peak: ' if en else 'Pico: ')+duration(maximum),15,muted)
            step=880/len(timeline);baseline=1038;bar_width=step*(.56 if data['month'] else .52)
            for i,item in enumerate(timeline):
                x=100+i*step+(step-bar_width)/2;height=144*item['seconds']/maximum
                if height:rect(x,baseline-height,bar_width,max(2,height),accent,3)
                else:rect(x,baseline-2,bar_width,2,border,1)
                index=item['index']
                if not data['month'] or index==1 or index%5==0 or index==len(timeline):
                    value=str(index) if data['month'] else (MESES_EN if en else MESES)[index-1][:3]
                    text(x-18,1048,bar_width+36,28,value,12,muted,align=Qt.AlignHCenter)
        else:text(96,887,888,130,'No saved sessions in this period.' if en else 'Nenhuma sessão salva neste período.',22,muted,align=Qt.AlignHCenter)
        dates=data['activity']
        def day(value):
            year,month,day=value.split('-');return f'{year}-{month}-{day}' if en else f'{day}/{month}/{year}'
        for x,title,value in [(64,'FIRST DAY' if en else 'PRIMEIRO DIA',day(dates[0]['date']) if dates else '—'),(548,'LATEST DAY' if en else 'ÚLTIMO DIA',day(dates[-1]['date']) if dates else '—')]:
            text(x,1120,460,30,title,12,muted,True);text(x,1154,460,44,value,24,bold=True)
    else:
        text(64,147,950,40,'YOUR GAMING RECAP' if en else 'SUA RETROSPECTIVA',16,muted,True)
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
