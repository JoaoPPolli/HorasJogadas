"""Atualização do app a partir de um arquivo ZIP, sem apagar pastas manualmente.

Fluxo (`aplicar_zip`):
  1. valida o ZIP (integridade, caminhos seguros, arquivos obrigatórios, sintaxe de todos os .py);
  2. extrai para uma pasta temporária ao lado do app;
  3. guarda a versão atual em `_versoes_anteriores/` e troca a pasta `horas_jogadas/` pela nova;
  4. se qualquer passo falhar, tudo volta ao estado anterior.

Os dados do usuário (jogos, histórico, config) ficam em %APPDATA% e nunca são tocados.
"""
import logging
import os
import re
import shutil
import subprocess
import sys
import tempfile
import time
import zipfile
from dataclasses import dataclass
from datetime import datetime
from typing import Dict, List, Optional, Sequence

from .constants import ARQUIVOS_DE_APOIO, MARCADOR_NAO_VALIDADA, MAX_BACKUPS, PASTA_BACKUPS
from .i18n import t
from .utils import modo_empacotado

log = logging.getLogger(__name__)

PACOTE = "horas_jogadas"
OBRIGATORIOS = ("__init__.py", "main.py", "storage.py", "ui/main_window.py")   # dentro do pacote
_RE_VERSAO = re.compile(r"""__version__\s*=\s*["']([^"']+)["']""")


class ErroAtualizacao(Exception):
    """Falha esperada ao validar/aplicar uma atualização (mensagem já pronta para o usuário)."""


@dataclass
class InfoZip:
    versao: str
    prefixo: str                 # pasta raiz dentro do ZIP (ex.: "HorasJogadas/"), pode ser ""
    arquivos_pacote: List[str]   # nomes (normalizados) dos arquivos de horas_jogadas/
    arquivos_apoio: List[str]    # app.py, README.md etc. presentes no ZIP


# ---------------------------------------------------------------------------
# Versões
# ---------------------------------------------------------------------------
def _versao_em_texto(texto: str) -> Optional[str]:
    achado = _RE_VERSAO.search(texto)
    return achado.group(1) if achado else None


def comparar_versoes(a: str, b: str) -> int:
    """-1 se a < b, 0 se iguais, 1 se a > b (compara os números: '2.10.0' > '2.9.0')."""
    na = [int(x) for x in re.findall(r"\d+", a)] or [0]
    nb = [int(x) for x in re.findall(r"\d+", b)] or [0]
    tamanho = max(len(na), len(nb))
    na += [0] * (tamanho - len(na))
    nb += [0] * (tamanho - len(nb))
    return (na > nb) - (na < nb)


def versao_instalada(pasta_app: str) -> str:
    """Versão do código que está em `pasta_app/horas_jogadas` (lida do arquivo, sem importar)."""
    try:
        with open(os.path.join(pasta_app, PACOTE, "__init__.py"), encoding="utf-8") as f:
            return _versao_em_texto(f.read()) or "?"
    except OSError:
        return "?"


# ---------------------------------------------------------------------------
# Validação do ZIP
# ---------------------------------------------------------------------------
def _normalizar(nome: str) -> str:
    return nome.replace("\\", "/")


def _caminho_inseguro(nome: str) -> bool:
    partes = nome.split("/")
    return nome.startswith("/") or ".." in partes or (len(partes[0]) == 2 and partes[0][1] == ":")


