"""Snapshots de revisão: nenhuma escrita é feita na pasta de dados original."""
import hashlib
import json
import os
import shutil
import tempfile
from pathlib import Path

MARKER = '.horasjogadas-preview.json'
IGNORED = {'app.lock', 'mostrar.sinal', 'app.log'}


def inventory(root):
    root = Path(root)
    result = {}
    if not root.exists():
        return result
    if root.is_symlink():
        raise ValueError('A pasta de origem não pode ser um link.')
    for folder, dirs, files in os.walk(root, followlinks=False):
        for name in dirs + files:
            if (Path(folder) / name).is_symlink():
                raise ValueError('Links não são aceitos na cópia de revisão.')
        for name in files:
            path = Path(folder) / name
            if name in IGNORED or name.startswith('app.log.'):
                continue
            result[str(path.relative_to(root))] = hashlib.sha256(path.read_bytes()).hexdigest()
    return result


def prepare_preview(source, destination):
    source, destination = Path(source).resolve(), Path(destination).resolve()
    if source == destination or source in destination.parents or destination in source.parents:
        raise ValueError('A revisão deve ficar em uma pasta separada dos dados originais.')
    marker = destination / MARKER
    if destination.exists():
        if not marker.is_file():
            raise ValueError('A pasta de destino já existe e não é uma revisão reconhecida.')
        metadata = json.loads(marker.read_text(encoding='utf-8'))
        if metadata.get('source') != str(source) or metadata.get('mode') != 'review-copy':
            raise ValueError('Esta revisão pertence a outra origem; escolha uma pasta nova.')
        return destination
    destination.parent.mkdir(parents=True, exist_ok=True)
    staging = Path(tempfile.mkdtemp(prefix='horasjogadas-copy-', dir=destination.parent))
    try:
        before = inventory(source)
        for relative in before:
            src, target = source / relative, staging / relative
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(src, target)
        if before != inventory(source) or before != inventory(staging):
            raise OSError('Os dados mudaram durante a cópia. Feche o aplicativo atual e tente novamente.')
        (staging / MARKER).write_text(json.dumps({'source': str(source), 'sha256': before,
                                                'mode': 'review-copy'}, indent=2), encoding='utf-8')
        # Nunca substitui um destino existente, mesmo se outra instância o criou.
        if destination.exists():
            raise FileExistsError(str(destination))
        staging.rename(destination)
        return destination
    finally:
        if staging.exists():
            shutil.rmtree(staging)
