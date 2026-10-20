"""Arquivo independente de conclusões. Nunca escreve jogos, sessões ou configurações."""
import json
import os
import re
import shutil
from dataclasses import asdict, dataclass, field, replace
from datetime import date, datetime
from typing import Iterable, List, Optional

from .i18n import t
from .models import novo_id
from .storage import escrever_json_atomico
from .utils import normalizar_texto

MESES = ('Janeiro', 'Fevereiro', 'Março', 'Abril', 'Maio', 'Junho',
         'Julho', 'Agosto', 'Setembro', 'Outubro', 'Novembro', 'Dezembro')
MESES_EN = ('January', 'February', 'March', 'April', 'May', 'June',
            'July', 'August', 'September', 'October', 'November', 'December')
TIPOS = ('zerado', 'experiencia')


def duracao_texto(segundos: Optional[int]) -> str:
    if segundos is None:
        return ''
    h, resto = divmod(segundos, 3600)
    m, s = divmod(resto, 60)
    return f'{h}h{m:02d}m{s:02d}s'


def ler_duracao(texto: str) -> Optional[int]:
    """Duração opcional, em 13h45m, 40min ou HH:MM:SS; sem conversões parciais."""
    texto = texto.strip().lower()
    if not texto:
        return None
    if re.fullmatch(r'\d+:\d{2}(?::\d{2})?', texto):
        partes = [int(p) for p in texto.split(':')]
        h, m, s = partes if len(partes) == 3 else (*partes, 0)
        if m >= 60 or s >= 60:
            raise ValueError(t('zer.erro_tempo'))
        return h * 3600 + m * 60 + s
    match = re.fullmatch(r'\s*(?:(\d+)\s*h(?:oras?)?)?\s*(?:(\d+)\s*m(?:in(?:utos?)?)?)?'
                         r'\s*(?:(\d+)\s*s(?:eg(?:undos?)?)?)?\s*', texto)
    if not match or not any(v is not None for v in match.groups()):
        raise ValueError(t('zer.erro_tempo'))
    h, m, s = (int(v or 0) for v in match.groups())
    if (h and m >= 60) or ((h or m) and s >= 60):
        raise ValueError(t('zer.erro_tempo'))
    return h * 3600 + m * 60 + s


@dataclass(frozen=True)
class Conclusao:
    nome: str
    ano: int
    mes: int
    segundos: Optional[int] = None
    dia: Optional[int] = None
    platina_segundos: Optional[int] = None
    notas: str = ''
    tipo: str = 'zerado'
    id: str = field(default_factory=novo_id)
    origem: str = 'manual'
    dlc: bool = False

    def validar(self):
        if not isinstance(self.nome, str) or not self.nome.strip():
            raise ValueError(t('zer.erro_nome'))
        if type(self.ano) is not int or not 1900 <= self.ano <= 9999:
            raise ValueError(t('zer.erro_data'))
        if type(self.mes) is not int or not 1 <= self.mes <= 12:
            raise ValueError(t('zer.erro_data'))
        if self.dia is not None and type(self.dia) is not int:
            raise ValueError(t('zer.erro_data'))
        try:
            dia = date(self.ano, self.mes, self.dia if self.dia is not None else 1)
        except ValueError:
            raise ValueError(t('zer.erro_data')) from None
        if dia > date.today():
            raise ValueError(t('zer.erro_futuro'))
        for tempo in (self.segundos, self.platina_segundos):
            if tempo is not None and (type(tempo) is not int or tempo < 0):
                raise ValueError(t('zer.erro_tempo'))
        if type(self.dlc) is not bool:
            raise ValueError(t('zer.erro_dlc'))
        if (self.tipo not in TIPOS or not isinstance(self.notas, str)
                or not isinstance(self.id, str) or not self.id or not isinstance(self.origem, str)):
            raise ValueError(t('zer.erro_arquivo'))
        return self

    def assinatura(self):
        # Dia e categoria não entram: um TXT antigo pode omitir esses metadados
        # da mesma conclusão que já foi editada no app.
        return (normalizar_texto(self.nome), self.ano, self.mes, self.segundos,
                self.platina_segundos, self.tipo, normalizar_texto(self.notas))


