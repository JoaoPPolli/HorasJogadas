"""Testes do Repositório (compatíveis com pytest e com `python -m unittest`)."""
import json
import os
import tempfile
import unittest
from datetime import datetime

from horas_jogadas.models import EstadoSessao
from horas_jogadas.storage import Repositorio, escrever_json_atomico, ler_json_seguro


def _escrever(caminho, dados):
    with open(caminho, "w", encoding="utf-8") as f:
        json.dump(dados, f)


def _ler(caminho):
    with open(caminho, encoding="utf-8") as f:
        return json.load(f)


class BaseTeste(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.dir = self._tmp.name
        self.sem_legado = os.path.join(self.dir, "nao_existe.json")

    def tearDown(self):
        self._tmp.cleanup()

    def repo(self):
        return Repositorio(self.dir, config_legado=self.sem_legado)

    def arquivos(self):
        return sorted(os.listdir(self.dir))


class TesteEscritaAtomica(BaseTeste):
    def test_grava_sem_deixar_tmp_e_cria_bak_na_segunda_escrita(self):
        caminho = os.path.join(self.dir, "a.json")
        escrever_json_atomico(caminho, [1])
        self.assertEqual(_ler(caminho), [1])
        self.assertNotIn("a.json.bak", self.arquivos())
        escrever_json_atomico(caminho, [2])
        self.assertEqual(_ler(caminho), [2])
        self.assertEqual(_ler(caminho + ".bak"), [1])
        self.assertNotIn("a.json.tmp", self.arquivos())

    def test_nao_sobrescreve_bak_bom_com_arquivo_atual_invalido(self):
        caminho = os.path.join(self.dir, "a.json")
        escrever_json_atomico(caminho, [1])
        escrever_json_atomico(caminho, [2])
        with open(caminho, "w") as f:
            f.write("{quebrado")
        escrever_json_atomico(caminho, [3])
        self.assertEqual(_ler(caminho + ".bak"), [1])   # bak bom preservado


class TesteLeituraSegura(BaseTeste):
    def test_arquivo_inexistente_devolve_padrao_sem_aviso(self):
        dados, aviso = ler_json_seguro(os.path.join(self.dir, "x.json"), list)
        self.assertEqual((dados, aviso), ([], None))

    def test_corrompido_restaura_do_bak_e_preserva_copia(self):
        caminho = os.path.join(self.dir, "r.json")
        escrever_json_atomico(caminho, [{"ok": 1}])
        escrever_json_atomico(caminho, [{"ok": 2}])      # cria .bak com [{"ok": 1}]
        with open(caminho, "w") as f:
            f.write("lixo{")
        dados, aviso = ler_json_seguro(caminho, list)
        self.assertEqual(dados, [{"ok": 1}])
        self.assertIsNotNone(aviso)
        self.assertEqual(_ler(caminho), [{"ok": 1}])
        self.assertTrue(any(".corrompido-" in a for a in self.arquivos()))

    def test_corrompido_sem_bak_nao_vira_lista_vazia_silenciosa(self):
        caminho = os.path.join(self.dir, "r.json")
        with open(caminho, "w") as f:
            f.write("lixo{")
        dados, aviso = ler_json_seguro(caminho, list)
        self.assertEqual(dados, [])
        self.assertIsNotNone(aviso)                      # usuário é avisado
        copias = [a for a in self.arquivos() if ".corrompido-" in a]
        self.assertEqual(len(copias), 1)                  # conteúdo original preservado
        with open(os.path.join(self.dir, copias[0])) as f:
            self.assertEqual(f.read(), "lixo{")

    def test_tipo_errado_e_tratado_como_corrompido(self):
        caminho = os.path.join(self.dir, "r.json")
        _escrever(caminho, {"nao": "lista"})
        dados, aviso = ler_json_seguro(caminho, list, list)
        self.assertEqual(dados, [])
        self.assertIsNotNone(aviso)

    def test_repositorio_reporta_aviso_de_arquivo_corrompido(self):
        with open(os.path.join(self.dir, "registros.json"), "w") as f:
            f.write("{{{")
        repo = self.repo()
        self.assertEqual(repo.sessoes, [])
        self.assertEqual(len(repo.pop_avisos()), 1)
        self.assertEqual(repo.pop_avisos(), [])


class TesteMigracao(BaseTeste):
    def test_cronometros_formato_antigo_de_strings(self):
        _escrever(os.path.join(self.dir, "cronometros.json"), ["Cronos The New Dawn"])
        repo = self.repo()
        self.assertEqual(len(repo.jogos), 1)
        jogo = repo.jogos[0]
        self.assertEqual((jogo.nome, jogo.status), ("Cronos The New Dawn", "Jogando"))
        self.assertTrue(jogo.id)
        salvo = _ler(os.path.join(self.dir, "cronometros.json"))
        self.assertEqual(salvo[0]["id"], jogo.id)
        self.assertIn("cronometros.json.pre-migracao", self.arquivos())
        self.assertEqual(_ler(os.path.join(self.dir, "cronometros.json.pre-migracao")),
                         ["Cronos The New Dawn"])

    def test_registros_antigos_ganham_ids_e_vinculo_por_nome(self):
        _escrever(os.path.join(self.dir, "cronometros.json"), [{"nome": "Cronos The New Dawn", "status": "Jogando"}])
        _escrever(os.path.join(self.dir, "registros.json"), [
            {"jogo": "Cronos The New Dawn", "segundos": 4322, "tempo": "01:12:02", "data": "2025-11-10 17:27:42"},
            {"jogo": "cronos the new dawn ", "segundos": 1, "tempo": "00:00:01", "data": "2025-11-10 17:50:16"},
            {"jogo": "Jogo Apagado", "segundos": 60, "tempo": "00:01:00", "data": "2025-11-11 10:00:00"},
        ])
        repo = self.repo()
        jogo = repo.jogos[0]
        self.assertEqual([s.jogo_id for s in repo.sessoes], [jogo.id, jogo.id, None])
        self.assertEqual(len({s.sessao_id for s in repo.sessoes}), 3)
        self.assertEqual(repo.totais_por_jogo_id(), {jogo.id: 4323})
        salvo = _ler(os.path.join(self.dir, "registros.json"))
        self.assertTrue(all("sessao_id" in r and "jogo_id" in r for r in salvo))
        self.assertEqual(salvo[0]["data"], "2025-11-10 17:27:42")   # campos antigos preservados
        self.assertEqual(salvo[0]["tempo"], "01:12:02")

    def test_arquivos_novos_nao_sao_regravados_sem_necessidade(self):
        repo = self.repo()
        repo.adicionar_jogo("A")
        repo.adicionar_sessao(repo.jogos[0].id, "A", 10, None, datetime(2025, 1, 1, 10))
        antes = os.path.getmtime(os.path.join(self.dir, "registros.json"))
        self.repo()
        self.assertEqual(os.path.getmtime(os.path.join(self.dir, "registros.json")), antes)

    def test_status_invalido_e_normalizado(self):
        _escrever(os.path.join(self.dir, "cronometros.json"), [{"nome": "X", "status": "zerado"}, {"nome": "Y", "status": "???"}])
        repo = self.repo()
        self.assertEqual([j.status for j in repo.jogos], ["Zerado", "Jogando"])


class TesteJogosESessoes(BaseTeste):
    def test_nome_duplicado_e_vazio_sao_bloqueados(self):
        repo = self.repo()
        repo.adicionar_jogo("Hades")
        with self.assertRaises(ValueError):
            repo.adicionar_jogo("  hades ")
        with self.assertRaises(ValueError):
            repo.adicionar_jogo("   ")

    def test_novo_jogo_entra_no_topo_e_a_ordem_persiste(self):
        repo = self.repo()
        for nome in ("Primeiro", "Segundo", "Terceiro"):
            repo.adicionar_jogo(nome)
        self.assertEqual([j.nome for j in repo.jogos], ["Terceiro", "Segundo", "Primeiro"])
        self.assertEqual([j["nome"] for j in _ler(os.path.join(self.dir, "cronometros.json"))],
                         ["Terceiro", "Segundo", "Primeiro"])
        self.assertEqual([j.nome for j in self.repo().jogos], ["Terceiro", "Segundo", "Primeiro"])

    def test_renomear_atualiza_sessoes_e_preserva_historico(self):
        repo = self.repo()
        jogo = repo.adicionar_jogo("Hades")
        repo.adicionar_sessao(jogo.id, "Hades", 100, None, datetime(2025, 1, 1, 10))
        repo.renomear_jogo(jogo.id, "Hades II")
        self.assertEqual(repo.jogos[0].nome, "Hades II")
        self.assertEqual(repo.sessoes[0].jogo, "Hades II")
        novo = self.repo()                                # persistiu
        self.assertEqual(novo.sessoes[0].jogo, "Hades II")
        self.assertEqual(novo.totais_por_jogo_id(), {jogo.id: 100})

    def test_renomear_para_nome_existente_falha_mas_pode_trocar_caixa_do_proprio(self):
        repo = self.repo()
        a = repo.adicionar_jogo("Alpha")
        repo.adicionar_jogo("Beta")
        with self.assertRaises(ValueError):
            repo.renomear_jogo(a.id, "beta")
        self.assertEqual(repo.renomear_jogo(a.id, "ALPHA"), "ALPHA")

    def test_excluir_jogo_deixa_orfas_e_recriar_readota(self):
        repo = self.repo()
        jogo = repo.adicionar_jogo("Hades")
        repo.adicionar_sessao(jogo.id, "Hades", 500, None, datetime(2025, 1, 1, 10))
        repo.salvar_jogos([])                              # exclui o card
        self.assertEqual(repo.sessoes[0].jogo_id, jogo.id)  # órfã
        novo = repo.adicionar_jogo("hades")
        self.assertEqual(repo.sessoes[0].jogo_id, novo.id)
        self.assertEqual(repo.totais_por_jogo_id(), {novo.id: 500})

    def test_sessao_nova_grava_inicio_fim_e_mantem_data(self):
        repo = self.repo()
        jogo = repo.adicionar_jogo("A")
        s = repo.adicionar_sessao(jogo.id, "A", 3661, datetime(2025, 5, 1, 9, 0, 0), datetime(2025, 5, 1, 10, 1, 1))
        self.assertEqual((s.tempo, s.data, s.inicio, s.fim),
                         ("01:01:01", "2025-05-01 10:01:01", "2025-05-01 09:00:00", "2025-05-01 10:01:01"))

    def test_sessao_antiga_sem_inicio_fim_e_tolerada(self):
        _escrever(os.path.join(self.dir, "registros.json"),
                  [{"jogo": "X", "segundos": 5, "tempo": "00:00:05", "data": "2025-01-01 10:00:00"}])
        repo = self.repo()
        self.assertIsNone(repo.sessoes[0].inicio)
        self.assertNotIn("inicio", repo.sessoes[0].to_dict())

    def test_remover_sessao_e_grupo_e_limpar(self):
        repo = self.repo()
        a = repo.adicionar_jogo("A")
        s1 = repo.adicionar_sessao(a.id, "A", 10, None, datetime(2025, 1, 1, 10))
        repo.adicionar_sessao(a.id, "A", 20, None, datetime(2025, 1, 2, 10))
        repo.adicionar_sessao(None, "Orfão", 30, None, datetime(2025, 1, 3, 10))
        self.assertTrue(repo.remover_sessao(s1.sessao_id))
        self.assertFalse(repo.remover_sessao("inexistente"))
        self.assertEqual(repo.remover_sessoes_do_grupo("nome:orfão"), 1)
        self.assertEqual(repo.remover_sessoes_do_grupo(a.id), 1)
        self.assertEqual(repo.sessoes, [])
        repo.adicionar_sessao(a.id, "A", 1, None, datetime(2025, 1, 1, 10))
        repo.limpar_sessoes()
        self.assertEqual(self.repo().sessoes, [])


class TesteAndamentoEConfig(BaseTeste):
    def test_andamento_ida_e_volta_e_calculo_de_recuperacao(self):
        repo = self.repo()
        estado = EstadoSessao("id1", "Hades", acumulado=100, rodando=True,
                              retomado_em=1000.0, ultimo_heartbeat=1060.6, inicio="2025-01-01 10:00:00")
        repo.salvar_andamento([estado])
        lido = self.repo().carregar_andamento()
        self.assertEqual(lido, [estado])
        self.assertEqual(lido[0].segundos_recuperaveis(), 161)       # 100 + 60,6 arredondado
        repo.salvar_andamento([])
        self.assertEqual(repo.carregar_andamento(), [])
        self.assertNotIn("em_andamento.json", self.arquivos())

    def test_andamento_pausado_usa_so_o_acumulado(self):
        e = EstadoSessao(None, "X", 50, False, 10.0, 999.0)
        self.assertEqual(e.segundos_recuperaveis(), 50)

    def test_andamento_corrompido_e_ignorado(self):
        with open(os.path.join(self.dir, "em_andamento.json"), "w") as f:
            f.write("???")
        self.assertEqual(self.repo().carregar_andamento(), [])

    def test_config_padrao_validacao_e_persistencia(self):
        repo = self.repo()
        cfg = repo.carregar_config()
        self.assertEqual((cfg["modo_navegacao"], cfg["ordenacao"]), ("janelas", "manual"))
        _escrever(os.path.join(self.dir, "config.json"), {"modo_navegacao": "xx", "ordenacao": "horas"})
        cfg = repo.carregar_config()
        self.assertEqual((cfg["modo_navegacao"], cfg["ordenacao"]), ("janelas", "horas"))
        cfg["ordenacao"] = "nome"
        repo.salvar_config(cfg)
        self.assertEqual(self.repo().carregar_config()["ordenacao"], "nome")

    def test_config_legado_na_pasta_atual_e_migrado_uma_vez(self):
        legado = os.path.join(self.dir, "pasta_antiga_config.json")
        _escrever(legado, {"modo_navegacao": "navegacao"})
        repo = Repositorio(self.dir, config_legado=legado)
        self.assertEqual(repo.carregar_config()["modo_navegacao"], "navegacao")
        self.assertTrue(os.path.exists(os.path.join(self.dir, "config.json")))
        _escrever(legado, {"modo_navegacao": "janelas"})              # não sobrescreve depois
        self.assertEqual(repo.carregar_config()["modo_navegacao"], "navegacao")

    def test_erro_de_gravacao_chama_notificar_erro_sem_levantar(self):
        repo = self.repo()
        mensagens = []
        repo.notificar_erro = mensagens.append
        repo.arq_jogos = os.path.join(self.dir, "arquivo_que_eh_pasta")
        os.makedirs(repo.arq_jogos)                                  # os.replace falhará
        repo.salvar_jogos([])
        self.assertEqual(len(mensagens), 1)


if __name__ == "__main__":
    unittest.main()
