"""Conclusões independentes: persistência, importação, idempotência e isolamento."""
import json
import os
import tempfile
import unittest
from dataclasses import replace
from datetime import date, datetime
from unittest.mock import patch

from horas_jogadas.models import EstadoSessao
from horas_jogadas.storage import Repositorio
from horas_jogadas.zerados import (Conclusao, RepositorioZerados, ano_do_texto, duracao_texto,
                                  exportar_txt, interpretar_txt, ler_duracao, ler_txt, resumo_ano)


class TesteImportacao(unittest.TestCase):
    def test_tempos_com_segundos_minutos_e_horas(self):
        for texto, total in [('40min', 2400), ('13h45m', 49500), ('6h37m25s', 23845),
                             ('3h1m13s', 10873), ('00:01:30', 90), ('1:30', 5400),
                             ('90min', 5400), ('0h00m00s', 0), ('', None)]:
            with self.subTest(texto=texto):
                self.assertEqual(ler_duracao(texto), total)

    def test_tempo_invalido_nao_vira_valor_parcial(self):
        for texto in ('-2h', '1.5h', '1h70m', '00:70:00', '1h lixo', '12', 'm', '2h3h'):
            with self.subTest(texto=texto), self.assertRaises(ValueError):
                ler_duracao(texto)

    def test_multiplos_anos_e_ausencia_de_dia(self):
        texto = 'ZERADOS EM 2024\nJaneiro:\n-Jogo A * 10h\nZERADOS EM 2025\nMarço:\n-Jogo B * 40min'
        itens = interpretar_txt(texto)
        self.assertEqual([(x.registro.ano, x.registro.mes, x.registro.dia) for x in itens], [(2024, 1, None), (2025, 3, None)])
        self.assertTrue(all(x.selecionado for x in itens))

    def test_platina_sao_horas_adicionais(self):
        r = interpretar_txt('ZERADOS EM 2025\nMarço:\n-Jogo (Personagem A) * 6h35m | Platina * 8h30m')[0].registro
        self.assertEqual((r.segundos, r.platina_segundos), (23700, 30600))
        self.assertEqual(duracao_texto(r.segundos + r.platina_segundos), '15h05m00s')

    def test_rejogada_dlc_e_notas_sem_inventar_platina(self):
        itens = interpretar_txt('Abril:\n-Jogo (2ª Jogada + Platina) * 6h37m25s\n-Jogo - DLC * 10h19m11s\n-Jogo B * 133h20m11s (100%)', 2025)
        self.assertIn('2ª Jogada', itens[0].registro.nome)
        self.assertIsNone(itens[0].registro.platina_segundos)
        self.assertIn('DLC', itens[1].registro.nome)
        self.assertEqual(itens[2].registro.notas, '(100%)')

    def test_experiencia_nao_conta_como_conclusao(self):
        r = interpretar_txt('Maio:\n-((Jogo aberto)) * 9h', 2024)[0].registro
        self.assertEqual((r.nome, r.tipo), ('Jogo aberto', 'experiencia'))

    def test_marcador_experiencia_apos_tempo(self):
        r = interpretar_txt('Maio:\n-Jogo aberto * 9h (())', 2024)[0].registro
        self.assertEqual((r.nome, r.tipo, r.segundos), ('Jogo aberto', 'experiencia', 32400))

    def test_linhas_desconhecidas_ficam_visiveis(self):
        itens = interpretar_txt('Jogo sem mês\nMaio:\n-Jogo A * errado\n-Jogo B * 2h', 2025)
        self.assertEqual(len(itens), 3)
        self.assertTrue(itens[0].aviso)
        self.assertTrue(itens[1].aviso)
        self.assertFalse(itens[1].selecionado)
        self.assertTrue(itens[2].selecionado)

    def test_sem_ano_exige_revisao(self):
        self.assertIsNone(ano_do_texto('Janeiro:\n-Jogo * 1h'))
        self.assertIsNone(interpretar_txt('Janeiro:\n-Jogo * 1h')[0].registro)

    def test_exportacao_reimportacao_preserva_todos_os_campos_editaveis(self):
        original = Conclusao('Jogo B', 2024, 2, 0, 29, 60, 'Duas linhas\nPersonagem B', 'experiencia')
        texto = exportar_txt([original, Conclusao('Outro ano', 2025, 1)], 2024)
        itens = interpretar_txt(texto)
        self.assertEqual(len(itens), 1)
        r = itens[0].registro
        self.assertEqual(r.assinatura(), original.assinatura())
        self.assertEqual(r.dia, 29)
        self.assertNotIn('Outro ano', texto)

    def test_dia_invalido_importado_nao_e_selecionado(self):
        item = interpretar_txt('ZERADOS EM 2025\nFevereiro:\n-Jogo * 1h\n @dia: 30')[0]
        self.assertTrue(item.aviso)
        self.assertFalse(item.selecionado)

    def test_codificacoes_do_bloco_de_notas(self):
        texto = 'ZERADOS EM 2024\nMarço:\n-Ação * 1h'
        with tempfile.TemporaryDirectory() as tmp:
            caminho = os.path.join(tmp, 'lista.txt')
            for encoding in ('utf-8-sig', 'utf-16', 'cp1252'):
                with self.subTest(encoding=encoding):
                    with open(caminho, 'w', encoding=encoding) as f:
                        f.write(texto)
                    self.assertEqual(ler_txt(caminho), texto)


