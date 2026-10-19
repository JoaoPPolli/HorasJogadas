"""Testes das estatísticas (compatíveis com pytest e com `python -m unittest`)."""
import unittest
from datetime import date, datetime

from horas_jogadas import stats
from horas_jogadas.models import Jogo, Sessao


def sess(jogo_id, nome, seg, data):
    return Sessao(sessao_id=f"{nome}{data}{seg}", jogo_id=jogo_id, jogo=nome, segundos=seg,
                  tempo="", data=data)


JOGOS = [Jogo("a", "Alpha", "Jogando"), Jogo("b", "Beta", "Zerado"), Jogo("c", "Sem Sessões", "Backlog")]


class TesteAgrupamento(unittest.TestCase):
    def setUp(self):
        self.sessoes = [
            sess("a", "Alpha", 3600, "2025-03-01 20:00:00"),
            sess("a", "Alpha", 1800, "2025-03-05 21:00:00"),
            sess("b", "Beta", 600, "2025-03-02 10:00:00"),
            sess("zzz", "Apagado", 100, "2025-03-03 10:00:00"),      # órfã (jogo removido)
            sess(None, "apagado ", 50, "2025-03-04 10:00:00"),        # órfã sem id, mesmo nome
            sess("a", "Alpha", 10, "data-invalida"),
        ]

    def test_grupos_incluem_jogos_sem_sessao_e_agrupam_orfas_por_nome(self):
        grupos = {g.nome: g for g in stats.agrupar_por_jogo(JOGOS, self.sessoes)}
        self.assertEqual(set(grupos), {"Alpha", "Beta", "Sem Sessões", "Apagado"})
        self.assertEqual(grupos["Alpha"].total, 5410)
        self.assertEqual(grupos["Alpha"].sessoes, 3)
        self.assertEqual(grupos["Apagado"].total, 150)
        self.assertIsNone(grupos["Apagado"].status)
        self.assertEqual(grupos["Sem Sessões"].total, 0)
        self.assertIsNone(grupos["Sem Sessões"].ultima)
        self.assertEqual(grupos["Alpha"].primeira, datetime(2025, 3, 1, 20))
        self.assertEqual(grupos["Alpha"].ultima, datetime(2025, 3, 5, 21))

    def test_ordenacao_por_ultima_sessao_e_sem_sessao_no_fim(self):
        nomes = [g.nome for g in stats.agrupar_por_jogo(JOGOS, self.sessoes)]
        self.assertEqual(nomes[0], "Alpha")
        self.assertEqual(nomes[-1], "Sem Sessões")

    def test_resumo_geral(self):
        grupos = stats.agrupar_por_jogo(JOGOS, self.sessoes)
        r = stats.resumo_geral(grupos, self.sessoes)
        self.assertEqual((r.total_segundos, r.total_sessoes), (5410 + 600 + 150, 6))
        self.assertAlmostEqual(r.media_sessao, 6160 / 6)
        self.assertEqual(r.sessao_mais_longa.segundos, 3600)
        self.assertEqual(r.jogo_mais_jogado.nome, "Alpha")

    def test_resumo_sem_sessoes(self):
        r = stats.resumo_geral(stats.agrupar_por_jogo(JOGOS, []), [])
        self.assertEqual((r.total_segundos, r.total_sessoes, r.media_sessao), (0, 0, 0.0))
        self.assertIsNone(r.sessao_mais_longa)
        self.assertIsNone(r.jogo_mais_jogado)

    def test_top_jogos(self):
        top = stats.top_jogos(stats.agrupar_por_jogo(JOGOS, self.sessoes), 2)
        self.assertEqual([g.nome for g in top], ["Alpha", "Beta"])

    def test_totais_e_ultima_por_jogo_id(self):
        self.assertEqual(stats.totais_por_jogo_id(self.sessoes), {"a": 5410, "b": 600, "zzz": 100})
        self.assertEqual(stats.ultima_sessao_por_jogo_id(self.sessoes)["a"], datetime(2025, 3, 5, 21))


