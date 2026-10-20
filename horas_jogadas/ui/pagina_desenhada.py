"""Página rolável pintada em um único Canvas, sem janelas filhas nos blocos."""
import tkinter as tk
import tkinter.font as tkfont
from dataclasses import dataclass
from tkinter import ttk

from ..constants import COR_BG, COR_CARD, COR_BTN, COR_TEXTO, COR_TEXTO_SUAVE, COR_ACCENT


@dataclass
class Acao:
    texto: str
    comando: object
    limites: tuple
    retangulo: int

    def invoke(self):
        self.comando()


class PaginaDesenhada(ttk.Frame):
    """Layout e ações permanecem no mesmo desenho durante a rolagem.

    O Tk apresenta os itens do Canvas juntos. Nenhum botão/label nativo precisa
    acompanhar o movimento da lista. Editores e campos continuam sendo widgets.
    """

    def __init__(self, parent, gerenciador):
        super().__init__(parent)
        self.gerenciador = gerenciador
        self.canvas = tk.Canvas(self, bg=COR_BG, highlightthickness=0, yscrollincrement=1, takefocus=True)
        self.vbar = ttk.Scrollbar(self, orient='vertical', command=self._barra)
        self.canvas.configure(yscrollcommand=self.vbar.set)
        self.vbar.pack(side='right', fill='y')
        self.canvas.pack(side='left', fill='both', expand=True)
        self.acoes = []
        self._desenhar = None
        self._timer = None
        self._largura = None
        self._foco = None
        self._fontes = {}
        self._medidas = {}
        self.y = 8
        self.largura = 600
        self.canvas.bind('<Configure>', self._redimensionar)
        self.canvas.bind('<Button-1>', self._clicar)
        self.canvas.bind('<Motion>', self._ponteiro)
        self.canvas.bind('<Tab>', lambda e: self._navegar(1))
        self.canvas.bind('<Shift-Tab>', lambda e: self._navegar(-1))
        if self.tk.call('tk', 'windowingsystem') != 'win32':
            self.canvas.bind('<ISO_Left_Tab>', lambda e: self._navegar(-1))
        self.canvas.bind('<Return>', self._ativar)
        self.canvas.bind('<space>', self._ativar)
        for tecla, args in (('Up', ('scroll', -1, 'units')), ('Down', ('scroll', 1, 'units')),
                            ('Prior', ('scroll', -1, 'pages')), ('Next', ('scroll', 1, 'pages')),
                            ('Home', ('moveto', 0)), ('End', ('moveto', 1))):
            self.canvas.bind(f'<{tecla}>', lambda e, movimento=args: self._tecla_rolagem(movimento))
        self.canvas.bind('<FocusOut>', lambda e: self._destacar(None))
        self.canvas.bind('<FocusIn>', lambda e: self._destacar(0) if self.acoes and self._foco is None else None)
        self.canvas.bind('<Destroy>', self._destruir)
        gerenciador.registrar(self.canvas)

    def fonte(self, tamanho=10, negrito=False):
        chave = (tamanho, negrito)
        if chave not in self._fontes:
            self._fontes[chave] = tkfont.Font(root=self.canvas, family='Segoe UI', size=tamanho,
                                            weight='bold' if negrito else 'normal')
        return self._fontes[chave]

    def medir(self, texto, tamanho=9):
        chave = (texto, tamanho)
        if chave not in self._medidas:
            self._medidas[chave] = self.fonte(tamanho).measure(texto)
        return self._medidas[chave]

    def texto(self, x, y, texto, largura=None, tamanho=10, negrito=False, cor=COR_TEXTO):
        item = self.canvas.create_text(x, y, text=texto, anchor='nw', fill=cor,
                                      font=self.fonte(tamanho, negrito), width=max(1, largura or self.largura - x - 14))
        box = self.canvas.bbox(item)
        return box[3] - y if box else 0

    def fundo(self, x, y, direita, fim, cor=COR_CARD):
        return self.canvas.create_rectangle(x, y, direita, fim, fill=cor, outline='')

    def botao(self, x, y, texto, comando, ativo=False):
        largura = max(64, self.medir(texto) + 20)
        rect = self.canvas.create_rectangle(x, y, x + largura, y + 30,
                                            fill=COR_ACCENT if ativo else COR_BTN, outline='#77777f')
        self.canvas.create_text(x + largura / 2, y + 15, text=texto, fill=COR_TEXTO, font=self.fonte(9))
        self.acoes.append(Acao(texto, comando, (x, y, x + largura, y + 30), rect))
        return largura

    def titulo(self, texto):
        self.y += 10
        self.y += self.texto(12, self.y, texto, tamanho=11, negrito=True) + 8

    def cartao(self, titulo, linhas=(), acoes=(), status=''):
        y = self.y
        rect = self.fundo(6, y, self.largura - 6, y + 1)
        total = sum(max(64, self.medir(txt) + 20) + 6 for txt, _ in acoes)
        ao_lado = self.largura - total >= 330
        largura = self.largura - 36 - (total + 12 if ao_lado else 0)
        fim = y + 12 + self.texto(18, y + 12, titulo, largura, tamanho=11, negrito=True)
        if linhas:
            fim += 6 + self.texto(18, fim + 6, '\n'.join(linhas), largura, tamanho=9, cor=COR_TEXTO_SUAVE)
        if status:
            fim += 6 + self.texto(18, fim + 6, status, largura, tamanho=8, cor=COR_TEXTO_SUAVE)
        if acoes:
            x = self.largura - 18 - total if ao_lado else 18
            by = y + 12 if ao_lado else fim + 10
            for txt, commande in acoes:
                largura_botao = max(64, self.medir(txt) + 20)
                if x + largura_botao > self.largura - 18:
                    x, by = 18, by + 36
                x += self.botao(x, by, txt, commande) + 6
            fim = max(fim, by + 30)
        fim += 12
        self.canvas.coords(rect, 6, y, self.largura - 6, fim)
        self.y = fim + 8

    def mostrar(self, desenhar):
        self._desenhar = desenhar
        self.atualizar()

    def atualizar(self):
        if self._timer is None:
            self._timer = self.after_idle(self._pintar)

    def _pintar(self):
        self._timer = None
        if not self._desenhar:
            return
        foco = self.acoes[self._foco].texto if self._foco is not None and self._foco < len(self.acoes) else None
        self.canvas.delete('all')
        self.acoes.clear()
        self._foco = None
        self.largura = max(320, self.canvas.winfo_width())
        self.y = 8
        # Sem update(), after() ou janelas filhas entre apagar e terminar o desenho.
        self._desenhar(self)
        self.canvas.configure(scrollregion=(0, 0, self.largura, max(self.y, self.canvas.winfo_height())))
        if foco is not None and self.canvas.focus_get() == self.canvas:
            self._destacar(next((i for i, a in enumerate(self.acoes) if a.texto == foco), None))

    def _redimensionar(self, event):
        if event.width != self._largura:
            self._largura = event.width
            self.gerenciador.cancelar(self.canvas)
            self.atualizar()

    def _barra(self, *args):
        self.gerenciador.cancelar(self.canvas)
        if args[0] == 'scroll' and args[2] == 'units':
            args = (args[0], int(args[1]) * 32, args[2])
        self.canvas.yview(*args)

    def _tecla_rolagem(self, args):
        self._barra(*args)
        return 'break'

    def _acao_no_ponto(self, x, y):
        y = self.canvas.canvasy(y)
        return next((i for i, a in enumerate(self.acoes)
                     if a.limites[0] <= x <= a.limites[2] and a.limites[1] <= y <= a.limites[3]), None)

    def _ponteiro(self, event):
        self.canvas.configure(cursor='hand2' if self._acao_no_ponto(event.x, event.y) is not None else '')

    def _clicar(self, event):
        self.gerenciador.cancelar(self.canvas)
        indice = self._acao_no_ponto(event.x, event.y)
        self.canvas.focus_set()
        self._destacar(indice)
        if indice is not None:
            self.acoes[indice].invoke()

    def _destacar(self, indice):
        if self._foco is not None and self._foco < len(self.acoes):
            self.canvas.itemconfigure(self.acoes[self._foco].retangulo, outline='#77777f', width=1)
        self._foco = indice
        if indice is not None:
            self.canvas.itemconfigure(self.acoes[indice].retangulo, outline=COR_ACCENT, width=2)

    def _navegar(self, direcao):
        indice = self._foco + direcao if self._foco is not None else (0 if direcao > 0 else len(self.acoes) - 1)
        if 0 <= indice < len(self.acoes):
            self._destacar(indice)
            topo, fim = self.canvas.canvasy(0), self.canvas.canvasy(self.canvas.winfo_height())
            by, bf = self.acoes[indice].limites[1], self.acoes[indice].limites[3]
            if by < topo or bf > fim:
                self.gerenciador.cancelar(self.canvas)
                self.canvas.yview_moveto(max(0, by - 20) / max(1, self.y))
        else:
            proximo = self.canvas.tk.call('tk_focusNext' if direcao > 0 else 'tk_focusPrev', self.canvas._w)
            self.canvas.nametowidget(str(proximo)).focus_set()
        return 'break'

    def _ativar(self, _event):
        if self._foco is not None:
            self.acoes[self._foco].invoke()
        return 'break'

    def _destruir(self, event):
        if event.widget == self.canvas:
            self.gerenciador.remover(self.canvas)
            if self._timer is not None:
                self.after_cancel(self._timer)
                self._timer = None
