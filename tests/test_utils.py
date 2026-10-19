"""Testes dos utilitários de formatação e normalização."""
import unittest

from horas_jogadas.utils import (
    chave_nome, ellipsizar, formatar_duracao, formatar_hhmmss, horas_curto, normalizar_texto,
)


class TesteUtils(unittest.TestCase):
    def test_formatar_hhmmss(self):
        self.assertEqual(formatar_hhmmss(4322), "01:12:02")
        self.assertEqual(formatar_hhmmss(4322, simplificado=True), "1h 12m")
        self.assertEqual(formatar_hhmmss(-5), "00:00:00")

    def test_formatar_duracao(self):
        self.assertEqual(formatar_duracao(45), "45s")
        self.assertEqual(formatar_duracao(750), "12m 30s")
        self.assertEqual(formatar_duracao(7500), "2h 05m")

    def test_horas_curto(self):
        self.assertEqual(horas_curto(1080), "18m")
        self.assertEqual(horas_curto(5400), "1,5h")
        self.assertEqual(horas_curto(12 * 3600), "12h")

    def test_normalizacao(self):
        self.assertEqual(normalizar_texto("  Árvore Mágica "), "arvore magica")
        self.assertEqual(chave_nome("  Hades   II "), chave_nome("hades ii"))
        self.assertNotEqual(chave_nome("Pokémon"), chave_nome("Pokemon"))   # duplicado só ignora caixa/espaços

    def test_ellipsizar_so_corta_se_nao_couber(self):
        medir = lambda t: len(t) * 10                      # 10 px por caractere
        self.assertEqual(ellipsizar("Red Dead Redemption 2", medir, 400), "Red Dead Redemption 2")
        self.assertEqual(ellipsizar("Red Dead Redemption 2", medir, 210), "Red Dead Redemption 2")
        self.assertEqual(ellipsizar("Red Dead Redemption 2", medir, 100), "Red Dead…")
        self.assertEqual(ellipsizar("Red Dead Redemption 2", medir, 100)[-1], "…")
        self.assertTrue(medir(ellipsizar("Red Dead Redemption 2", medir, 150)) <= 150)
        self.assertEqual(ellipsizar("Hades", medir, 5), "…")                # nem uma letra cabe
        self.assertEqual(ellipsizar("", medir, 0), "")


if __name__ == "__main__":
    unittest.main()
