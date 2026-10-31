"""Preparação dos dados oficiais: trava é obtida pelo lançador antes desta etapa."""
import hashlib
import json
import os
import shutil
import tempfile
from datetime import datetime
from pathlib import Path
from .preview import inventory

VERSION = '3.4.0'
RELEASE_URL = 'https://github.com/JoaoPPolli/HorasJogadas/releases/latest'
SITE_URL = 'https://joaoppolli.github.io/HorasJogadas/'
MARKER = '.horasjogadas-release.json'


def prepare_official_data(folder, version=VERSION):
    """Preserva todos os arquivos antes de qualquer migração de leitura do domínio.

    Não importa nem mescla a cópia de revisão. O diretório e o formato dos dados
    oficiais continuam os mesmos da edição Tkinter. Requer app.lock exclusivo.
    """
    folder = Path(folder).resolve()
    folder.mkdir(parents=True, exist_ok=True)
    marker = folder / MARKER
    if marker.exists():
        previous = json.loads(marker.read_text(encoding='utf-8'))
        if previous.get('version') == version:
            return None
    before = inventory(folder)
    before.pop(MARKER, None)
    backup = None
    if before:
        root = folder.parent / (folder.name + '-Backups-de-Versao')
        root.mkdir(exist_ok=True)
        stage = Path(tempfile.mkdtemp(prefix='.preparando-', dir=root))
        try:
            payload=stage/'data'; payload.mkdir()
            for relative in before:
                source, target = folder / relative, payload / relative
                target.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(source, target)
            after = inventory(folder); after.pop(MARKER, None)
            if before != after or before != inventory(payload):
                raise OSError('Os dados mudaram durante o backup. Feche o app antigo e tente novamente.')
            (stage/'manifest.json').write_text(json.dumps(before,indent=2),encoding='utf-8')
            backup = root / (version + '-' + datetime.now().strftime('%Y%m%d-%H%M%S-%f'))
            stage.rename(backup)
        finally:
            if stage.exists(): shutil.rmtree(stage)
    metadata = {'version':version, 'backup':str(backup) if backup else None,
                'created_at':datetime.now().isoformat(timespec='seconds')}
    fd, temporary = tempfile.mkstemp(prefix='.release-', suffix='.tmp', dir=folder)
    try:
        with os.fdopen(fd,'w',encoding='utf-8') as stream:
            json.dump(metadata,stream,indent=2)
            stream.flush(); os.fsync(stream.fileno())
        os.replace(temporary,marker)
    finally:
        Path(temporary).unlink(missing_ok=True)
    return backup
