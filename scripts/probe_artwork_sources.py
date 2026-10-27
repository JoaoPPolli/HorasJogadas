"""Confere os fluxos reais usando títulos públicos fixos; não grava imagens."""
import json
import os
import sys
from pathlib import Path
from threading import Event
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from PySide6.QtGui import QImage
from horas_jogadas_qt.artwork_sources import search_artwork
from horas_jogadas_qt.covers import download,similarity

result = {'commit': os.environ.get('GITHUB_SHA'), 'checks': [], 'ok': True}
for kind, source, query, expected in [
    ('cover', 'Steam', 'DAVE THE DIVER', 'DAVE THE DIVER'),
    ('cover', 'GOG', 'The Witcher 3 Wild Hunt', 'The Witcher 3 Wild Hunt'),
    ('cover', 'Wikipedia', 'Hollow Knight', 'Hollow Knight'),
    ('icon', 'Steam', 'The Witcher 3 Wild Hunt', 'The Witcher 3 Wild Hunt'),
    ('icon', 'GOG', 'The Witcher 3 Wild Hunt', 'The Witcher 3 Wild Hunt'),
    ('cover', None, 'stardew valey', 'Stardew Valley'),
    ('cover', None, 'hollo knigt', 'Hollow Knight'),
]:
    entry = {'kind': kind, 'source': source or 'all', 'query': query}
    try:
        matches = search_artwork(query, source=source, kind=kind)
        entry['matches'] = [{'source': item.source, 'name': item.name, 'score': round(item.score, 3)} for item in matches[:5]]
        match = next((item for item in matches if similarity(expected,item.name)>=.93), None)
        if match is None:
            raise ValueError('Título esperado ausente / Expected title not found')
        data = download(match, Event(), kind=kind)
        image = QImage.fromData(data)
        if image.isNull():
            raise ValueError('Imagem ilegível / Unreadable image')
        entry.update(ok=True, image_bytes=len(data), width=image.width(), height=image.height())
    except Exception as error:
        entry.update(ok=False, error=str(error)); result['ok'] = False
        if source=='Steam' and kind=='icon':
            import re
            from horas_jogadas_qt.artwork_sources import _read
            from horas_jogadas_qt.network import urlopen
            raw=_read('https://steamcommunity.com/app/292030/',urlopen).decode('utf-8',errors='replace')
            entry['diagnostic_tags']=re.findall(r'<[^>]*(?:292030|apphub_AppIcon)[^>]*>',raw)[:25]
            from urllib.parse import urlencode
            endpoints={
                'community':'https://api.steampowered.com/ICommunityService/GetApps/v1/?'+urlencode({'input_json':json.dumps({'appids':[292030]})}),
                'store_browse':'https://api.steampowered.com/IStoreBrowseService/GetItems/v1/?'+urlencode({'input_json':json.dumps({'ids':[{'appid':292030}],'context':{'language':'english','country_code':'US'},'data_request':{'include_assets':True}})}),
                'community_ajax':'https://steamcommunity.com/actions/ajaxgetappdetails/?appids=292030',
            }
            entry['diagnostic_api']={}
            for label,endpoint in endpoints.items():
                try:entry['diagnostic_api'][label]=json.loads(_read(endpoint,urlopen))
                except Exception as exc:entry['diagnostic_api'][label]={'error':str(exc)}
    result['checks'].append(entry)
Path('artwork-catalogs.json').write_text(json.dumps(result, indent=2), encoding='utf-8')
print(json.dumps(result, indent=2))
sys.exit(0 if result['ok'] else 1)