@dataclass(frozen=True)
class ResumoAno:
    jogos_zerados: int = 0
    dlcs_zeradas: int = 0
    experiencias: int = 0
    segundos_registrados: int = 0
    platina_segundos: int = 0
    sem_tempo: int = 0
    registros: int = 0


def resumo_ano(registros: Iterable[Conclusao], ano: int) -> ResumoAno:
    """Conta cada jogada e soma apenas tempos conhecidos do arquivo de conclusões."""
    itens = [r for r in registros if r.ano == ano]
    platina = sum(r.platina_segundos for r in itens if r.platina_segundos is not None)
    return ResumoAno(
        jogos_zerados=sum(r.tipo == 'zerado' and not r.dlc for r in itens),
        dlcs_zeradas=sum(r.tipo == 'zerado' and r.dlc for r in itens),
        experiencias=sum(r.tipo == 'experiencia' for r in itens),
        segundos_registrados=sum(r.segundos for r in itens if r.segundos is not None) + platina,
        platina_segundos=platina,
        sem_tempo=sum(r.segundos is None for r in itens),
        registros=len(itens),
    )


class RepositorioZerados:
    """Estado em zerados.json e backup próprio. Commit em memória só após gravação bem-sucedida."""

    def __init__(self, data_dir: str):
        self.caminho = os.path.join(data_dir, 'zerados.json')
        self.registros: List[Conclusao] = []
        self.automaticos: List[str] = []
        self.avisos: List[str] = []
        self._carregar()

    @staticmethod
    def _decodificar(caminho):
        with open(caminho, encoding='utf-8') as arquivo:
            dados = json.load(arquivo)
        if not isinstance(dados, dict) or dados.get('versao') != 1:
            raise ValueError(t('zer.erro_arquivo'))
        raw = dados.get('registros')
        automaticos = dados.get('automaticos')
        dlcs = dados.get('dlcs', [])
        if not isinstance(raw, list) or not isinstance(automaticos, list) or not isinstance(dlcs, list):
            raise ValueError(t('zer.erro_arquivo'))
        if not all(isinstance(i, str) for i in automaticos + dlcs):
            raise ValueError(t('zer.erro_arquivo'))
        try:
            registros = [Conclusao(**item).validar() for item in raw]
        except (TypeError, ValueError):
            raise ValueError(t('zer.erro_arquivo')) from None
        if len({r.id for r in registros}) != len(registros):
            raise ValueError(t('zer.erro_arquivo'))
        if len(set(dlcs)) != len(dlcs) or not set(dlcs).issubset({r.id for r in registros}):
            raise ValueError(t('zer.erro_arquivo'))
        ids_dlc = set(dlcs)
        registros = [replace(r, dlc=r.id in ids_dlc) for r in registros]
        return registros, automaticos

    def _carregar(self):
        if not os.path.exists(self.caminho):
            return
        try:
            self.registros, self.automaticos = self._decodificar(self.caminho)
        except (ValueError, UnicodeError):
            # Falha fechada: sem backup válido, não permita sobrescrever o arquivo.
            try:
                registros, automaticos = self._decodificar(self.caminho + '.bak')
            except (OSError, ValueError, UnicodeError):
                raise ValueError(t('zer.erro_arquivo')) from None
            copia = self.caminho + datetime.now().strftime('.corrompido-%Y%m%d-%H%M%S%f')
            shutil.copy2(self.caminho, copia)
            shutil.copy2(self.caminho + '.bak', self.caminho)
            self.registros, self.automaticos = registros, automaticos
            self.avisos.append(t('zer.recuperado', caminho=copia))

    def _salvar(self, registros, automaticos=None):
        automaticos = list(self.automaticos if automaticos is None else automaticos)
        registros = [r.validar() for r in registros]
        # O leitor anterior aceita campos extras na raiz, mas não dentro dos registros.
        # Assim, um downgrade continua abrindo as conclusões normalmente.
        raw = []
        for registro in registros:
            item = asdict(registro)
            del item['dlc']
            raw.append(item)
        escrever_json_atomico(self.caminho, {'versao': 1, 'registros': raw,
                                            'automaticos': automaticos,
                                            'dlcs': [r.id for r in registros if r.dlc]})
        self.registros, self.automaticos = list(registros), automaticos

    def guardar(self, registro: Conclusao):
        registro.validar()
        novos = [registro if r.id == registro.id else r for r in self.registros]
        if not any(r.id == registro.id for r in self.registros):
            novos.append(registro)
        self._salvar(novos)

    def excluir(self, registro_id: str):
        # Conserva recibos automáticos: alternar status não ressuscita um registro excluído.
        self._salvar([r for r in self.registros if r.id != registro_id])

    def importar(self, registros: List[Conclusao]) -> int:
        assinaturas = {r.assinatura() for r in self.registros}
        novos = []
        for r in registros:
            r.validar()
            if r.assinatura() not in assinaturas:
                novos.append(replace(r, id=novo_id(), origem='txt'))
                assinaturas.add(r.assinatura())
        if novos:
            self._salvar(self.registros + novos)
        return len(novos)

    def registrar_automatico(self, jogo_id: str, nome: str, segundos: int,
                            agora: Optional[date] = None) -> Optional[Conclusao]:
        if jogo_id in self.automaticos:
            return None
        hoje = agora or date.today()
        registro = Conclusao(nome, hoje.year, hoje.month, max(0, int(round(segundos))),
                             dia=hoje.day, origem='cronometro')
        recibos = self.automaticos + [jogo_id]
        if any(r.assinatura() == registro.assinatura() for r in self.registros):
            self._salvar(self.registros, recibos)
            return None
        self._salvar(self.registros + [registro], recibos)
        return registro


