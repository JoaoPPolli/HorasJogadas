"""O ZIP distribuído contém o código e atravessa o atualizador, com rollback intacto."""
import os
import tempfile
import unittest
import zipfile

from empacotar_atualizacao import empacotar
from horas_jogadas import __version__, updater
from tests.test_updater import instalar


class TestePacoteAtualizacao(unittest.TestCase):
    def test_pacote_completo_sem_dados_instala_e_restaura(self):
        with tempfile.TemporaryDirectory() as tmp:
            caminho = empacotar(os.path.join(tmp, 'update.zip'))
            with zipfile.ZipFile(caminho) as z:
                nomes = z.namelist()
                self.assertIn('horas_jogadas/zerados.py', nomes)
                self.assertIn('horas_jogadas/ui/zerados.py', nomes)
                self.assertFalse(any(n.endswith(('.json', '.exe', '.pyc')) or '.git/' in n for n in nomes))
            base = os.path.join(tmp, 'instalacao')
            instalar(base, '2.5.0')
            # Mesmo um arquivo pessoal colocado na raiz da instalação deve permanecer intacto.
            privado = os.path.join(base, 'zerados.json')
            with open(privado, 'w') as f:
                f.write('dados pessoais preservados')
            updater.aplicar_zip(caminho, base)
            self.assertEqual(updater.versao_instalada(base), __version__)
            self.assertTrue(os.path.isfile(os.path.join(base, 'horas_jogadas', 'zerados.py')))
            self.assertEqual(updater.restaurar_versao_anterior(base), '2.5.0')
            with open(privado) as f:
                self.assertEqual(f.read(), 'dados pessoais preservados')


if __name__ == '__main__':
    unittest.main()
