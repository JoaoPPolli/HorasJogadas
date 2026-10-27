import json
import tempfile
import unittest
from datetime import datetime, timedelta, date
from pathlib import Path
from unittest.mock import patch
from horas_jogadas.storage import Repositorio
from horas_jogadas.zerados import Conclusao, RepositorioZerados, exportar_txt, interpretar_txt
from horas_jogadas_qt.preview import prepare_preview, inventory, MARKER
from horas_jogadas_qt.controller import Controller
from horas_jogadas_qt.timer import Timer
from horas_jogadas_qt.backup import create_full, read_full, restore_full
from horas_jogadas_qt.texts import TEXTS
from horas_jogadas.models import Jogo


class Clock:
    def __init__(self, now=None):
        self.epoch = (now or datetime(2024, 1, 1, 23, 59, 50)).timestamp()
        self.mono = 1000
    def time(self): return self.epoch
    def monotonic(self): return self.mono
    def advance(self, seconds):
        self.epoch += seconds; self.mono += seconds


class DataTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        self.source = self.root/'source'; self.source.mkdir()
        r = Repositorio(str(self.source), config_legado='')
        self.game = r.adicionar_jogo('Meu jogo')
        r.adicionar_sessao(self.game.id,self.game.nome,120,None,datetime(2024,1,1,20))
        z = RepositorioZerados(str(self.source))
        z.guardar(Conclusao('Campanha',2024,1,300,dlc=True,notas='Preservar'))
        self.before = inventory(self.source)
        self.folder = prepare_preview(self.source,self.root/'review')
        self.c = Controller(self.folder)

    def tearDown(self):
        self.assertEqual(inventory(self.source),self.before,'A origem não pode ser alterada')

    def change(self, callback):
        with self.c.transaction(): callback()

    def test_copy_preserves_every_source_byte_and_existing_review(self):
        for name, digest in self.before.items():
            self.assertEqual(inventory(self.folder)[name],digest)
        self.change(lambda:self.c.add_game('Novo'))
        prepare_preview(self.source,self.folder)
        self.assertEqual(len(Repositorio(str(self.folder)).jogos),2)

    def test_existing_destination_without_marker_is_rejected(self):
        target=self.root/'other'; target.mkdir()
        (target/'keep.txt').write_text('keep')
        with self.assertRaises(ValueError): prepare_preview(self.source,target)
        self.assertEqual((target/'keep.txt').read_text(),'keep')

    def test_source_and_descendants_cannot_be_destinations(self):
        for target in (self.source,self.source/'preview',self.root):
            with self.subTest(target=target),self.assertRaises(ValueError):
                prepare_preview(self.source,target)

    def test_changed_source_aborts_copy_without_partial_destination(self):
        target=self.root/'unstable'
        with patch('horas_jogadas_qt.preview.inventory',side_effect=[{'registros.json':'x'},{'registros.json':'y'}]):
            with self.assertRaises(OSError): prepare_preview(self.source,target)
        self.assertFalse(target.exists())

    def test_transaction_rolls_back_files_memory_and_timer_on_save_failure(self):
        timer=self.c.timers[self.game.id]; timer.clock=Clock(); timer.start(); timer.clock.advance(12)
        self.c.save_pending()
        before=(self.folder/'registros.json').read_bytes()
        pending=(self.folder/'em_andamento.json').read_bytes()
        with patch.object(self.c.repo,'limpar_andamento',side_effect=OSError('Disco cheio')):
            with self.assertRaises(OSError):
                self.change(lambda:self.c.finish(self.game.id))
        self.assertEqual((self.folder/'registros.json').read_bytes(),before)
        self.assertEqual((self.folder/'em_andamento.json').read_bytes(),pending)
        self.assertTrue(self.c.timers[self.game.id].rodando)
        self.assertEqual(len(self.c.repo.sessoes),1)

    def test_persisted_journal_recovers_interrupted_operation(self):
        files={n:(self.folder/n).read_text(encoding='utf-8') if (self.folder/n).exists() else None
            for n in ('cronometros.json','registros.json','config.json','zerados.json','em_andamento.json')}
        (self.folder/'.qt-transaction.json').write_text(json.dumps(files),encoding='utf-8')
        (self.folder/'registros.json').write_text('[]',encoding='utf-8')
        Controller.restore_journal(self.folder)
        self.assertEqual(len(Repositorio(str(self.folder)).sessoes),1)
        self.assertFalse((self.folder/'.qt-transaction.json').exists())

    def test_journal_cannot_write_arbitrary_paths(self):
        (self.folder/'.qt-transaction.json').write_text(json.dumps({'../escape':'test'}))
        with self.assertRaises(ValueError): Controller.restore_journal(self.folder)
        self.assertFalse((self.root/'escape').exists())

    def test_new_session_round_trips_through_legacy_repository(self):
        timer=self.c.timers[self.game.id]; timer.clock=Clock(); timer.start(); timer.clock.advance(30)
        self.change(lambda:self.c.finish(self.game.id))
        legacy=Repositorio(str(self.folder))
        new=legacy.sessoes[-1]
        self.assertEqual(new.segundos,30)
        self.assertEqual(new.jogo_id,self.game.id)
        self.assertEqual(new.dias,{'2024-01-01':10,'2024-01-02':20})
        self.assertEqual(sum(new.dias.values()),new.segundos)
        self.assertEqual(len(legacy.sessoes),2)

    def test_rename_and_delete_keep_history_and_ids(self):
        sid=self.c.repo.sessoes[0].sessao_id
        self.change(lambda:self.c.repo.renomear_jogo(self.game.id,'Novo nome'))
        self.assertEqual(self.c.repo.sessoes[0].jogo,'Novo nome')
        self.change(lambda:self.c.delete_game(self.game.id))
        self.assertEqual(len(self.c.repo.sessoes),1)
        self.assertEqual(self.c.repo.sessoes[0].sessao_id,sid)

    def test_delete_and_undo_restore_exact_session(self):
        original=self.c.repo.sessoes[0].to_dict()
        self.change(lambda:self.c.delete_session(self.c.repo.sessoes[0]))
        self.assertEqual(len(self.c.repo.sessoes),0)
        self.change(self.c.undo_session)
        self.assertEqual(self.c.repo.sessoes[0].to_dict(),original)

    def test_auto_completion_deduplicates_and_does_not_stop_timer(self):
        timer=self.c.timers[self.game.id]; timer.clock=Clock(); timer.start(); timer.clock.advance(10)
        self.change(lambda:self.c.set_status(self.game.id,'Zerado'))
        self.assertTrue(self.c.timers[self.game.id].rodando)
        self.assertEqual(self.c.zerados.registros[-1].segundos,130)
        self.change(lambda:self.c.set_status(self.game.id,'Jogando'))
        self.change(lambda:self.c.set_status(self.game.id,'Zerado'))
        self.assertEqual(len(self.c.zerados.registros),2)

    def test_recovery_preserves_day_distribution_and_only_runs_once(self):
        timer=self.c.timers[self.game.id]; timer.clock=Clock(); timer.start(); timer.clock.advance(30)
        self.c.save_pending()
        fresh=Controller(self.folder)
        with fresh.transaction(): fresh.recover()
        self.assertEqual(fresh.repo.sessoes[-1].segundos,30)
        self.assertEqual(fresh.repo.sessoes[-1].dias,{'2024-01-01':10,'2024-01-02':20})
        with fresh.transaction(): fresh.recover()
        self.assertEqual(len(fresh.repo.sessoes),2)

    def test_complete_backup_restores_zerados_and_sessions(self):
        backup=create_full(self.folder)
        originals=read_full(backup)
        self.change(lambda:self.c.zerados.excluir(self.c.zerados.registros[0].id))
        self.change(self.c.repo.limpar_sessoes)
        self.change(lambda:restore_full(self.folder,backup))
        for name,data in originals.items(): self.assertEqual((self.folder/name).read_bytes(),data)
        self.assertTrue(RepositorioZerados(str(self.folder)).registros[0].dlc)

    def test_corrupted_backup_is_rejected_before_restore(self):
        backup=create_full(self.folder)
        (backup/'registros.json').write_text('[]')
        before=(self.folder/'registros.json').read_bytes()
        with self.assertRaises(ValueError): read_full(backup)
        self.assertEqual((self.folder/'registros.json').read_bytes(),before)

    def test_txt_round_trip_retains_dlc_notes_and_prevents_duplicates(self):
        record=self.c.zerados.registros[0]
        imported=[i.registro for i in interpretar_txt(exportar_txt([record],2024))]
        self.assertEqual(imported[0].assinatura(),record.assinatura())
        self.assertTrue(imported[0].dlc)
        self.assertEqual(self.c.zerados.importar(imported),0)

    def test_translation_keys_match(self):
        self.assertEqual(set(TEXTS['pt']),set(TEXTS['en']))


