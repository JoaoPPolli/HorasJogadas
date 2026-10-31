"""Transferência offline revisada, deduplicação e preservação dos dados antigos."""
import copy
import json
import os
os.environ.setdefault('QT_QPA_PLATFORM', 'offscreen')
import tempfile
import unittest
import uuid
from dataclasses import replace
from datetime import datetime, timedelta, timezone
from pathlib import Path
from unittest.mock import patch

from PySide6.QtCore import Qt, QEvent
from PySide6.QtWidgets import QApplication, QDialogButtonBox, QMessageBox
from horas_jogadas import i18n
from horas_jogadas.storage import Repositorio
from horas_jogadas_qt.backup import read_full, restore_full
from horas_jogadas_qt.controller import Controller
from horas_jogadas_qt.phone_import import (MAX_BYTES, MAX_SECONDS, ReviewDialog, export_library,
                                          import_mobile, load_mobile, parse_mobile)
from horas_jogadas_qt.preview import inventory, prepare_preview
from horas_jogadas_qt.theme import apply_theme
from horas_jogadas_qt.window import Window
from .test_data import Clock

APP = QApplication.instance() or QApplication([])
CORE = ('cronometros.json', 'registros.json', 'em_andamento.json', 'zerados.json', 'config.json')


def payload(**changes):
    record = dict(id=str(uuid.uuid4()), game='Meu jogo', game_id=None, seconds=120,
                  started_at='2024-04-03T18:00:00-03:00', ended_at='2024-04-03T18:05:00-03:00')
    record.update(changes)
    return {'format': 'HorasJogadas-Mobile', 'version': 1, 'sessions': [record]}


def encoded(value):
    return json.dumps(value, ensure_ascii=False).encode('utf-8')


class MobileImportTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        self.source = self.root / 'source'; self.source.mkdir()
        repo = Repositorio(str(self.source), config_legado='')
        game = repo.adicionar_jogo('Meu jogo')
        self.existing = repo.adicionar_sessao(game.id, game.nome, 45, None, datetime(2024, 1, 1, 20))
        self.before_source = inventory(self.source)
        self.folder = prepare_preview(self.source, self.root / 'review')
        self.c = Controller(self.folder)
        self.key = game.id
        self.clock = Clock()
        self.c.timers[self.key].clock = self.clock
        i18n.definir_idioma('pt')

    def tearDown(self):
        self.assertEqual(self.before_source, inventory(self.source))
        self.tmp.cleanup()

    def core_bytes(self):
        return {name: (self.folder / name).read_bytes() if (self.folder / name).exists() else None for name in CORE}

    def test_import_converts_timezone_preserves_old_history_and_live_timer(self):
        timer = self.c.timers[self.key]
        timer.start(); self.clock.advance(30)
        identity = id(timer)
        records = parse_mobile(encoded(payload(game_id=self.key)))
        original = self.c.repo.sessoes[0].to_dict()
        result = import_mobile(self.c, records)
        self.assertEqual((result['imported'], result['skipped']), (1, 0))
        self.assertTrue(Path(result['backup']).is_dir())
        self.assertEqual(json.loads(read_full(result['backup'])['registros.json']), [original])
        self.assertEqual(self.c.repo.sessoes[0].to_dict(), original)
        saved = self.c.repo.sessoes[-1]
        expected = records[0].ended_at.astimezone().replace(tzinfo=None)
        self.assertEqual(saved.segundos, 120)
        self.assertEqual(saved.fim, expected.strftime('%Y-%m-%d %H:%M:%S'))
        self.assertEqual(saved.sessao_id, records[0].session_id)
        self.assertEqual(id(self.c.timers[self.key]), identity)
        self.assertTrue(timer.rodando)
        self.assertEqual(timer.seconds(), 30)
        reopened = Repositorio(str(self.folder), config_legado='')
        self.assertEqual(len(reopened.sessoes), 2)

    def test_reimport_skips_even_after_local_edit_without_backup_or_overwrite(self):
        records = parse_mobile(encoded(payload()))
        import_mobile(self.c, records)
        session = self.c.repo.sessoes[-1]
        self.c.repo.atualizar_sessao(session.sessao_id, self.key, 'Meu jogo', 240, datetime(2024, 4, 3, 21))
        before = self.core_bytes()
        with patch('horas_jogadas_qt.phone_import.create_full') as backup:
            result = import_mobile(self.c, records)
        backup.assert_not_called()
        self.assertEqual(result, {'imported': 0, 'skipped': 1, 'backup': None})
        self.assertEqual(self.core_bytes(), before)

    def test_deduplication_survives_full_backup_and_restore(self):
        records = parse_mobile(encoded(payload()))
        import_mobile(self.c, records)
        from horas_jogadas_qt.backup import create_full
        backup = create_full(self.folder)
        other = self.root / 'other'; other.mkdir()
        c = Controller(other)
        with c.transaction():
            restore_full(other, backup)
        c = Controller(other)
        result = import_mobile(c, records)
        self.assertEqual((result['imported'], result['skipped']), (0, 1))
        self.assertEqual(len(c.repo.sessoes), 2)

    def test_unknown_game_is_created_once_for_two_sessions_only_on_commit(self):
        value = payload(game='Novo   jogo')
        second = copy.deepcopy(value['sessions'][0]); second['id'] = str(uuid.uuid4())
        value['sessions'].append(second)
        records = parse_mobile(encoded(value))
        self.assertEqual(len(self.c.repo.jogos), 1)
        result = import_mobile(self.c, records)
        self.assertEqual(result['imported'], 2)
        self.assertEqual(len(self.c.repo.jogos), 2)
        game = next(game for game in self.c.repo.jogos if game.nome == 'Novo jogo')
        self.assertEqual(sum(session.jogo_id == game.id for session in self.c.repo.sessoes), 2)

    def test_exported_wrong_id_never_silently_maps_a_name_to_another_game(self):
        other = self.c.add_game('Outro jogo')
        records = parse_mobile(encoded(payload(game_id=other.id)))
        import_mobile(self.c, records)
        self.assertEqual(self.c.repo.sessoes[-1].jogo_id, self.key)
        explicit = replace(parse_mobile(encoded(payload(game='Nome no telefone')))[0], destination_id=other.id)
        import_mobile(self.c, [explicit])
        self.assertEqual(self.c.repo.sessoes[-1].jogo_id, other.id)
        self.assertEqual(self.c.repo.sessoes[-1].jogo, 'Outro jogo')

    def test_removed_selected_destination_blocks_before_backup_or_writes(self):
        record = replace(parse_mobile(encoded(payload()))[0], destination_id='removed')
        before = self.core_bytes()
        with patch('horas_jogadas_qt.phone_import.create_full') as backup:
            with self.assertRaises(ValueError):
                import_mobile(self.c, [record])
        backup.assert_not_called()
        self.assertEqual(self.core_bytes(), before)

    def test_storage_failure_rolls_back_new_game_and_history(self):
        before = self.core_bytes()
        records = parse_mobile(encoded(payload(game='Novo jogo')))
        with patch.object(self.c.repo, '_salvar_sessoes', side_effect=OSError('disco cheio simulado')):
            with self.assertRaises(OSError):
                import_mobile(self.c, records)
        self.assertEqual(self.core_bytes(), before)
        self.assertEqual([game.nome for game in self.c.repo.jogos], ['Meu jogo'])
        self.assertEqual([session.sessao_id for session in self.c.repo.sessoes], [self.existing.sessao_id])
        self.assertFalse((self.folder / '.qt-transaction.json').exists())

    def test_failed_backup_verification_blocks_import(self):
        before = self.core_bytes()
        with patch('horas_jogadas_qt.phone_import.read_full', side_effect=ValueError('hash alterado')):
            with self.assertRaises(ValueError):
                import_mobile(self.c, parse_mobile(encoded(payload())))
        self.assertEqual(self.core_bytes(), before)

    def test_parser_rejects_entire_file_for_bad_or_repeated_rows(self):
        invalid_rows = [dict(id='no-uuid'), dict(game=''), dict(game='a\nb'), dict(seconds=True),
                        dict(seconds=0), dict(seconds=MAX_SECONDS + 1), dict(seconds=303),
                        dict(started_at='2024-04-03T18:00:00'), dict(ended_at='2020-01-01T00:00:00Z'),
                        dict(started_at='1999-01-01T00:00:00Z'),
                        dict(ended_at=(datetime.now(timezone.utc) + timedelta(days=1)).isoformat()),
                        dict(unknown='field')]
        before = self.core_bytes()
        for changes in invalid_rows:
            with self.subTest(changes=changes), self.assertRaises(ValueError):
                parse_mobile(encoded(payload(**changes)))
        repeated = payload(); repeated['sessions'].append(copy.deepcopy(repeated['sessions'][0]))
        with self.assertRaises(ValueError):
            parse_mobile(encoded(repeated))
        repeated['sessions'][1]['seconds'] = 119
        with self.assertRaises(ValueError):
            parse_mobile(encoded(repeated))
        self.assertEqual(self.core_bytes(), before)

    def test_strict_json_and_bounded_loading(self):
        bad = [b'{"format":"HorasJogadas-Mobile","format":"HorasJogadas-Mobile","version":1,"sessions":[]}',
               b'{"format":"HorasJogadas-Mobile","version":1,"sessions":NaN}',
               b'{"format":"HorasJogadas-Mobile","version":1,"sessions":1e999}',
               encoded({'format': 'HorasJogadas-Mobile', 'version': True, 'sessions': []}),
               encoded(payload()) + b' trailing', b'[' * 1500, b'\xff', b'x' * (MAX_BYTES + 1)]
        for data in bad:
            with self.subTest(data=data[:70]), self.assertRaises(ValueError):
                parse_mobile(data)
        path = self.root / 'huge.json'; path.write_bytes(b'x' * (MAX_BYTES + 100))
        with self.assertRaises(ValueError):
            load_mobile(path)

    def test_export_library_contains_only_names_ids_and_valid_preferences(self):
        library = json.loads(export_library(self.c, 'original', 'en'))
        self.assertEqual(library['format'], 'HorasJogadas-Library')
        self.assertEqual(library['games'], [{'id': self.key, 'name': 'Meu jogo'}])
        self.assertEqual((library['theme'], library['language']), ('original', 'en'))
        self.assertEqual(set(library), {'format', 'version', 'games', 'theme', 'language'})

    def test_review_cancel_does_not_create_games_backup_or_mutate_data(self):
        apply_theme(APP, 'original')
        window = Window(self.c); window.timer.stop(); window.show(); APP.processEvents()
        try:
            before = inventory(self.folder)
            dialog = ReviewDialog(window, encoded(payload(game='Novo jogo')))
            dialog.show(); APP.processEvents()
            self.assertEqual(dialog.destinations[0].currentData(), None)
            self.assertTrue(dialog.buttons.button(QDialogButtonBox.Save).isEnabled())
            dialog.reject(); dialog.deleteLater(); APP.processEvents()
            self.assertEqual(inventory(self.folder), before)
            self.assertEqual([game.nome for game in self.c.repo.jogos], ['Meu jogo'])
        finally:
            window.closing_allowed = True; window.close(); window.deleteLater()
            APP.sendPostedEvents(None, QEvent.DeferredDelete); APP.processEvents()

    def test_review_selection_imports_only_checked_rows_and_duplicates_disabled(self):
        apply_theme(APP)
        window = Window(self.c); window.timer.stop(); window.show(); APP.processEvents()
        try:
            value = payload()
            second = copy.deepcopy(value['sessions'][0]); second['id'] = str(uuid.uuid4())
            value['sessions'].append(second)
            dialog = ReviewDialog(window, encoded(value))
            dialog.grid.item(1, 0).setCheckState(Qt.Unchecked)
            with patch.object(QMessageBox, 'critical') as error:
                dialog.submit()
            error.assert_not_called()
            self.assertEqual(dialog.result_counts['imported'], 1)
            self.assertEqual(len(self.c.repo.sessoes), 2)
            dialog.deleteLater()
            repeated = ReviewDialog(window, encoded(value))
            self.assertEqual(repeated.grid.item(0, 0).checkState(), Qt.Unchecked)
            self.assertFalse(repeated.grid.item(0, 0).flags() & Qt.ItemIsUserCheckable)
            self.assertFalse(repeated.destinations[0].isEnabled())
            self.assertEqual(len(repeated.selected()), 1)
            repeated.reject(); repeated.deleteLater()
        finally:
            window.closing_allowed = True; window.close(); window.deleteLater()
            APP.sendPostedEvents(None, QEvent.DeferredDelete); APP.processEvents()
