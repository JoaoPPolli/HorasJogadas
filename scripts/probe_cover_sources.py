"""Prova de acesso às APIs públicas com nomes fictícios; não usa dados de usuários."""
import json
from pathlib import Path
from urllib.request import Request,urlopen
from urllib.parse import urlencode
result={'source':'Steam public Store search','titles':[]}
for name in ['DAVE THE DIVER','The Witcher 3 Wild Hunt','Valor Mortis']:
    try:
        url='https://store.steampowered.com/api/storesearch/?'+urlencode({'term':name,'l':'english','cc':'US'})
        with urlopen(Request(url,headers={'User-Agent':'HorasJogadas/3.1.0'}),timeout=20) as response:data=json.load(response)
        matches=[{'id':item['id'],'name':item['name']} for item in data.get('items',[])[:3]]
        entry={'query':name,'matches':matches}
        if matches:
            image='https://shared.fastly.steamstatic.com/store_item_assets/steam/apps/'+str(matches[0]['id'])+'/header.jpg'
            with urlopen(image,timeout=20) as response: entry['image']={'status':response.status,'bytes':len(response.read(10*1024*1024))}
        result['titles'].append(entry)
    except Exception as error:result['titles'].append({'query':name,'error':str(error)})
folder=Path('build-diagnostics');folder.mkdir(exist_ok=True)
(folder/'cover-source.json').write_text(json.dumps(result,indent=2),encoding='utf-8')
print(json.dumps(result,indent=2))