class TesteSequencias(unittest.TestCase):
    def dias(self, *datas):
        return [sess("a", "A", 60, f"{d} 12:00:00") for d in datas]

    def test_sem_sessoes(self):
        self.assertEqual(stats.sequencias([], date(2025, 3, 10)), (0, 0))

    def test_sequencia_atual_termina_hoje(self):
        s = self.dias("2025-03-08", "2025-03-09", "2025-03-10")
        self.assertEqual(stats.sequencias(s, date(2025, 3, 10)), (3, 3))

    def test_sequencia_atual_termina_ontem_ainda_conta(self):
        s = self.dias("2025-03-08", "2025-03-09")
        self.assertEqual(stats.sequencias(s, date(2025, 3, 10)), (2, 2))

    def test_sequencia_quebrada_zera_atual_mas_mantem_maior(self):
        s = self.dias("2025-03-01", "2025-03-02", "2025-03-03", "2025-03-07")
        self.assertEqual(stats.sequencias(s, date(2025, 3, 10)), (0, 3))

    def test_virada_de_mes_e_de_ano(self):
        s = self.dias("2024-12-30", "2024-12-31", "2025-01-01", "2025-01-01")
        self.assertEqual(stats.sequencias(s, date(2025, 1, 2)), (3, 3))

    def test_varias_sessoes_no_mesmo_dia_contam_um_dia(self):
        s = self.dias("2025-03-10", "2025-03-10", "2025-03-10")
        self.assertEqual(stats.sequencias(s, date(2025, 3, 10)), (1, 1))

    def test_datas_invalidas_sao_ignoradas(self):
        s = self.dias("2025-03-10") + [sess("a", "A", 1, "lixo")]
        self.assertEqual(stats.sequencias(s, date(2025, 3, 10)), (1, 1))


class TestePeriodos(unittest.TestCase):
    HOJE = date(2025, 3, 12)   # quarta-feira

    def test_sete_dias(self):
        s = [sess("a", "A", 100, "2025-03-12 10:00:00"), sess("a", "A", 50, "2025-03-12 23:00:00"),
             sess("a", "A", 70, "2025-03-06 10:00:00"),      # 6 dias atrás: dentro
             sess("a", "A", 999, "2025-03-05 10:00:00"),     # 7 dias atrás: fora
             sess("a", "A", 5, "invalida")]
        r = stats.horas_por_periodo(s, "7d", self.HOJE)
        self.assertEqual(len(r), 7)
        self.assertEqual(r[-1], ("Qua", 150))
        self.assertEqual(r[0], ("Qui", 70))
        self.assertEqual(sum(v for _, v in r), 220)

    def test_oito_semanas_comecam_na_segunda(self):
        s = [sess("a", "A", 10, "2025-03-10 10:00:00"),      # segunda da semana atual
             sess("a", "A", 20, "2025-03-09 10:00:00"),      # domingo -> semana anterior
             sess("a", "A", 30, "2025-01-20 10:00:00"),      # 7 semanas atrás: dentro
             sess("a", "A", 40, "2025-01-19 10:00:00")]      # fora
        r = stats.horas_por_periodo(s, "8s", self.HOJE)
        self.assertEqual(len(r), 8)
        self.assertEqual(r[-1], ("10/03", 10))
        self.assertEqual(r[-2], ("03/03", 20))
        self.assertEqual(r[0], ("20/01", 30))

    def test_seis_meses_atravessando_o_ano(self):
        s = [sess("a", "A", 1, "2025-03-01 10:00:00"), sess("a", "A", 2, "2024-12-31 23:59:59"),
             sess("a", "A", 4, "2024-10-15 10:00:00"),       # 5 meses atrás: dentro
             sess("a", "A", 8, "2024-09-30 10:00:00")]       # fora
        r = stats.horas_por_periodo(s, "6m", self.HOJE)
        self.assertEqual([rot for rot, _ in r], ["Out/24", "Nov/24", "Dez/24", "Jan/25", "Fev/25", "Mar/25"])
        self.assertEqual([v for _, v in r], [4, 0, 2, 0, 0, 1])

    def test_periodo_invalido(self):
        with self.assertRaises(ValueError):
            stats.horas_por_periodo([], "xx", self.HOJE)


if __name__ == "__main__":
    unittest.main()