def inspecionar_zip(caminho: str) -> InfoZip:
    """Valida o ZIP sem extrair nada. Levanta ErroAtualizacao se não for uma atualização válida."""
    try:
        zf = zipfile.ZipFile(caminho)
    except (zipfile.BadZipFile, OSError):
        raise ErroAtualizacao(t("atu.erro.nao_zip")) from None
    with zf:
        if zf.testzip() is not None:
            raise ErroAtualizacao(t("atu.erro.nao_zip"))
        original = {_normalizar(i.filename): i.filename for i in zf.infolist()}
        for nome in original:
            if _caminho_inseguro(nome):
                raise ErroAtualizacao(t("atu.erro.inseguro", arquivo=nome))

        alvo = f"{PACOTE}/__init__.py"
        candidatos = [n for n in original if n == alvo or n.endswith("/" + alvo)]
        if not candidatos:
            raise ErroAtualizacao(t("atu.erro.sem_pacote"))
        init = min(candidatos, key=len)
        prefixo = init[: -len(alvo)]
        raiz_pacote = prefixo + PACOTE + "/"

        arquivos_pacote = [n for n in original if n.startswith(raiz_pacote) and not n.endswith("/")
                           and "__pycache__" not in n and not n.endswith(".pyc")]
        for obrigatorio in OBRIGATORIOS:
            if raiz_pacote + obrigatorio not in original:
                raise ErroAtualizacao(t("atu.erro.faltando", arquivo=f"{PACOTE}/{obrigatorio}"))

        for nome in arquivos_pacote:                      # nenhum .py pode ter erro de sintaxe
            if nome.endswith(".py"):
                rel = nome[len(prefixo):]
                try:
                    compile(zf.read(original[nome]).decode("utf-8"), rel, "exec", dont_inherit=True)
                except SyntaxError as e:
                    raise ErroAtualizacao(t("atu.erro.sintaxe", arquivo=rel, linha=e.lineno or 0)) from None
                except UnicodeDecodeError:
                    raise ErroAtualizacao(t("atu.erro.sintaxe", arquivo=rel, linha=0)) from None

        versao = _versao_em_texto(zf.read(original[init]).decode("utf-8", errors="replace"))
        if not versao:
            raise ErroAtualizacao(t("atu.erro.sem_versao"))
        apoio = [a for a in ARQUIVOS_DE_APOIO if prefixo + a in original]
    return InfoZip(versao=versao, prefixo=prefixo, arquivos_pacote=arquivos_pacote, arquivos_apoio=apoio)


# ---------------------------------------------------------------------------
# Operações de arquivo
# ---------------------------------------------------------------------------
def _mover(origem: str, destino: str, tentativas: int = 4) -> None:
    """Move arquivo/pasta, repetindo algumas vezes (antivírus/indexador podem travar por instantes)."""
    for i in range(tentativas):
        try:
            shutil.move(origem, destino)
            return
        except PermissionError:
            if i == tentativas - 1:
                raise
            time.sleep(0.4)


def _extrair(caminho_zip: str, info: InfoZip, destino: str) -> None:
    """Extrai pacote -> destino/horas_jogadas e arquivos de apoio -> destino/."""
    raiz_pacote = info.prefixo + PACOTE + "/"
    with zipfile.ZipFile(caminho_zip) as zf:
        original = {_normalizar(i.filename): i.filename for i in zf.infolist()}
        pedidos = [(n, os.path.join(destino, PACOTE, n[len(raiz_pacote):])) for n in info.arquivos_pacote]
        pedidos += [(info.prefixo + a, os.path.join(destino, a)) for a in info.arquivos_apoio]
        base = os.path.abspath(destino)
        for nome, caminho in pedidos:
            caminho = os.path.abspath(caminho)
            if os.path.commonpath([base, caminho]) != base:          # defesa extra contra path traversal
                raise ErroAtualizacao(t("atu.erro.inseguro", arquivo=nome))
            os.makedirs(os.path.dirname(caminho), exist_ok=True)
            with zf.open(original[nome]) as origem, open(caminho, "wb") as saida:
                shutil.copyfileobj(origem, saida)


def _pasta_backups(pasta_app: str) -> str:
    return os.path.join(pasta_app, PASTA_BACKUPS)


def _listar_backups(pasta_app: str) -> List[str]:
    """Pastas de backup que contêm um pacote, da mais antiga para a mais recente."""
    raiz = _pasta_backups(pasta_app)
    if not os.path.isdir(raiz):
        return []
    nomes = sorted(n for n in os.listdir(raiz) if os.path.isdir(os.path.join(raiz, n, PACOTE)))
    return [os.path.join(raiz, n) for n in nomes]


