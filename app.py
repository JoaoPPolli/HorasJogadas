"""Registro de Horas Jogadas — lançador.

Este arquivo é só a "porta de entrada". Todo o código do app fica na pasta `horas_jogadas/`,
ao lado dele, e é essa pasta que o botão "Atualizar app…" (Configurações) substitui.
Por isso o .exe gerado a partir deste arquivo não precisa ser refeito a cada atualização.

Execute com:  python app.py   (ou dê dois cliques no HorasJogadas.exe)
"""
import importlib
import os
import shutil
import subprocess
import sys
import traceback

# --- Bibliotecas do Python que o app usa --------------------------------------------------------
# O PyInstaller só inclui no .exe o que enxerga aqui. Como o código do app é carregado dinamicamente
# (para poder ser atualizado sem refazer o .exe), as dependências são listadas explicitamente.
# O teste tests/test_launcher.py garante que esta lista cobre tudo o que o app importa.
import __future__  # noqa: F401,E402
import calendar  # noqa: F401,E402
import collections  # noqa: F401,E402
import csv  # noqa: F401,E402
import ctypes  # noqa: F401,E402
try:
    import ctypes.wintypes  # noqa: F401,E402  (selo da barra de tarefas; só o Windows tem tudo)
except (ImportError, ValueError):
    pass
import dataclasses  # noqa: F401,E402
import datetime  # noqa: F401,E402
import json  # noqa: F401,E402
import logging  # noqa: F401,E402
import logging.handlers  # noqa: F401,E402
import math  # noqa: F401,E402
import random  # noqa: F401,E402
import re  # noqa: F401,E402
import string  # noqa: F401,E402
import struct  # noqa: F401,E402
import tempfile  # noqa: F401,E402
import threading  # noqa: F401,E402
import time  # noqa: F401,E402
import typing  # noqa: F401,E402
import unicodedata  # noqa: F401,E402
import uuid  # noqa: F401,E402
import zipfile  # noqa: F401,E402
try:                              # trava de instância única: cada sistema usa um destes (o outro não existe)
    import msvcrt  # noqa: F401,E402  (Windows)
except ImportError:
    pass
try:
    import fcntl  # noqa: F401,E402  (Linux/macOS)
except ImportError:
    pass
import tkinter  # noqa: F401,E402
import tkinter.filedialog  # noqa: F401,E402
import tkinter.font  # noqa: F401,E402
import tkinter.messagebox  # noqa: F401,E402
import tkinter.simpledialog  # noqa: F401,E402
import tkinter.ttk  # noqa: F401,E402

PACOTE = "horas_jogadas"
PASTA_BACKUPS = "_versoes_anteriores"
MARCADOR = ".nova_versao_nao_validada"        # mesmo nome usado por horas_jogadas/constants.py
MARCADOR_EMPACOTADO = "empacotado.flag"       # idem: presente só no .exe de distribuição (itch.io)


def pasta_base() -> str:
    """Pasta do app: a do .exe (congelado) ou a deste arquivo."""
    if getattr(sys, "frozen", False):
        return os.path.dirname(os.path.abspath(sys.executable))
    return os.path.dirname(os.path.abspath(__file__))


def empacotado() -> bool:
    """True no .exe de distribuição (itch.io): o código do app está DENTRO do executável."""
    base = getattr(sys, "_MEIPASS", None)
    return bool(getattr(sys, "frozen", False) and base and os.path.exists(os.path.join(base, MARCADOR_EMPACOTADO)))


def verificar(destino: str, criar_janela: bool = True) -> int:
    """Autoteste usado pelo build: importa o app inteiro e (opcional) abre/fecha uma janela Tk.

    Grava o resultado em `destino` ("OK ..." ou o erro) e devolve o código de saída (0 = tudo certo).
    Pega na hora um .exe quebrado (biblioteca faltando, dados do Tcl/Tk ausentes etc.).
    """
    try:
        importlib.import_module(PACOTE + ".main")
        versao = importlib.import_module(PACOTE).__version__
        if criar_janela:
            raiz = tkinter.Tk()
            raiz.withdraw()
            raiz.update()
            raiz.destroy()
        texto, codigo = f"OK versao={versao} empacotado={empacotado()}", 0
    except Exception:                               # noqa: BLE001
        texto, codigo = "ERRO\n" + traceback.format_exc(), 1
    try:
        with open(destino, "w", encoding="utf-8") as f:
            f.write(texto)
    except OSError:
        pass
    return codigo


