"""Preferências visuais independentes dos registros do domínio."""
import json
from pathlib import Path
from horas_jogadas.storage import escrever_json_atomico


def read(folder):
    try:
        value=json.loads((Path(folder)/'.qt-preferences.json').read_text(encoding='utf-8'))
        return value if isinstance(value,dict) else {}
    except (ValueError,OSError):
        return {}


def save(folder,**changes):
    value=read(folder); value.update(changes)
    escrever_json_atomico(str(Path(folder)/'.qt-preferences.json'),value)
