"""Testes do runner com preservação do status de saída e diagnóstico sem segredos."""
import json
import subprocess
import sys
from pathlib import Path

root=Path(__file__).resolve().parent.parent
suite=sys.argv[1]
platform='windows' if sys.platform=='win32' else 'linux'
log=root/'build'/('tests-'+suite+'-'+platform+'.log'); log.parent.mkdir(exist_ok=True)
with log.open('w',encoding='utf-8') as output:
    result=subprocess.run([sys.executable,'-m','unittest','discover','-s',suite,'-t','.'],cwd=root,stdout=output,stderr=subprocess.STDOUT)
text=log.read_text(encoding='utf-8',errors='replace')
print(text[-18000:])
folder=root/'build-diagnostics'; folder.mkdir(exist_ok=True)
(folder/('tests-'+suite+'-'+platform+'.json')).write_text(json.dumps({'ok':result.returncode==0,
    'exit_code':result.returncode,'log_tail':text[-14000:] if result.returncode else text[-500:]},indent=2),encoding='utf-8')
sys.exit(result.returncode)
