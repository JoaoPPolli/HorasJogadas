"""Confere o site e os links públicos depois do deploy, sem baixar pacotes inteiros."""
import hashlib
import json
import os
import re
import sys
from urllib.request import Request, urlopen
from pathlib import Path

site=os.environ['SITE_URL']
release='https://github.com/JoaoPPolli/HorasJogadas/releases/latest/download/'
result={'ok':False,'site_url':site,'run_url':os.environ.get('RUN_URL','')}
try:
    with urlopen(site,timeout=60) as response:
        html=response.read().decode('utf-8')
        if response.status!=200 or '<h1>' not in html or '__RELEASE__' in html:
            raise RuntimeError('A página publicada não contém o site esperado')
        result['site_http']=response.status
    from urllib.parse import urljoin
    history_url=urljoin(site,'changelog/')
    with urlopen(history_url,timeout=60) as response:
        history=response.read().decode('utf-8')
        expected=re.findall(r'^## (\d+\.\d+\.\d+)',(Path(__file__).resolve().parent.parent/'CHANGELOG.md').read_text(encoding='utf-8'),re.M)
        actual=re.findall(r'data-version="([^"]+)"',history)
        if response.status!=200 or actual!=expected or '__CHANGELOG_' in history:
            raise RuntimeError('O changelog público não contém todas as versões esperadas')
        result['changelog']={'url':history_url,'http':response.status,'versions':actual}
    with urlopen(release+'SHA256SUMS.txt',timeout=60) as response:
        hashes=response.read().decode('utf-8')
    result['assets']={}
    for name in ['HorasJogadas-Windows-Setup.exe','HorasJogadas-Windows-Portable.zip','HorasJogadas-Linux-x86_64.tar.gz']:
        match=re.search(r'^([a-f0-9]{64})\s+'+re.escape(name)+r'$',hashes,re.M)
        if not match or release+name not in html:
            raise RuntimeError('Link ou checksum ausente: '+name)
        with urlopen(Request(release+name,method='HEAD'),timeout=60) as response:
            if response.status!=200: raise RuntimeError('Download indisponível: '+name)
            result['assets'][name]={'http':response.status,'sha256':match.group(1)}
    result['ok']=True
except Exception as error:
    result['error']=str(error)
Path('site-verification.json').write_text(json.dumps(result,indent=2),encoding='utf-8')
print(json.dumps(result,indent=2))
sys.exit(0 if result['ok'] else 1)
