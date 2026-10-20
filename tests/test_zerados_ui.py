"""Integração Tk com diretórios temporários; nenhum dado da instalação real."""
import os
import tempfile
import tkinter as tk
import time
import unittest
from dataclasses import replace
from datetime import datetime
from tkinter import ttk
from unittest.mock import patch

from horas_jogadas import i18n
from horas_jogadas.storage import Repositorio
from horas_jogadas.models import Sessao
from horas_jogadas.ui.main_window import App
from horas_jogadas.ui.zerados import editar_registro, revisar_importacao
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

    def test_trocas_rapidas_cancelam_listas_antigas_sem_mudar_dados(self):
        jogo = self.repo.adicionar_jogo('Teste de navegação')
        card = self.app._criar_cronometro(jogo)
        card.tempo_acumulado = 90
        self.repo.sessoes = [Sessao.nova(jogo.id, jogo.nome, 60, None, datetime(2024, 1, 1)) for _ in range(230)]
        self.app.obter_zerados().registros = [Conclusao(f'Jogo {i}', 2024, 1, 60) for i in range(70)]
        originais = list(self.repo.sessoes)
        for modo in ('navegacao', 'janela'):
            self.app.config['modo_navegacao'] = modo
            for abrir in (self.app.abrir_historico, self.app.abrir_dashboard, self.app.abrir_zerados):
                abrir()
                if modo == 'janela':
                    self.app._popups[-1].destroy()
                self.root.update()
            self.app.mostrar_home()
        self.app.config['modo_navegacao'] = 'navegacao'
        self.app.abrir_historico()
        limite = time.monotonic() + 5
        while time.monotonic() < limite:
            self.root.update()
            botoes = [w for w in descendentes(self.app.frame_conteudo) if isinstance(w, ttk.Button) and '30' in w.cget('text')]
            if botoes:
                break
            time.sleep(.003)
        self.assertTrue(botoes, 'A primeira página de 200 sessões não terminou')
        self.assertEqual(self.repo.sessoes, originais)
        self.assertEqual(card.tempo_acumulado, 90)
        self.assertEqual(len(self.app.zerados.registros), 70)
        self.assertEqual(self.erros, [])


if __name__ == '__main__':
    unittest.main()
