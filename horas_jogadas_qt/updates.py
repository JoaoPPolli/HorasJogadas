"""Releases oficiais, download verificado e preparação da atualização nativa."""
import hashlib
import json
import os
import platform
import re
import shutil
import stat
import subprocess
import sys
import tarfile
import tempfile
import time
from dataclasses import dataclass
from pathlib import Path,PurePosixPath
from urllib.parse import urlparse
from urllib.request import Request,urlopen
from .release import VERSION

REPOSITORY='JoaoPPolli/HorasJogadas'
API='https://api.github.com/repos/'+REPOSITORY+'/releases/latest'
MAX_PACKAGE=512*1024*1024
MAX_UNPACKED=2*1024*1024*1024


def version_tuple(value):
    if not isinstance(value,str) or not re.fullmatch(r'v?\d+\.\d+\.\d+',value):
        raise ValueError('Versão estável inválida / Invalid stable version')
    return tuple(map(int,value.lstrip('v').split('.')))


@dataclass(frozen=True)
class Release:
    version:str
    notes:str
    asset_url:str
    size:int
    checksum_url:str
    asset_name:str


def official_url(url,tag,name):
    return url=='https://github.com/'+REPOSITORY+'/releases/download/'+tag+'/'+name


def parse_release(data,current=VERSION,system=None):
    if data.get('draft') or data.get('prerelease'): return None
    tag=data.get('tag_name',''); version=version_tuple(tag)
    if version<=version_tuple(current): return None
    system=system or sys.platform
    name='HorasJogadas-Windows-Setup.exe' if system=='win32' else 'HorasJogadas-Linux-x86_64.tar.gz' if system.startswith('linux') else None
    if not name: raise ValueError('Sistema sem pacote de atualização / Unsupported system')
    assets={item.get('name'):item for item in data.get('assets',[]) if isinstance(item,dict)}
    package,checks=assets.get(name,{}),assets.get('SHA256SUMS.txt',{})
    size=package.get('size',0)
    if not isinstance(size,int) or not 0<size<=MAX_PACKAGE:
        raise ValueError('Pacote ausente ou tamanho inválido / Missing or invalid package')
    if not official_url(package.get('browser_download_url'),tag,name) or not official_url(checks.get('browser_download_url'),tag,'SHA256SUMS.txt'):
        raise ValueError('Endereço de atualização inválido / Invalid update address')
    return Release(tag.lstrip('v'),str(data.get('body') or '')[:30000],package['browser_download_url'],size,checks['browser_download_url'],name)


def request(url,opener=urlopen):
    return opener(Request(url,headers={'User-Agent':'HorasJogadas/'+VERSION,'Accept':'application/vnd.github+json' if url==API else 'application/octet-stream'}),timeout=15)


def check_release(opener=urlopen,current=VERSION,system=None):
    with request(API,opener) as response:
        raw=response.read(1024*1024+1)
        if len(raw)>1024*1024: raise ValueError('Resposta excessiva / Response too large')
        return parse_release(json.loads(raw),current,system)


def download(release,destination,cancel,progress,opener=urlopen):
    from .tasks import Cancelled
    destination=Path(destination); destination.mkdir(parents=True,exist_ok=True)
    with request(release.checksum_url,opener) as response:
        text=response.read(65537)
        if len(text)>65536: raise ValueError('Checksum inválido / Invalid checksum')
        match=re.search(r'^([a-fA-F0-9]{64})\s+'+re.escape(release.asset_name)+r'\s*$',text.decode('utf-8'),re.M)
        if not match: raise ValueError('Checksum ausente / Missing checksum')
        expected=match.group(1).lower()
    target=destination/release.asset_name; partial=destination/(release.asset_name+'.part')
    try:
        digest=hashlib.sha256(); count=0
        with request(release.asset_url,opener) as response,partial.open('wb') as output:
            while True:
                if cancel.is_set(): raise Cancelled()
                block=response.read(256*1024)
                if not block: break
                count+=len(block)
                if count>release.size or count>MAX_PACKAGE: raise ValueError('Tamanho de download inválido / Invalid download size')
                digest.update(block); output.write(block); progress(count,release.size)
            output.flush(); os.fsync(output.fileno())
        if count!=release.size or digest.hexdigest()!=expected:
            raise ValueError('Download corrompido. Tente novamente / Corrupted download. Try again')
        os.replace(partial,target)
        return target
    finally:
        partial.unlink(missing_ok=True)


def cache_directory():
    base=Path(os.environ.get('LOCALAPPDATA') or (Path.home()/'.cache'))
    return base/'HorasJogadas'/'updates'


