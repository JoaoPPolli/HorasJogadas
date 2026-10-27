"""Recupera a base movida pelo atualizador Linux 3.0.1 se app e dados coincidiam."""
import hashlib
import json
import os
import re
import shutil
import tempfile
import time
from pathlib import Path
from horas_jogadas.instancia import TravaInstancia
from horas_jogadas.storage import escrever_json_atomico
from .preview import inventory

BUNDLE={'HorasJogadas','_internal','THIRD-PARTY','LEIA-ME.txt','package.json'}
JOURNAL='.qt-linux-recovery.json'
CORE={'cronometros.json','registros.json','zerados.json'}


def recover_moved_data(folder):
    """Só recupera uma pasta vazia, ou retoma uma recuperação interrompida.

    Exige nome de pasta criado pelo helper antigo, marcadores 3.0.1 e bloqueio
    exclusivo da origem. A origem permanece intacta; o diário torna cópias parciais
    retomáveis antes de o controlador carregar qualquer registro.
    """
    folder=Path(folder).resolve();journal=folder/JOURNAL
    if not journal.exists() and any((folder/name).exists() for name in CORE):return False
    def valid(source,check_time=True):
        if not source.is_dir() or source.is_symlink():return False
        if source.parent!=folder.parent or not re.fullmatch(re.escape(folder.name)+r'-previous-\d+',source.name):return False
        if check_time and not 0<=time.time()-int(source.name.rsplit('-',1)[1])<900:return False
        try:
            return (json.loads((source/'package.json').read_text(encoding='utf-8')).get('version')=='3.0.1'
                and json.loads((source/'.horasjogadas-release.json').read_text(encoding='utf-8')).get('version')=='3.0.1'
                and any((source/name).is_file() for name in CORE))
        except (ValueError,OSError):return False
    if journal.exists():
        source=Path(json.loads(journal.read_text(encoding='utf-8'))['source']).resolve()
        if not valid(source,False):raise ValueError('Recuperação Linux inválida; arquivos preservados')
    else:
        candidates=[path for path in folder.parent.glob(folder.name+'-previous-*') if valid(path)]
        if not candidates:return False
        source=max(candidates,key=lambda path:int(path.name.rsplit('-',1)[1]))
    lock=TravaInstancia(str(source))
    if not lock.adquirir() or not lock.ativa:raise OSError('Feche a versão anterior antes de recuperar os registros')
    stage=None
    try:
        before={name:digest for name,digest in inventory(source).items() if Path(name).parts[0] not in BUNDLE and name!=JOURNAL}
        stage=Path(tempfile.mkdtemp(prefix='.horasjogadas-recovery-',dir=folder.parent))
        for name in before:
            target=stage/name;target.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(source/name,target)
        if inventory(stage)!=before:raise OSError('Falha ao conferir os registros recuperados')
        escrever_json_atomico(str(journal),{'source':str(source)},backup=False)
        for name in before:
            target=folder/name;target.parent.mkdir(parents=True,exist_ok=True)
            temporary=target.with_name(target.name+'.recovering')
            with temporary.open('wb') as output:
                output.write((stage/name).read_bytes());output.flush();os.fsync(output.fileno())
            os.replace(temporary,target)
        if any(hashlib.sha256((folder/name).read_bytes()).hexdigest()!=digest for name,digest in before.items()):
            raise OSError('Falha na recuperação; o processo será retomado ao abrir novamente')
        journal.unlink();return True
    finally:
        lock.liberar()
        if stage:shutil.rmtree(stage)
