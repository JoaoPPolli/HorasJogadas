"""Componentes de interface reutilizáveis."""
import logging
import time
import tkinter as tk
import tkinter.font as tkfont
from tkinter import ttk
from typing import List, Optional

from ..constants import COR_BG
from ..utils import ellipsizar

log = logging.getLogger(__name__)


class RenderizadorEmLotes:
    """Monta listas em pequenos lotes, devolvendo tempo ao Tk para pintar e receber input."""

    def __init__(self, parent: tk.Misc):
        self.parent = parent
        self._timer = None
        self._geracao = 0
        parent.bind('<Destroy>', self._ao_destruir, add='+')

    def _ao_destruir(self, event):
        if event.widget == self.parent:
            self.cancelar()

    def cancelar(self):
        self._geracao += 1
        if self._timer is not None:
            self.parent.after_cancel(self._timer)
            self._timer = None

    def preencher(self, itens, criar, ao_terminar=None):
        self.cancelar()
        geracao = self._geracao
        pendentes = iter(itens)

        def passo():
            self._timer = None
            if geracao != self._geracao:
                return
            inicio = time.perf_counter()
            for _ in range(8):
                try:
                    item = next(pendentes)
                except StopIteration:
                    if ao_terminar:
                        ao_terminar()
                    return
                criar(item)
                if geracao != self._geracao:
                    return
                if time.perf_counter() - inicio >= .006:
                    break
            self._timer = self.parent.after(8, passo)

        passo()


class GerenciadorScroll:
    """Roda do mouse "inteligente" para todos os ScrollableFrame do app.

    Um único `bind_all`. O scroll vai para o canvas que está sob o ponteiro; se não
    houver um, usa o canvas visível registrado mais recentemente. Não rola além do
    topo/fim (a "trava inteligente" do app original).
    """

    def __init__(self, root: tk.Misc):
        self.root = root
        self._canvases: List[tk.Canvas] = []
        self._movimentos = {}
        root.bind_all("<MouseWheel>", self._ao_rolar)
        root.bind_all("<Button-4>", self._ao_rolar)
        root.bind_all("<Button-5>", self._ao_rolar)

    def registrar(self, canvas: tk.Canvas) -> None:
        if canvas not in self._canvases:
            self._canvases.append(canvas)

    def remover(self, canvas: tk.Canvas) -> None:
        self.cancelar(canvas)
        if canvas in self._canvases:
            self._canvases.remove(canvas)

    def cancelar(self, canvas):
        movimento = self._movimentos.pop(canvas, None)
        if movimento and movimento['timer'] is not None:
            self.root.after_cancel(movimento['timer'])

    def _mover(self, canvas, pixels):
        """Acumula a roda em pixels e interpola por ~120 ms; mantém movimentos pequenos."""
        topo, fundo = canvas.yview()
        regiao = canvas.cget('scrollregion')
        if not regiao or fundo - topo >= 1:
            return
        coords = [float(n) for n in canvas.tk.splitlist(regiao)]
        altura = coords[3] - coords[1]
        if altura <= 0:
            return
        atual = topo * altura
        movimento = self._movimentos.get(canvas)
        base = movimento['alvo'] if movimento else atual
        if movimento:
            self.cancelar(canvas)
        movimento = {'inicio': atual, 'alvo': max(0, min(base + pixels, altura * (1 - (fundo - topo)))),
                     'tempo': time.perf_counter(), 'timer': None}
        if abs(movimento['alvo'] - atual) < .5:
            return
        self._movimentos[canvas] = movimento

        def animar():
            movimento['timer'] = None
            try:
                if not canvas.winfo_viewable():
                    self.cancelar(canvas)
                    return
                progresso = min(1, (time.perf_counter() - movimento['tempo']) / .12)
                suavizado = 1 - (1 - progresso) ** 3
                posicao = movimento['inicio'] + (movimento['alvo'] - movimento['inicio']) * suavizado
                canvas.yview_moveto(posicao / altura)
                if progresso < 1:
                    movimento['timer'] = self.root.after(16, animar)
                else:
                    self._movimentos.pop(canvas, None)
            except tk.TclError:
                self._movimentos.pop(canvas, None)

        movimento['timer'] = self.root.after(0, animar)

    def _canvas_alvo(self, event: tk.Event) -> Optional[tk.Canvas]:
        try:
            widget = self.root.winfo_containing(event.x_root, event.y_root)
        except (KeyError, tk.TclError):
            widget = None
        while widget is not None:
            if widget in self._canvases:
                return widget
            if isinstance(widget, (tk.Text, tk.Listbox, ttk.Treeview, ttk.Combobox)):
                return None                          # esses controles já têm sua própria roda
            widget = getattr(widget, "master", None)
        janela = event.widget.winfo_toplevel() if getattr(event, 'widget', None) else None
        for canvas in reversed(self._canvases):          # fallback: último visível
            try:
                if canvas.winfo_exists() and canvas.winfo_viewable() and (janela is None or canvas.winfo_toplevel() == janela):
                    return canvas
            except tk.TclError:
                continue
        return None

    def _ao_rolar(self, event: tk.Event) -> None:
        canvas = self._canvas_alvo(event)
        if canvas is None:
            return
        try:
            delta = 0
            if getattr(event, "num", None) == 4:           # Linux: para cima
                delta = -48
            elif getattr(event, "num", None) == 5:         # Linux: para baixo
                delta = 48
            elif getattr(event, "delta", 0):               # Windows / macOS
                delta = -event.delta / 120 * 48
            if delta == 0:
                return
            self._mover(canvas, delta)
        except tk.TclError:
            log.debug("Scroll ignorado: canvas não está mais disponível", exc_info=True)


