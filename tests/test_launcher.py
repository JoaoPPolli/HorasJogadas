"""Testes do lançador (app.py): recuperação de versão com falha e cobertura das dependências do .exe."""
import ast
import importlib.util
import os
import json
import shutil
import subprocess
import sys
import tempfile
import types
import unittest
import zipfile

from horas_jogadas import updater
from horas_jogadas.constants import MARCADOR_NAO_VALIDADA, PASTA_BACKUPS

from tests.test_updater import RAIZ_PROJETO, instalar, ler, montar_zip


def carregar_lancador():
    """Importa app.py como módulo. Se o Tkinter não existir (ambiente de teste), usa um substituto."""
    if importlib.util.find_spec("tkinter") is None:
        for nome in ("tkinter", "tkinter.filedialog", "tkinter.font", "tkinter.messagebox",
                     "tkinter.simpledialog", "tkinter.ttk"):
            sys.modules.setdefault(nome, types.ModuleType(nome))
    spec = importlib.util.spec_from_file_location("lancador_app", os.path.join(RAIZ_PROJETO, "app.py"))
    modulo = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(modulo)
    return modulo


class TesteLancador(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = carregar_lancador()

    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.base = os.path.join(self._tmp.name, "app")
        os.makedirs(self.base)

    def tearDown(self):
        self._tmp.cleanup()

    def instalar_versao_com_falha(self):
        """Instala 2.0.0, atualiza para 2.1.0 (que 'não abre') e deixa o marcador de não validada."""
        instalar(self.base, "2.0.0")
        zip_novo = os.path.join(self._tmp.name, "novo.zip")
        montar_zip(zip_novo, "2.1.0")
        updater.aplicar_zip(zip_novo, self.base)

    def test_restaurar_backup_do_lancador_le_o_backup_feito_pelo_atualizador(self):
        self.instalar_versao_com_falha()
        self.assertTrue(self.app.restaurar_backup(self.base))
        self.assertEqual(updater.versao_instalada(self.base), "2.0.0")
        self.assertIn("2.0.0", ler(os.path.join(self.base, "app.py")))
        self.assertIsNone(updater.versao_pendente_de_validacao(self.base))
        self.assertTrue(os.path.exists(os.path.join(self.base, PASTA_BACKUPS, "_versao_com_falha")))
        self.assertFalse(self.app.restaurar_backup(self.base))                  # não há mais backup

    def test_marcador_tem_o_mesmo_nome_nos_dois_lados(self):
        self.assertEqual(self.app.MARCADOR, MARCADOR_NAO_VALIDADA)
        self.assertEqual(self.app.PASTA_BACKUPS, PASTA_BACKUPS)

    def test_falha_apos_atualizacao_oferece_restaurar(self):
        self.instalar_versao_com_falha()
        chamadas = []
        resultado = self.app.tratar_falha(
            self.base, "Traceback...\nImportError: algo deu errado",
            perguntar=lambda erro: chamadas.append(("perguntou", erro)) or True,
            mostrar=lambda txt: chamadas.append(("mostrou", txt)),
            reiniciar=lambda base: chamadas.append(("reiniciou", base)))
        self.assertEqual(resultado, "restaurado")
        self.assertEqual([c[0] for c in chamadas], ["perguntou", "reiniciou"])
        self.assertIn("ImportError", chamadas[0][1])
        self.assertEqual(updater.versao_instalada(self.base), "2.0.0")
        self.assertIn("ImportError", ler(os.path.join(self.base, "erro_ao_iniciar.log")))

    def test_usuario_recusa_restaurar_ve_o_erro(self):
        self.instalar_versao_com_falha()
        chamadas = []
        resultado = self.app.tratar_falha(
            self.base, "x\nBoom", perguntar=lambda e: False,
            mostrar=lambda txt: chamadas.append(txt), reiniciar=lambda b: chamadas.append("reiniciou"))
        self.assertEqual(resultado, "erro")
        self.assertEqual(updater.versao_instalada(self.base), "2.1.0")           # nada foi alterado
        self.assertEqual(len(chamadas), 1)
        self.assertIn("Boom", chamadas[0])

    def test_falha_sem_atualizacao_recente_nao_oferece_restaurar(self):
        """Erro comum (ex.: arquivo de dados com problema) não deve sugerir trocar de versão."""
        self.instalar_versao_com_falha()
        updater.confirmar_inicializacao(self.base)                              # versão já validada antes
        perguntou = []
        resultado = self.app.tratar_falha(
            self.base, "x\nErro qualquer", perguntar=lambda e: perguntou.append(1) or True,
            mostrar=lambda t: None, reiniciar=lambda b: None)
        self.assertEqual((resultado, perguntou), ("erro", []))

    def test_falha_sem_backup(self):
        instalar(self.base, "2.0.0")
        resultado = self.app.tratar_falha(self.base, "x\nErro", perguntar=lambda e: True,
                                          mostrar=lambda t: None, reiniciar=lambda b: None)
        self.assertEqual(resultado, "erro")

    def test_main_chama_tratar_falha_quando_o_app_nao_inicia(self):
        pacote_falso = "pacote_falso_para_teste"
        os.makedirs(os.path.join(self.base, pacote_falso))
        for nome, texto in (("__init__.py", ""), ("main.py", "def executar(argv):\n    raise RuntimeError('boom')\n")):
            with open(os.path.join(self.base, pacote_falso, nome), "w") as f:
                f.write(texto)
        registrado = []
        antigos = (self.app.PACOTE, self.app.pasta_base, self.app.tratar_falha)
        self.app.PACOTE = pacote_falso
        self.app.pasta_base = lambda: self.base
        self.app.tratar_falha = lambda base, detalhes, **k: registrado.append((base, detalhes))
        try:
            self.app.main()
        finally:
            self.app.PACOTE, self.app.pasta_base, self.app.tratar_falha = antigos
            sys.modules.pop(pacote_falso, None)
            sys.modules.pop(pacote_falso + ".main", None)
            if self.base in sys.path:
                sys.path.remove(self.base)
        self.assertEqual(len(registrado), 1)
        self.assertIn("boom", registrado[0][1])


class TesteDependenciasDoExe(unittest.TestCase):
    """O .exe só contém o que o app.py importa explicitamente; o resto do app é carregado depois."""

    @staticmethod
    def importados(arvore):
        modulos = set()
        for no in ast.walk(arvore):
            if isinstance(no, ast.Import):
                modulos.update(a.name for a in no.names)
            elif isinstance(no, ast.ImportFrom) and no.level == 0 and no.module:
                modulos.add(no.module)
                if no.module == "tkinter":                       # submódulos importados com "from tkinter import x"
                    modulos.update(f"tkinter.{a.name}" for a in no.names
                                   if a.name in {"ttk", "messagebox", "simpledialog", "font", "filedialog"})
        return modulos

    def test_lancador_importa_tudo_da_biblioteca_padrao_que_o_app_usa(self):
        if not hasattr(sys, "stdlib_module_names"):
            self.skipTest("requer Python 3.10+ para listar a biblioteca padrão")
        usados = set()
        for pasta, subpastas, nomes in os.walk(os.path.join(RAIZ_PROJETO, "horas_jogadas")):
            subpastas[:] = [d for d in subpastas if d != "__pycache__"]
            for nome in nomes:
                if nome.endswith(".py"):
                    with open(os.path.join(pasta, nome), encoding="utf-8") as f:
                        usados |= self.importados(ast.parse(f.read()))
        stdlib = {m for m in usados if m.split(".")[0] in sys.stdlib_module_names}
        with open(os.path.join(RAIZ_PROJETO, "app.py"), encoding="utf-8") as f:
            do_lancador = self.importados(ast.parse(f.read()))
        faltando = sorted(m for m in stdlib if m not in do_lancador)
        self.assertEqual(faltando, [], "adicione estes imports ao app.py (senão o .exe quebra): " + ", ".join(faltando))

    def test_scripts_de_apoio_existem(self):
        for nome in ("build_exe.bat", "Iniciar.bat", "app.py"):
            self.assertTrue(os.path.exists(os.path.join(RAIZ_PROJETO, nome)), nome)


# Roda em dois processos: (A) carrega só o que o app.py importa e anota quais módulos existem;
# (B) bloqueia qualquer outra biblioteca do Python e importa o app inteiro, como num .exe.
_SCRIPT_A = r"""
import ast, importlib, json, sys
arvore = ast.parse(open(sys.argv[1], encoding="utf-8").read())
for no in arvore.body:
    if isinstance(no, ast.Import):
        for a in no.names:
            try:
                importlib.import_module(a.name)
            except ModuleNotFoundError:
                if not a.name.startswith("tkinter"):
                    raise
print(json.dumps(sorted(sys.modules)))
"""

_SCRIPT_B = r"""
import importlib, json, pkgutil, sys, types
permitidos = set(json.load(open(sys.argv[1])))

class Bloqueador:                                   # imita o .exe: só existe o que o lançador incluiu
    def find_spec(self, nome, path=None, target=None):
        if (nome.split(".")[0] in sys.stdlib_module_names and nome not in permitidos
                and not nome.startswith(("encodings", "_"))):
            raise ModuleNotFoundError("No module named %r (simulando o .exe)" % nome)
        return None

sys.meta_path.insert(0, Bloqueador())

if "tkinter" not in sys.modules:                     # ambiente sem Tkinter: usa um substituto
    class Modulo(types.ModuleType):
        def __getattr__(self, nome):
            if nome.startswith("__"):
                raise AttributeError(nome)
            return type(nome, (object,), {})
    for nome in ("tkinter", "tkinter.ttk", "tkinter.messagebox", "tkinter.simpledialog",
                 "tkinter.font", "tkinter.filedialog"):
        sys.modules[nome] = Modulo(nome)
    for sub in ("ttk", "messagebox", "simpledialog", "font", "filedialog"):
        setattr(sys.modules["tkinter"], sub, sys.modules["tkinter." + sub])

sys.path.insert(0, sys.argv[2])
import horas_jogadas
for m in pkgutil.walk_packages(horas_jogadas.__path__, "horas_jogadas."):
    importlib.import_module(m.name)
print("OK")
"""


class TesteSimulacaoDoExe(unittest.TestCase):
    def test_app_inteiro_importa_so_com_as_bibliotecas_do_lancador(self):
        if not hasattr(sys, "stdlib_module_names"):
            self.skipTest("requer Python 3.10+")
        with tempfile.TemporaryDirectory() as tmp:
            a = subprocess.run([sys.executable, "-c", _SCRIPT_A, os.path.join(RAIZ_PROJETO, "app.py")],
                               capture_output=True, text=True, cwd=tmp)
            self.assertEqual(a.returncode, 0, a.stderr)
            lista = os.path.join(tmp, "permitidos.json")
            with open(lista, "w", encoding="utf-8") as f:
                f.write(a.stdout)
            b = subprocess.run([sys.executable, "-c", _SCRIPT_B, lista, RAIZ_PROJETO],
                               capture_output=True, text=True, cwd=tmp)
            self.assertEqual(b.returncode, 0, "No .exe o app não abriria:\n" + b.stderr[-900:])
            self.assertIn("OK", b.stdout)


if __name__ == "__main__":
    unittest.main()
