"""Tela de histórico de sessões (com paginação e exclusão estável por id)."""
import tkinter as tk
from tkinter import messagebox, ttk
from typing import TYPE_CHECKING, Dict, List, Tuple

from ..constants import TAMANHO_PAGINA_HISTORICO
from ..edicao_sessao import LIMITE_AVISO_S
from ..i18n import t
from ..models import Sessao
from .dados import exportar_historico_csv
from .sessao_dialogo import abrir_dialogo_sessao
from .widgets import ScrollableFrame

if TYPE_CHECKING:
    from .main_window import App


def abrir_historico(app: "App") -> None:
    parent, _is_toplevel = app.preparar_janela_ou_frame(t("tela.historico"))

    topo = ttk.Frame(parent)
    topo.pack(fill="x", pady=8, padx=8)
    area = ScrollableFrame(parent, app.scroll)
    area.pack(fill="both", expand=True, padx=(8, 0), pady=(6, 8))

    sessoes: List[Sessao] = []                 # snapshot, da mais recente para a mais antiga
    estado: Dict[str, object] = {"mostradas": 0, "botao_mais": None, "timer": None}
    excluidas: List[Tuple[int, Sessao]] = []   # pilha do "Desfazer" (posição original, sessão)

    # Barra "Sessão excluída. [Desfazer]" (aparece por alguns segundos após cada exclusão)
    barra = ttk.Frame(parent, style="Card.TFrame", padding=6)
    lbl_desfazer = ttk.Label(barra, text="", style="Card.TLabel")
    lbl_desfazer.pack(side="left", padx=6)

    def esconder_barra() -> None:
        excluidas.clear()
        estado["timer"] = None
        if barra.winfo_exists():                      # a janela pode ter sido fechada antes do prazo
            barra.pack_forget()

    def mostrar_barra() -> None:
        n = len(excluidas)
        lbl_desfazer.config(text=t("hist.excluida") if n == 1 else t("hist.excluidas", n=n))
        barra.pack(fill="x", padx=8, pady=(0, 4), before=area)
        if estado["timer"] is not None:
            parent.after_cancel(estado["timer"])
        estado["timer"] = parent.after(10000, esconder_barra)

    def desfazer() -> None:
        if not excluidas:
            return
        indice, sessao = excluidas.pop()
        app.repo.inserir_sessao(indice, sessao)
        app.recarregar_totais()
        renderizar()
        if excluidas:
            mostrar_barra()
        else:
            if estado["timer"] is not None:
                parent.after_cancel(estado["timer"])
            esconder_barra()

    ttk.Button(barra, text=t("hist.desfazer"), style="Accent.TButton", command=desfazer).pack(side="right")

    def criar_bloco(sessao: Sessao) -> None:
        bloco = ttk.Frame(area.interior, style="Card.TFrame", padding=8)
        bloco.pack(fill="x", pady=6, padx=6)
        bloco.grid_columnconfigure(0, weight=1)
        ttk.Label(bloco, text=f"🎮  {sessao.jogo or t('hist.sem_nome')}", font=("Segoe UI", 10, "bold"),
                  style="Card.TLabel").grid(row=0, column=0, sticky="w")
        aviso = f"   {t('hist.longa_aviso')}" if sessao.segundos > LIMITE_AVISO_S else ""
        ttk.Label(bloco, text=f"⏱  {sessao.tempo or '00:00:00'}{aviso}",
                  style="CardSmall.TLabel").grid(row=1, column=0, sticky="w")
        ttk.Label(bloco, text=f"📅  {sessao.data}", style="CardSmall.TLabel").grid(row=2, column=0, sticky="w")
        acoes = ttk.Frame(bloco, style="Card.TFrame")
        acoes.grid(row=0, column=1, rowspan=3, sticky="e", padx=6)
        ttk.Button(acoes, text=t("hist.editar"), width=10,
                   command=lambda: abrir_dialogo_sessao(app, parent, sessao, renderizar)).pack(pady=(0, 3))
        ttk.Button(acoes, text=t("btn.excluir"), width=10,
                   command=lambda: excluir(sessao, bloco)).pack()

    def anexar_pagina() -> None:
        if estado["botao_mais"] is not None:
            estado["botao_mais"].destroy()
            estado["botao_mais"] = None
        inicio = int(estado["mostradas"])
        for sessao in sessoes[inicio:inicio + TAMANHO_PAGINA_HISTORICO]:
            criar_bloco(sessao)
        estado["mostradas"] = min(len(sessoes), inicio + TAMANHO_PAGINA_HISTORICO)
        restantes = len(sessoes) - int(estado["mostradas"])
        if restantes > 0:
            botao = ttk.Button(area.interior, text=t("hist.mais", n=restantes),
                               command=anexar_pagina)
            botao.pack(pady=10)
            estado["botao_mais"] = botao

    def renderizar() -> None:
        area.limpar()
        sessoes[:] = list(reversed(app.repo.sessoes))
        estado["mostradas"], estado["botao_mais"] = 0, None
        if not sessoes:
            ttk.Label(area.interior, text=t("hist.vazio"), style="Small.TLabel",
                      font=("Segoe UI", 11)).pack(pady=40)
            return
        anexar_pagina()

    def excluir(sessao: Sessao, bloco: tk.Misc) -> None:
        try:
            indice = app.repo.sessoes.index(sessao)
        except ValueError:
            indice = len(app.repo.sessoes)
        if app.repo.remover_sessao(sessao.sessao_id):
            excluidas.append((indice, sessao))
            if sessao in sessoes:
                sessoes.remove(sessao)
                estado["mostradas"] = int(estado["mostradas"]) - 1
            bloco.destroy()
            app.recarregar_totais()
            mostrar_barra()
            if not sessoes:
                renderizar()

    def apagar_tudo() -> None:
        if messagebox.askyesno(t("dlg.confirmar"), t("hist.apagar_tudo_confirma"), parent=parent):
            app.repo.limpar_sessoes()                 # guarda um backup automático antes de apagar
            app.recarregar_totais()
            if estado["timer"] is not None:
                parent.after_cancel(estado["timer"])
            esconder_barra()                          # desfazer exclusões antigas não faz mais sentido
            renderizar()

    ttk.Button(topo, text=t("hist.adicionar"),
               command=lambda: abrir_dialogo_sessao(app, parent, None, renderizar)).pack(side="left", padx=(0, 8))
    ttk.Button(topo, text=t("dados.exportar_historico"),
               command=lambda: exportar_historico_csv(app, parent)).pack(side="left", padx=(0, 8))
    ttk.Button(topo, text=t("hist.apagar_tudo"), style="Danger.TButton",
               command=apagar_tudo).pack(side="left")
    renderizar()