@dataclass
class ItemImportacao:
    linha: int
    texto: str
    registro: Optional[Conclusao]
    aviso: str = ''
    selecionado: bool = False


def ano_do_texto(texto: str) -> Optional[int]:
    for linha in texto.splitlines():
        if re.search(r'zerad|complet|finished', normalizar_texto(linha)):
            match = re.search(r'\b(19\d{2}|20\d{2})\b', linha)
            if match:
                return int(match[1])
    return None


def ler_txt(caminho: str) -> str:
    with open(caminho, 'rb') as arquivo:
        dados = arquivo.read(2_000_001)
    if len(dados) > 2_000_000:
        raise ValueError(t('zer.txt_grande'))
    if dados.startswith((b'\xff\xfe', b'\xfe\xff')):
        texto = dados.decode('utf-16')
    else:
        try:
            texto = dados.decode('utf-8-sig')
        except UnicodeDecodeError:
            texto = dados.decode('cp1252')
    return texto.replace('\r\n', '\n').replace('\r', '\n')


def interpretar_txt(texto: str, ano_padrao: Optional[int] = None) -> List[ItemImportacao]:
    """Interpreta sem gravar. Linhas desconhecidas permanecem visíveis para revisão."""
    ano = ano_do_texto(texto) or ano_padrao
    mes = None
    resultado = []
    meses = {normalizar_texto(n): i + 1 for lista in (MESES, MESES_EN) for i, n in enumerate(lista)}
    for numero, original in enumerate(texto.splitlines(), 1):
        linha = original.strip()
        if not linha:
            continue
        norm = normalizar_texto(linha)
        if norm.startswith(('@dia:', '@nota:', '@dlc:')) and resultado and resultado[-1].registro:
            anterior = resultado[-1]
            anterior.texto += '\n' + original
            try:
                if norm.startswith('@dia:'):
                    anterior.registro = replace(anterior.registro, dia=int(linha[5:].strip())).validar()
                elif norm.startswith('@dlc:'):
                    valor = normalizar_texto(linha[5:])
                    opcoes = {'sim': True, 'true': True, 'yes': True,
                              'nao': False, 'false': False, 'no': False}
                    if valor not in opcoes:
                        raise ValueError(t('zer.erro_dlc'))
                    anterior.registro = replace(anterior.registro, dlc=opcoes[valor]).validar()
                else:
                    notas = anterior.registro.notas
                    anterior.registro = replace(anterior.registro, notas=(notas + '\n' if notas else '') + linha[6:].strip())
            except ValueError:
                anterior.aviso = t('zer.erro_dlc' if norm.startswith('@dlc:') else 'zer.erro_data')
                anterior.selecionado = False
            continue
        cabecalho = re.fullmatch(r'(?:zerados?(?: em)?|jogos zerados(?: em)?|completed(?: in)?|finished(?: in)?)?\s*(19\d{2}|20\d{2})\s*[:.!]?', norm)
        if cabecalho:
            ano, mes = int(cabecalho[1]), None
            continue
        mes_match = re.fullmatch(r'([a-z]+)(?:\s*[/ -]\s*(\d{4}))?\s*:', norm)
        nome_mes = (mes_match[1] if mes_match else norm.rstrip(':').strip())
        if nome_mes in meses:
            mes = meses[nome_mes]
            if mes_match and mes_match[2]:
                ano = int(mes_match[2])
            continue
        if linha.startswith(('"', "'")) or norm.lstrip('- ').startswith(('essa lista', 'esta lista')):
            continue
        item = ItemImportacao(numero, original, None)
        resultado.append(item)
        try:
            if ano is None or mes is None:
                raise ValueError(t('zer.import_sem_data'))
            conteudo = re.sub(r'^\s*(?:[-•–]|\d+[.)])\s*', '', linha).strip()
            if '*' not in conteudo:
                raise ValueError(t('zer.import_formato'))
            experiencia = '((' in conteudo
            nome, resto = conteudo.split('*', 1)
            nome = nome.strip()
            segmentos = resto.split('|')
            tempo_texto = segmentos[0].strip()
            observacoes = []
            sufixo = re.search(r'\s*(\(\(.*?\)\)|\([^()]*\))\s*$', tempo_texto)
            while sufixo:
                observacoes.insert(0, sufixo[1])
                tempo_texto = tempo_texto[:sufixo.start()].strip()
                sufixo = re.search(r'\s*(\(\(.*?\)\)|\([^()]*\))\s*$', tempo_texto)
            segundos = ler_duracao(tempo_texto)
            platina = None
            for extra in segmentos[1:]:
                chave, separador, tempo = extra.partition('*')
                if separador and normalizar_texto(chave.strip()) in ('platina', 'platinum') and platina is None:
                    platina = ler_duracao(tempo)
                else:
                    raise ValueError(t('zer.import_formato'))
            tipo = 'experiencia' if experiencia else 'zerado'
            nome = nome.replace('((', '').replace('))', '').strip()
            item.registro = Conclusao(nome, ano, mes, segundos, platina_segundos=platina,
                                      notas=' · '.join(observacoes), tipo=tipo, origem='txt').validar()
            item.selecionado = True
        except ValueError as erro:
            item.aviso = str(erro)
    return resultado


def exportar_txt(registros: List[Conclusao], ano: int) -> str:
    linhas = [f'ZERADOS EM {ano}', '']
    for mes in range(1, 13):
        itens = [r for r in registros if r.ano == ano and r.mes == mes]
        if not itens:
            continue
        linhas.append(MESES[mes - 1] + ':')
        for r in itens:
            nome = f'(({r.nome}))' if r.tipo == 'experiencia' else r.nome
            linha = f'-{nome} * {duracao_texto(r.segundos)}'
            if r.platina_segundos is not None:
                linha += f' | Platina * {duracao_texto(r.platina_segundos)}'
            # Notas são preservadas em linhas próprias reconhecidas pelo importador.
            linhas.append(linha)
            if r.dlc:
                linhas.append('  @dlc: sim')
            if r.dia is not None:
                linhas.append(f'  @dia: {r.dia}')
            if r.notas:
                for nota in r.notas.splitlines():
                    linhas.append(f'  @nota: {nota}')
        linhas.append('')
    return '\n'.join(linhas)
