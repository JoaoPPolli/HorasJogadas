"""Backups dos dados do usuário (jogos e histórico): diário, antes de apagar, manual e antes de restaurar.

Layout em DATA_DIR/backups/<tipo>/<nome>/{registros.json, cronometros.json}
  diario/AAAA-MM-DD/                    uma cópia por dia (mantém as últimas 7)
  antes_de_apagar/AAAAMMDD-HHMMSS_*/    criada automaticamente antes de exclusões em massa
  manual/AAAAMMDD-HHMMSS/               botão "Criar backup agora"
  antes_de_restaurar/AAAAMMDD-HHMMSS/   guarda os dados atuais antes de uma restauração
"""
import json
import logging
import os
import re
import shutil
from dataclasses import dataclass
from datetime import date, datetime
from typing import List, Optional

from .constants import (
    MAX_BACKUPS_DIARIOS, MAX_BACKUPS_EXTRAS, MAX_BACKUPS_RESTAURAR, NOME_ARQ_CRONOMETROS,
    NOME_ARQ_REGISTROS, PASTA_BACKUPS_DADOS,
)

log = logging.getLogger(__name__)

TIPOS = ("diario", "antes_de_apagar", "manual", "antes_de_restaurar")
ARQUIVOS = (NOME_ARQ_REGISTROS, NOME_ARQ_CRONOMETROS)
_LIMITES = {"diario": MAX_BACKUPS_DIARIOS, "antes_de_apagar": MAX_BACKUPS_EXTRAS,
            "manual": MAX_BACKUPS_EXTRAS, "antes_de_restaurar": MAX_BACKUPS_RESTAURAR}


class ErroBackup(Exception):
    """Falha esperada ao restaurar um backup (arquivo inválido, etc.)."""


@dataclass
class InfoBackup:
    caminho: str
    tipo: str
    momento: datetime
    motivo: str
    jogos: int
    sessoes: int
    total_segundos: int


def _raiz(data_dir: str) -> str:
    return os.path.join(data_dir, PASTA_BACKUPS_DADOS)


def _ler_lista(caminho: str) -> Optional[list]:
    """Conteúdo do JSON se for uma lista válida; senão None."""
    try:
        with open(caminho, "r", encoding="utf-8") as f:
            dados = json.load(f)
    except (OSError, ValueError):
        return None
    return dados if isinstance(dados, list) else None


def _nome_seguro(texto: str) -> str:
    return re.sub(r"[^0-9A-Za-z\-]", "-", texto).strip("-")[:40]


def criar_backup(data_dir: str, tipo: str, motivo: str = "", agora: Optional[datetime] = None) -> Optional[str]:
    """Copia os arquivos de dados VÁLIDOS para um novo backup. Devolve o caminho (ou None).

    Para o tipo 'diario' só cria se ainda não existe o do dia. Arquivos corrompidos não são copiados
    (não faz sentido guardar lixo como "backup").
    """
    if tipo not in TIPOS:
        raise ValueError(f"tipo de backup desconhecido: {tipo}")
    agora = agora or datetime.now()
    fonte = {nome: os.path.join(data_dir, nome) for nome in ARQUIVOS}
    validos = [n for n, c in fonte.items() if os.path.exists(c) and _ler_lista(c) is not None]
    if not validos:
        return None

    pasta_tipo = os.path.join(_raiz(data_dir), tipo)
    if tipo == "diario":
        nome = agora.strftime("%Y-%m-%d")
    else:
        nome = agora.strftime("%Y%m%d-%H%M%S") + (f"_{_nome_seguro(motivo)}" if motivo else "")
    destino = os.path.join(pasta_tipo, nome)
    if os.path.exists(destino):
        if tipo == "diario":
            return None
        base, i = destino, 2                                  # dois backups no mesmo segundo
        while os.path.exists(destino):
            destino, i = f"{base}-{i}", i + 1

    provisorio = destino + ".tmp"
    shutil.rmtree(provisorio, ignore_errors=True)
    os.makedirs(provisorio)
    try:
        for nome_arq in validos:
            shutil.copy2(fonte[nome_arq], os.path.join(provisorio, nome_arq))
        os.replace(provisorio, destino)                       # só aparece na lista quando está completo
    except OSError:
        shutil.rmtree(provisorio, ignore_errors=True)
        raise
    _podar(data_dir, tipo)
    return destino


def backup_diario(data_dir: str, hoje: Optional[date] = None) -> Optional[str]:
    agora = datetime.combine(hoje, datetime.min.time()) if hoje else None
    return criar_backup(data_dir, "diario", agora=agora)


def _podar(data_dir: str, tipo: str) -> None:
    pasta = os.path.join(_raiz(data_dir), tipo)
    if not os.path.isdir(pasta):
        return
    nomes = sorted(n for n in os.listdir(pasta) if not n.endswith(".tmp") and os.path.isdir(os.path.join(pasta, n)))
    for antigo in nomes[:-_LIMITES[tipo]]:
        shutil.rmtree(os.path.join(pasta, antigo), ignore_errors=True)


def _momento_e_motivo(tipo: str, nome: str) -> Optional[tuple]:
    try:
        if tipo == "diario":
            return datetime.strptime(nome[:10], "%Y-%m-%d"), ""
        momento = datetime.strptime(nome[:15], "%Y%m%d-%H%M%S")
        return momento, nome[16:] if len(nome) > 16 and nome[15] == "_" else ""
    except ValueError:
        return None


def listar_backups(data_dir: str) -> List[InfoBackup]:
    """Todos os backups, do mais recente para o mais antigo, com contagens para exibição."""
    infos: List[InfoBackup] = []
    for tipo in TIPOS:
        pasta = os.path.join(_raiz(data_dir), tipo)
        if not os.path.isdir(pasta):
            continue
        for nome in os.listdir(pasta):
            caminho = os.path.join(pasta, nome)
            if nome.endswith(".tmp") or not os.path.isdir(caminho):
                continue
            parsed = _momento_e_motivo(tipo, nome)
            if parsed is None:
                continue
            sessoes = _ler_lista(os.path.join(caminho, NOME_ARQ_REGISTROS)) or []
            jogos = _ler_lista(os.path.join(caminho, NOME_ARQ_CRONOMETROS)) or []
            total = 0
            for s in sessoes:
                try:
                    total += int(s.get("segundos", 0))
                except (AttributeError, TypeError, ValueError):
                    pass
            infos.append(InfoBackup(caminho, tipo, parsed[0], parsed[1], len(jogos), len(sessoes), total))
    return sorted(infos, key=lambda b: (b.momento, b.caminho), reverse=True)


def restaurar_backup(data_dir: str, caminho: str) -> None:
    """Substitui os dados atuais pelos do backup. Antes, guarda os atuais em 'antes_de_restaurar'."""
    presentes = {n: os.path.join(caminho, n) for n in ARQUIVOS if os.path.exists(os.path.join(caminho, n))}
    if not presentes or any(_ler_lista(c) is None for c in presentes.values()):
        raise ErroBackup("backup inválido ou incompleto")
    criar_backup(data_dir, "antes_de_restaurar")               # rede de segurança da própria restauração
    for nome, origem in presentes.items():
        destino = os.path.join(data_dir, nome)
        provisorio = destino + ".restaurando"
        shutil.copy2(origem, provisorio)
        os.replace(provisorio, destino)                        # troca atômica, arquivo a arquivo
        try:                                                   # o .bak antigo não pertence mais a estes dados
            os.remove(destino + ".bak")
        except FileNotFoundError:
            pass
