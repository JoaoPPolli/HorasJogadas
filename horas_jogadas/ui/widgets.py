"""Componentes de interface reutilizáveis."""
import logging
import tkinter as tk
import tkinter.font as tkfont
from tkinter import ttk
from typing import List, Optional

from ..constants import COR_BG
from ..utils import ellipsizar

log = logging.getLogger(__name__)


class GerenciadorScroll:
    """Roda do mouse "inteligente" para todos os ScrollableFrame do app.

    Um único `bind_all`. O scroll vai para o canvas que está sob o ponteiro; se não
    houver um, usa o canvas visível registrado mais recentemente. Não rola além do
    topo/fim (a "trava inteligente" do app original).
    """

    def __init__(self, root: tk.Misc):
        self.root = root
        self._canvases: List[tk.Canvas] = []
        root.bind_all("<MouseWheel>", self._ao_rolar)
        root.bind_all("<Button-4>", self._ao_rolar)
        root.bind_all("<Button-5>", self._ao_rolar)

    def registrar(self, canvas: tk.Canvas) -> None:
        if canvas not in self._canvases:
            self._canvases.append(canvas)

    def remover(self, canvas: tk.Canvas) -> None:
        if canvas in self._canvases:
            self._canvases.remove(canvas)

    def _canvas_alvo(self, event: tk.Event) -> Optional[tk.Canvas]:
        try:
            widget = self.root.winfo_containing(event.x_root, event.y_root)
        except (KeyError, tk.TclError):
            widget = None
        while widget is not None:
            if widget in self._canvases:
                return widget
            widget = getattr(widget, "master", None)
        for canvas in reversed(self._canvases):          # fallback: último visível
            try:
                if canvas.winfo_exists() and canvas.winfo_viewable():
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
                delta = -1
            elif getattr(event, "num", None) == 5:         # Linux: para baixo
                delta = 1
            elif getattr(event, "delta", 0):               # Windows / macOS
                delta = int(-event.delta / 120) or (-1 if event.delta > 0 else 1)
            if delta == 0:
                return
            topo, fundo = canvas.yview()
            if (delta < 0 and topo <= 0.0) or (delta > 0 and fundo >= 1.0):
                return
            canvas.yview_scroll(delta, "units")
        except tk.TclError:
            log.debug("Scroll ignorado: canvas não está mais disponível", exc_info=True)


class ScrollableFrame(ttk.Frame):
    """Canvas + barra de rolagem + frame interno (`.interior`) que acompanha a largura."""

    def __init__(self, parent: tk.Misc, gerenciador: GerenciadorScroll, bg: str = COR_BG):
        super().__init__(parent)
        self.gerenciador = gerenciador
        self.canvas = tk.Canvas(self, bg=bg, highlightthickness=0)
        self.vbar = ttk.Scrollbar(self, orient="vertical", command=self.canvas.yview)
        self.canvas.configure(yscrollcommand=self.vbar.set)
        self.vbar.pack(side="right", fill="y")
        self.canvas.pack(side="left", fill="both", expand=True)

        self.interior = ttk.Frame(self.canvas)
        self._janela = self.canvas.create_window((0, 0), window=self.interior, anchor="nw")
        self.canvas.bind("<Configure>", self._ao_redimensionar)
        self.interior.bind("<Configure>", self._atualizar_scrollregion)
        self.canvas.bind("<Destroy>", lambda e: self.gerenciador.remover(self.canvas))
        gerenciador.registrar(self.canvas)

    def _ao_redimensionar(self, event: tk.Event) -> None:
        self.canvas.itemconfig(self._janela, width=event.width)

    def _atualizar_scrollregion(self, _event: tk.Event = None) -> None:
        self.canvas.configure(scrollregion=self.canvas.bbox("all"))

    def limpar(self) -> None:
        """Remove todo o conteúdo do frame interno."""
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

    def ajustar(event: tk.Event) -> None:
        novo = ellipsizar(texto, fonte.measure, event.width - 4)
        if novo != str(rotulo.cget("text")):
            rotulo.config(text=novo)

    rotulo.bind("<Configure>", ajustar)
    return rotulo
