"""Teste do lançador oficial em subprocesso, sem tocar no perfil real da máquina."""
import os
import unittest
import tempfile
import subprocess
import sys
import importlib.util
from pathlib import Path
if importlib.util.find_spec('PySide6') is None:
    raise unittest.SkipTest('Interface Qt opcional: instale requirements-qt.txt')

ROOT=Path(__file__).resolve().parent.parent


class ReleaseLauncherTests(unittest.TestCase):
    def run_launcher(self,mode):
        with tempfile.TemporaryDirectory() as temporary:
            code='''import sys
from pathlib import Path
from PySide6.QtWidgets import QApplication,QMessageBox
from PySide6.QtCore import QTimer
from app_qt import main,seed_demo
from horas_jogadas.constants import DATA_DIR
from horas_jogadas_qt.preview import inventory
from horas_jogadas.instancia import TravaInstancia
source=Path(DATA_DIR); source.mkdir(parents=True); seed_demo(source)
before=inventory(source)
app_exec=QApplication.exec
errors=[]
def run(self):
    def ready():
        try:
            window=next(w for w in self.topLevelWidgets() if hasattr(w,'navigate'))
            assert window.mode==MODE
            if MODE=='release':
                assert window.c.folder==source
                other=TravaInstancia(str(source))
                assert not other.adquirir()
                assert (source/'.horasjogadas-release.json').exists()
            else:
                assert window.c.folder!=source
                assert not (source/'.horasjogadas-release.json').exists()
            assert len(window.c.repo.jogos)==6
            for name,digest in before.items(): assert inventory(source)[name]==digest
        except Exception as error: errors.append(str(error))
        self.quit()
    QTimer.singleShot(100,ready)
    return app_exec()
QApplication.exec=run
QMessageBox.information=lambda *args:QMessageBox.Ok
QMessageBox.critical=lambda *args:errors.append(str(args))
result=main(['--review'] if MODE=='review' else [])
assert result==0 and not errors,(result,errors)
'''.replace('MODE',repr(mode))
            result=subprocess.run([sys.executable,'-c',code],cwd=ROOT,
                env=dict(os.environ,APPDATA=temporary,QT_QPA_PLATFORM='offscreen'),capture_output=True,text=True,timeout=30)
            self.assertEqual(result.returncode,0,result.stderr+result.stdout)

    def test_official_release_uses_existing_records_and_same_instance_lock(self):
        self.run_launcher('release')

    def test_explicit_review_still_uses_a_separate_copy(self):
        self.run_launcher('review')
