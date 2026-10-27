"""Confere os fluxos reais usando títulos públicos fixos; não grava imagens."""
import json
import os
import sys
from pathlib import Path
from threading import Event
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from PySide6.QtGui import QImage
from horas_jogadas_qt.artwork_sources import search_artwork
from horas_jogadas_qt.covers import download

result = {'commit': os.environ.get('GITHUB_SHA'), 'checks': [], 'ok': True}
for kind, source, query, expected in [
    ('cover', 'Steam', 'DAVE THE DIVER', 'DAVE THE DIVER'),
    ('cover', 'GOG', 'The Witcher 3 Wild Hunt', 'The Witcher 3'),
    ('cover', 'Wikipedia', 'Hollow Knight', 'Hollow Knight'),
    ('icon', 'Steam', 'The Witcher 3 Wild Hunt', 'The Witcher 3'),
    ('icon', 'GOG', 'The Witcher 3 Wild Hunt', 'The Witcher 3'),
    ('cover', None, 'stardew valey', 'Stardew Valley'),
    ('cover', None, 'hollo knigt', 'Hollow Knight'),
]:
    entry = {'kind': kind, 'source': source or 'all', 'query': query}
    try:
        matches = search_artwork(query, source=source, kind=kind)
        entry['matches'] = [{'source': item.source, 'name': item.name, 'score': round(item.score, 3)} for item in matches[:5]]
        match = next((item for item in matches if expected.casefold() in item.name.casefold()), None)
        if match is None:
            raise ValueError('Título esperado ausente / Expected title not found')
        data = download(match, Event(), kind=kind)
        image = QImage.fromData(data)
        if image.isNull():
            raise ValueError('Imagem ilegível / Unreadable image')
        entry.update(ok=True, image_bytes=len(data), width=image.width(), height=image.height())
    except Exception as error:
        entry.update(ok=False, error=str(error)); result['ok'] = False
    result['checks'].append(entry)
Path('artwork-catalogs.json').write_text(json.dumps(result, indent=2), encoding='utf-8')
print(json.dumps(result, indent=2))
sys.exit(0 if result['ok'] else 1)