def stage_linux(archive,target,version):
    """Extrai somente arquivos e links internos do bundle, em um diretório vizinho."""
    target=Path(target).resolve()
    stage=Path(tempfile.mkdtemp(prefix='.horasjogadas-update-',dir=target.parent))
    try:
        with tarfile.open(archive,'r:gz') as package:
            members=package.getmembers()
            if len(members)>10000 or sum(max(0,m.size) for m in members)>MAX_UNPACKED: raise ValueError('Pacote excessivo')
            names=set()
            for member in members:
                path=PurePosixPath(member.name)
                if path.is_absolute() or '..' in path.parts or not path.parts or path.parts[0]!='HorasJogadas' or member.name in names:
                    raise ValueError('Caminho inválido no pacote')
                names.add(member.name)
                if not (member.isfile() or member.isdir() or member.issym()): raise ValueError('Tipo de arquivo inválido')
                if member.issym():
                    link=PurePosixPath(member.linkname)
                    resolved=(stage/Path(member.name).parent/str(link)).resolve()
                    if link.is_absolute() or not resolved.is_relative_to(stage/'HorasJogadas'): raise ValueError('Link externo no pacote')
            # Cria arquivos antes dos links: nenhum caminho pode atravessar um link.
            symlinks={PurePosixPath(m.name) for m in members if m.issym()}
            if any(any(p in symlinks for p in PurePosixPath(m.name).parents) for m in members): raise ValueError('Arquivo dentro de link')
            for member in members:
                output=stage/member.name
                if member.isdir(): output.mkdir(parents=True,exist_ok=True)
                elif member.isfile():
                    output.parent.mkdir(parents=True,exist_ok=True)
                    with package.extractfile(member) as source,output.open('wb') as dest: shutil.copyfileobj(source,dest)
                    output.chmod(member.mode & 0o777)
            for member in members:
                if member.issym():
                    output=stage/member.name; output.parent.mkdir(parents=True,exist_ok=True); output.symlink_to(member.linkname)
        bundle=stage/'HorasJogadas'
        metadata=json.loads((bundle/'package.json').read_text(encoding='utf-8'))
        if metadata.get('version')!=version or metadata.get('platform')!='linux': raise ValueError('Versão do pacote não confere')
        executable=bundle/'HorasJogadas'
        if not executable.is_file() or not os.access(executable,os.X_OK): raise ValueError('Executável ausente')
        # Testa a nova versão antes de encerrar a atual; só usa dados fictícios.
        subprocess.run([str(executable),'--self-test',str(stage/'self-test.json')],check=True,timeout=120)
        if not json.loads((stage/'self-test.json').read_text(encoding='utf-8')).get('ok'): raise ValueError('Autoteste da atualização falhou')
        return bundle
    except Exception:
        shutil.rmtree(stage); raise


LINUX_HELPER=r'''#!/bin/sh
set -u
pid=$1; target=$2; staged=$3; previous=$4; log=$5
count=0
while kill -0 "$pid" 2>/dev/null; do
  count=$((count + 1))
  if [ "$count" -ge 120 ]; then printf '%s\n' 'Update cancelled: application still running' >> "$log"; exit 1; fi
  sleep 1
done
if mv -- "$target" "$previous"; then
  if mv -- "$staged" "$target"; then
    printf '%s\n' 'Update installed' >> "$log"
    "$target/HorasJogadas" >> "$log" 2>&1 &
    exit 0
  fi
  mv -- "$previous" "$target"
fi
printf '%s\n' 'Update failed; previous version preserved' >> "$log"
"$target/HorasJogadas" >> "$log" 2>&1 &
exit 1
'''


def launch_update(package,staged=None,executable=None,system=None):
    executable=Path(executable or sys.executable).resolve(); system=system or sys.platform
    target=executable.parent
    if system=='win32':
        command=[str(package),'/SILENT','/SUPPRESSMSGBOXES','/NORESTART','/SP-','/DIR='+str(target),'/RESTARTAPP']
    elif system.startswith('linux'):
        if staged is None: raise ValueError('Atualização não preparada')
        helper=Path(package).parent/'apply-update.sh'; helper.write_text(LINUX_HELPER,encoding='utf-8')
        previous=target.with_name(target.name+'-previous-'+str(int(time.time())))
        if previous.exists(): raise FileExistsError(previous)
        command=['/bin/sh',str(helper),str(os.getpid()),str(target),str(staged),str(previous),str(Path(package).parent/'update.log')]
    else: raise ValueError('Sistema não suportado')
    return subprocess.Popen(command,cwd=str(Path(package).parent),stdin=subprocess.DEVNULL,stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL,start_new_session=system!='win32')
