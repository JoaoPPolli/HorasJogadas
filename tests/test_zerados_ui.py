"""Integração Tk com diretórios temporários; nenhum dado da instalação real."""
import os
import tempfile
import tkinter as tk
import unittest
from dataclasses import replace
from datetime import datetime
from tkinter import ttk
from unittest.mock import patch

from horas_jogadas import i18n
from horas_jogadas.storage import Repositorio
from horas_jogadas.ui.main_window import App
from horas_jogadas.ui.zerados import criar_resumo_anual, editar_registro, revisar_importacao
from horas_jogadas.zerados import Conclusao, interpretar_txt


def descendentes(widget):
    for filho in widget.winfo_children():
        yield filho
        yield from descendentes(filho)


class TesteZeradosUI(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        try:
            self.root = tk.Tk()
        except tk.TclError as erro:
            self.skipTest(str(erro))
        self.root.withdraw()
        self.addCleanup(self.fechar)
        self.repo = Repositorio(self.tmp.name, config_legado=os.path.join(self.tmp.name, 'ausente'))
        self.app = App(self.root, repo=self.repo, backend_icone=None)
        self.erros = []
        self.root.report_callback_exception = lambda *args: self.erros.append(args)

    def fechar(self):
        for timer in self.root.tk.call('after', 'info'):
            self.root.after_cancel(timer)
        self.root.destroy()
        i18n.definir_idioma('pt')

    def botao(self, widget, texto):
        return next(w for w in descendentes(widget) if isinstance(w, ttk.Button) and w.cget('text') == texto)

    def test_status_copia_sessao_aberta_sem_parar_salvar_ou_reescrever(self):
        jogo = self.repo.adicionar_jogo('Exemplo')
        self.repo.adicionar_sessao(jogo.id, jogo.nome, 60, None, datetime(2024, 1, 1))
        card = self.app._criar_cronometro(jogo)
        card.tempo_acumulado = 30
        card.mudar_status('Zerado')
        self.assertEqual(len(self.app.zerados.registros), 1)
        r = self.app.zerados.registros[0]
        self.assertEqual(r.segundos, 90)
        self.assertEqual(self.repo.totais_por_jogo_id()[jogo.id], 60)
        self.assertEqual(card.tempo_acumulado, 30)
        self.app.zerados.guardar(replace(r, nome='Nome independente', segundos=200))
        card.mudar_status('Jogando')
        card.mudar_status('Zerado')
        self.assertEqual(self.app.zerados.registros[0].segundos, 200)
        self.assertEqual(card.nome, 'Exemplo')
        self.assertEqual(len(self.app.zerados.registros), 1)
        self.root.update()
        self.assertEqual(self.erros, [])

    def test_zerados_preexistentes_nao_sao_inventados_ao_abrir(self):
        jogo = self.repo.adicionar_jogo('Antigo', status='Zerado')
        self.app._criar_cronometro(jogo)
        janela = self.app.abrir_zerados()
        janela.withdraw()
        self.assertEqual(self.app.zerados.registros, [])
        self.root.update()
        self.assertEqual(self.erros, [])

    def test_formulario_salva_platina_adicional_dia_opcional_e_notas(self):
        resultados = []
        janela = editar_registro(self.root, Conclusao('Jogo', 2024, 3, 23700, platina_segundos=30600), resultados.append)
        janela.withdraw()
        self.root.update_idletasks()
        self.botao(janela, 'Salvar').invoke()
        self.assertEqual(len(resultados), 1)
        self.assertEqual(resultados[0].platina_segundos, 30600)
        self.assertIsNone(resultados[0].dia)
        self.assertEqual(self.repo.jogos, [])
        self.assertEqual(self.erros, [])

    def test_categoria_dlc_editavel_independente_e_preservada_na_nova_jogada(self):
        repo = self.app.obter_zerados()
        registro = Conclusao('Expansão', 2024, 3, 3600)
        repo.guardar(registro)
        resultados = []
        janela = editar_registro(self.root, registro, resultados.append)
        janela.withdraw()
        opcao = next(w for w in descendentes(janela) if isinstance(w, ttk.Checkbutton))
        opcao.invoke()
        self.botao(janela, 'Salvar').invoke()
        self.assertTrue(resultados[0].dlc)
        repo.guardar(resultados[0])
        self.app.config['modo_navegacao'] = 'navegacao'
        pagina = self.app.abrir_zerados()
        seletor = next(w for w in descendentes(pagina) if isinstance(w, ttk.Combobox))
        seletor.set('2024')
        seletor.event_generate('<<ComboboxSelected>>')
        self.root.update()
        selos = [w for w in descendentes(pagina) if isinstance(w, tk.Label) and w.cget('text') == 'DLC']
        self.assertEqual(len(selos), 1)
        self.assertEqual(selos[0].master.winfo_children()[0].cget('text'), 'Expansão')
        with patch('horas_jogadas.ui.zerados.editar_registro') as editar:
            self.botao(pagina, i18n.t('zer.rejogada')).invoke()
        self.assertTrue(editar.call_args.args[1].dlc)
        self.assertEqual(self.repo.jogos, [])
        self.assertEqual(self.repo.sessoes, [])
        self.assertEqual(self.erros, [])

    def test_resumo_acompanha_ano_edicao_exclusao_desfazer_e_tempo_desconhecido(self):
        repo = self.app.obter_zerados()
        jogo = Conclusao('Jogo', 2024, 1, 3600, platina_segundos=1800)
        repo.guardar(jogo)
        repo.guardar(Conclusao('DLC', 2024, 2, 600, dlc=True))
        repo.guardar(Conclusao('Sem horas', 2025, 1))
        self.app.config['modo_navegacao'] = 'navegacao'
        pagina = self.app.abrir_zerados()
        seletor = next(w for w in descendentes(pagina) if isinstance(w, ttk.Combobox))

        def ano(valor):
            seletor.set(str(valor))
            seletor.event_generate('<<ComboboxSelected>>')
            self.root.update()

        def textos():
            return [str(w.cget('text')) for w in descendentes(pagina) if isinstance(w, ttk.Label)]

        ano(2024)
        self.assertIn('Resumo de 2024', textos())
        self.assertIn('1h40m00s', textos())
        self.assertIn('0h30m00s', textos())
        with patch('horas_jogadas.ui.zerados.messagebox.askyesno', return_value=True):
            self.botao(pagina, 'Excluir').invoke()
        self.root.update()
        self.assertIn('0h10m00s', textos())
        self.botao(pagina, i18n.t('hist.desfazer')).invoke()
        self.root.update()
        self.assertIn('1h40m00s', textos())
        repo.guardar(replace(jogo, segundos=7200))
        self.root.event_generate('<<ZeradosAlterados>>', when='tail')
        self.root.update()
        self.assertIn('2h40m00s', textos())
        ano(2025)
        self.assertIn('Resumo de 2025', textos())
        self.assertIn('1 registros · 0 experiências sem zerar · 1 sem tempo informado', textos())
        self.assertEqual(textos().count('—'), 2)
        self.assertEqual(self.erros, [])

    def test_preview_nao_grava_antes_de_confirmar_e_importa_ano_anterior(self):
        repo = self.app.obter_zerados()
        itens = [('lista.txt', x) for x in interpretar_txt('ZERADOS EM 2024\nJaneiro:\n-Jogo A * 2h\n-Jogo A * 2h')]
        chamadas = []
        janela = revisar_importacao(self.root, repo, itens, lambda: chamadas.append(True))
        janela.withdraw()
        self.assertFalse(os.path.exists(repo.caminho))
        with patch('horas_jogadas.ui.zerados.messagebox.showinfo'):
            self.botao(janela, 'Importar selecionados').invoke()
        self.assertEqual(len(repo.registros), 1)
        self.assertEqual(repo.registros[0].ano, 2024)
        self.assertEqual(chamadas, [True])
        self.assertEqual(self.repo.jogos, [])
        self.assertEqual(self.repo.sessoes, [])
        self.assertEqual(self.erros, [])

    def test_resumo_ocupa_largura_ao_reduzir_e_ampliar_janela(self):
        janela = tk.Toplevel(self.root)
        janela.geometry('950x350')
        resumo = criar_resumo_anual(janela, [Conclusao('Jogo', 2024, 1, 3600)], 2024)
        grade = next(w for w in resumo.winfo_children() if isinstance(w, ttk.Frame))
        self.root.update()
        self.assertEqual(grade.grid_size()[0], 4)
        janela.geometry('650x350')
        self.root.update()
        # As colunas antigas não podem continuar reservando espaço vazio.
        self.assertEqual(grade.grid_bbox(2, 0, 3, 1)[2], 0)
        self.assertGreaterEqual(grade.grid_bbox(0, 0, 1, 1)[2], grade.winfo_width() - 1)
        janela.geometry('950x350')
        self.root.update()
        self.assertGreater(grade.grid_bbox(3, 0)[2], 0)
        self.assertEqual(self.erros, [])

    def test_tela_edicao_exclusao_desfazer_e_navegacao(self):
        repo = self.app.obter_zerados()
        repo.guardar(Conclusao('Jogo', 2024, 1, 60))
        self.app.config['modo_navegacao'] = 'navegacao'
        pagina = self.app.abrir_zerados()
        seletor = next(w for w in descendentes(pagina) if isinstance(w, ttk.Combobox))
        seletor.set('2024')
        seletor.event_generate('<<ComboboxSelected>>')
        self.root.update()
        with patch('horas_jogadas.ui.zerados.messagebox.askyesno', return_value=True):
            self.botao(pagina, 'Excluir').invoke()
        self.assertEqual(repo.registros, [])
        self.botao(pagina, i18n.t('hist.desfazer')).invoke()
        self.assertEqual(len(repo.registros), 1)
        self.app.mostrar_home()
        self.app.abrir_dashboard()
        self.root.update()
        self.assertEqual(self.erros, [])


if __name__ == '__main__':
    unittest.main()
