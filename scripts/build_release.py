"""Build nativo Windows/Linux, autoteste do executável e pacote sem dependência de Python."""
import argparse
import hashlib
import importlib.metadata
import json
import os
import shutil
import subprocess
import sys
import tarfile
from pathlib import Path
from zipfile import ZipFile, ZIP_DEFLATED

ROOT=Path(__file__).resolve().parent.parent
sys.path.insert(0,str(ROOT))
from horas_jogadas_qt.release import VERSION


def run(command,**kwargs):
    print('+', ' '.join(str(item) for item in command),flush=True)
    subprocess.run([str(item) for item in command],check=True,**kwargs)


def build():
    import PySide6
    from PySide6.QtCore import QLibraryInfo
    work=ROOT/'build'/'qt-release'
    output=ROOT/'dist'
    bundle=output/'HorasJogadas'
    if work.exists(): shutil.rmtree(work)
    if bundle.exists(): shutil.rmtree(bundle)
    work.mkdir(parents=True)
    command=[sys.executable,'-m','PyInstaller','--noconfirm','--clean','--onedir','--windowed',
        '--noupx','--name','HorasJogadas','--distpath',output,'--workpath',work/'work',
        '--specpath',work,'--paths',ROOT,'--collect-submodules','horas_jogadas_qt',
        '--collect-data','horas_jogadas_qt','--hidden-import','PySide6.QtSvg',
        '--add-data',str(ROOT/'icon.ico')+os.pathsep+'.']
    if sys.platform=='win32': command+=['--icon',ROOT/'icon.ico']
    translations=Path(QLibraryInfo.path(QLibraryInfo.TranslationsPath))
    relative=translations.relative_to(Path(PySide6.__file__).resolve().parent)
    qm=translations/'qtbase_pt_BR.qm'
    if not qm.exists(): raise RuntimeError('Catálogo de tradução Qt ausente')
    command+=['--add-data',str(qm)+os.pathsep+str(Path('PySide6')/relative),ROOT/'app_qt.py']
    run(command,cwd=ROOT)
    executable=bundle/('HorasJogadas.exe' if sys.platform=='win32' else 'HorasJogadas')
    if not executable.exists(): raise RuntimeError('Executável ausente')
    results=work/'self-test.json'
    # No Linux, o runner chama este script dentro de xvfb-run.
    run([executable,'--self-test',results],cwd=bundle,timeout=180)
    evidence=json.loads(results.read_text(encoding='utf-8'))
    if not evidence.get('ok'): raise RuntimeError(str(evidence))
    shutil.copy2(ROOT/'packaging'/'LEIA-ME.txt',bundle/'LEIA-ME.txt')
    licenses=bundle/'THIRD-PARTY'; licenses.mkdir(exist_ok=True)
    shutil.copy2(ROOT/'packaging'/'THIRD-PARTY.txt',licenses/'NOTICES.txt')
    # Textos integrais dos componentes são copiados de fontes oficiais pelo workflow.
    legal=ROOT/'build'/'legal'
    if legal.exists():
        shutil.copytree(legal,licenses,dirs_exist_ok=True)
    for path in bundle.rglob('*'):
        if path.name in {'.git','cronometros.json','registros.json','zerados.json','config.json','app.lock','app.log'}:
            raise RuntimeError('Arquivo pessoal ou de desenvolvimento no pacote: '+str(path))
    release=ROOT/'release'; release.mkdir(exist_ok=True)
    if sys.platform=='win32':
        archive=release/'HorasJogadas-Windows-Portable.zip'
        with ZipFile(archive,'w',ZIP_DEFLATED,compresslevel=9) as z:
            for path in sorted(bundle.rglob('*')):
                if path.is_file(): z.write(path,Path('HorasJogadas')/path.relative_to(bundle))
    else:
        archive=release/'HorasJogadas-Linux-x86_64.tar.gz'
        with tarfile.open(archive,'w:gz') as tar:
            tar.add(bundle,arcname='HorasJogadas')
    shutil.copy2(results,release/('self-test-windows.json' if sys.platform=='win32' else 'self-test-linux.json'))
    print('Pacote validado:',archive,flush=True)


if __name__=='__main__':
    build()
