"""Rolagem, cancelamento de montagens e gráficos com Tk real e dados fictícios."""
import time
import tkinter as tk
import unittest
from tkinter import ttk
from types import SimpleNamespace
from unittest.mock import patch

from horas_jogadas.ui.widgets import GerenciadorScroll, ScrollableFrame
from horas_jogadas.ui.pagina_desenhada import PaginaDesenhada


class TesteFluidez(unittest.TestCase):
    def setUp(self):
        try:
            self.root = tk.Tk()
        except tk.TclError as erro:
            self.skipTest(str(erro))
        self.root.geometry('480x300')
        self.erros = []
        self.root.report_callback_exception = lambda *args: self.erros.append(args)
        self.scroll = GerenciadorScroll(self.root)
        self.area = ScrollableFrame(self.root, self.scroll)
        self.area.pack(fill='both', expand=True)
        ttk.Frame(self.area.interior, height=2000).pack(fill='x')
        self.root.update()
        self.addCleanup(self.fechar)

    def fechar(self):
        for timer in self.root.tk.call('after', 'info'):
            self.root.after_cancel(timer)
        self.root.destroy()

    def esperar(self, condicao):
        limite = time.monotonic() + 3
        while not condicao() and time.monotonic() < limite:
            self.root.update()
            time.sleep(.002)
        self.assertTrue(condicao(), 'A operação não terminou')
        self.assertEqual(self.erros, [])

    def posicao(self):
        return self.area.canvas.yview()[0] * 2000

    def test_lista_devolve_controle_preserva_ordem_e_conclui(self):
        criados, concluidos = [], []
        self.area.renderizador.preencher(range(100), criados.append, lambda: concluidos.append(True))
        self.assertLess(len(criados), 100)
        marcador = []
        self.root.after(0, lambda: marcador.append(len(criados)))
        self.esperar(lambda: bool(concluidos))
        self.assertEqual(criados, list(range(100)))
        self.assertLess(marcador[0], 100)
        self.assertEqual(concluidos, [True])

    def test_novo_filtro_cancela_itens_e_callback_do_anterior(self):
        antigos, novos, concluidos = [], [], []
        self.area.renderizador.preencher(range(100), antigos.append, lambda: concluidos.append('antigo'))
        quantidade = len(antigos)
        self.area.renderizador.preencher(['novo'], novos.append, lambda: concluidos.append('novo'))
        self.root.update()
        self.assertEqual(len(antigos), quantidade)
        self.assertEqual(novos, ['novo'])
        self.assertEqual(concluidos, ['novo'])

    def test_fechar_pagina_cancela_montagem_e_animacao(self):
        criados = []
        self.area.renderizador.preencher(range(100), criados.append)
        self.scroll._mover(self.area.canvas, 100)
        canvas = self.area.canvas
        self.area.destroy()
        self.root.update()
        self.assertNotIn(canvas, self.scroll._canvases)
        self.assertNotIn(canvas, self.scroll._movimentos)
        self.assertEqual(self.erros, [])

    def test_roda_pequena_nao_vira_um_salto_inteiro_e_acumula(self):
        evento = SimpleNamespace(delta=-30, num=None)
        with patch.object(self.scroll, '_canvas_alvo', return_value=self.area.canvas):
            self.scroll._ao_rolar(evento)
            self.scroll._ao_rolar(evento)
        self.esperar(lambda: not self.scroll._movimentos)
        self.assertAlmostEqual(self.posicao(), 24, delta=1)

    def test_limites_e_inversao_antes_do_primeiro_frame(self):
        self.scroll._mover(self.area.canvas, 48)
        self.scroll._mover(self.area.canvas, -48)
        self.assertEqual(self.scroll._movimentos, {})
        self.scroll._mover(self.area.canvas, 99999)
        self.esperar(lambda: not self.scroll._movimentos)
        self.assertAlmostEqual(self.area.canvas.yview()[1], 1, places=3)
        self.scroll._mover(self.area.canvas, -99999)
        self.esperar(lambda: not self.scroll._movimentos)
        self.assertEqual(self.posicao(), 0)

    def test_barra_assume_controle_sem_voltar_para_alvo_antigo(self):
        self.scroll._mover(self.area.canvas, 100)
        self.area._rolar_barra('moveto', '.5')
        self.root.update()
        self.assertEqual(self.scroll._movimentos, {})
        self.assertAlmostEqual(self.posicao(), 1000, delta=1)
        self.area._rolar_barra('scroll', '1', 'units')
        self.assertAlmostEqual(self.posicao(), 1032, delta=1)

    def test_campo_texto_e_outra_janela_nao_rolam_pagina_ao_fundo(self):
        texto = tk.Text(self.area.interior)
        evento = SimpleNamespace(x_root=0, y_root=0, widget=texto)
        with patch.object(self.root, 'winfo_containing', return_value=texto):
            self.assertIsNone(self.scroll._canvas_alvo(evento))
        popup = tk.Toplevel(self.root)
        evento.widget = popup
        with patch.object(self.root, 'winfo_containing', return_value=popup):
            self.assertIsNone(self.scroll._canvas_alvo(evento))
        popup.destroy()

    def test_blocos_inteiros_no_mesmo_canvas_sem_remontagem_ao_rolar(self):
        self.area.destroy()
        pagina = PaginaDesenhada(self.root, self.scroll)
        pagina.pack(fill='both', expand=True)
        desenhos = []

        def pintar(p):
            desenhos.append(True)
            for i in range(100):
                p.cartao(f'Jogo {i}', ['Zerado em: 2h'], [('Editar', lambda: None)])

        pagina.mostrar(pintar)
        self.root.update()
        total = len(desenhos)
        itens = pagina.canvas.find_all()
        self.assertEqual(len(pagina.acoes), 100)
        self.assertFalse(pagina.canvas.winfo_children())
        self.assertNotIn('window', [pagina.canvas.type(i) for i in itens])
        pagina.canvas.yview_moveto(.5)
        self.root.update()
        self.assertEqual(len(desenhos), total)
        self.assertEqual(pagina.canvas.find_all(), itens)
        pagina.destroy()
        self.root.update()
        self.assertEqual(self.erros, [])

    def test_clique_em_acao_rolada_e_navegacao_pelo_teclado(self):
        self.area.destroy()
        pagina = PaginaDesenhada(self.root, self.scroll)
        pagina.pack(fill='both', expand=True)
        chamadas = []

        def pintar(p):
            for i in range(15):
                p.cartao(f'Jogo {i}', ['Detalhe'], [('Editar', lambda n=i: chamadas.append(n))])

        pagina.mostrar(pintar)
        self.root.update()
        pagina.canvas.yview_moveto(.5)
        topo = pagina.canvas.canvasy(0)
        indice = next(i for i, a in enumerate(pagina.acoes) if topo + 10 < a.limites[1] < topo + 180)
        alvo = pagina.acoes[indice]
        pagina.canvas.event_generate('<Button-1>', x=int(alvo.limites[0] + 10), y=int(alvo.limites[1] - topo + 10))
        self.root.update()
        self.assertEqual(chamadas, [indice])
        pagina._navegar(1)
        pagina._ativar(None)
        pagina._navegar(-1)
        pagina._ativar(None)
        self.assertEqual(chamadas, [indice, indice + 1, indice])
        self.assertEqual(self.erros, [])

    def test_redesenho_nao_acumula_callbacks_e_botoes_cabem_em_janela_estreita(self):
        self.area.destroy()
        pagina = PaginaDesenhada(self.root, self.scroll)
        pagina.pack(fill='both', expand=True)
        pagina.mostrar(lambda p: p.cartao('Nome longo ' * 15, ['Observação longa ' * 20],
                                        [('Editar', lambda: None), ('Nova jogada', lambda: None), ('Excluir', lambda: None)]))
        self.root.update()
        comandos = len(pagina.canvas._tclCommands)
        for _ in range(20):
            pagina.atualizar()
            self.root.update()
        self.assertEqual(len(pagina.canvas._tclCommands), comandos)
        self.assertEqual(len(pagina.acoes), 3)
        for a in pagina.acoes:
            self.assertGreaterEqual(a.limites[0], 0)
            self.assertLessEqual(a.limites[2], pagina.largura)
            self.assertLess(a.limites[3], pagina.y)
        self.assertEqual(self.erros, [])


if __name__ == '__main__':
    unittest.main()
