"""Busca pública da Steam e capas locais, independentes dos registros de horas."""
import hashlib
import json
import os
import re
import tempfile
import unicodedata
from dataclasses import dataclass
from difflib import SequenceMatcher
from pathlib import Path
from urllib.parse import urlencode,urlparse
from urllib.request import Request
from .network import urlopen
from horas_jogadas.storage import escrever_json_atomico

MAX_IMAGE=10*1024*1024
FILE_PATTERN=re.compile(r'[a-f0-9]{64}\.jpg')


def valid_image_url(url,app_id):
    try:
        parsed=urlparse(url)
        return (parsed.scheme=='https' and bool(parsed.hostname) and parsed.hostname.endswith('.steamstatic.com')
                and parsed.port is None and not parsed.username and not parsed.password
                and ('/steam/apps/'+str(app_id)+'/') in parsed.path)
    except (ValueError,TypeError):return False


@dataclass(frozen=True)
class Candidate:
    app_id:int
    name:str
    image_url:str
    score:float=0
    @property
    def page(self):return 'https://store.steampowered.com/app/'+str(self.app_id)+'/'


def normalized(name):
    name=''.join(c for c in unicodedata.normalize('NFKD',name.casefold()) if not unicodedata.combining(c))
    name=re.sub(r'\b(game of the year|goty|remastered|remaster|definitive edition|complete edition|enhanced edition)\b','',name)
    return ' '.join(re.findall(r'[a-z0-9]+',name))


def similarity(query,name):
    a,b=normalized(query),normalized(name)
    score=SequenceMatcher(None,a,b).ratio()
    numbers=lambda value:re.findall(r'\b(?:\d+|ii|iii|iv|vi|vii|viii|ix)\b',value)
    if numbers(a)!=numbers(b):score=min(score,.85)
    return score


def search(query,opener=urlopen):
    if not query.strip():return []
    url='https://store.steampowered.com/api/storesearch/?'+urlencode({'term':query[:200],'l':'english','cc':'US'})
    with opener(Request(url,headers={'User-Agent':'HorasJogadas (+https://github.com/JoaoPPolli/HorasJogadas)'}),timeout=15) as response:
        raw=response.read(1024*1024+1)
        if len(raw)>1024*1024:raise ValueError('Resposta excessiva / Response too large')
        value=json.loads(raw)
    candidates={}
    for item in value.get('items',[]):
        app_id=item.get('id');name=item.get('name');tiny=item.get('tiny_image','')
        if type(app_id) is not int or not 0<app_id<100000000 or not isinstance(name,str) or not name.strip():continue
        if not isinstance(tiny,str) or not valid_image_url(tiny,app_id):continue
        # Cada arte nova pode ter seu próprio hash: não adivinha a URL de outro tamanho.
        candidates[app_id]=Candidate(app_id,name[:300],tiny,similarity(query,name))
    return sorted(candidates.values(),key=lambda item:item.score,reverse=True)[:8]


def normalize_image(data):
    from PySide6.QtCore import QBuffer,QIODevice,Qt
    from PySide6.QtGui import QImageReader,QImage
    if len(data)>MAX_IMAGE:raise ValueError('Imagem muito grande / Image too large')
    buffer=QBuffer();buffer.setData(data);buffer.open(QIODevice.ReadOnly)
    reader=QImageReader(buffer);reader.setAutoTransform(True)
    size=reader.size()
    if size.width()<=0 or size.height()<=0 or size.width()*size.height()>40_000_000:
        raise ValueError('Imagem inválida ou muito grande / Invalid or oversized image')
    if max(size.width(),size.height())>1280:reader.setScaledSize(size.scaled(1280,1280,Qt.KeepAspectRatio))
    image=reader.read()
    if image.isNull():raise ValueError('Imagem ilegível / Unreadable image')
    image=image.convertToFormat(QImage.Format_RGB32)
    output=QBuffer();output.open(QIODevice.WriteOnly)
    if not image.save(output,'JPEG',90):raise ValueError('Não foi possível salvar a imagem / Cannot save image')
    return bytes(output.data())


def download(candidate,cancel,opener=urlopen):
    from .tasks import Cancelled
    if type(candidate.app_id) is not int or not 0<candidate.app_id<100000000 or not valid_image_url(candidate.image_url,candidate.app_id):
        raise ValueError('URL de capa inválida / Invalid cover URL')
    if cancel.is_set():raise Cancelled()
    urls=[]
    # appdetails fornece a URL exata de alta qualidade, inclusive para artes com hash.
    try:
        endpoint='https://store.steampowered.com/api/appdetails?'+urlencode({'appids':candidate.app_id,'l':'english','cc':'US'})
        with opener(Request(endpoint,headers={'User-Agent':'HorasJogadas'}),timeout=15) as response:
            raw=response.read(1024*1024+1)
            if len(raw)>1024*1024:raise ValueError('Resposta excessiva')
            detail=json.loads(raw).get(str(candidate.app_id),{})
            header=detail.get('data',{}).get('header_image','')
            if valid_image_url(header,candidate.app_id):urls.append(header)
    except Exception:
        if cancel.is_set():raise Cancelled()
    if candidate.image_url not in urls:urls.append(candidate.image_url)
    last_error=None
    for url in urls:
        if cancel.is_set():raise Cancelled()
        try:
            with opener(Request(url,headers={'User-Agent':'HorasJogadas'}),timeout=15) as response:
                chunks=[];count=0
                while True:
                    if cancel.is_set():raise Cancelled()
                    block=response.read(65536)
                    if not block:break
                    count+=len(block)
                    if count>MAX_IMAGE:raise ValueError('Imagem muito grande / Image too large')
                    chunks.append(block)
            return normalize_image(b''.join(chunks))
        except Cancelled:raise
        except Exception as error:last_error=error
    raise last_error


class CoverStore:
    def __init__(self,folder):
        self.folder=Path(folder)/'covers';self.index_path=self.folder/'index.json'
        try:
            value=json.loads(self.index_path.read_text(encoding='utf-8'))
            self.entries=value if isinstance(value,dict) else {}
        except (ValueError,OSError):self.entries={}

    def path(self,key):
        entry=self.entries.get(key,{})
        name=entry.get('file') if isinstance(entry,dict) else None
        if not isinstance(name,str) or not FILE_PATTERN.fullmatch(name):return None
        path=self.folder/name
        return path if path.is_file() and not path.is_symlink() else None

    def save_many(self,records):
        """Arquivos por conteúdo primeiro; índice de toda a operação publicado por último."""
        if self.folder.is_symlink():raise ValueError('Pasta de capas inválida')
        self.folder.mkdir(parents=True,exist_ok=True);entries=dict(self.entries)
        for key,image,metadata in records:
            name=hashlib.sha256(image).hexdigest()+'.jpg';path=self.folder/name
            if not path.exists():
                fd,temporary=tempfile.mkstemp(prefix='.cover-',dir=self.folder)
                try:
                    with os.fdopen(fd,'wb') as output:output.write(image);output.flush();os.fsync(output.fileno())
                    os.replace(temporary,path)
                finally:Path(temporary).unlink(missing_ok=True)
            entries[key]={**metadata,'file':name}
        escrever_json_atomico(str(self.index_path),entries)
        self.entries=entries

    def remove(self,key):
        entries=dict(self.entries);entries.pop(key,None)
        if self.folder.exists():escrever_json_atomico(str(self.index_path),entries)
        self.entries=entries
