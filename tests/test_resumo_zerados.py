"""Resumo e categoria DLC usam exclusivamente os registros independentes de zerados."""
import json
import tempfile
import unittest
from dataclasses import asdict, replace
from datetime import date
from unittest.mock import patch

from horas_jogadas.zerados import (
    Conclusao, RepositorioZerados, ResumoAno, exportar_txt, interpretar_txt, resumo_ano,
)


class TesteResumoAno(unittest.TestCase):
    def test_resumo_conta_jogadas_e_so_tempos_conhecidos(self):
        jogo = Conclusao('Campanha', 2024, 1, 3600, platina_segundos=600)
        registros = [
            jogo,
            replace(jogo, id='segunda-jogada', mes=2, segundos=1800, platina_segundos=None),
            Conclusao('Expansão', 2024, 2, 1200, dlc=True),
            Conclusao('Exploração', 2024, 3, 300, tipo='experiencia'),
            Conclusao('Expansão aberta', 2024, 3, tipo='experiencia', dlc=True),
            Conclusao('Platina anotada', 2024, 4, notas='Platina', platina_segundos=60),
            Conclusao('Outro ano', 2025, 1, 99999, dlc=True),
        ]
        antes = list(registros)
        self.assertEqual(resumo_ano(registros, 2024), ResumoAno(
            jogos_zerados=3, dlcs_zeradas=1, experiencias=2,
            segundos_registrados=7560, platina_segundos=660, sem_tempo=2, registros=6,
        ))
        self.assertEqual(registros, antes)
        self.assertIsNone(registros[4].segundos)

    def test_ano_vazio_e_tempo_zero_nao_e_desconhecido(self):
        self.assertEqual(resumo_ano([], 2024), ResumoAno())
        r = Conclusao('Platina sem duração', 2024, 1, 0, notas='Platina')
        resumo = resumo_ano([r], 2024)
        self.assertEqual((resumo.registros, resumo.sem_tempo, resumo.platina_segundos), (1, 0, 0))
        self.assertIsNone(r.platina_segundos)
        self.assertEqual(resumo_ano([r], 2025), ResumoAno())


