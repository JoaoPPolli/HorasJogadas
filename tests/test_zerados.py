"""Regressões da lista independente, do resumo anual e da importação TXT."""
import json
import tempfile
import unittest
from dataclasses import replace
from datetime import date
from pathlib import Path
from unittest.mock import patch

from horas_jogadas.zerados import (
    Conclusao, RepositorioZerados, exportar_txt, interpretar_txt, ler_duracao,
    resumo_ano,
)


class TesteResumoEImportacao(unittest.TestCase):
    def test_resumo_separa_jogos_dlcs_e_experiencias_sem_inventar_tempos(self):
        registros = [
            Conclusao('Campanha', 2024, 1, 3600, platina_segundos=1800),
            Conclusao('Expansão', 2024, 2, 900, dlc=True),
            Conclusao('Experiência', 2024, 3, 600, tipo='experiencia'),
            Conclusao('Sem tempo', 2024, 4),
            Conclusao('Outro ano', 2023, 1, 10000),
        ]
        resumo = resumo_ano(registros, 2024)
        self.assertEqual((resumo.jogos_zerados, resumo.dlcs_zeradas, resumo.experiencias),
                         (2, 1, 1))
        self.assertEqual(resumo.segundos_registrados, 6900)
        self.assertEqual(resumo.platina_segundos, 1800)
        self.assertEqual((resumo.sem_tempo, resumo.registros), (1, 4))

    def test_nova_jogada_conta_separadamente(self):
        registro = Conclusao('Campanha', 2024, 1, 3600)
        resumo = resumo_ano([registro, replace(registro, id='outra-jogada')], 2024)
        self.assertEqual((resumo.jogos_zerados, resumo.segundos_registrados), (2, 7200))

    def test_exportacao_reimporta_dlc_dia_notas_e_platina(self):
        original = Conclusao('Expansão', 2024, 3, 3600, dia=15,
                             platina_segundos=900, dlc=True, notas='Linha 1\nLinha 2')
        itens = interpretar_txt(exportar_txt([original], 2024))
        self.assertEqual(len(itens), 1)
        self.assertTrue(itens[0].selecionado)
        self.assertEqual(itens[0].aviso, '')
        reimportado = itens[0].registro
        self.assertEqual(reimportado.assinatura(), original.assinatura())
        self.assertTrue(reimportado.dlc)
        self.assertEqual(reimportado.dia, 15)

    def test_nome_com_dlc_nao_classifica_automaticamente(self):
        item = interpretar_txt('ZERADOS EM 2024\nJaneiro:\n-Jogo + DLC * 2h')[0]
        self.assertTrue(item.selecionado)
        self.assertFalse(item.registro.dlc)

    def test_metadado_dlc_invalido_exige_revisao(self):
        item = interpretar_txt('ZERADOS EM 2024\nJaneiro:\n-Jogo * 2h\n@dlc: talvez')[0]
        self.assertFalse(item.selecionado)
        self.assertTrue(item.aviso)

    def test_experiencia_e_tempo_desconhecido_sobrevivem_ao_txt(self):
        registro = Conclusao('Uma tentativa', 2024, 1, tipo='experiencia')
        item = interpretar_txt(exportar_txt([registro], 2024))[0]
        self.assertTrue(item.selecionado)
        self.assertEqual(item.registro.tipo, 'experiencia')
        self.assertIsNone(item.registro.segundos)

    def test_tempos_documentados_e_rejeicao_de_entrada_parcial(self):
        for texto, esperado in [('13h45m', 49500), ('40min', 2400), ('01:30:00', 5400), ('', None)]:
            with self.subTest(texto=texto):
                self.assertEqual(ler_duracao(texto), esperado)
        for texto in ('1h lixo', '01:90:00', '-1h'):
            with self.subTest(texto=texto), self.assertRaises(ValueError):
                ler_duracao(texto)


class TestePersistenciaZerados(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.pasta = Path(self.tmp.name)
        self.repo = RepositorioZerados(self.tmp.name)

    def test_dlc_persiste_em_metadado_compativel_com_formato_anterior(self):
        registro = Conclusao('Expansão', 2024, 1, 1200, dlc=True)
        self.repo.guardar(registro)
        raw = json.loads((self.pasta / 'zerados.json').read_text(encoding='utf-8'))
        self.assertEqual(raw['dlcs'], [registro.id])
        self.assertNotIn('dlc', raw['registros'][0])
        self.assertTrue(RepositorioZerados(self.tmp.name).registros[0].dlc)

    def test_txt_antigo_nao_duplica_registro_categorizado_depois(self):
        registro = interpretar_txt('ZERADOS EM 2024\nJaneiro:\n-Jogo * 2h')[0].registro
        self.assertEqual(self.repo.importar([registro]), 1)
        salvo = self.repo.registros[0]
        self.repo.guardar(replace(salvo, dlc=True, dia=10))
        self.assertEqual(self.repo.importar([registro]), 0)
        self.assertEqual(len(self.repo.registros), 1)
        self.assertTrue(self.repo.registros[0].dlc)

    def test_recibo_automatico_impede_duplicata_apos_exclusao_e_reabertura(self):
        registro = self.repo.registrar_automatico('jogo-1', 'Jogo', 3600, date(2024, 1, 10))
        self.repo.excluir(registro.id)
        reaberto = RepositorioZerados(self.tmp.name)
        self.assertIsNone(reaberto.registrar_automatico('jogo-1', 'Jogo', 7200, date(2024, 1, 11)))
        self.assertEqual(reaberto.registros, [])

    def test_falha_de_gravacao_preserva_estado_e_arquivo(self):
        registro = Conclusao('Original', 2024, 1, 100)
        self.repo.guardar(registro)
        antes = (self.pasta / 'zerados.json').read_bytes()
        with patch('horas_jogadas.zerados.escrever_json_atomico', side_effect=OSError('disco cheio')):
            with self.assertRaises(OSError):
                self.repo.guardar(replace(registro, nome='Alterado'))
        self.assertEqual(self.repo.registros, [registro])
        self.assertEqual((self.pasta / 'zerados.json').read_bytes(), antes)

    def test_arquivo_corrompido_recupera_backup_e_preserva_original(self):
        registro = Conclusao('Original', 2024, 1, 100)
        self.repo.guardar(registro)
        self.repo.guardar(replace(registro, nome='Mais recente'))
        (self.pasta / 'zerados.json').write_text('{invalido', encoding='utf-8')
        reaberto = RepositorioZerados(self.tmp.name)
        self.assertEqual(reaberto.registros[0].nome, 'Original')
        self.assertTrue(reaberto.avisos)
        copias = list(self.pasta.glob('zerados.json.corrompido-*'))
        self.assertEqual(len(copias), 1)
        self.assertEqual(copias[0].read_text(encoding='utf-8'), '{invalido')

    def test_lista_nao_altera_dados_de_jogos_e_sessoes(self):
        arquivos = {'cronometros.json': '["jogo"]', 'registros.json': '[]', 'config.json': '{}'}
        for nome, conteudo in arquivos.items():
            (self.pasta / nome).write_text(conteudo, encoding='utf-8')
        self.repo.guardar(Conclusao('Conclusão independente', 2024, 1, 120))
        for nome, conteudo in arquivos.items():
            self.assertEqual((self.pasta / nome).read_text(encoding='utf-8'), conteudo)


if __name__ == '__main__':
    unittest.main()