# --- Recuperação: se uma versão recém-instalada nem abre, volta para a anterior ----------------
def backup_mais_recente(base: str):
    raiz = os.path.join(base, PASTA_BACKUPS)
    if not os.path.isdir(raiz):
        return None
    nomes = sorted(n for n in os.listdir(raiz) if os.path.isdir(os.path.join(raiz, n, PACOTE)))
    return os.path.join(raiz, nomes[-1]) if nomes else None


def restaurar_backup(base: str) -> bool:
    """Troca a versão com falha pelo backup mais recente. A versão com falha é descartada."""
    backup = backup_mais_recente(base)
    if backup is None:
        return False
    pacote = os.path.join(base, PACOTE)
    com_falha = os.path.join(base, PASTA_BACKUPS, "_versao_com_falha")
    shutil.rmtree(com_falha, ignore_errors=True)
    if os.path.isdir(pacote):
        shutil.move(pacote, com_falha)
    shutil.move(os.path.join(backup, PACOTE), pacote)
    for arq in os.listdir(backup):                  # arquivos de apoio guardados (app.py etc.)
        origem = os.path.join(backup, arq)
        if os.path.isfile(origem):
            shutil.copy2(origem, os.path.join(base, arq))
    shutil.rmtree(backup, ignore_errors=True)
    try:
        os.remove(os.path.join(base, PASTA_BACKUPS, MARCADOR))
    except OSError:
        pass
    return True


def _perguntar_restaurar(erro: str) -> bool:
    from tkinter import messagebox
    raiz = tkinter.Tk()
    raiz.withdraw()
    try:
        return messagebox.askyesno(
            "Falha ao iniciar / Failed to start",
            "A versão nova do app não conseguiu abrir.\nThe new app version failed to start.\n\n"
            f"{erro}\n\nRestaurar a versão anterior? / Restore the previous version?")
    finally:
        raiz.destroy()


def _mostrar_erro(texto: str) -> None:
    from tkinter import messagebox
    raiz = tkinter.Tk()
    raiz.withdraw()
    try:
        messagebox.showerror("Erro ao iniciar / Startup error", texto)
    finally:
        raiz.destroy()


def _reiniciar(base: str) -> None:
    comando = [sys.executable] if getattr(sys, "frozen", False) else [sys.executable, os.path.join(base, "app.py")]
    ambiente = dict(os.environ)
    ambiente.pop("_MEIPASS2", None)
    ambiente["PYINSTALLER_RESET_ENVIRONMENT"] = "1"
    subprocess.Popen(comando, cwd=base, env=ambiente, close_fds=True)


def tratar_falha(base: str, detalhes: str, perguntar=_perguntar_restaurar, mostrar=_mostrar_erro,
                 reiniciar=_reiniciar) -> str:
    """Decide o que fazer quando o app não consegue iniciar. Devolve 'restaurado' ou 'erro'."""
    try:
        with open(os.path.join(base, "erro_ao_iniciar.log"), "w", encoding="utf-8") as f:
            f.write(detalhes)
    except OSError:
        pass
    ultima_linha = detalhes.strip().splitlines()[-1] if detalhes.strip() else "?"
    # só oferece voltar atrás se acabou de ser instalada uma versão ainda não validada
    if os.path.exists(os.path.join(base, PASTA_BACKUPS, MARCADOR)) and backup_mais_recente(base):
        if perguntar(ultima_linha):
            if restaurar_backup(base):
                reiniciar(base)
                return "restaurado"
    mostrar(f"{ultima_linha}\n\nDetalhes / Details: {os.path.join(base, 'erro_ao_iniciar.log')}")
    return "erro"


def main() -> None:
    base = pasta_base()
    if not empacotado() and base not in sys.path:
        sys.path.insert(0, base)                    # modo normal: o código vem da pasta ao lado do .exe
    # (no modo empacotado o código vem de dentro do .exe: uma pasta solta ao lado dele é ignorada de propósito)
    if "--verificar" in sys.argv:
        i = sys.argv.index("--verificar")
        destino = sys.argv[i + 1] if i + 1 < len(sys.argv) else os.path.join(base, "verificacao.txt")
        sys.exit(verificar(destino))
    try:
        importlib.import_module(PACOTE + ".main").executar(sys.argv[1:])
    except Exception:                               # noqa: BLE001 - qualquer falha de inicialização
        tratar_falha(base, traceback.format_exc())


if __name__ == "__main__":
    main()
