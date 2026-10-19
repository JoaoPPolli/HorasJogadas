"""Testes do sistema de atualização por ZIP."""
import os
import tempfile
import unittest
import zipfile
from unittest import mock

from horas_jogadas import updater
from horas_jogadas.constants import MARCADOR_NAO_VALIDADA, PASTA_BACKUPS
from horas_jogadas.updater import ErroAtualizacao

RAIZ_PROJETO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def arquivos_do_pacote(versao, conteudo="x = 1\n"):
    return {
        "horas_jogadas/__init__.py": f'__version__ = "{versao}"\n',
        "horas_jogadas/main.py": conteudo,
        "horas_jogadas/storage.py": conteudo,
        "horas_jogadas/ui/__init__.py": "",
        "horas_jogadas/ui/main_window.py": conteudo,
        "horas_jogadas/novo_modulo.py": f"VERSAO = '{versao}'\n",
    }


def montar_zip(caminho, versao, prefixo="HorasJogadas/", extras=None, sem=(), apoio=True):
    arquivos = arquivos_do_pacote(versao)
    if apoio:
        arquivos["app.py"] = f"# launcher {versao}\n"
        arquivos["README.md"] = f"# readme {versao}\n"
    arquivos.update(extras or {})
    with zipfile.ZipFile(caminho, "w") as z:
        for nome, texto in arquivos.items():
            if nome not in sem:
                z.writestr(prefixo + nome if not nome.startswith("../") else nome, texto)


def instalar(base, versao):
    """Simula uma instalação existente do app em `base`."""
    for nome, texto in arquivos_do_pacote(versao).items():
        caminho = os.path.join(base, nome)
        os.makedirs(os.path.dirname(caminho), exist_ok=True)
        with open(caminho, "w", encoding="utf-8") as f:
            f.write(texto)
    for nome, texto in (("app.py", f"# launcher {versao}\n"), ("README.md", f"# readme {versao}\n"),
                        ("icon.ico", "ICONE-DO-USUARIO"), ("meu_arquivo.txt", "NAO-MEXER")):
        with open(os.path.join(base, nome), "w", encoding="utf-8") as f:
            f.write(texto)


def ler(caminho):
    with open(caminho, encoding="utf-8") as f:
        return f.read()


