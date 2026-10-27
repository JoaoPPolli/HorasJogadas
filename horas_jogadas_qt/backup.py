"""Backup completo da cópia de revisão, incluindo zerados e estados abertos."""
import hashlib
import json
import os
import shutil
import tempfile
from datetime import datetime
from pathlib import Path

FILES = ('cronometros.json', 'registros.json', 'zerados.json', 'config.json', 'em_andamento.json')


def create_full(folder):
    folder = Path(folder)
    root = folder / 'full-backups'
    root.mkdir(exist_ok=True)
    stage = Path(tempfile.mkdtemp(prefix='.building-', dir=root))
    try:
        hashes = {}
        for name in FILES:
            source = folder / name
            if source.exists():
                data = source.read_bytes()
                json.loads(data)
                (stage / name).write_bytes(data)
                hashes[name] = hashlib.sha256(data).hexdigest()
        (stage / 'manifest.json').write_text(json.dumps(hashes, indent=2), encoding='utf-8')
        target = root / datetime.now().strftime('%Y%m%d-%H%M%S-%f')
        stage.rename(target)
        return target
    finally:
        if stage.exists():
            shutil.rmtree(stage)


def read_full(backup):
    backup = Path(backup)
    hashes = json.loads((backup / 'manifest.json').read_text(encoding='utf-8'))
    if not isinstance(hashes, dict) or not set(hashes).issubset(FILES):
        raise ValueError('Backup inválido.')
    result = {}
    for name, expected in hashes.items():
        path = backup / name
        if path.is_symlink():
            raise ValueError('Backup inválido.')
        data = path.read_bytes()
        if hashlib.sha256(data).hexdigest() != expected:
            raise ValueError('Backup alterado ou corrompido; restauração cancelada.')
        json.loads(data)
        result[name] = data
    return result


def restore_full(folder, backup):
    data = read_full(backup)
    # Só deve ser chamado dentro de Controller.transaction().
    for name in FILES:
        target = Path(folder) / name
        if name not in data:
            target.unlink(missing_ok=True)
        else:
            temp = target.with_suffix('.restore')
            with temp.open('wb') as f:
                f.write(data[name]); f.flush(); os.fsync(f.fileno())
            os.replace(temp, target)
