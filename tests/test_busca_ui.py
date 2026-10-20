"""Foco da busca usando eventos reais do Tk e dados temporários."""
import os
import tempfile
import tkinter as tk
import unittest
from tkinter import ttk

from horas_jogadas import i18n
from horas_jogadas.storage import Repositorio
from horas_jogadas.ui.main_window import App


class TesteBuscaUI(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        try:
            self.root = tk.Tk()
        except tk.TclError as erro:
            self.skipTest(str(erro))
        self.addCleanup(self.fechar)
        self.root.withdraw()
        self.repo = Repositorio(self.tmp.name, config_legado=os.path.join(self.tmp.name, 'ausente'))
        self.repo.adicionar_jogo('Jogo de exemplo')
        self.app = App(self.root, repo=self.repo, backend_icone=None)
        self.erros = []
        self.root.report_callback_exception = lambda *args: self.erros.append(args)
        self.root.deiconify()
        self.root.update()
        self.root.focus_force()
        self.root.update()

    def fechar(self):
        for timer in self.root.tk.call('after', 'info'):
            self.root.after_cancel(timer)
        self.root.destroy()
        i18n.definir_idioma('pt')

    def clicar(self, widget):
        widget.event_generate('<Button-1>', x=3, y=3)
        widget.event_generate('<ButtonRelease-1>', x=3, y=3)
        self.root.update()

    def digitar(self, texto):
        for letra in texto:
            foco = self.root.focus_get()
            self.assertIsNotNone(foco)
            foco.event_generate('<KeyPress>', keysym=letra)
            foco.event_generate('<KeyRelease>', keysym=letra)
        self.root.update()

    def buscar(self):
        self.root.focus_set()
        self.root.event_generate('<Control-f>')
        self.root.update()
        self.assertIs(self.root.focus_get(), self.app.entry_busca)
        self.digitar('Jogo')
        self.assertEqual(self.app.var_busca.get(), 'Jogo')

    def test_clicar_no_fundo_ou_cartao_libera_digitacao_sem_apagar_filtro(self):
        self.buscar()
        for destino in (self.app.canvas_home, self.app.cronometros[0].lbl_nome,
                        self.app.cronometros[0].frame):
            with self.subTest(destino=destino.winfo_class()):
                self.app.entry_busca.focus_set()
                self.root.update()
                self.clicar(destino)
                self.assertIsNot(self.root.focus_get(), self.app.entry_busca)
                self.digitar('x')
                self.assertEqual(self.app.var_busca.get(), 'Jogo')
                self.assertEqual(len(self.app._cronometros_visiveis()), 1)
        self.assertEqual(self.erros, [])

    def test_clicar_outro_campo_transfere_digitacao_e_na_busca_mantem_foco(self):
        self.buscar()
        self.clicar(self.app.entry_nome)
        self.assertIs(self.root.focus_get(), self.app.entry_nome)
        self.digitar('Novo')
        self.assertEqual(self.app.entry_nome.get(), 'Novo')
        self.assertEqual(self.app.var_busca.get(), 'Jogo')
        self.clicar(self.app.entry_busca)
        self.assertIs(self.root.focus_get(), self.app.entry_busca)
        self.app.entry_busca.icursor(tk.END)
        self.digitar('x')
        self.assertEqual(self.app.var_busca.get(), 'Jogox')
        self.assertEqual(self.erros, [])

    def test_ctrl_f_reseleciona_e_escape_limpa_e_libera_foco(self):
        self.buscar()
        self.root.event_generate('<Control-f>')
        self.root.update()
        self.assertTrue(self.app.entry_busca.selection_present())
        self.digitar('Outro')
        self.assertEqual(self.app.var_busca.get(), 'Outro')
        self.app.entry_busca.event_generate('<Escape>')
        self.root.update()
        self.assertEqual(self.app.var_busca.get(), '')
        self.assertIsNot(self.root.focus_get(), self.app.entry_busca)
        self.digitar('x')
        self.assertEqual(self.app.var_busca.get(), '')
        self.assertEqual(self.erros, [])

    def test_outros_controles_e_dialogos_mantem_seu_foco(self):
        self.buscar()
        self.clicar(self.app.combo_ordem)
        # O dropdown é um controle criado pelo Tcl, sem objeto widget Python.
        foco = str(self.root.tk.call('focus'))
        self.assertTrue(foco.startswith(str(self.app.combo_ordem)))
        self.root.tk.call('event', 'generate', foco, '<Escape>')
        self.root.update()
        janela = tk.Toplevel(self.root)
        campo = ttk.Entry(janela)
        campo.pack()
        self.root.update()
        janela.focus_force()
        self.clicar(campo)
        self.assertIs(self.root.focus_get(), campo)
        self.digitar('Dialogo')
        self.assertEqual(campo.get(), 'Dialogo')
        self.assertEqual(self.app.var_busca.get(), 'Jogo')
        janela.destroy()
        self.assertEqual(self.erros, [])


if __name__ == '__main__':
    unittest.main()