class Base(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.dir = self._tmp.name
        self.base = os.path.join(self.dir, "app")
        os.makedirs(self.base)

    def tearDown(self):
        self._tmp.cleanup()

    def zip(self, versao, nome=None, **kw):
        caminho = os.path.join(self.dir, nome or f"update_{versao}.zip")
        montar_zip(caminho, versao, **kw)
        return caminho

    def sobras(self):
        return [n for n in os.listdir(self.base) if n.startswith(".atualizando-")]


class TesteVersoes(unittest.TestCase):
    def test_comparar(self):
        c = updater.comparar_versoes
        self.assertEqual((c("2.1.0", "2.0.9"), c("2.0.0", "2.0.0"), c("1.9.9", "2.0.0")), (1, 0, -1))
        self.assertEqual(c("2.10.0", "2.9.0"), 1)              # numérico, não texto
        self.assertEqual(c("2.0", "2.0.0"), 0)


class TesteValidacao(Base):
    def test_zip_valido_com_e_sem_pasta_raiz(self):
        info = updater.inspecionar_zip(self.zip("3.0.0"))
        self.assertEqual((info.versao, info.prefixo), ("3.0.0", "HorasJogadas/"))
        self.assertEqual(sorted(info.arquivos_apoio), ["README.md", "app.py"])
        info = updater.inspecionar_zip(self.zip("3.0.1", nome="b.zip", prefixo=""))
        self.assertEqual((info.versao, info.prefixo), ("3.0.1", ""))

    def test_pycache_nao_entra(self):
        z = self.zip("3.0.0", extras={"horas_jogadas/__pycache__/x.cpython-312.pyc": "lixo"})
        info = updater.inspecionar_zip(z)
        self.assertFalse(any("__pycache__" in n for n in info.arquivos_pacote))

    def test_nao_e_zip_e_zip_corrompido(self):
        falso = os.path.join(self.dir, "falso.zip")
        with open(falso, "w") as f:
            f.write("isto não é um zip")
        with self.assertRaises(ErroAtualizacao):
            updater.inspecionar_zip(falso)
        bom = self.zip("3.0.0")
        with open(bom, "rb") as f:
            dados = bytearray(f.read())
        dados[len(dados) // 2] ^= 0xFF
        quebrado = os.path.join(self.dir, "quebrado.zip")
        with open(quebrado, "wb") as f:
            f.write(bytes(dados))
        with self.assertRaises(ErroAtualizacao):
            updater.inspecionar_zip(quebrado)
        with self.assertRaises(ErroAtualizacao):
            updater.inspecionar_zip(os.path.join(self.dir, "nao_existe.zip"))

    def test_sem_pacote_arquivo_obrigatorio_sintaxe_e_versao(self):
        z = os.path.join(self.dir, "outro.zip")
        with zipfile.ZipFile(z, "w") as zf:
            zf.writestr("qualquer/coisa.txt", "oi")
        with self.assertRaisesRegex(ErroAtualizacao, "horas_jogadas"):
            updater.inspecionar_zip(z)
        with self.assertRaisesRegex(ErroAtualizacao, "storage.py"):
            updater.inspecionar_zip(self.zip("3.0.0", sem=("horas_jogadas/storage.py",)))
        with self.assertRaisesRegex(ErroAtualizacao, "main_window.py"):
            updater.inspecionar_zip(self.zip("3.0.0", sem=("horas_jogadas/ui/main_window.py",)))
        with self.assertRaisesRegex(ErroAtualizacao, "sintaxe"):
            updater.inspecionar_zip(self.zip("3.0.0", extras={"horas_jogadas/ui/main_window.py": "def quebrado(:\n"}))
        with self.assertRaisesRegex(ErroAtualizacao, "versão"):
            updater.inspecionar_zip(self.zip("3.0.0", extras={"horas_jogadas/__init__.py": "# sem versao\n"}))

    def test_caminhos_inseguros_sao_recusados(self):
        for nome in ("../fora.py", "/etc/passwd", "C:/Windows/x.py"):
            z = os.path.join(self.dir, "mau.zip")
            with zipfile.ZipFile(z, "w") as zf:
                for n, texto in arquivos_do_pacote("3.0.0").items():
                    zf.writestr(n, texto)
                zf.writestr(nome, "mal")
            with self.assertRaisesRegex(ErroAtualizacao, "inseguro"):
                updater.inspecionar_zip(z)


class TesteAplicar(Base):
    def test_atualiza_preservando_arquivos_do_usuario_e_guardando_backup(self):
        instalar(self.base, "2.0.0")
        info = updater.aplicar_zip(self.zip("2.1.0"), self.base)
        self.assertEqual(info.versao, "2.1.0")
        self.assertEqual(updater.versao_instalada(self.base), "2.1.0")
        self.assertTrue(os.path.exists(os.path.join(self.base, "horas_jogadas", "novo_modulo.py")))
        self.assertIn("2.1.0", ler(os.path.join(self.base, "app.py")))           # arquivo de apoio atualizado
        self.assertEqual(ler(os.path.join(self.base, "icon.ico")), "ICONE-DO-USUARIO")
        self.assertEqual(ler(os.path.join(self.base, "meu_arquivo.txt")), "NAO-MEXER")
        backup = updater.backup_mais_recente(self.base)
        self.assertEqual(updater.versao_do_backup(backup), "2.0.0")
        self.assertIn("2.0.0", ler(os.path.join(backup, "app.py")))
        self.assertEqual(updater.versao_pendente_de_validacao(self.base), "2.1.0")
        self.assertEqual(self.sobras(), [])

    def test_remove_arquivos_que_nao_existem_mais_na_versao_nova(self):
        instalar(self.base, "2.0.0")
        with open(os.path.join(self.base, "horas_jogadas", "obsoleto.py"), "w") as f:
            f.write("x = 1\n")
        updater.aplicar_zip(self.zip("2.1.0"), self.base)
        self.assertFalse(os.path.exists(os.path.join(self.base, "horas_jogadas", "obsoleto.py")))

    def test_instalacao_do_zero_sem_pacote_anterior(self):
        updater.aplicar_zip(self.zip("2.1.0"), self.base)
        self.assertEqual(updater.versao_instalada(self.base), "2.1.0")

    def test_falha_ao_trocar_pacote_restaura_tudo(self):
        instalar(self.base, "2.0.0")
        original = updater._mover
        chamadas = []

        def falha_na_segunda(origem, destino, tentativas=4):
            chamadas.append(origem)
            if len(chamadas) == 2:                                   # logo após mover o antigo para o backup
                raise OSError("disco cheio (simulado)")
            return original(origem, destino, tentativas)

        with mock.patch.object(updater, "_mover", falha_na_segunda):
            with self.assertRaises(ErroAtualizacao):
                updater.aplicar_zip(self.zip("2.1.0"), self.base)
        self.assertEqual(updater.versao_instalada(self.base), "2.0.0")
        self.assertIn("2.0.0", ler(os.path.join(self.base, "app.py")))
        self.assertIsNone(updater.backup_mais_recente(self.base))
        self.assertIsNone(updater.versao_pendente_de_validacao(self.base))
        self.assertEqual(self.sobras(), [])

    def test_falha_ao_copiar_arquivos_de_apoio_restaura_tudo(self):
        instalar(self.base, "2.0.0")
        copia_original = updater.shutil.copy2
        chamadas = []

        def falha_na_terceira(origem, destino, *a, **k):
            chamadas.append(destino)
            if len(chamadas) == 3:
                raise OSError("sem permissão (simulado)")
            return copia_original(origem, destino, *a, **k)

        with mock.patch.object(updater.shutil, "copy2", falha_na_terceira):
            with self.assertRaises(ErroAtualizacao):
                updater.aplicar_zip(self.zip("2.1.0"), self.base)
        self.assertEqual(updater.versao_instalada(self.base), "2.0.0")
        self.assertIn("2.0.0", ler(os.path.join(self.base, "app.py")))
        self.assertIn("2.0.0", ler(os.path.join(self.base, "README.md")))
        self.assertIn("2.0.0", ler(os.path.join(self.base, "horas_jogadas", "novo_modulo.py")))   # pacote antigo de volta
        self.assertEqual(self.sobras(), [])

    def test_zip_invalido_nao_altera_nada(self):
        instalar(self.base, "2.0.0")
        with self.assertRaises(ErroAtualizacao):
            updater.aplicar_zip(self.zip("2.1.0", extras={"horas_jogadas/main.py": "def (:\n"}), self.base)
        self.assertEqual(updater.versao_instalada(self.base), "2.0.0")
        self.assertIsNone(updater.backup_mais_recente(self.base))
        self.assertEqual(self.sobras(), [])

    def test_mantem_so_os_ultimos_backups(self):
        instalar(self.base, "2.0.0")
        for v in ("2.1.0", "2.2.0", "2.3.0", "2.4.0", "2.5.0"):
            updater.aplicar_zip(self.zip(v), self.base, manter_backups=3)
        backups = updater._listar_backups(self.base)
        self.assertEqual([updater.versao_do_backup(b) for b in backups], ["2.2.0", "2.3.0", "2.4.0"])


class TesteRestaurar(Base):
    def test_restaurar_volta_e_permite_refazer(self):
        instalar(self.base, "2.0.0")
        updater.aplicar_zip(self.zip("2.1.0"), self.base)
        self.assertEqual(updater.restaurar_versao_anterior(self.base), "2.0.0")
        self.assertEqual(updater.versao_instalada(self.base), "2.0.0")
        self.assertIn("2.0.0", ler(os.path.join(self.base, "app.py")))
        self.assertIsNone(updater.versao_pendente_de_validacao(self.base))
        self.assertEqual(updater.versao_do_backup(updater.backup_mais_recente(self.base)), "2.1.0")
        self.assertEqual(updater.restaurar_versao_anterior(self.base), "2.1.0")      # "refazer"
        self.assertEqual(updater.versao_instalada(self.base), "2.1.0")

    def test_sem_backup(self):
        instalar(self.base, "2.0.0")
        self.assertFalse(updater.tem_backup(self.base))
        with self.assertRaisesRegex(ErroAtualizacao, "anterior"):
            updater.restaurar_versao_anterior(self.base)

    def test_confirmar_inicializacao_remove_marcador(self):
        instalar(self.base, "2.0.0")
        updater.aplicar_zip(self.zip("2.1.0"), self.base)
        self.assertTrue(os.path.exists(os.path.join(self.base, PASTA_BACKUPS, MARCADOR_NAO_VALIDADA)))
        updater.confirmar_inicializacao(self.base)
        self.assertIsNone(updater.versao_pendente_de_validacao(self.base))
        updater.confirmar_inicializacao(self.base)                                   # idempotente


class TesteReinicio(unittest.TestCase):
    def test_comando(self):
        self.assertEqual(updater.comando_reinicio("/p", congelado=True, executavel="/p/HorasJogadas.exe"),
                         ["/p/HorasJogadas.exe"])
        self.assertEqual(updater.comando_reinicio("/p", congelado=False, executavel="/usr/bin/pythonw"),
                         ["/usr/bin/pythonw", os.path.join("/p", "app.py")])


class TesteZipDoProprioProjeto(Base):
    """Empacota o código REAL do projeto como será entregue e o instala numa pasta de teste."""

    def test_zip_real_e_valido_e_instalavel(self):
        zip_real = os.path.join(self.dir, "real.zip")
        with zipfile.ZipFile(zip_real, "w") as z:
            for pasta, subpastas, nomes in os.walk(os.path.join(RAIZ_PROJETO, "horas_jogadas")):
                subpastas[:] = [d for d in subpastas if d != "__pycache__"]
                for nome in nomes:
                    caminho = os.path.join(pasta, nome)
                    z.write(caminho, "HorasJogadas/" + os.path.relpath(caminho, RAIZ_PROJETO).replace(os.sep, "/"))
            z.write(os.path.join(RAIZ_PROJETO, "app.py"), "HorasJogadas/app.py")
        instalar(self.base, "1.0.0")
        info = updater.aplicar_zip(zip_real, self.base)
        from horas_jogadas import __version__
        self.assertEqual(info.versao, __version__)
        for pasta, _, nomes in os.walk(os.path.join(self.base, "horas_jogadas")):     # tudo compila
            for nome in nomes:
                if nome.endswith(".py"):
                    compile(ler(os.path.join(pasta, nome)), nome, "exec")


if __name__ == "__main__":
    unittest.main()