def backup_mais_recente(pasta_app: str) -> Optional[str]:
    backups = _listar_backups(pasta_app)
    return backups[-1] if backups else None


def tem_backup(pasta_app: str) -> bool:
    return backup_mais_recente(pasta_app) is not None


def versao_do_backup(pasta_backup: str) -> str:
    return versao_instalada(pasta_backup)


def _nova_pasta_backup(pasta_app: str, versao: str) -> str:
    seguro = re.sub(r"[^0-9A-Za-z.\-]", "_", versao)
    caminho = os.path.join(_pasta_backups(pasta_app), f"{datetime.now():%Y%m%d-%H%M%S%f}_v{seguro}")
    os.makedirs(caminho, exist_ok=True)
    return caminho


def _podar_backups(pasta_app: str, manter: int = MAX_BACKUPS) -> None:
    for antigo in _listar_backups(pasta_app)[:-manter] if manter > 0 else _listar_backups(pasta_app):
        shutil.rmtree(antigo, ignore_errors=True)


def _caminho_marcador(pasta_app: str) -> str:
    return os.path.join(_pasta_backups(pasta_app), MARCADOR_NAO_VALIDADA)


def marcar_nao_validada(pasta_app: str, versao: str) -> None:
    os.makedirs(_pasta_backups(pasta_app), exist_ok=True)
    with open(_caminho_marcador(pasta_app), "w", encoding="utf-8") as f:
        f.write(versao)


def versao_pendente_de_validacao(pasta_app: str) -> Optional[str]:
    try:
        with open(_caminho_marcador(pasta_app), encoding="utf-8") as f:
            return f.read().strip() or "?"
    except OSError:
        return None


def confirmar_inicializacao(pasta_app: str) -> None:
    """Chamado quando a janela principal abriu com sucesso: a versão nova está validada."""
    try:
        os.remove(_caminho_marcador(pasta_app))
    except FileNotFoundError:
        pass
    except OSError:
        log.exception("Não foi possível remover o marcador de validação")


# ---------------------------------------------------------------------------
# Aplicar e restaurar
# ---------------------------------------------------------------------------
def aplicar_zip(caminho_zip: str, pasta_app: str, manter_backups: int = MAX_BACKUPS) -> InfoZip:
    """Instala a atualização do ZIP. Em caso de falha, restaura tudo e levanta ErroAtualizacao."""
    if modo_empacotado():
        raise ErroAtualizacao(t("atu.erro.empacotado"))
    info = inspecionar_zip(caminho_zip)
    pacote = os.path.join(pasta_app, PACOTE)
    staging = tempfile.mkdtemp(prefix=".atualizando-", dir=pasta_app)
    backup = ""
    novo_instalado = False
    apoio_guardado: Dict[str, bool] = {}
    try:
        _extrair(caminho_zip, info, staging)
        backup = _nova_pasta_backup(pasta_app, versao_instalada(pasta_app))
        pacote_bk = os.path.join(backup, PACOTE)
        if os.path.isdir(pacote):
            _mover(pacote, pacote_bk)
        _mover(os.path.join(staging, PACOTE), pacote)
        novo_instalado = True
        for arq in info.arquivos_apoio:
            destino = os.path.join(pasta_app, arq)
            apoio_guardado[arq] = os.path.exists(destino)
            if apoio_guardado[arq]:
                shutil.copy2(destino, os.path.join(backup, arq))
            shutil.copy2(os.path.join(staging, arq), destino)
        marcar_nao_validada(pasta_app, info.versao)
    except ErroAtualizacao:
        _desfazer(pacote, backup, novo_instalado, apoio_guardado, pasta_app)
        raise
    except Exception as e:
        log.exception("Falha ao aplicar a atualização; revertendo")
        _desfazer(pacote, backup, novo_instalado, apoio_guardado, pasta_app)
        raise ErroAtualizacao(str(e)) from e
    finally:
        shutil.rmtree(staging, ignore_errors=True)
    _podar_backups(pasta_app, manter_backups)
    return info


