"""Tela de configurações."""
import tkinter as tk
from tkinter import messagebox, ttk
from typing import TYPE_CHECKING

from .. import __version__, i18n, updater
from ..constants import IDIOMAS_DISPONIVEIS
from ..i18n import t
from ..utils import modo_empacotado, pasta_do_app
from .atualizacao import iniciar_atualizacao, restaurar_versao
from .dados import abrir_backups, exportar_historico_csv, exportar_resumo_csv
from .widgets import ScrollableFrame

if TYPE_CHECKING:
    from .main_window import App


def abrir_configuracao(app: "App") -> None:
    parent, is_toplevel = app.preparar_janela_ou_frame(t("tela.config"))
    if is_toplevel:
        parent.geometry("460x700")
    area = ScrollableFrame(parent, app.scroll)               # rola se a tela for pequena
    area.pack(fill="both", expand=True)
    container = area.interior

    negrito = ("Segoe UI", 10, "bold")
    ttk.Label(container, text=t("cfg.modo"), font=negrito).pack(pady=(20, 8))
    var_modo = tk.StringVar(value=app.config.get("modo_navegacao", "janelas"))
    frame_modo = ttk.Frame(container)
    frame_modo.pack(pady=4)
    ttk.Radiobutton(frame_modo, text=t("cfg.janelas"), variable=var_modo, value="janelas").pack(anchor="w", pady=2)
    ttk.Radiobutton(frame_modo, text=t("cfg.navegacao"), variable=var_modo, value="navegacao").pack(anchor="w", pady=2)

    ttk.Label(container, text=t("cfg.idioma"), font=negrito).pack(pady=(18, 8))
    var_idioma = tk.StringVar(value=app.config.get("idioma", i18n.idioma_atual()))
    frame_idioma = ttk.Frame(container)
    frame_idioma.pack(pady=4)
    for codigo, nome in IDIOMAS_DISPONIVEIS.items():          # cada idioma escrito em si mesmo
        ttk.Radiobutton(frame_idioma, text=nome, variable=var_idioma, value=codigo).pack(anchor="w", pady=2)

    def salvar() -> None:
        idioma_mudou = var_idioma.get() != app.config.get("idioma")
        app.config["modo_navegacao"] = var_modo.get()
        app.config["idioma"] = var_idioma.get()
        app.repo.salvar_config(app.config)
        if idioma_mudou:
            i18n.definir_idioma(var_idioma.get())             # a mensagem abaixo já sai no novo idioma
        messagebox.showinfo(t("dlg.sucesso"), t("cfg.salva"), parent=parent if is_toplevel else None)
        if is_toplevel:
            parent.destroy()
        if idioma_mudou:
            app.aplicar_idioma()
        if not is_toplevel:
            app.mostrar_home()

    ttk.Button(container, text=t("btn.salvar"), style="Accent.TButton", command=salvar).pack(pady=(18, 8))

    # --- Dados e backups ---
    ttk.Separator(container, orient="horizontal").pack(fill="x", padx=30, pady=10)
    ttk.Label(container, text=t("dados.titulo"), font=negrito).pack(pady=(4, 6))
    quadro_dados = ttk.Frame(container)
    quadro_dados.pack(pady=4)
    ttk.Button(quadro_dados, text=t("dados.exportar_historico"),
               command=lambda: exportar_historico_csv(app, parent)).pack(pady=3, fill="x")
    ttk.Button(quadro_dados, text=t("dados.exportar_resumo"),
               command=lambda: exportar_resumo_csv(app, parent)).pack(pady=3, fill="x")
    ttk.Button(quadro_dados, text=t("dados.backups"), command=lambda: abrir_backups(app)).pack(pady=3, fill="x")

    # --- Versão e atualização do app ---
    ttk.Separator(container, orient="horizontal").pack(fill="x", padx=30, pady=10)
    ttk.Label(container, text=t("cfg.versao", versao=__version__), style="Small.TLabel").pack()
    if modo_empacotado():                                     # versão do itch.io: atualiza pelo itch.io
        ttk.Label(container, text=t("cfg.atualizacoes_itch"), style="Small.TLabel", justify="center").pack(pady=8)
    else:
        quadro = ttk.Frame(container)
        quadro.pack(pady=8)
        ttk.Button(quadro, text=t("cfg.atualizar"), command=lambda: iniciar_atualizacao(app, parent)).pack(pady=3, fill="x")
        if updater.tem_backup(pasta_do_app()):
            ttk.Button(quadro, text=t("cfg.restaurar"), command=lambda: restaurar_versao(app, parent)).pack(pady=3, fill="x")
    ttk.Frame(container, height=16).pack()
