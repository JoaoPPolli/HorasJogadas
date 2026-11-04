"""Paridade dos registros conectados com o domínio, sem ler perfis pessoais."""
import csv
import io
import tempfile
import unittest
from dataclasses import replace
from datetime import date, datetime, timedelta
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

from horas_jogadas import i18n, stats, exportacao
from horas_jogadas.storage import Repositorio
from horas_jogadas.zerados import Conclusao, resumo_ano, exportar_txt
from horas_jogadas_qt.controller import Controller
from horas_jogadas_qt.phone_records import PhoneRecords, ACTIONS, needs_backup
from horas_jogadas_qt.preview import inventory, prepare_preview
from horas_jogadas_qt.backup import create_full, read_full
from horas_jogadas_qt.remote_server import RemoteError


class PhoneRecordsTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        self.source = self.root / 'source'; self.source.mkdir()
        source = Repositorio(str(self.source), config_legado='')
        self.game_id = source.adicionar_jogo('Meu jogo').id
        source.adicionar_sessao(self.game_id, 'Meu jogo', 3600, datetime(2024, 1, 1, 20), datetime(2024, 1, 1, 21))
        source.adicionar_sessao(None, 'Jogo removido', 45, None, datetime(2024, 2, 1, 20))
        self.before = inventory(self.source)
        self.folder = prepare_preview(self.source, self.root / 'review')
        self.c = Controller(self.folder)
        self.w = SimpleNamespace(c=self.c, year=date.today().year, deleted_completions=[])
        self.control = SimpleNamespace(window=self.w, workspace_revision=lambda: 'workspace-current')
        self.api = PhoneRecords(self.control)
        i18n.definir_idioma('pt')

    def tearDown(self):
        self.assertEqual(self.before, inventory(self.source))
        i18n.definir_idioma('pt')
        self.temp.cleanup()

    def execute(self, action, **kwargs):
        body = dict(action=action, **kwargs)
        if needs_backup(action):
            read_full(create_full(self.folder))
        with self.c.transaction():
            result = self.api.execute(body)
        self.api.after_commit(body, result)
        return result

    def assert_error(self, action, code='invalid', **kwargs):
        before = {name: data for name, data in self._core().items()}
        with self.assertRaises(RemoteError) as raised:
            self.execute(action, **kwargs)
        self.assertEqual(raised.exception.code, code)
        self.assertEqual(before, self._core())

    def _core(self):
        return {name: (self.folder / name).read_bytes() if (self.folder / name).exists() else None
                for name in ('cronometros.json', 'registros.json', 'zerados.json', 'em_andamento.json')}

    def test_history_pagination_search_and_original_order(self):
        result = self.api.view('history', {'limit': '1', 'offset': '0'})
        self.assertEqual(result['revision'], 'workspace-current')
        self.assertEqual(result['sessions'][0]['name'], 'Jogo removido')
        self.assertEqual(result['total'], 2)
        self.assertEqual(self.api.view('history', {'search': 'MEU'})['sessions'][0]['game_id'], self.game_id)
        self.assertEqual(self.api.view('history', {'offset': '100'})['sessions'], [])
        self.assert_error('history_save', game_id=self.game_id, seconds=0, end='2024-02-02 20:00:00')
        with self.assertRaises(RemoteError): self.api.view('history', {'limit': '101'})
        with self.assertRaises(RemoteError): self.api.view('history', {'offset': '-1'})

    def test_history_add_edit_delete_and_shared_undo(self):
        result = self.execute('history_save', game_id=self.game_id, seconds=90, end='2024-03-02 20:00:00')
        identifier = result['saved_id']
        self.assertEqual(self.c.repo.sessoes[-1].segundos, 90)
        self.execute('history_save', session_id=identifier, game_id=self.game_id, seconds=120, end='2024-03-02 21:00:00')
        self.assertEqual(self.c.repo.sessoes[-1].sessao_id, identifier)
        self.assertEqual(self.c.repo.sessoes[-1].segundos, 120)
        self.assert_error('history_delete', code='confirm_required', session_id=identifier)
        self.execute('history_delete', session_id=identifier, confirmed=True)
        self.assertEqual(len(self.c.undo), 1)
        self.assertTrue(self.api.view('history')['can_undo'])
        self.execute('history_undo')
        self.assertEqual(self.c.repo.sessoes[-1].sessao_id, identifier)
        self.assertFalse(self.c.undo)

    def test_history_orphan_edit_preserves_old_name_and_long_duration_needs_confirmation(self):
        old = self.c.repo.sessoes[1]
        self.execute('history_save', session_id=old.sessao_id, game_id=None, seconds=60, end='2024-03-02 20:00:00')
        self.assertEqual(self.c.repo.sessoes[1].jogo, 'Jogo removido')
        self.assert_error('history_save', code='confirm_long', game_id=self.game_id, seconds=90000, end='2024-03-02 20:00:00')
        self.execute('history_save', game_id=self.game_id, seconds=90000, end='2024-03-02 20:00:00', confirmed_long=True)
        self.assertTrue(self.api.view('history')['sessions'][0]['warning'])
        self.assert_error('history_save', game_id=self.game_id, seconds=True, end='2024-03-02 20:00:00')
        self.assert_error('history_save', game_id=self.game_id, seconds=1, end='9999-01-01 00:00:00')

    def test_history_storage_failure_rolls_back_and_does_not_change_undo(self):
        identifier = self.c.repo.sessoes[0].sessao_id
        before = self._core()
        with patch.object(self.c.repo, '_salvar_sessoes', side_effect=OSError('simulated failure')):
            with self.assertRaises(OSError):
                self.execute('history_delete', session_id=identifier, confirmed=True)
        self.assertEqual(before, self._core())
        self.assertEqual(len(self.c.repo.sessoes), 2)
        self.assertFalse(self.c.undo)

    def test_stats_match_pc_domain_and_delete_group_preserves_other_records(self):
        expected = stats.agrupar_por_jogo(self.c.repo.jogos, self.c.repo.sessoes)
        result = self.api.view('stats', {'period': '7d'})
        self.assertEqual([g['key'] for g in result['groups']], [g.chave for g in expected])
        self.assertEqual(result['summary']['total_seconds'], 3645)
        self.assertEqual(result['summary']['sessions'], 2)
        self.assertEqual(result['top'][0]['name'], 'Meu jogo')
        self.execute('stats_delete_group', key=self.game_id, confirmed=True)
        self.assertEqual([s.jogo for s in self.c.repo.sessoes], ['Jogo removido'])
        with self.assertRaises(RemoteError): self.api.view('stats', {'period': 'invalid'})
        with self.assertRaises(RemoteError): self.api.view('stats', {'status': 'invalid'})

    def test_completions_preserve_null_dlc_platinum_and_month_summary(self):
        result = self.execute('completion_save', record=dict(name='Campanha', year=2024, month=2,
                             day=3, seconds=None, platinum_seconds=3600, type='zerado', dlc=True, notes='Preservar'))
        records = self.c.zerados.registros
        self.assertIsNone(records[0].segundos)
        view = self.api.view('completed', {'year': '2024'})
        self.assertEqual(view['records'][0]['id'], result['saved_id'])
        self.assertEqual(view['records'][0]['notes'], 'Preservar')
        self.assertEqual(view['summary']['dlcs'], 1)
        self.assertEqual(view['summary']['games'], 0)
        self.assertEqual(view['summary']['total_seconds'], 3600)
        self.assertEqual(view['months'][0]['name'], 'Fevereiro')
        i18n.definir_idioma('en')
        self.assertEqual(self.api.view('completed', {'year': '2024'})['months'][0]['name'], 'February')
        self.assert_error('completion_save', record=dict(name='Bad', year=2024, month=2, day=30))
        self.assert_error('completion_save', record=dict(name='Bad', year=2024, month=True))

    def test_completion_replay_creates_id_preserves_original_and_resets_extra_fields(self):
        identifier = self.execute('completion_save', record=dict(name='Campanha', year=2024, month=1, seconds=20,
                         platinum_seconds=10, notes='Original', dlc=True))['saved_id']
        original = self.c.zerados.registros[0]
        result = self.execute('completion_replay', id=identifier)
        self.assertNotEqual(result['saved_id'], identifier)
        self.assertEqual(self.c.zerados.registros[0], original)
        replay = self.c.zerados.registros[1]
        self.assertIsNone(replay.segundos); self.assertIsNone(replay.platina_segundos)
        self.assertEqual(replay.notas, ''); self.assertTrue(replay.dlc)
        self.assertEqual((replay.ano, replay.mes), (date.today().year, date.today().month))

    def test_completion_shared_delete_undo_is_committed_only_after_success(self):
        identifier = self.execute('completion_save', record=dict(name='Campanha', year=2024, month=1))['saved_id']
        self.execute('completion_delete', id=identifier, confirmed=True)
        self.assertTrue(self.w.deleted_completions)
        self.execute('completion_undo')
        self.assertEqual(self.c.zerados.registros[0].id, identifier)
        self.assertFalse(self.w.deleted_completions)
        before = self._core()
        with patch.object(self.c.zerados, '_salvar', side_effect=OSError('simulated failure')):
            with self.assertRaises(OSError): self.execute('completion_delete', id=identifier, confirmed=True)
        self.assertFalse(self.w.deleted_completions)
        self.assertEqual(before, self._core())

    def test_txt_preview_does_not_write_and_import_requires_reviewed_valid_selection(self):
        text = 'Zerados 2024\nJaneiro\nCampanha * 1h\nlinha inválida\n'
        before = self._core()
        preview = self.api.preview_import(text, 2024)
        self.assertEqual(before, self._core())
        self.assertEqual(len(preview['items']), 2)
        self.assertTrue(preview['items'][0]['selected'])
        self.assertTrue(preview['items'][1]['warning'])
        self.assert_error('completion_import', text=text, year=2024, selected=[1], confirmed=True)
        result = self.execute('completion_import', text=text, year=2024, selected=[0], confirmed=True)
        self.assertEqual(result['imported'], 1)
        result = self.execute('completion_import', text=text, year=2024, selected=[0], confirmed=True)
        self.assertEqual(result['imported'], 0)
        self.assertEqual(len(self.c.zerados.registros), 1)

    def test_csv_txt_exports_match_existing_core_without_filesystem_paths(self):
        self.execute('completion_save', record=dict(name='Campanha', year=2024, month=1, seconds=3600))
        data, mime, name = self.api.export('history_csv')
        self.assertTrue(data.startswith(b'\xef\xbb\xbf')); self.assertIn('text/csv', mime)
        self.assertEqual(list(csv.reader(io.StringIO(data.decode('utf-8-sig')), delimiter=';')),
                         exportacao.linhas_historico(self.c.repo.jogos, self.c.repo.sessoes))
        text, _, filename = self.api.export('completions_txt', {'year': '2024'})
        self.assertEqual(text.decode(), exportar_txt(self.c.zerados.registros, 2024))
        self.assertEqual(filename, 'zerados-2024.txt')
        with self.assertRaises(RemoteError): self.api.export('../../registros.json')

    def test_global_clear_requires_confirmation_and_preserves_games_and_open_timer(self):
        timer = self.c.timers[self.game_id]; timer.start()
        self.assert_error('history_clear', code='confirm_required')
        timer = self.c.timers[self.game_id]
        self.execute('history_clear', confirmed=True)
        self.assertFalse(self.c.repo.sessoes)
        self.assertIs(self.c.timers[self.game_id], timer)
        self.assertTrue(timer.rodando)
        self.assertEqual(self.c.repo.jogos[0].id, self.game_id)
        self.assertEqual(set(ACTIONS), self.api.actions)
