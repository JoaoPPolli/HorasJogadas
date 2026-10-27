"""Diagnóstico dos catálogos públicos, sem consultar dados do usuário."""
import json
import os
from pathlib import Path
from urllib.request import Request, urlopen

ENDPOINTS = {
    'gog': 'https://catalog.gog.com/v1/catalog?query=witcher&limit=3&productType=in:game',
    'gog_legacy': 'https://www.gog.com/games/ajax/filtered?mediaType=game&search=witcher',
    'wikipedia': 'https://en.wikipedia.org/w/api.php?action=query&format=json&generator=search&gsrsearch=Hollow%20Knight&gsrlimit=3&prop=pageimages%7Cdescription&piprop=thumbnail%7Coriginal&pithumbsize=800',
    'steam_icon': 'https://steamcommunity.com/games/292030/?xml=1',
    'apple': 'https://itunes.apple.com/search?term=stardew+valey&entity=software&limit=3',
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
        result['sources'][name] = value
    except Exception as error:
        result['sources'][name] = {'error': str(error)}
Path('artwork-endpoints.json').write_text(json.dumps(result, indent=2), encoding='utf-8')