class ScrollableFrame(ttk.Frame):
    """Canvas + barra de rolagem + frame interno (`.interior`) que acompanha a largura."""

    def __init__(self, parent: tk.Misc, gerenciador: GerenciadorScroll, bg: str = COR_BG):
        super().__init__(parent)
        self.gerenciador = gerenciador
        self.canvas = tk.Canvas(self, bg=bg, highlightthickness=0, yscrollincrement=1)
        self.vbar = ttk.Scrollbar(self, orient="vertical", command=self._rolar_barra)
        self.canvas.configure(yscrollcommand=self.vbar.set)
        self.vbar.pack(side="right", fill="y")
        self.canvas.pack(side="left", fill="both", expand=True)

        self.interior = ttk.Frame(self.canvas)
        self._janela = self.canvas.create_window((0, 0), window=self.interior, anchor="nw")
        self.renderizador = RenderizadorEmLotes(self.interior)
        self._largura = None
        self._regiao = None
        self._timer_regiao = None
        self.canvas.bind("<Configure>", self._ao_redimensionar)
        self.interior.bind("<Configure>", self._atualizar_scrollregion)
        self.canvas.bind("<Destroy>", self._ao_destruir)
        self.canvas.bind('<ButtonPress-1>', lambda e: self.gerenciador.cancelar(self.canvas), add='+')
        gerenciador.registrar(self.canvas)

    def _ao_redimensionar(self, event: tk.Event) -> None:
        if event.width != self._largura:
            self._largura = event.width
            self.canvas.itemconfig(self._janela, width=event.width)

    def _atualizar_scrollregion(self, _event: tk.Event = None) -> None:
        if self._timer_regiao is None:
            self._timer_regiao = self.after_idle(self._aplicar_scrollregion)

    def _aplicar_scrollregion(self):
        self._timer_regiao = None
        regiao = self.canvas.bbox('all')
        if regiao != self._regiao:
            self.gerenciador.cancelar(self.canvas)
            self._regiao = regiao
            self.canvas.configure(scrollregion=regiao or (0, 0, 0, 0))

    def _rolar_barra(self, *args):
        self.gerenciador.cancelar(self.canvas)
        if args[0] == 'scroll' and args[2] == 'units':
            args = (args[0], int(args[1]) * 32, args[2])
        self.canvas.yview(*args)

    def _ao_destruir(self, event):
        if event.widget == self.canvas:
            self.gerenciador.remover(self.canvas)
            if self._timer_regiao is not None:
                self.after_cancel(self._timer_regiao)
                self._timer_regiao = None

    def limpar(self) -> None:
        """Remove todo o conteúdo do frame interno."""
        self.renderizador.cancelar()
        self.gerenciador.cancelar(self.canvas)
        for widget in self.interior.winfo_children():
            widget.destroy()


def criar_rotulo_elastico(parent: tk.Misc, texto: str, style: str, familia: str = "Segoe UI",
                          tamanho: int = 10, peso: str = "normal") -> ttk.Label:
    """Label que ocupa a largura disponível e só abrevia o texto com '…' se ele não couber.

    O `width=1` impede que um texto longo force a coluna a crescer; a largura real vem do
    layout e o texto é recalculado a cada <Configure>.
    """
    fonte = tkfont.Font(family=familia, size=tamanho, weight=peso)
    rotulo = ttk.Label(parent, text=texto, style=style, font=fonte, width=1, anchor="w")
    rotulo._fonte = fonte                                   # evita coleta da fonte pelo GC
    ultima_largura = [None]

    def ajustar(event: tk.Event) -> None:
        if event.width == ultima_largura[0]:
            return
        ultima_largura[0] = event.width
        novo = ellipsizar(texto, fonte.measure, event.width - 4)
        if novo != str(rotulo.cget("text")):
            rotulo.config(text=novo)

    rotulo.bind("<Configure>", ajustar)
    return rotulo
