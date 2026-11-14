"""Verifica PNG, consulta do jogo e extensão nativa de processos no pacote."""
import os
import sys
from threading import Event
from PySide6.QtGui import QImage
from .insights import recap,game_details,completed_recap
from .recap_image import png_bytes
from .detection import scan_processes


def run_insights_self_test(window):
    if window.mode!='review':raise RuntimeError('Isolated test profile required')
    key=window.c.repo.jogos[0].id
    data=game_details(window.c,key)
    if data['id']!=key:raise RuntimeError('Game details mismatch')
    from datetime import date
    image=QImage.fromData(png_bytes(recap(window.c,date.today().year),window.theme_name()))
    if image.isNull() or image.width()!=1080 or image.height()!=1350:raise RuntimeError('Recap PNG missing')
    individual=recap(window.c,date.today().year,game_id=key)
    if individual['game']['id']!=key or any(item['id']!=key for item in individual['top']):raise RuntimeError('Individual recap filter missing')
    image=QImage.fromData(png_bytes(individual,window.theme_name()))
    if image.isNull() or image.width()!=1080 or image.height()!=1350:raise RuntimeError('Individual recap PNG missing')
    completed=completed_recap(window.c,date.today().year)
    if completed['source']!='completed' or completed['records']!=sum(r.ano==date.today().year for r in window.c.zerados.registros):raise RuntimeError('Completion recap source mismatch')
    image=QImage.fromData(png_bytes(completed,window.theme_name()))
    if image.isNull() or image.width()!=1080 or image.height()!=1350:raise RuntimeError('Completion recap PNG missing')
    sample=scan_processes({key:dict(executable=sys.executable,mode='path')},{},Event())
    if sample is None or os.getpid() not in {pid for pid,_ in sample['found'][key]}:raise RuntimeError('Native process detection unavailable')
    if window.game_detection.timer.isActive():raise RuntimeError('Review mode started process detection')
    return dict(game_details=True,recap_png=True,individual_recap_png=True,completed_recap_png=True,native_process_scan=True)
