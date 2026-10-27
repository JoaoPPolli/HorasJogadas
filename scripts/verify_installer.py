"""Instala, abre o autoteste e desinstala em um perfil fictício do runner Windows."""
import hashlib
import json
import os
import subprocess
import sys
import tempfile
from pathlib import Path

root=Path(__file__).resolve().parent.parent
package=root/'build'/'installer-check'
result={'ok':False,'run_url':os.environ.get('RUN_URL','')}
try:
    installer=package/'HorasJogadas-Windows-Setup.exe'
    sums=(package/'SHA256SUMS.txt').read_text(encoding='utf-8')
    expected=next(line.split()[0] for line in sums.splitlines() if line.endswith(installer.name))
    if hashlib.sha256(installer.read_bytes()).hexdigest()!=expected:
        raise RuntimeError('Checksum do instalador não confere')
    with tempfile.TemporaryDirectory(prefix='horasjogadas-installer-check-') as temporary:
        folder=Path(temporary); install=folder/'program'; profile=folder/'profile'
        data=profile/'HorasJogadas'; data.mkdir(parents=True)
        # Representa dados preexistentes. O autoteste do binário usa outra pasta temporária.
        originals={'cronometros.json':b'[{"keep":"library"}]','registros.json':b'[{"keep":"sessions"}]','zerados.json':b'[{"keep":"completed"}]'}
        for name,content in originals.items(): (data/name).write_bytes(content)
        env=dict(os.environ,APPDATA=str(profile))
        subprocess.run([str(installer),'/VERYSILENT','/SUPPRESSMSGBOXES','/NORESTART','/SP-','/DIR='+str(install)],check=True,env=env,timeout=180)
        executable=install/'HorasJogadas.exe'
        if not executable.is_file(): raise RuntimeError('Instalador não criou o executável')
        evidence=folder/'self-test.json'
        subprocess.run([str(executable),'--self-test',str(evidence)],check=True,env=env,timeout=180)
        bundle=json.loads(evidence.read_text(encoding='utf-8'))
        if not bundle.get('ok'): raise RuntimeError(str(bundle))
        subprocess.run([str(install/'unins000.exe'),'/VERYSILENT','/SUPPRESSMSGBOXES','/NORESTART'],check=True,env=env,timeout=180)
        if any((data/name).read_bytes()!=content for name,content in originals.items()):
            raise RuntimeError('Os dados preexistentes foram alterados')
        result.update(ok=True,checksum=True,installed=True,bundle=bundle,uninstalled=True,existing_data_unchanged=True)
except Exception as error:
    result['error']=str(error)
Path('installer-verification.json').write_text(json.dumps(result,indent=2),encoding='utf-8')
print(json.dumps(result,indent=2))
sys.exit(0 if result['ok'] else 1)
