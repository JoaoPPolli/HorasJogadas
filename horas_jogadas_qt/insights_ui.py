"""Página do jogo e prévia de retrospectiva com exportação local em PNG."""
from datetime import date,datetime
from pathlib import Path
from PySide6.QtCore import Qt
from PySide6.QtGui import QPixmap
from PySide6.QtWidgets import QDialog,QVBoxLayout,QHBoxLayout,QLabel,QComboBox,QFileDialog,QMessageBox,QScrollArea,QWidget,QFrame
from horas_jogadas import i18n
from horas_jogadas.i18n import t_status
from horas_jogadas.utils import formatar_duracao,formatar_hhmmss
from horas_jogadas.zerados import MESES,MESES_EN,duracao_texto
from .widgets import label,button,row,metric,table
from .insights import game_details,recap,available_years,recap_filename
from .recap_image import render,save_png
from .texts import tr


def show_recap(window,game_id=None):
    game=window.c.repo.jogo_por_id(game_id) if game_id is not None else None
    if game_id is not None and game is None:
        window.notify(tr('game_missing'));return
    title=tr('recap_individual') if game else tr('recap_title')
    d=QDialog(window);d.setObjectName('recapDialog');d.setProperty('gameId',game_id or '');d.setWindowTitle(title+(' · '+game.nome if game else ''));d.resize(600,810);box=QVBoxLayout(d);box.setContentsMargins(22,20,22,20);box.setSpacing(12)
    box.addWidget(label(game.nome if game else title,'gameName',True));box.addWidget(label(tr('recap_individual_intro') if game else tr('recap_intro'),'muted',True))
    year=QComboBox();year.setObjectName('recapYear')
    for value in available_years(window.c,game_id):year.addItem(str(value),value)
    year.setCurrentIndex(max(0,year.findData(date.today().year)))
    month=QComboBox();month.setObjectName('recapMonth');month.addItem(tr('recap_year'),0)
    for i,name in enumerate(MESES_EN if i18n.idioma_atual()=='en' else MESES,1):month.addItem(name,i)
    box.addWidget(row(year,month))
    preview=QLabel();preview.setObjectName('recapPreview');preview.setAlignment(Qt.AlignCenter)
    scroll=QScrollArea();scroll.setWidgetResizable(True);scroll.setFrameShape(QFrame.NoFrame);scroll.setWidget(preview);box.addWidget(scroll,1)
    def update():
        data=recap(window.c,year.currentData(),month.currentData(),game_id);preview.setPixmap(QPixmap.fromImage(render(data,window.theme_name(),i18n.idioma_atual())).scaled(480,600,Qt.KeepAspectRatio,Qt.SmoothTransformation))
    year.currentIndexChanged.connect(update);month.currentIndexChanged.connect(update);update()
    def export():
        data=recap(window.c,year.currentData(),month.currentData(),game_id)
        path,_=QFileDialog.getSaveFileName(d,tr('recap_export'),recap_filename(data),'PNG (*.png)')
        if path:
            if not path.lower().endswith('.png'):path+='.png'
            try:save_png(path,data,window.theme_name(),i18n.idioma_atual());window.notify(tr('recap_exported'))
            except OSError as error:QMessageBox.warning(d,tr('error'),str(error))
    export_button=button(tr('recap_export'),export,'primary');export_button.setObjectName('recapExport')
    box.addWidget(row(button(tr('close'),d.reject),None,export_button));d.exec()


def build_game(window):
    key=window.selected_game
    scroll=QScrollArea();scroll.setWidgetResizable(True);host=QWidget();box=QVBoxLayout(host);box.setContentsMargins(0,0,12,0);box.setSpacing(18)
    box.addWidget(row(button('‹ '+tr('library'),lambda:window.navigate('library')),None))
    if key not in window.c.timers:
        box.addWidget(label(tr('game_missing'),'muted',True));scroll.setWidget(host);return scroll
    data=game_details(window.c,key)
    from .window import GameCard
    from .covers import CoverStore
    from . import preferences
    window.covers_enabled=bool(preferences.read(window.c.folder).get('covers_enabled',False));window.icons_enabled=bool(preferences.read(window.c.folder).get('icons_enabled',True))
    window.cover_store=CoverStore(window.c.folder);window.icon_store=CoverStore(window.c.folder,'icon')
    card=GameCard(window,key,detail=True);window.detail_card=card;box.addWidget(card)
    box.addWidget(row(metric(tr('game_saved'),formatar_duracao(data['saved_seconds'])),metric(tr('sessions'),str(data['session_count'])),metric(tr('average'),formatar_duracao(data['average_seconds']))))
    def date_text(value):return datetime.fromisoformat(value).strftime('%Y-%m-%d %H:%M' if i18n.idioma_atual()=='en' else '%d/%m/%Y %H:%M') if value else '—'
    dates=QFrame();dates.setObjectName('card');dates_box=QVBoxLayout(dates);dates_box.addWidget(label(tr('game_first')+': '+date_text(data['first']),'muted'));dates_box.addWidget(label(tr('game_last')+': '+date_text(data['last']),'muted'));box.addWidget(dates)
    from .detection_ui import configure
    from .detection import profiles
    profile=profiles(window.c.folder).get(key,{})
    state='detect_unconfigured' if not profile.get('executable') else 'detect_link_on' if profile.get('enabled') and preferences.read(window.c.folder).get('detection_enabled',False) else 'detect_link_off'
    box.addWidget(label(tr(state),'muted'))
    recap_button=button(tr('recap_individual'),lambda:show_recap(window,key));recap_button.setObjectName('gameRecap')
    box.addWidget(row(button(tr('detect_configure'),lambda:configure(window,key)),recap_button,None))
    box.addWidget(label(tr('completed'),'gameName'))
    records={r.id:r for r in window.c.zerados.registros}
    for record in data['completions']:
        panel=QFrame();panel.setObjectName('card');layout=QVBoxLayout(panel);layout.setContentsMargins(20,16,20,16)
        layout.addWidget(label(record['name'],'gameName'));layout.addWidget(label(f"{record['month']:02d}/{record['year']} · "+tr('duration_col')+': '+(duracao_texto(record['seconds']) or '—'),'muted'))
        layout.addWidget(label(tr('dlc') if record['dlc'] else tr('experience') if record['type']=='experiencia' else tr('completion'),'muted'))
        if record['platinum_seconds'] is not None:layout.addWidget(label(tr('platinum')+': '+duracao_texto(record['platinum_seconds'])+(' · '+tr('platinum_done') if record['platinum_completed'] else ''),'muted'))
        if record['notes']:layout.addWidget(label(record['notes'],'muted',True))
        layout.addWidget(button(tr('edit'),lambda checked=False,r=records[record['id']]:window.edit_completion(r)));box.addWidget(panel)
    if not data['completions']:box.addWidget(label(tr('game_no_completions'),'muted',True))
    box.addWidget(label(tr('game_recent_sessions'),'gameName'))
    grid=table([tr('duration_col'),tr('end')]);sessions=[s for s in reversed(window.c.repo.sessoes) if s.jogo_id==key][:100]
    window.fill_table(grid,[(s.tempo,s.data) for s in sessions]);grid.setMinimumHeight(220)
    def edit(index):
        if 0<=index.row()<len(sessions):window.edit_session(sessions[index.row()])
    grid.doubleClicked.connect(edit);box.addWidget(grid)
    if data['session_count']>100:box.addWidget(label(tr('game_last_100'),'muted',True))
    box.addStretch();scroll.setWidget(host);return scroll
