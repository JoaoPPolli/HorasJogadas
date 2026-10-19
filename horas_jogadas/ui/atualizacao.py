"""Telas de atualização do app (escolher ZIP) e de restauração da versão anterior."""
import logging
import os
import tkinter as tk
from tkinter import filedialog, messagebox
from typing import TYPE_CHECKING

from .. import updater
from ..i18n import t
from ..utils import pasta_do_app

if TYPE_CHECKING:
    from .main_window import App

log = logging.getLogger(__name__)


def _pasta_downloads() -> str:
    downloads = os.path.join(os.path.expanduser("~"), "Downloads")
    return downloads if os.path.isdir(downloads) else os.path.expanduser("~")


def _reiniciar(app: "App", versao: str, parent: tk.Misc) -> None:
    """Abre uma nova instância (já com o código novo) e encerra esta."""
    app.repo.limpar_andamento()
    app.liberar_instancia()                               # senão a nova instância acharia que já há outra aberta
    try:
        updater.reiniciar_app(pasta_do_app(), ["--atualizado", versao])
    except OSError:
        log.exception("Não foi possível reabrir o app automaticamente")
        messagebox.showinfo(t("atu.titulo"), t("atu.reabrir", versao=versao), parent=parent)
    app.root.destroy()


def iniciar_atualizacao(app: "App", parent: tk.Misc) -> None:
    """Fluxo completo: escolher o ZIP, validar, confirmar, instalar e reiniciar."""
    caminho = filedialog.askopenfilename(
        parent=parent, title=t("atu.escolher"), initialdir=_pasta_downloads(),
        filetypes=[(t("atu.filtro_zip"), "*.zip"), (t("atu.todos"), "*.*")])
    if not caminho:
        return
    pasta = pasta_do_app()
    try:
        info = updater.inspecionar_zip(caminho)
    except updater.ErroAtualizacao as e:
        messagebox.showerror(t("atu.titulo"), t("atu.invalido", erro=e), parent=parent)
        return

    atual = updater.versao_instalada(pasta)
    comparacao = updater.comparar_versoes(info.versao, atual)
    if comparacao == 0:
        pergunta = t("atu.mesma", nova=info.versao)
    elif comparacao < 0:
        pergunta = t("atu.antiga", nova=info.versao, atual=atual)
    else:
        pergunta = t("atu.confirma", atual=atual, nova=info.versao)
    if not messagebox.askyesno(t("atu.titulo"), pergunta, parent=parent):
        return
    if not app.resolver_sessoes_pendentes("atu.sessoes.titulo", "atu.sessoes.msg"):
        return
    try:
        updater.aplicar_zip(caminho, pasta)
    except updater.ErroAtualizacao as e:
        messagebox.showerror(t("atu.titulo"), t("atu.falha", erro=e), parent=parent)
        return
    _reiniciar(app, info.versao, parent)


def restaurar_versao(app: "App", parent: tk.Misc) -> None:
    """Volta para a versão guardada antes da última atualização."""
    pasta = pasta_do_app()
    anterior = updater.backup_mais_recente(pasta)
    if anterior is None:
        messagebox.showinfo(t("atu.titulo"), t("atu.sem_backup"), parent=parent)
        return
    versao = updater.versao_do_backup(anterior)
    if not messagebox.askyesno(
            t("atu.titulo"), t("atu.restaurar_confirma", versao=versao, atual=updater.versao_instalada(pasta)),
            parent=parent):
        return
    if not app.resolver_sessoes_pendentes("atu.sessoes.titulo", "atu.sessoes.msg"):
        return
    try:
        updater.restaurar_versao_anterior(pasta)
    except updater.ErroAtualizacao as e:
        messagebox.showerror(t("atu.titulo"), t("atu.falha", erro=e), parent=parent)
        return
    _reiniciar(app, versao, parent)
