"""Prova do fluxo real Steam com dados fictícios; não consulta a biblioteca do usuário."""
import json
import sys
from pathlib import Path
from threading import Event
sys.path.insert(0,str(Path(__file__).resolve().parent.parent))
from horas_jogadas_qt.covers import search,download
result={'source':'Steam public Store search + appdetails','titles':[]}
for name in ['DAVE THE DIVER','The Witcher 3 Wild Hunt','Valor Mortis']:
    entry={'query':name}
    try:
        matches=search(name)
        entry['matches']=[{'id':item.app_id,'name':item.name,'score':item.score} for item in matches[:3]]
        if matches:
            image=download(matches[0],Event())
            entry['image']={'normalized_jpeg_bytes':len(image),'ok':image.startswith(b'\xff\xd8')}
    except Exception as error:entry['error']=str(error)
    result['titles'].append(entry)
folder=Path('build-diagnostics');folder.mkdir(exist_ok=True)
(folder/'cover-source.json').write_text(json.dumps(result,indent=2),encoding='utf-8')
print(json.dumps(result,indent=2))
