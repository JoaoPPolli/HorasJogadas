"""Dashboard: resumo da biblioteca, gráfico por período, top jogos e lista por jogo."""
import tkinter as tk
import tkinter.font as tkfont
from collections import Counter
from datetime import date
from tkinter import messagebox, ttk
from typing import TYPE_CHECKING, Dict, List, Optional, Sequence, Tuple

from .. import stats
from ..constants import (
    COR_ACCENT, COR_BTN, COR_CARD, COR_TEXTO, COR_TEXTO_SUAVE, FILTROS_STATUS, STATUS_OPCOES,
)
from ..i18n import lista, rotulo_filtro, t, t_status
from ..models import Sessao
from ..utils import ellipsizar, formatar_duracao, formatar_hhmmss, horas_curto
from .sessao_dialogo import abrir_dialogo_sessao
from .widgets import ScrollableFrame, criar_rotulo_elastico

if TYPE_CHECKING:
    from .main_window import App

ALTURA_GRAFICO = 190
ALTURA_LINHA_TOP = 26
FONTE_PEQUENA = ("Segoe UI", 8)

PERIODOS: List[str] = [stats.PERIODO_7_DIAS, stats.PERIODO_8_SEMANAS, stats.PERIODO_6_MESES]  # rótulo: "periodo.<chave>"


def _qtd_sessoes(n: int) -> str:
    return t("dash.sessao_um") if n == 1 else t("dash.sessoes", n=n)


def _qtd_dias(n: int) -> str:
    return t("dash.dia", n=n) if n == 1 else t("dash.dias", n=n)


# ---------------------------------------------------------------------------
# Desenho em Canvas (sem dependências externas)
# ---------------------------------------------------------------------------
def desenhar_barras(canvas: tk.Canvas, dados: Sequence[Tuple[str, int]]) -> None:
    """Gráfico de barras verticais: dados = [(rótulo, segundos), ...]."""
    canvas.delete("all")
    largura = max(canvas.winfo_width(), 300)
    if not any(seg for _, seg in dados):
        canvas.create_text(largura / 2, ALTURA_GRAFICO / 2, text=t("dash.sem_periodo"),
                           fill=COR_TEXTO_SUAVE, font=("Segoe UI", 10))
        return
    margem, topo, base = 12, 24, ALTURA_GRAFICO - 26
    maximo = max(seg for _, seg in dados)
    slot = (largura - 2 * margem) / len(dados)
    largura_barra = min(slot * 0.6, 56)
    canvas.create_line(margem, base, largura - margem, base, fill=COR_BTN)
    for i, (rotulo, seg) in enumerate(dados):
        cx = margem + slot * (i + 0.5)
        if seg > 0:
            altura = (base - topo) * seg / maximo
            canvas.create_rectangle(cx - largura_barra / 2, base - altura, cx + largura_barra / 2, base,
                                    fill=COR_ACCENT, outline="")
            canvas.create_text(cx, base - altura - 9, text=horas_curto(seg, t("fmt.decimal")), fill=COR_TEXTO, font=FONTE_PEQUENA)
        canvas.create_text(cx, base + 13, text=rotulo, fill=COR_TEXTO_SUAVE, font=FONTE_PEQUENA)


def desenhar_top(canvas: tk.Canvas, grupos: Sequence[stats.GrupoJogo]) -> None:
    """Barras horizontais com os jogos mais jogados."""
    canvas.delete("all")
    largura = max(canvas.winfo_width(), 300)
    fonte = tkfont.Font(family="Segoe UI", size=9)
    # a coluna de nomes ocupa o que o maior nome precisa (até 40% da largura)
    x_barra = int(min(max(max(fonte.measure(g.nome) for g in grupos) + 24, 120), largura * 0.4))
    x_fim = largura - 90
    maximo = grupos[0].total
    for i, g in enumerate(grupos):
        y = 16 + i * ALTURA_LINHA_TOP
        nome = ellipsizar(g.nome, fonte.measure, x_barra - 16)
        canvas.create_text(8, y, text=nome, anchor="w", fill=COR_TEXTO, font=fonte)
        comprimento = max(2, (x_fim - x_barra) * g.total / maximo)
        canvas.create_rectangle(x_barra, y - 7, x_barra + comprimento, y + 7, fill=COR_ACCENT, outline="")
        canvas.create_text(x_barra + comprimento + 6, y, text=formatar_duracao(g.total), anchor="w",
                           fill=COR_TEXTO_SUAVE, font=FONTE_PEQUENA)


# ---------------------------------------------------------------------------
# Blocos da tela
# ---------------------------------------------------------------------------
def _card(parent: tk.Misc) -> ttk.Frame:
    frame = ttk.Frame(parent, style="Card.TFrame", padding=10)
    frame.pack(fill="x", padx=6, pady=6)
    return frame