class TimerTests(unittest.TestCase):
    def setUp(self):
        self.clock=Clock(); self.timer=Timer(Jogo('id','Game'),self.clock)

    def test_pause_resume_does_not_include_pause(self):
        self.timer.start(); self.clock.advance(10); self.timer.pause()
        self.clock.advance(50); self.timer.start(); self.clock.advance(20)
        total,_,_,days=self.timer.finish_values()
        self.assertEqual(total,30); self.assertEqual(sum(days.values()),30)

    def test_partial_pause_counts_only_last_minutes(self):
        self.timer.start(); self.clock.advance(10); self.timer.pause()
        self.clock.advance(300); self.timer.count_pause(120)
        self.assertEqual(self.timer.seconds(),130)
        self.assertTrue(self.timer.rodando)
        self.assertEqual(sum(self.timer.dias.values()),130)

    def test_adjustment_subtracts_recent_days_without_negative_time(self):
        self.timer.start(); self.clock.advance(30); self.timer.pause()
        self.timer.adjust(-25)
        self.assertEqual(self.timer.seconds(),5)
        self.assertEqual(sum(self.timer.dias.values()),5)
        self.timer.adjust(-100)
        self.assertEqual(self.timer.seconds(),0)
        self.assertFalse(self.timer.pending)

    def test_monotonic_clock_survives_wall_clock_correction(self):
        self.timer.start(); self.clock.mono+=20; self.clock.epoch-=3600
        self.assertEqual(self.timer.seconds(),20)
        self.timer.pause()
        self.assertEqual(sum(self.timer.dias.values()),20)


class PendingJournalTests(unittest.TestCase):
    def test_new_transaction_does_not_overwrite_unresolved_recovery(self):
        with tempfile.TemporaryDirectory() as tmp:
            c=Controller(tmp)
            journal=Path(tmp)/'.qt-transaction.json'
            journal.write_text('preserve me',encoding='utf-8')
            with self.assertRaises(RuntimeError):
                with c.transaction(): c.add_game('Cannot save')
            self.assertEqual(journal.read_text(encoding='utf-8'),'preserve me')
            self.assertEqual(c.repo.jogos,[])
