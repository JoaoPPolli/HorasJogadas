"""Inicialização do aplicativo (chamada pelo lançador `app.py`)."""
import logging
import os
import tkinter as tk
from tkinter import messagebox
from typing import Optional, Sequence

from . import __version__, instancia, updater
from .constants import DATA_DIR
from .i18n import t
from .logging_setup import configurar_logging
from .ui.main_window import App
from .utils import pasta_do_app, resource_path

log = logging.getLogger(__name__)


def _valor_do_argumento(argv: Sequence[str], nome: str) -> Optional[str]:
    """Valor que vem depois de `nome` na linha de comando (ex.: --atualizado 2.1.0)."""
    if nome in argv:
        i = list(argv).index(nome)
        if i + 1 < len(argv):
            return argv[i + 1]
    return None


def _definir_icone(root: tk.Tk) -> None:
    """Usa `icon.ico` ao lado do app (ou embutido) em todas as janelas; sem ele, segue com o ícone padrão."""
    for caminho in (os.path.join(pasta_do_app(), "icon.ico"), resource_path("icon.ico")):
        if os.path.exists(caminho):
            for tentativa in (lambda: root.iconbitmap(default=caminho), lambda: root.iconbitmap(caminho)):
                try:
                    tentativa()
                    return
                except tk.TclError:
                    continue


def executar(argv: Optional[Sequence[str]] = None) -> None:
    """Abre a janela principal e roda o app até ser fechado."""
    argv = list(argv or [])
    configurar_logging(DATA_DIR)
    # Logo após reiniciar (atualização/restauração) a instância anterior ainda está encerrando: espera um pouco.
    reinicio = "--atualizado" in argv or "--reiniciado" in argv
    trava = instancia.TravaInstancia(DATA_DIR)
    if not trava.adquirir(espera=4.0 if reinicio else 0.0):
        log.info("O app já está aberto; pedindo à janela existente que venha para a frente")
        instancia.sinalizar_mostrar(DATA_DIR)
        return
    try:
        log.info("Aplicativo iniciado (versão %s)", __version__)
        root = tk.Tk()
        _definir_icone(root)
        App(root, trava=trava)
        updater.confirmar_inicializacao(pasta_do_app())  # chegou até aqui: a versão (nova) funciona
        versao_nova = _valor_do_argumento(argv, "--atualizado")
        if versao_nova:
            root.after(500, lambda: messagebox.showinfo(t("atu.titulo"), t("atu.concluida", versao=versao_nova)))
        root.mainloop()
    finally:
        trava.liberar()