def _desfazer(pacote: str, backup: str, novo_instalado: bool, apoio_guardado: Dict[str, bool],
              pasta_app: str) -> None:
    """Volta ao estado anterior à tentativa de atualização."""
    try:
        if backup:
            pacote_bk = os.path.join(backup, PACOTE)
            if novo_instalado and os.path.isdir(pacote):
                shutil.rmtree(pacote, ignore_errors=True)
            if os.path.isdir(pacote_bk) and not os.path.exists(pacote):
                _mover(pacote_bk, pacote)
            for arq, existia in apoio_guardado.items():
                guardado = os.path.join(backup, arq)
                if existia and os.path.exists(guardado):
                    shutil.copy2(guardado, os.path.join(pasta_app, arq))
            shutil.rmtree(backup, ignore_errors=True)
    except Exception:
        log.exception("Falha ao reverter a atualização")


def restaurar_versao_anterior(pasta_app: str) -> str:
    """Volta para a versão guardada mais recente. A versão atual vira o novo backup. Devolve a versão."""
    if modo_empacotado():
        raise ErroAtualizacao(t("atu.erro.empacotado"))
    anterior = backup_mais_recente(pasta_app)
    if anterior is None:
        raise ErroAtualizacao(t("atu.sem_backup"))
    versao_restaurada = versao_do_backup(anterior)
    pacote = os.path.join(pasta_app, PACOTE)
    bk_atual = _nova_pasta_backup(pasta_app, versao_instalada(pasta_app))
    try:
        if os.path.isdir(pacote):
            _mover(pacote, os.path.join(bk_atual, PACOTE))
        _mover(os.path.join(anterior, PACOTE), pacote)
    except Exception as e:
        log.exception("Falha ao restaurar a versão anterior; revertendo")
        if not os.path.exists(pacote) and os.path.isdir(os.path.join(bk_atual, PACOTE)):
            _mover(os.path.join(bk_atual, PACOTE), pacote)
        raise ErroAtualizacao(str(e)) from e
    for arq in ARQUIVOS_DE_APOIO:                     # restaura também os arquivos de apoio da época
        guardado = os.path.join(anterior, arq)
        if os.path.exists(guardado):
            shutil.copy2(guardado, os.path.join(pasta_app, arq))
    shutil.rmtree(anterior, ignore_errors=True)
    confirmar_inicializacao(pasta_app)
    _podar_backups(pasta_app)
    return versao_restaurada


# ---------------------------------------------------------------------------
# Reinício
# ---------------------------------------------------------------------------
def comando_reinicio(pasta_app: str, congelado: Optional[bool] = None,
                     executavel: Optional[str] = None) -> List[str]:
    """Comando que abre o app de novo: o próprio .exe (congelado) ou `python app.py`."""
    congelado = bool(getattr(sys, "frozen", False)) if congelado is None else congelado
    executavel = executavel or sys.executable
    return [executavel] if congelado else [executavel, os.path.join(pasta_app, "app.py")]


def reiniciar_app(pasta_app: str, argumentos: Sequence[str] = ()) -> None:
    """Abre uma nova instância do app, independente desta (que deve ser encerrada em seguida)."""
    comando = comando_reinicio(pasta_app) + list(argumentos)
    ambiente = dict(os.environ)
    ambiente.pop("_MEIPASS2", None)                       # .exe "onefile": a nova instância extrai a própria cópia
    ambiente["PYINSTALLER_RESET_ENVIRONMENT"] = "1"
    flags = 0
    if os.name == "nt":
        flags = getattr(subprocess, "DETACHED_PROCESS", 0) | getattr(subprocess, "CREATE_NEW_PROCESS_GROUP", 0)
    subprocess.Popen(comando, cwd=pasta_app, env=ambiente, close_fds=True, creationflags=flags)