def _tile(parent: tk.Misc, linha: int, coluna: int, titulo: str, valor: str, detalhe: str = "") -> ttk.Frame:
    tile = ttk.Frame(parent, style="Card.TFrame", padding=(6, 4))
    tile.grid(row=linha, column=coluna, sticky="nsew", padx=4, pady=4)
    ttk.Label(tile, text=titulo, style="CardSmall.TLabel").pack(anchor="w")
    criar_rotulo_elastico(tile, valor, "CardValue.TLabel", tamanho=13, peso="bold").pack(fill="x")
    if detalhe:
        criar_rotulo_elastico(tile, detalhe, "CardSmall.TLabel", tamanho=8).pack(fill="x")
    return tile


def _botao_toggle(parent: tk.Misc, texto: str, comando) -> tk.Button:
    btn = tk.Button(parent, text=texto, bg=COR_CARD, fg=COR_TEXTO_SUAVE, relief="flat",
                    font=("Segoe UI", 8, "bold"), cursor="hand2", command=comando)
    btn.pack(side="left", padx=2, pady=5)
    return btn


def _marcar(botoes: Dict[str, tk.Button], selecionado: str) -> None:
    for chave, btn in botoes.items():
        btn.config(bg=COR_ACCENT if chave == selecionado else COR_CARD,
                   fg="white" if chave == selecionado else COR_TEXTO_SUAVE)


def _bloco_resumo(parent: tk.Misc, app: "App", grupos: Sequence[stats.GrupoJogo],
                  sessoes: Sequence[Sessao], ao_editar_sessao) -> None:
    card = _card(parent)
    ttk.Label(card, text=t("dash.resumo"), style="CardTitle.TLabel").pack(anchor="w", pady=(0, 5))
    resumo = stats.resumo_geral(grupos, sessoes)
    atual, maior = stats.sequencias(sessoes, date.today())

    grade = ttk.Frame(card, style="Card.TFrame")
    grade.pack(fill="x")
    for c in range(3):
        grade.grid_columnconfigure(c, weight=1, uniform="tiles")

    longa = resumo.sessao_mais_longa
    detalhe_longa = ""
    if longa:
        dt = longa.data_dt
        detalhe_longa = f"{longa.jogo} · {dt.strftime(t('fmt.data'))}" if dt else longa.jogo
    mais = resumo.jogo_mais_jogado
    _tile(grade, 0, 0, t("dash.total"), formatar_duracao(resumo.total_segundos),
          _qtd_sessoes(resumo.total_sessoes))
    _tile(grade, 0, 1, t("dash.media"), formatar_duracao(resumo.media_sessao))
    tile_longa = _tile(grade, 0, 2, t("dash.longa"), formatar_duracao(longa.segundos) if longa else "--",
                       detalhe_longa)
    if longa:                                      # sessão suspeita (ex.: tempo lançado de uma vez)? corrige daqui
        ttk.Button(tile_longa, text=t("dash.editar_longa"),
                   command=lambda: ao_editar_sessao(longa)).pack(anchor="w", pady=(4, 0))
    _tile(grade, 1, 0, t("dash.mais_jogado"), mais.nome if mais else "--",
          formatar_duracao(mais.total) if mais else "")
    _tile(grade, 1, 1, t("dash.seq_atual"), _qtd_dias(atual))
    _tile(grade, 1, 2, t("dash.maior_seq"), _qtd_dias(maior))

    contagem = Counter(c.status.upper() for c in app.cronometros)
    linha = ttk.Frame(card, style="Card.TFrame")
    linha.pack(fill="x", pady=(6, 0))
    for status in STATUS_OPCOES:
        ttk.Label(linha, text=f"{t_status(status).upper()}: {contagem.get(status.upper(), 0)}",
                  style="CardSmall.TLabel").pack(side="left", padx=8)


def _bloco_grafico(parent: tk.Misc, sessoes: Sequence[Sessao], estado: Dict[str, str]) -> None:
    card = _card(parent)
    cabecalho = ttk.Frame(card, style="Card.TFrame")
    cabecalho.pack(fill="x")
    ttk.Label(cabecalho, text=t("dash.horas"), style="CardTitle.TLabel").pack(side="left")
    canvas = tk.Canvas(card, height=ALTURA_GRAFICO, bg=COR_CARD, highlightthickness=0)
    botoes: Dict[str, tk.Button] = {}

    def redesenhar(_event: Optional[tk.Event] = None) -> None:
        desenhar_barras(canvas, stats.horas_por_periodo(
            sessoes, estado["periodo"], date.today(), dias_semana=lista("dias_semana"),
            meses_nomes=lista("meses"), formato_semana=t("fmt.semana")))

    def escolher(periodo: str) -> None:
        estado["periodo"] = periodo
        _marcar(botoes, periodo)
        redesenhar()

    barra = ttk.Frame(cabecalho, style="Card.TFrame")
    barra.pack(side="right")
    for chave in PERIODOS:
        botoes[chave] = _botao_toggle(barra, t(f"periodo.{chave}"), lambda p=chave: escolher(p))
    _marcar(botoes, estado["periodo"])
    canvas.pack(fill="x", pady=(6, 0))
    canvas.bind("<Configure>", redesenhar)