class TesteArquivoIndependente(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.repo = RepositorioZerados(self.tmp.name)

    def test_automatico_preserva_snapshot_e_nao_duplica_apos_editar_excluir(self):
        r = self.repo.registrar_automatico('jogo1', 'Original', 23700, date(2025, 3, 2))
        self.repo.guardar(replace(r, nome='Nome editado', segundos=100))
        self.assertIsNone(self.repo.registrar_automatico('jogo1', 'Renomeado', 99999))
        self.assertEqual((self.repo.registros[0].nome, self.repo.registros[0].segundos), ('Nome editado', 100))
        self.repo.excluir(r.id)
        reaberto = RepositorioZerados(self.tmp.name)
        self.assertIsNone(reaberto.registrar_automatico('jogo1', 'Renomeado', 99999))
        self.assertEqual(reaberto.registros, [])

    def test_automatico_usa_data_do_momento_e_tempo_recebido(self):
        r = self.repo.registrar_automatico('a', 'Jogo', 3600.6, date(2024, 12, 31))
        self.assertEqual((r.ano, r.mes, r.dia, r.segundos), (2024, 12, 31, 3601))

    def test_importar_duas_vezes_e_repetidos_no_mesmo_lote(self):
        r = Conclusao('Jogo', 2024, 1, 3600)
        self.assertEqual(self.repo.importar([r, replace(r, id='outro')]), 1)
        self.assertEqual(self.repo.importar([r]), 0)
        self.assertEqual(self.repo.importar([replace(r, mes=2)]), 1)

    def test_automatico_nao_repete_importado_com_mes_sem_dia(self):
        self.repo.importar([Conclusao('Jogo', 2024, 1, 3600)])
        self.assertIsNone(self.repo.registrar_automatico('a', 'Jogo', 3600, date(2024, 1, 2)))
        self.assertEqual(len(self.repo.registros), 1)
        self.assertIn('a', self.repo.automaticos)

    def test_crud_importacao_e_exportacao_nao_tocam_nenhum_outro_arquivo(self):
        principal = Repositorio(self.tmp.name, config_legado=os.path.join(self.tmp.name, 'ausente'))
        jogo = principal.adicionar_jogo('Jogo')
        principal.adicionar_sessao(jogo.id, jogo.nome, 60, None, datetime(2024, 1, 2))
        principal.salvar_config({'idioma': 'pt'})
        principal.salvar_andamento([EstadoSessao(jogo.id, jogo.nome, 30, False, 0, 0, None)])
        caminhos = [principal.arq_jogos, principal.arq_sessoes, principal.arq_config, principal.arq_andamento]
        def ler(caminho):
            with open(caminho, 'rb') as f:
                return f.read()
        antes = {c: ler(c) for c in caminhos}
        r = self.repo.registrar_automatico(jogo.id, jogo.nome, 90, date(2024, 1, 2))
        self.repo.guardar(replace(r, nome='Outro', segundos=5000, platina_segundos=100, dlc=True))
        self.repo.importar([Conclusao('Manual', 2025, 1, 500)])
        exportar_txt(self.repo.registros, 2024)
        self.assertEqual(resumo_ano(self.repo.registros, 2024).dlcs_zeradas, 1)
        self.repo.excluir(r.id)
        self.assertEqual({c: ler(c) for c in caminhos}, antes)
        self.assertEqual(principal.totais_por_jogo_id(), {jogo.id: 60})
        self.assertEqual(principal.jogos[0].nome, 'Jogo')

    def test_falha_de_gravacao_nao_altera_memoria_ou_recibos(self):
        with patch('horas_jogadas.zerados.escrever_json_atomico', side_effect=OSError('disco cheio')):
            with self.assertRaises(OSError):
                self.repo.registrar_automatico('a', 'Jogo', 60)
        self.assertEqual(self.repo.registros, [])
        self.assertEqual(self.repo.automaticos, [])
        self.assertIsNotNone(self.repo.registrar_automatico('a', 'Jogo', 60))

    def test_backup_recupera_arquivo_corrompido_sem_apagar_original(self):
        self.repo.guardar(Conclusao('Primeiro', 2024, 1))
        self.repo.guardar(Conclusao('Segundo', 2024, 2))
        with open(self.repo.caminho, 'w') as f:
            f.write('{invalido')
        recuperado = RepositorioZerados(self.tmp.name)
        self.assertEqual([r.nome for r in recuperado.registros], ['Primeiro'])
        self.assertTrue(recuperado.avisos)
        self.assertTrue(any('.corrompido-' in nome for nome in os.listdir(self.tmp.name)))

    def test_schema_invalido_nao_e_silenciosamente_descartado(self):
        for dados in ({'versao': 99}, {'versao': 1, 'registros': [{'nome': 'incompleto'}], 'automaticos': []}):
            with open(self.repo.caminho, 'w', encoding='utf-8') as f:
                json.dump(dados, f)
            with self.assertRaises(ValueError):
                RepositorioZerados(self.tmp.name)
            with open(self.repo.caminho, encoding='utf-8') as f:
                self.assertEqual(json.load(f), dados)

    def test_datas_reais_opcionais_e_futuras(self):
        Conclusao('Jogo', 2024, 2, dia=29).validar()
        Conclusao('Jogo', 2025, 2).validar()
        for r in (Conclusao('Jogo', 2025, 2, dia=29), Conclusao('Jogo', 2025, 13),
                  Conclusao('Jogo', 9999, 1), Conclusao('Jogo', 2025, 1, segundos=-1)):
            with self.subTest(r=r), self.assertRaises(ValueError):
                r.validar()


if __name__ == '__main__':
    unittest.main()
