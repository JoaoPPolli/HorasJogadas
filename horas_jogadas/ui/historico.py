"""Tela de histórico de sessões (com paginação e exclusão estável por id)."""
from tkinter import messagebox, ttk
from typing import TYPE_CHECKING, Dict, List, Tuple

from ..constants import TAMANHO_PAGINA_HISTORICO
from ..edicao_sessao import LIMITE_AVISO_S
from ..i18n import t
from ..models import Sessao
from .dados import exportar_historico_csv
from .sessao_dialogo import abrir_dialogo_sessao
from .pagina_desenhada import PaginaDesenhada

if TYPE_CHECKING:
    from .main_window import App


def abrir_historico(app: "App") -> None:
    parent, _is_toplevel = app.preparar_janela_ou_frame(t("tela.historico"))

    topo = ttk.Frame(parent)
    topo.pack(fill="x", pady=8, padx=8)
    area = PaginaDesenhada(parent, app.scroll)
    area.pack(fill="both", expand=True, padx=(8, 0), pady=(6, 8))

    sessoes: List[Sessao] = []                 # snapshot, da mais recente para a mais antiga
    estado: Dict[str, object] = {"mostradas": TAMANHO_PAGINA_HISTORICO, "timer": None}
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

    def anexar_pagina() -> None:
        estado['mostradas'] = int(estado['mostradas']) + TAMANHO_PAGINA_HISTORICO
        area.atualizar()

    def pintar(p):
        if not sessoes:
            p.titulo(t('hist.vazio'))
        for sessao in sessoes[:int(estado['mostradas'])]:
            aviso = f"   {t('hist.longa_aviso')}" if sessao.segundos > LIMITE_AVISO_S else ''
            p.cartao(f"🎮  {sessao.jogo or t('hist.sem_nome')}",
                     [f"⏱  {sessao.tempo or '00:00:00'}{aviso}", f'📅  {sessao.data}'],
                     [(t('hist.editar'), lambda s=sessao: abrir_dialogo_sessao(app, parent, s, renderizar)),
                      (t('btn.excluir'), lambda s=sessao: excluir(s))])
        restantes = len(sessoes) - int(estado['mostradas'])
        if restantes > 0:
            p.botao(12, p.y, t('hist.mais', n=restantes), anexar_pagina)
            p.y += 42

    def renderizar() -> None:
        sessoes[:] = list(reversed(app.repo.sessoes))
        estado['mostradas'] = TAMANHO_PAGINA_HISTORICO
        area.atualizar()

    def excluir(sessao: Sessao) -> None:
        try:
            indice = app.repo.sessoes.index(sessao)
        except ValueError:
            indice = len(app.repo.sessoes)
        if app.repo.remover_sessao(sessao.sessao_id):
            excluidas.append((indice, sessao))
            if sessao in sessoes:
                sessoes.remove(sessao)
            app.recarregar_totais()
            mostrar_barra()
            area.atualizar()

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
    area.mostrar(pintar)
