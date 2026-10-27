"""Backup completo dos registros, preferências Qt e capas locais referenciadas."""
import hashlib
import json
import os
import re
import shutil
import tempfile
from datetime import datetime
from pathlib import Path

FILES=('cronometros.json','registros.json','zerados.json','config.json','em_andamento.json')
EXTRAS=('.qt-preferences.json','covers/index.json')
IMAGE=re.compile(r'covers/[a-f0-9]{64}\.jpg')


def safe_path(root,path):
    root=Path(root).absolute();path=Path(path).absolute()
    if root.is_symlink() or not path.is_relative_to(root):return False
    while path!=root:
        if path.is_symlink():return False
        path=path.parent
    return True


def allowed(name):return name in FILES+EXTRAS or bool(IMAGE.fullmatch(name))


def create_full(folder):
    folder=Path(folder);root=folder/'full-backups';root.mkdir(exist_ok=True)
    stage=Path(tempfile.mkdtemp(prefix='.building-',dir=root))
    try:
        names=list(FILES+EXTRAS)
        index=folder/'covers'/'index.json'
        if index.exists():
            entries=json.loads(index.read_text(encoding='utf-8'))
            if not isinstance(entries,dict):raise ValueError('Índice de capas inválido')
            for entry in entries.values():
                name='covers/'+str(entry.get('file','')) if isinstance(entry,dict) else ''
                if IMAGE.fullmatch(name):names.append(name)
        hashes={}
        for name in dict.fromkeys(names):
            source=folder/name
            if not source.exists():continue
            if not safe_path(folder,source):
                raise ValueError('Links não são aceitos no backup')
            data=source.read_bytes();digest=hashlib.sha256(data).hexdigest()
            if name.endswith('.json'):json.loads(data)
            elif Path(name).stem!=digest:raise ValueError('Capa corrompida; importe-a novamente')
            target=stage/name;target.parent.mkdir(parents=True,exist_ok=True);target.write_bytes(data);hashes[name]=digest
        (stage/'manifest.json').write_text(json.dumps(hashes,indent=2),encoding='utf-8')
        target=root/datetime.now().strftime('%Y%m%d-%H%M%S-%f');stage.rename(target);return target
    finally:
        if stage.exists():shutil.rmtree(stage)


def read_full(backup):
    backup=Path(backup)
    hashes=json.loads((backup/'manifest.json').read_text(encoding='utf-8'))
    if not isinstance(hashes,dict) or not all(isinstance(n,str) and allowed(n) for n in hashes):raise ValueError('Backup inválido.')
    result={}
    for name,expected in hashes.items():
        path=backup/name
        if not safe_path(backup,path):raise ValueError('Backup inválido.')
        data=path.read_bytes();digest=hashlib.sha256(data).hexdigest()
        if digest!=expected or IMAGE.fullmatch(name) and Path(name).stem!=digest:
            raise ValueError('Backup alterado ou corrompido; restauração cancelada.')
        if name.endswith('.json'):json.loads(data)
        result[name]=data
    return result


def restore_full(folder,backup):
    data=read_full(backup)
    # Chamado dentro de Controller.transaction(). Imagens são imutáveis por SHA-256.
    for name in set(FILES)|set(data):
        target=Path(folder)/name
        if name not in data:target.unlink(missing_ok=True)
        else:
            if target.parent.is_symlink() or target.is_symlink():raise ValueError('Destino de restauração inválido')
            target.parent.mkdir(parents=True,exist_ok=True)
            temp=target.with_name(target.name+'.restore')
            with temp.open('wb') as output:output.write(data[name]);output.flush();os.fsync(output.fileno())
            os.replace(temp,target)
