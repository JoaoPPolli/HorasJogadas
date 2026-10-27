"""Diagnóstico dos catálogos públicos, sem consultar dados do usuário."""
import json
import os
from pathlib import Path
from urllib.request import Request, urlopen

ENDPOINTS = {
    'gog': 'https://catalog.gog.com/v1/catalog?query=witcher&limit=3&productType=in:game',
    'gog_icon': 'https://api.gog.com/products/1207664643',
    'wikipedia': 'https://en.wikipedia.org/w/api.php?action=query&format=json&generator=search&gsrsearch=Hollow%20Knight&gsrlimit=3&prop=pageimages%7Cdescription&piprop=thumbnail%7Coriginal&pithumbsize=800&pilicense=any',
    'steam_icon': 'https://steamcommunity.com/ogg/292030/?xml=1',
    'wiki_fuzzy': 'https://en.wikipedia.org/w/api.php?action=query&format=json&generator=search&gsrsearch=stardew~%20valey~&gsrlimit=6&prop=pageimages%7Cdescription&piprop=thumbnail&pithumbsize=800&pilicense=any',
}
result = {'commit': os.environ.get('GITHUB_SHA'), 'sources': {}}
for name, url in ENDPOINTS.items():
    try:
        with urlopen(Request(url, headers={'User-Agent': 'HorasJogadas/3.2 (https://github.com/JoaoPPolli/HorasJogadas)'}), timeout=20) as response:
            raw = response.read(200000)
        try:
            value = json.loads(raw)
        except ValueError:
            value = raw.decode('utf-8', errors='replace')[:12000]
        if name == 'gog': value = [{k: p.get(k) for k in ('id', 'title', 'coverHorizontal', 'logo', 'storeLink')} for p in value.get('products', [])[:4]]
        if name == 'gog_icon': value = {k: value.get(k) for k in ('id', 'title', 'images', 'links')}
        result['sources'][name] = value
    except Exception as error:
        result['sources'][name] = {'error': str(error)}
Path('artwork-endpoints.json').write_text(json.dumps(result, indent=2), encoding='utf-8')