def _bloco_top(parent: tk.Misc, grupos: Sequence[stats.GrupoJogo]) -> None:
    card = _card(parent)
    ttk.Label(card, text=t("dash.top5"), style="CardTitle.TLabel").pack(anchor="w", pady=(0, 4))
    top = stats.top_jogos(grupos, 5)
    if not top:
        ttk.Label(card, text=t("dash.sem_sessoes"), style="CardSmall.TLabel").pack(anchor="w")
        return
    canvas = tk.Canvas(card, height=len(top) * ALTURA_LINHA_TOP + 8, bg=COR_CARD, highlightthickness=0)
    canvas.pack(fill="x")
    canvas.bind("<Configure>", lambda e: desenhar_top(canvas, top))


def _bloco_lista(parent: tk.Misc, grupos: Sequence[stats.GrupoJogo], estado: Dict[str, str],
                 ao_excluir) -> None:
    ttk.Label(parent, text=t("dash.jogos"), font=("Segoe UI", 11, "bold")).pack(anchor="w", padx=10, pady=(10, 0))
    barra = ttk.Frame(parent, padding=(10, 0))
    barra.pack(fill="x")
    lista = ttk.Frame(parent)
    lista.pack(fill="x")
    botoes: Dict[str, tk.Button] = {}

    def renderizar(filtro: str) -> None:
        estado["filtro"] = filtro
        _marcar(botoes, filtro)
        for widget in lista.winfo_children():
            widget.destroy()
        for g in grupos:
            status = (g.status or "DESCONHECIDO").upper()
            if filtro != "TODOS" and status != filtro:
                continue
            bloco = ttk.Frame(lista, style="Card.TFrame", padding=8)
            bloco.pack(fill="x", pady=6, padx=6)
            bloco.grid_columnconfigure(0, weight=1)
            ttk.Label(bloco, text=g.nome, font=("Segoe UI", 11, "bold"),
                      style="Card.TLabel").grid(row=0, column=0, sticky="w")
            cores = STATUS_OPCOES.get(g.status or "", {"cor_bg": COR_BTN, "cor_fg": COR_TEXTO_SUAVE})
            tk.Label(bloco, text=rotulo_filtro(status), font=("Segoe UI", 7, "bold"), padx=6, pady=2, bd=0,
                     bg=cores["cor_bg"], fg=cores["cor_fg"]).grid(row=0, column=1, sticky="e", padx=8)
            primeira = g.primeira.strftime(t("fmt.data")) if g.primeira else "--"
            ultima = g.ultima.strftime(t("fmt.data_hora")) if g.ultima else "--"
            ttk.Label(bloco, text=t("dash.linha_total", tempo=formatar_hhmmss(g.total), sessoes=_qtd_sessoes(g.sessoes)),
                      style="CardSmall.TLabel").grid(row=1, column=0, sticky="w")
            ttk.Label(bloco, text=t("dash.primeira", data=primeira), style="CardSmall.TLabel").grid(row=2, column=0, sticky="w")
            ttk.Label(bloco, text=t("dash.ultima", data=ultima), style="CardSmall.TLabel").grid(row=3, column=0, sticky="w")
            if g.sessoes:
                tk.Button(bloco, text="✖", width=2, relief="flat", bg=COR_CARD, fg="#ff6b6b",
                          activebackground="#402b2b", cursor="hand2",
                          command=lambda grupo=g: ao_excluir(grupo)).grid(row=0, column=2, rowspan=4,
                                                                          padx=8, sticky="e")

    for f in FILTROS_STATUS:
        botoes[f] = _botao_toggle(barra, rotulo_filtro(f), lambda opt=f: renderizar(opt))
    renderizar(estado["filtro"])


# ---------------------------------------------------------------------------
# Tela principal do dashboard
# ---------------------------------------------------------------------------
def abrir_dashboard(app: "App") -> None:
    parent, is_toplevel = app.preparar_janela_ou_frame(t("tela.dashboard"))
    if is_toplevel:
        parent.geometry("660x780")
    area = ScrollableFrame(parent, app.scroll)
    area.pack(fill="both", expand=True, padx=8, pady=8)
    estado: Dict[str, str] = {"periodo": stats.PERIODO_7_DIAS, "filtro": "TODOS"}

    def excluir_registros(grupo: stats.GrupoJogo) -> None:
        if not messagebox.askyesno(t("dlg.confirmar"), t("dash.excluir_registros", nome=grupo.nome),
                                   parent=parent):
            return
        app.repo.remover_sessoes_do_grupo(grupo.chave)
        app.recarregar_totais()
        renderizar()

    def renderizar() -> None:
        area.limpar()
        sessoes = list(app.repo.sessoes)
        grupos = stats.agrupar_por_jogo([c.jogo for c in app.cronometros], sessoes)
        _bloco_resumo(area.interior, app, grupos, sessoes,
                      lambda sessao: abrir_dialogo_sessao(app, parent, sessao, renderizar))
        _bloco_grafico(area.interior, sessoes, estado)
        _bloco_top(area.interior, grupos)
        _bloco_lista(area.interior, grupos, estado, excluir_registros)

    renderizar()
