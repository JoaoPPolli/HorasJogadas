"""Adoção oficial: backup íntegro, mesma base de dados e revisões separadas."""
import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
from horas_jogadas.storage import Repositorio
from horas_jogadas.zerados import Conclusao, RepositorioZerados
from horas_jogadas_qt.release import prepare_official_data, MARKER
from horas_jogadas_qt.preview import inventory


class OfficialDataTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory(); self.addCleanup(self.tmp.cleanup)
        self.folder=Path(self.tmp.name)/'HorasJogadas'; self.folder.mkdir()
        repo=Repositorio(str(self.folder),config_legado='')
        repo.adicionar_jogo('Não perder')
        zerados=RepositorioZerados(str(self.folder))
        zerados.guardar(Conclusao('Campanha',2024,1,120,notas='Preservar',dlc=True))
        self.before=inventory(self.folder)

    def test_first_release_preserves_all_bytes_in_verified_backup(self):
        backup=prepare_official_data(self.folder)
        self.assertEqual(inventory(backup/'data'),self.before)
        current=inventory(self.folder); current.pop(MARKER)
        self.assertEqual(current,self.before)
        metadata=json.loads((self.folder/MARKER).read_text())
        self.assertEqual(metadata['backup'],str(backup))
        self.assertIsNone(prepare_official_data(self.folder))
        self.assertEqual(len(list(backup.parent.iterdir())),1)

    def test_changed_data_aborts_without_marker_or_partial_backup(self):
        with patch('horas_jogadas_qt.release.inventory',side_effect=[self.before,{}]):
            with self.assertRaises(OSError): prepare_official_data(self.folder)
        self.assertFalse((self.folder/MARKER).exists())
        self.assertEqual(inventory(self.folder),self.before)
        root=self.folder.parent/(self.folder.name+'-Backups-de-Versao')
        self.assertEqual(list(root.iterdir()),[])

    def test_empty_new_install_has_no_unnecessary_backup(self):
        empty=Path(self.tmp.name)/'new'
        self.assertIsNone(prepare_official_data(empty))
        self.assertTrue((empty/MARKER).exists())

    def test_backup_payload_does_not_overwrite_source_file_named_manifest(self):
        (self.folder/'manifest.json').write_text('keep this raw file')
        backup=prepare_official_data(self.folder)
        self.assertEqual((backup/'data'/'manifest.json').read_text(),'keep this raw file')
        self.assertIsInstance(json.loads((backup/'manifest.json').read_text()),dict)

    def test_review_folder_is_not_merged_into_official_data(self):
        review=self.folder.parent/'HorasJogadas-Revisao-Qt'; review.mkdir()
        (review/'registros.json').write_text('[{"review-only": true}]')
        prepare_official_data(self.folder)
        self.assertFalse((self.folder/'registros.json').exists())
        self.assertEqual((review/'registros.json').read_text(),'[{"review-only": true}]')
