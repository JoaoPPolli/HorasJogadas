"""Atualiza e reabre o bundle real com perfil fictício, sem acessar dados pessoais."""
import argparse
import json
import os
import shutil
import signal
import subprocess
import sys
import tempfile
import time
from pathlib import Path

ROOT=Path(__file__).resolve().parent.parent
sys.path.insert(0,str(ROOT))
from app_qt import seed_demo
from horas_jogadas_qt.preview import inventory
from horas_jogadas_qt import preferences
from horas_jogadas_qt.release import VERSION


def verify(bundle,archive):
    result={'version':VERSION,'ok':False};pid=None;helper_pid=None
    with tempfile.TemporaryDirectory(prefix='horasjogadas-native-update-') as temporary:
        root=Path(temporary);target=root/"App com espaços $ '";cache=root/'cache';cache.mkdir()
        try:
            shutil.copytree(bundle,target,symlinks=True)
            package=cache/Path(archive).name;shutil.copy2(archive,package)
            profile=root/'profile';data=profile/'HorasJogadas';data.mkdir(parents=True);seed_demo(data)
            preferences.save(data,check_updates=False)
            (data/'.horasjogadas-release.json').write_text(json.dumps({'version':VERSION}),encoding='utf-8')
            before=inventory(data)
            env=dict(os.environ,APPDATA=str(profile),HORASJOGADAS_UPDATE_SELFTEST_ARCHIVE=str(package))
            # Offscreen reproduz loader, shell, troca e janela sem depender de um compositor.
            env['QT_QPA_PLATFORM']=os.environ.get('QT_QPA_PLATFORM','offscreen')
            handoff=root/'handoff.json'
            process=subprocess.run([str(target/'HorasJogadas'),'--self-test',str(handoff)],env=env,
                                   capture_output=True,timeout=180)
            if process.returncode:
                raise RuntimeError(process.stdout.decode(errors='replace')+process.stderr.decode(errors='replace'))
            evidence=json.loads(handoff.read_text(encoding='utf-8'))
            if not evidence.get('ok'):raise RuntimeError(str(evidence))
            helper_pid=evidence['helper_pid']
            ready=cache/'restart-ready.json';deadline=time.monotonic()+150
            while not ready.exists() and time.monotonic()<deadline:time.sleep(.2)
            if not ready.exists():raise RuntimeError('Nova janela não confirmou o reinício')
            opened=json.loads(ready.read_text(encoding='utf-8'));pid=opened['pid']
            if opened['version']!=VERSION:raise RuntimeError('Versão incorreta após reiniciar')
            os.kill(pid,0)
            if Path('/proc/'+str(pid)+'/exe').resolve()!=target/'HorasJogadas':
                raise RuntimeError('Executável reaberto fora da instalação atual')
            for name,digest in before.items():
                if inventory(data).get(name)!=digest:raise RuntimeError('Registro fictício alterado: '+name)
            previous=list(root.glob(target.name+'-previous-*'))
            if len(previous)!=1:raise RuntimeError('Versão anterior não foi preservada')
            deadline=time.monotonic()+5
            while time.monotonic()<deadline:
                if 'Restart confirmed' in (cache/'update.log').read_text(errors='replace'):break
                time.sleep(.1)
            else:raise RuntimeError('Auxiliar não confirmou o reinício')
            result.update(ok=True,frozen_environment=evidence['frozen_environment_detected'],
                          stage_test=True,swapped=True,reopened=True,previous_preserved=True,records_unchanged=True)
        except Exception as error:
            result['error']=str(error)
            log=cache/'update.log'
            if log.exists():result['update_log_tail']=log.read_text(errors='replace')[-8000:]
        finally:
            if helper_pid and not result['ok']:
                try:os.killpg(helper_pid,signal.SIGTERM)
                except ProcessLookupError:pass
            if pid:
                try:os.kill(pid,signal.SIGTERM)
                except ProcessLookupError:pass
    return result


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('bundle');parser.add_argument('archive');parser.add_argument('--result',required=True)
    args=parser.parse_args();result=verify(Path(args.bundle).resolve(),Path(args.archive).resolve())
    destination=Path(args.result);destination.parent.mkdir(parents=True,exist_ok=True)
    destination.write_text(json.dumps(result,indent=2),encoding='utf-8');print(json.dumps(result,indent=2))
    sys.exit(0 if result['ok'] else 1)
