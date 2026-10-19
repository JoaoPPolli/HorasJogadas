"""Exportação para CSV e tela de backups."""
import logging
import os
import tkinter as tk
from datetime import date
from tkinter import filedialog, messagebox, ttk
from typing import TYPE_CHECKING, Callable

from .. import exportacao, updater
from ..backups import ErroBackup, InfoBackup
from ..i18n import t
from ..utils import formatar_duracao, pasta_do_app
from .widgets import ScrollableFrame

if TYPE_CHECKING:
    from .main_window import App

log = logging.getLogger(__name__)


def _pasta_inicial() -> str:
    documentos = os.path.join(os.path.expanduser("~"), "Documents")
    return documentos if os.path.isdir(documentos) else os.path.expanduser("~")


# ---------------------------------------------------------------------------
# CSV
# ---------------------------------------------------------------------------
def _exportar(app: "App", parent: tk.Misc, chave_arquivo: str, funcao: Callable) -> None:
    sugerido = f"horas_jogadas_{t(chave_arquivo)}_{date.today():%Y-%m-%d}.csv"
    caminho = filedialog.asksaveasfilename(
        parent=parent, title=t("dados.salvar_como"), initialdir=_pasta_inicial(), initialfile=sugerido,
        defaultextension=".csv", filetypes=[(t("csv.filtro"), "*.csv")])
    if not caminho:
        return
    try:
        linhas = funcao(caminho, list(app.repo.jogos), list(app.repo.sessoes))
    except OSError as e:
        log.exception("Falha ao exportar CSV")
        messagebox.showerror(t("dlg.erro"), t("dados.csv_erro", erro=e), parent=parent)
        return
    messagebox.showinfo(t("dlg.sucesso"), t("dados.csv_salvo", caminho=caminho, linhas=linhas), parent=parent)


def exportar_historico_csv(app: "App", parent: tk.Misc) -> None:
    _exportar(app, parent, "csv.arquivo_historico", exportacao.exportar_historico)


def exportar_resumo_csv(app: "App", parent: tk.Misc) -> None:
    _exportar(app, parent, "csv.arquivo_resumo", exportacao.exportar_resumo)


# ---------------------------------------------------------------------------
# Backups
# ---------------------------------------------------------------------------
def _reiniciar_app(app: "App", parent: tk.Misc) -> None:
    """Abre uma nova instância (que recarrega os dados restaurados) e encerra esta."""
    app.repo.limpar_andamento()
    app.liberar_instancia()
    try:
        updater.reiniciar_app(pasta_do_app(), ["--reiniciado"])
    except OSError:
        log.exception("Não foi possível reabrir o app automaticamente")
        messagebox.showinfo(t("dlg.sucesso"), t("bk.reabrir"), parent=parent)
    app.root.destroy()


def abrir_backups(app: "App") -> None:
    parent, is_toplevel = app.preparar_janela_ou_frame(t("bk.titulo"))
    if is_toplevel:
        parent.geometry("640x560")

    topo = ttk.Frame(parent)
    topo.pack(fill="x", padx=12, pady=10)
    ttk.Label(topo, text=t("bk.ajuda"), style="Small.TLabel", wraplength=440, justify="left").pack(
        side="left", fill="x", expand=True)
    area = ScrollableFrame(parent, app.scroll)
    area.pack(fill="both", expand=True, padx=8, pady=8)

    def descricao(info: InfoBackup) -> str:
        formato = "fmt.data" if info.tipo == "diario" else "fmt.data_hora"
        return info.momento.strftime(t(formato))

    def resumo(info: InfoBackup) -> str:
        return t("bk.resumo", jogos=info.jogos, sessoes=info.sessoes, total=formatar_duracao(info.total_segundos))

    def renderizar() -> None:
        area.limpar()
        lista = app.repo.listar_backups()
        if not lista:
            ttk.Label(area.interior, text=t("bk.vazio"), style="Small.TLabel", wraplength=480,
                      font=("Segoe UI", 11)).pack(pady=40, padx=20)
            return
        for info in lista:
            bloco = ttk.Frame(area.interior, style="Card.TFrame", padding=8)
            bloco.pack(fill="x", pady=6, padx=6)
            bloco.grid_columnconfigure(0, weight=1)
            ttk.Label(bloco, text=f"🗂  {descricao(info)}", font=("Segoe UI", 10, "bold"),
                      style="Card.TLabel").grid(row=0, column=0, sticky="w")
            ttk.Label(bloco, text=t(f"bk.tipo.{info.tipo}"), style="CardSmall.TLabel").grid(row=1, column=0, sticky="w")
            ttk.Label(bloco, text=resumo(info), style="CardSmall.TLabel").grid(row=2, column=0, sticky="w")
            ttk.Button(bloco, text=t("bk.restaurar"), width=12,
                       command=lambda i=info: restaurar(i)).grid(row=0, column=1, rowspan=3, sticky="e", padx=6)

    def criar_agora() -> None:
        try:
            caminho = app.repo.criar_backup_manual()
        except OSError as e:
            log.exception("Falha ao criar backup manual")
            messagebox.showerror(t("dlg.erro"), t("dados.csv_erro", erro=e), parent=parent)
            return
        messagebox.showinfo(t("bk.titulo"), t("bk.criado") if caminho else t("bk.nada_para_copiar"), parent=parent)
        renderizar()

    def restaurar(info: InfoBackup) -> None:
        if not messagebox.askyesno(
                t("dlg.confirmar"), t("bk.restaurar_confirma", data=descricao(info), resumo=resumo(info)), parent=parent):
            return
        if not app.resolver_sessoes_pendentes("bk.sessoes.titulo", "bk.sessoes.msg"):
            return
        try:
            app.repo.restaurar_backup(info)
        except (ErroBackup, OSError) as e:
            log.exception("Falha ao restaurar backup")
            messagebox.showerror(t("dlg.erro"), t("bk.falha", erro=e), parent=parent)
            return
        _reiniciar_app(app, parent)

    ttk.Button(topo, text=t("bk.criar_agora"), command=criar_agora).pack(side="right", padx=(10, 0))
    renderizar()
