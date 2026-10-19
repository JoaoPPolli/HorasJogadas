"""Testes de internacionalização."""
import os
import string
import tempfile
import unittest
from datetime import date

from horas_jogadas import i18n, stats
from horas_jogadas.constants import IDIOMA_PADRAO, IDIOMAS_DISPONIVEIS
from horas_jogadas.models import Sessao
from horas_jogadas.storage import Repositorio


def _campos(texto):
    return {nome for _, nome, _, _ in string.Formatter().parse(str(texto)) if nome}


class BaseI18n(unittest.TestCase):
    def tearDown(self):
        i18n.definir_idioma(IDIOMA_PADRAO)          # não vaza idioma para outros testes


class TesteTraducoes(BaseI18n):
    def test_todas_as_chaves_existem_nos_dois_idiomas(self):
        pt, en = set(i18n.TEXTOS["pt"]), set(i18n.TEXTOS["en"])
        self.assertEqual(pt - en, set(), "faltam no inglês")
        self.assertEqual(en - pt, set(), "faltam no português")

    def test_marcadores_sao_os_mesmos_em_todos_os_idiomas(self):
        for chave, texto in i18n.TEXTOS["pt"].items():
            if isinstance(texto, str):
                self.assertEqual(_campos(texto), _campos(i18n.TEXTOS["en"][chave]), chave)

    def test_listas_tem_o_mesmo_tamanho(self):
        for chave, valor in i18n.TEXTOS["pt"].items():
            if isinstance(valor, list):
                self.assertEqual(len(valor), len(i18n.TEXTOS["en"][chave]), chave)
        self.assertEqual(len(i18n.TEXTOS["en"]["dias_semana"]), 7)
        self.assertEqual(len(i18n.TEXTOS["en"]["meses"]), 12)

    def test_todo_idioma_disponivel_tem_textos(self):
        self.assertEqual(set(IDIOMAS_DISPONIVEIS), set(i18n.TEXTOS))

    def test_troca_de_idioma_e_marcadores(self):
        self.assertEqual(i18n.t("card.total", tempo="1h 2m"), "Total Geral: 1h 2m")
        i18n.definir_idioma("en")
        self.assertEqual(i18n.t("card.total", tempo="1h 2m"), "Total: 1h 2m")
        self.assertEqual(i18n.t("btn.salvar"), "Save")

    def test_idioma_invalido_volta_ao_padrao_e_chave_desconhecida_vira_ela_mesma(self):
        i18n.definir_idioma("xx")
        self.assertEqual(i18n.idioma_atual(), IDIOMA_PADRAO)
        self.assertEqual(i18n.t("chave.que.nao.existe"), "chave.que.nao.existe")

    def test_status_e_filtros_sao_traduzidos_mas_chaves_salvas_nao_mudam(self):
        i18n.definir_idioma("en")
        self.assertEqual(i18n.t_status("Zerado"), "Completed")
        self.assertEqual(i18n.rotulo_filtro("JOGANDO"), "PLAYING")
        self.assertEqual(i18n.rotulo_filtro("TODOS"), "ALL")
        self.assertEqual(i18n.t_status("StatusDesconhecido"), "StatusDesconhecido")


class TesteTraducaoEmOutrasCamadas(BaseI18n):
    def test_rotulos_do_grafico_em_ingles(self):
        sessoes = [Sessao("1", "a", "A", 60, "", "2025-03-12 10:00:00")]
        hoje = date(2025, 3, 12)
        sete = stats.horas_por_periodo(sessoes, "7d", hoje, dias_semana=i18n.TEXTOS["en"]["dias_semana"])
        self.assertEqual(sete[-1][0], "Wed")
        semanas = stats.horas_por_periodo(sessoes, "8s", hoje, formato_semana="%m/%d")
        self.assertEqual(semanas[-1][0], "03/10")                  # mês/dia
        meses = stats.horas_por_periodo(sessoes, "6m", hoje, meses_nomes=i18n.TEXTOS["en"]["meses"])
        self.assertEqual(meses[0][0], "Oct/24")
        self.assertEqual(stats.horas_por_periodo(sessoes, "7d", hoje)[-1][0], "Qua")   # padrão continua PT

    def test_mensagens_do_repositorio_seguem_o_idioma(self):
        with tempfile.TemporaryDirectory() as d:
            repo = Repositorio(d, config_legado=os.path.join(d, "x.json"))
            i18n.definir_idioma("en")
            with self.assertRaises(ValueError) as ctx:
                repo.adicionar_jogo("   ")
            self.assertEqual(str(ctx.exception), "Enter a name for the entry.")
            repo.adicionar_jogo("Hades")
            with self.assertRaises(ValueError) as ctx:
                repo.adicionar_jogo("hades")
            self.assertIn("already exists", str(ctx.exception))

    def test_aviso_de_arquivo_corrompido_e_traduzido_so_ao_exibir(self):
        with tempfile.TemporaryDirectory() as d:
            with open(os.path.join(d, "registros.json"), "w") as f:
                f.write("{{{")
            repo = Repositorio(d, config_legado=os.path.join(d, "x.json"))   # criado em PT...
            i18n.definir_idioma("en")                                        # ...idioma muda depois (config)
            aviso = repo.pop_avisos()[0]
            self.assertIn("corrupted", aviso)
            self.assertIn("registros.json", aviso)

    def test_config_valida_idioma(self):
        with tempfile.TemporaryDirectory() as d:
            repo = Repositorio(d, config_legado=os.path.join(d, "x.json"))
            self.assertEqual(repo.carregar_config()["idioma"], "pt")          # config antiga sem a chave
            with open(os.path.join(d, "config.json"), "w") as f:
                f.write('{"idioma": "en"}')
            self.assertEqual(repo.carregar_config()["idioma"], "en")
            with open(os.path.join(d, "config.json"), "w") as f:
                f.write('{"idioma": "klingon"}')
            self.assertEqual(repo.carregar_config()["idioma"], "pt")


if __name__ == "__main__":
    unittest.main()
