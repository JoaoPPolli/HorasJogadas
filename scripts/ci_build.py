"""Executa o build com diagnóstico limitado; nunca imprime ambiente ou credenciais."""
import json
import os
import subprocess
import sys
import traceback
from pathlib import Path

root=Path(__file__).resolve().parent.parent
platform='windows' if sys.platform=='win32' else 'linux'
log=root/'build'/('ci-'+platform+'.log'); log.parent.mkdir(exist_ok=True)
status={'platform':platform,'ok':False}
try:
    with log.open('w',encoding='utf-8') as output:
        result=subprocess.run([sys.executable,str(root/'scripts'/'build_release.py')],cwd=root,
                              stdout=output,stderr=subprocess.STDOUT)
    status['ok']=result.returncode==0
    status['exit_code']=result.returncode
    if not status['ok']: status['log_tail']=log.read_text(encoding='utf-8',errors='replace')[-14000:]
except Exception as error:
    status['error']=str(error)
diagnostics=root/'build-diagnostics'; diagnostics.mkdir(exist_ok=True)
(diagnostics/(platform+'.json')).write_text(json.dumps(status,indent=2),encoding='utf-8')
print(json.dumps(status,indent=2))
sys.exit(0 if status['ok'] else 1)