class TesteCategoriaDlc(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.repo = RepositorioZerados(self.tmp.name)

    def test_categoria_e_booleano_estrito(self):
        for valor in (None, 0, 1, 'true', 'false', [], {}):
            with self.subTest(valor=valor), self.assertRaises(ValueError):
                Conclusao('Jogo', 2024, 1, dlc=valor).validar()
        Conclusao('Jogo', 2024, 1, dlc=False).validar()
        Conclusao('Expansão', 2024, 1, tipo='experiencia', dlc=True).validar()

    def test_leitura_legada_sem_categoria_nao_infere_dlc_pelo_nome(self):
        r = Conclusao('Jogo + DLC', 2024, 1, 3600, id='legado')
        raw = asdict(r)
        del raw['dlc']
        with open(self.repo.caminho, 'w', encoding='utf-8') as arquivo:
            json.dump({'versao': 1, 'registros': [raw], 'automaticos': ['jogo-1']}, arquivo)
        reaberto = RepositorioZerados(self.tmp.name)
        self.assertEqual(reaberto.registros, [r])
        self.assertEqual(reaberto.automaticos, ['jogo-1'])

    def test_salva_categoria_sem_mudar_formato_lido_pela_versao_anterior(self):
        r = Conclusao('Expansão', 2024, 1, dlc=True)
        self.repo.guardar(r)
        with open(self.repo.caminho, encoding='utf-8') as arquivo:
            dados = json.load(arquivo)
        self.assertEqual(dados['versao'], 1)
        self.assertNotIn('dlc', dados['registros'][0])
        self.assertEqual(dados['dlcs'], [r.id])
        reaberto = RepositorioZerados(self.tmp.name)
        self.assertEqual(reaberto.registros, [r])
        reaberto.guardar(replace(r, dlc=False))
        self.assertFalse(RepositorioZerados(self.tmp.name).registros[0].dlc)
        reaberto.guardar(r)
        reaberto.excluir(r.id)
        self.assertEqual(RepositorioZerados(self.tmp.name).registros, [])
        with open(self.repo.caminho, encoding='utf-8') as arquivo:
            self.assertEqual(json.load(arquivo)['dlcs'], [])

    def test_metadados_invalidos_nao_sao_descartados(self):
        for dlcs in (None, 'abc', [True], ['inexistente'], ['r', 'r']):
            with self.subTest(dlcs=dlcs):
                r = asdict(Conclusao('Jogo', 2024, 1, id='r'))
                del r['dlc']
                dados = {'versao': 1, 'registros': [r], 'automaticos': [], 'dlcs': dlcs}
                with open(self.repo.caminho, 'w', encoding='utf-8') as arquivo:
                    json.dump(dados, arquivo)
                with self.assertRaises(ValueError):
                    RepositorioZerados(self.tmp.name)
                with open(self.repo.caminho, encoding='utf-8') as arquivo:
                    self.assertEqual(json.load(arquivo), dados)

    def test_falha_de_gravacao_preserva_categoria_em_memoria(self):
        r = Conclusao('Jogo', 2024, 1)
        self.repo.guardar(r)
        with patch('horas_jogadas.zerados.escrever_json_atomico', side_effect=OSError('disco cheio')):
            with self.assertRaises(OSError):
                self.repo.guardar(replace(r, dlc=True))
        self.assertEqual(self.repo.registros, [r])
        self.assertEqual(RepositorioZerados(self.tmp.name).registros, [r])

    def test_recuperacao_do_backup_preserva_categoria(self):
        dlc = Conclusao('Expansão', 2024, 1, dlc=True)
        self.repo.guardar(dlc)
        self.repo.guardar(Conclusao('Outro jogo', 2024, 2))
        with open(self.repo.caminho, 'w', encoding='utf-8') as arquivo:
            arquivo.write('{invalido')
        recuperado = RepositorioZerados(self.tmp.name)
        self.assertEqual(recuperado.registros, [dlc])
        self.assertTrue(recuperado.avisos)

    def test_categorizar_importado_nao_cria_copia_automatica(self):
        r = Conclusao('Expansão', 2024, 1, 3600, dlc=True)
        self.repo.importar([r])
        self.assertIsNone(self.repo.registrar_automatico('jogo-1', r.nome, 3600, date(2024, 1, 2)))
        self.assertEqual(len(self.repo.registros), 1)
        self.assertTrue(self.repo.registros[0].dlc)
        self.assertIn('jogo-1', self.repo.automaticos)

    def test_categoria_e_exclusao_preservam_recibo_automatico(self):
        r = self.repo.registrar_automatico('jogo-1', 'Expansão', 600, date(2024, 1, 2))
        self.repo.guardar(replace(r, dlc=True))
        self.assertIsNone(self.repo.registrar_automatico('jogo-1', 'Expansão', 600, date(2024, 1, 2)))
        self.repo.excluir(r.id)
        reaberto = RepositorioZerados(self.tmp.name)
        self.assertIsNone(reaberto.registrar_automatico('jogo-1', 'Expansão', 600, date(2024, 1, 2)))
        self.assertEqual(reaberto.registros, [])

    def test_reimportar_txt_antigo_preserva_categoria_sem_duplicar(self):
        texto = 'ZERADOS EM 2024\nJaneiro:\n-Expansão * 1h'
        antigo = interpretar_txt(texto)[0].registro
        self.assertEqual(self.repo.importar([antigo]), 1)
        dlc = replace(self.repo.registros[0], dlc=True)
        self.repo.guardar(dlc)
        self.assertEqual(antigo.assinatura(), dlc.assinatura())
        self.assertEqual(self.repo.importar([interpretar_txt(texto)[0].registro]), 0)
        self.assertEqual(self.repo.registros, [dlc])
        self.assertEqual(RepositorioZerados(self.tmp.name).registros, [dlc])

    def test_importacao_ignora_categoria_ao_eliminar_repeticoes_no_lote(self):
        jogo = Conclusao('Expansão', 2024, 1, 3600)
        dlc = replace(jogo, id='dlc', dlc=True)
        self.assertEqual(self.repo.importar([dlc, jogo]), 1)
        self.assertTrue(self.repo.registros[0].dlc)


class TesteDlcTxt(unittest.TestCase):
    def test_exportar_e_reimportar_preserva_categoria_e_campos(self):
        registros = [
            Conclusao('Expansão', 2024, 2, 0, dia=29, platina_segundos=600, dlc=True,
                      notas='Primeira linha\nSegunda linha'),
            Conclusao('Jogo + DLC', 2024, 3, 3600),
            Conclusao('Expansão aberta', 2024, 4, tipo='experiencia', dlc=True),
        ]
        texto = exportar_txt(registros, 2024)
        itens = interpretar_txt(texto)
        self.assertEqual(len(itens), 3)
        self.assertTrue(all(i.selecionado and not i.aviso for i in itens))
        self.assertEqual([i.registro.assinatura() for i in itens], [r.assinatura() for r in registros])
        self.assertEqual([i.registro.dlc for i in itens], [r.dlc for r in registros])
        self.assertEqual(itens[0].registro.dia, 29)
        self.assertEqual(texto.count('@dlc: sim'), 2)

    def test_booleanos_explicitos_e_nome_nao_inferido(self):
        for valor, esperado in (('sim', True), ('TRUE', True), ('yes', True),
                                ('não', False), ('nao', False), ('false', False), ('no', False)):
            with self.subTest(valor=valor):
                item = interpretar_txt(f'Janeiro:\n-Jogo + DLC * 1h\n @DLC: {valor}', 2024)[0]
                self.assertEqual(item.registro.dlc, esperado)
                self.assertTrue(item.selecionado)
        item = interpretar_txt('Janeiro:\n-Jogo - DLC * 1h', 2024)[0]
        self.assertFalse(item.registro.dlc)

    def test_categoria_invalida_fica_visivel_para_revisao(self):
        item = interpretar_txt('Janeiro:\n-Expansão * 1h\n @dlc: talvez\n @nota: Rever', 2024)[0]
        self.assertTrue(item.aviso)
        self.assertFalse(item.selecionado)
        self.assertIn('@dlc: talvez', item.texto)
        self.assertEqual(item.registro.notas, 'Rever')


if __name__ == '__main__':
    unittest.main()
