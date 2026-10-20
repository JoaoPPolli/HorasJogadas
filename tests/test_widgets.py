"""Rolagem, cancelamento de montagens e gráficos com Tk real e dados fictícios."""
import time
import tkinter as tk
import unittest
from tkinter import ttk
from types import SimpleNamespace
from unittest.mock import patch

from horas_jogadas.ui.widgets import GerenciadorScroll, ScrollableFrame
from horas_jogadas.ui.dashboard import _bloco_grafico, PERIODOS


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

    def test_grafico_nao_recalcula_sessoes_ao_rolar_ou_redimensionar(self):
        with patch('horas_jogadas.ui.dashboard.stats.horas_por_periodo', return_value=[('dia', 3600)]) as calcular:
            _bloco_grafico(self.area.interior, [], {'periodo': PERIODOS[0]})
            self.root.update()
            graficos = [w for card in self.area.interior.winfo_children() for w in card.winfo_children() if isinstance(w, tk.Canvas)]
            grafico = graficos[0]
            with patch('horas_jogadas.ui.dashboard.desenhar_barras') as desenhar:
                grafico.event_generate('<Configure>', width=grafico.winfo_width(), height=grafico.winfo_height())
                self.root.update()
                desenhar.assert_not_called()
                self.root.geometry('560x300')
                self.root.update()
                self.assertTrue(desenhar.called)
            self.assertEqual(calcular.call_count, 1)
        self.assertEqual(self.erros, [])


if __name__ == '__main__':
    unittest.main()
