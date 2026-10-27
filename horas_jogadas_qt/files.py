"""Escrita de exportações sem substituir um arquivo por conteúdo parcial."""
import os
import tempfile
from pathlib import Path


def write_text_atomic(path, text):
    target = Path(path)
    fd, temporary = tempfile.mkstemp(dir=target.parent, prefix='.'+target.name+'-', suffix='.tmp')
    try:
        with os.fdopen(fd, 'w', encoding='utf-8', newline='') as stream:
            stream.write(text)
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(temporary, target)
    finally:
        Path(temporary).unlink(missing_ok=True)
