"""Capas opcionais: paridade dos registros, busca, cache, cancelamento e backups."""
import importlib.util
import io
import json
import hashlib
import os
import tempfile
import threading
import unittest
from pathlib import Path
from unittest.mock import patch
if importlib.util.find_spec('PySide6') is None:raise unittest.SkipTest('PySide6 necessário')
os.environ.setdefault('QT_QPA_PLATFORM','offscreen')
from PySide6.QtCore import QBuffer,QIODevice,QEvent,Qt
from PySide6.QtGui import QImage,QColor
from PySide6.QtWidgets import QApplication
from PySide6.QtTest import QTest
from horas_jogadas_qt.covers import Candidate,CoverStore,search,similarity,download,normalize_image
from horas_jogadas_qt.backup import create_full,restore_full,read_full
from horas_jogadas_qt import preferences
from horas_jogadas_qt.controller import Controller
from horas_jogadas_qt.preview import inventory
from horas_jogadas_qt.window import Window
from horas_jogadas_qt.cover_widget import GameCover
from horas_jogadas_qt.cover_dialog import CoverDialog
from horas_jogadas_qt.tasks import Cancelled
from app_qt import seed_demo

APP=QApplication.instance() or QApplication([])


def image_bytes(color='#5646b0'):
    image=QImage(460,215,QImage.Format_RGB32);image.fill(QColor(color))
    output=QBuffer();output.open(QIODevice.WriteOnly);image.save(output,'PNG');return bytes(output.data())


def candidate(app_id=42,name='Demo',score=1):
    return Candidate(app_id,name,'https://shared.fastly.steamstatic.com/store_item_assets/steam/apps/'+str(app_id)+'/hash/header.jpg',score)


class CoverDataTests(unittest.TestCase):
    def test_search_preserves_new_steam_asset_hash_and_rejects_other_hosts(self):
        payload={'items':[{'id':42,'name':'Demo','tiny_image':candidate().image_url.replace('header.jpg','capsule_231x87.jpg')},
                          {'id':43,'name':'bad','tiny_image':'https://example.org/steam/apps/43/cover.jpg'}]}
        results=search('Demo',opener=lambda *args,**kwargs:io.BytesIO(json.dumps(payload).encode()))
        self.assertEqual(len(results),1);self.assertEqual(results[0].image_url,candidate().image_url.replace('header.jpg','capsule_231x87.jpg'))
        self.assertEqual(results[0].score,1)

    def test_similar_sequels_are_not_selected_automatically(self):
        self.assertLess(similarity('The Witcher 3 Wild Hunt','The Witcher 2 Wild Hunt'),.93)
        self.assertLess(similarity('Hades II','Hades III'),.93)
        self.assertEqual(similarity('The Witcher 3 Wild Hunt','The Witcher 3: Wild Hunt — Remastered'),1)

    def test_invalid_or_oversized_image_rejected(self):
        with self.assertRaises(ValueError):normalize_image(b'not an image')
        with self.assertRaises(ValueError):normalize_image(b'x'*(10*1024*1024+1))
        data=normalize_image(image_bytes());self.assertFalse(QImage.fromData(data).isNull())

    def test_download_cancel_and_external_image_url_rejected(self):
        cancel=threading.Event();cancel.set()
        with self.assertRaises(Cancelled):download(candidate(),cancel,opener=lambda *args,**kwargs:io.BytesIO(image_bytes()))
        with self.assertRaises(ValueError):download(Candidate(42,'Bad','https://evil.example/a.jpg'),threading.Event())

    def test_cover_store_does_not_modify_any_existing_records(self):
        with tempfile.TemporaryDirectory() as folder:
            root=Path(folder);seed_demo(root);before=inventory(root)
            data=normalize_image(image_bytes());store=CoverStore(root)
            store.save_many([('game-id',data,{'source':'Steam','app_id':42})])
            for name,digest in before.items():self.assertEqual(inventory(root)[name],digest)
            self.assertEqual(store.path('game-id').read_bytes(),data)
            loaded=CoverStore(root);self.assertEqual(loaded.path('game-id'),store.path('game-id'))
            loaded.remove('game-id');self.assertIsNone(loaded.path('game-id'))
            for name,digest in before.items():self.assertEqual(inventory(root)[name],digest)

    def test_index_write_failure_keeps_old_cover_mapping(self):
        with tempfile.TemporaryDirectory() as folder:
            store=CoverStore(folder);store.save_many([('game',normalize_image(image_bytes()),{})]);before=store.index_path.read_bytes()
            with patch('horas_jogadas_qt.covers.escrever_json_atomico',side_effect=OSError('disk full')):
                with self.assertRaises(OSError):store.save_many([('game',normalize_image(image_bytes('#55aa66')),{'source':'new'})])
            self.assertEqual(store.index_path.read_bytes(),before);self.assertEqual(CoverStore(folder).entries,store.entries)

    def test_malformed_index_cannot_access_files_outside_covers(self):
        with tempfile.TemporaryDirectory() as folder:
            root=Path(folder);(root/'covers').mkdir();(root/'keep').write_text('keep')
            (root/'covers'/'index.json').write_text('{"game":{"file":"../keep"}}')
            self.assertIsNone(CoverStore(root).path('game'))

    def test_complete_backup_restores_covers_preferences_and_core_records(self):
        with tempfile.TemporaryDirectory() as folder:
            root=Path(folder);seed_demo(root);c=Controller(root);store=CoverStore(root)
            store.save_many([(c.repo.jogos[0].id,normalize_image(image_bytes()),{'source':'local'})])
            preferences.save(root,covers_enabled=True,theme='original',check_updates=False)
            backup=create_full(root);original=read_full(backup)
            preferences.save(root,covers_enabled=False,theme='light');store.remove(c.repo.jogos[0].id)
            with c.transaction():restore_full(root,backup)
            for name,data in original.items():self.assertEqual((root/name).read_bytes(),data)

    def test_transaction_rollback_preserves_qt_preferences_and_cover_index(self):
        with tempfile.TemporaryDirectory() as folder:
            root=Path(folder);seed_demo(root);c=Controller(root)
            preferences.save(root,covers_enabled=True);before=(root/'.qt-preferences.json').read_bytes()
            with self.assertRaises(OSError):
                with c.transaction():
                    preferences.save(root,covers_enabled=False)
                    CoverStore(root).save_many([('game',normalize_image(image_bytes()),{})])
                    raise OSError('simulated')
            self.assertEqual((root/'.qt-preferences.json').read_bytes(),before)
            self.assertFalse((root/'covers'/'index.json').exists())


class CoverUiTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory();self.folder=Path(self.temp.name)
        seed_demo(self.folder);self.c=Controller(self.folder);self.w=Window(self.c)
        self.w.show();APP.processEvents()

    def tearDown(self):
        self.w.timer.stop();self.w.closing_allowed=True;self.w.close();APP.removeEventFilter(self.w)
        self.w.deleteLater();APP.sendPostedEvents(None,QEvent.DeferredDelete);APP.processEvents();self.temp.cleanup()

    def test_default_layout_has_no_cover_widgets_and_toggle_preserves_running_timer(self):
        self.assertFalse(self.w.findChildren(GameCover))
        key=self.c.repo.jogos[0].id;timer=self.c.timers[key];timer.start();before=self.c.repo.totais_por_jogo_id()
        self.w.save_settings('dark','pt',covers_enabled=True);self.w.navigate('library');APP.processEvents()
        self.assertEqual(len(self.w.cards),len(self.c.repo.jogos))
        self.assertTrue(self.w.cards[key].findChildren(GameCover));self.assertIs(self.c.timers[key],timer);self.assertTrue(timer.rodando)
        self.w.save_settings('dark','pt',covers_enabled=False);self.w.navigate('library');APP.processEvents()
        self.assertFalse(self.w.cards[key].findChildren(GameCover));self.assertEqual(self.c.repo.totais_por_jogo_id(),before)
        timer.reset()

    def test_cover_toggle_does_not_delete_saved_covers_or_reload_on_tick(self):
        key=self.c.repo.jogos[0].id;CoverStore(self.folder).save_many([(key,normalize_image(image_bytes()),{})])
        preferences.save(self.folder,covers_enabled=True);self.w.refresh();APP.processEvents()
        cover=self.w.cards[key].findChild(GameCover);self.assertFalse(cover.image.isNull());self.assertGreaterEqual(cover.height(),120)
        with patch('horas_jogadas_qt.covers.download',side_effect=AssertionError('network on scroll')):
            for width in [840,1240,1000]:self.w.resize(width,820);self.w.tick();APP.processEvents()
        self.assertIs(self.w.cards[key].findChild(GameCover),cover)
        self.w.save_settings('dark','pt',covers_enabled=False);self.assertIsNotNone(CoverStore(self.folder).path(key))

    def test_bulk_search_and_import_only_checked_matches(self):
        dialog=CoverDialog(self.w);dialog.show();APP.processEvents()
        for row,combo in enumerate(dialog.selectors):self.assertLessEqual(combo.height(),dialog.table.rowHeight(row))
        names=[game.nome for game in dialog.games];baseline=self.c.repo.totais_por_jogo_id()
        def found(query):return [candidate(42,query,1)]
        with patch('horas_jogadas_qt.cover_dialog.search',side_effect=found),patch('horas_jogadas_qt.cover_dialog.download',return_value=normalize_image(image_bytes())):
            dialog.find_all();self.wait(dialog)
            for row in range(len(names)):self.assertIsNotNone(dialog.selected(row))
            dialog.table.item(1,0).setCheckState(Qt.Unchecked)
            dialog.import_selected();self.wait(dialog)
        store=CoverStore(self.folder)
        self.assertIsNone(store.path(dialog.games[1].id));self.assertEqual(len(store.entries),len(names)-1)
        self.assertEqual(self.c.repo.totais_por_jogo_id(),baseline)
        dialog.reject();dialog.deleteLater();APP.sendPostedEvents(None,QEvent.DeferredDelete)

    def wait(self,dialog):
        for _ in range(500):
            APP.processEvents();QTest.qWait(10)
            if not dialog.busy:
                APP.processEvents()
                if not dialog.busy:return
        self.fail('background operation did not settle')

class LinuxCompatibilityTests(unittest.TestCase):
    def test_recovers_records_from_old_updater_when_program_and_data_coincided(self):
        import time
        from horas_jogadas_qt.linux_compat import recover_moved_data
        with tempfile.TemporaryDirectory() as temporary:
            root=Path(temporary);current=root/'HorasJogadas';current.mkdir()
            previous=root/('HorasJogadas-previous-'+str(int(time.time())));previous.mkdir();seed_demo(previous)
            (previous/'package.json').write_text('{"version":"3.0.1"}')
            (previous/'.horasjogadas-release.json').write_text('{"version":"3.0.1"}')
            (previous/'HorasJogadas').write_bytes(b'old program');(current/'HorasJogadas').write_bytes(b'new program')
            before=(previous/'cronometros.json').read_bytes()
            self.assertTrue(recover_moved_data(current))
            self.assertEqual((current/'cronometros.json').read_bytes(),before)
            self.assertEqual((previous/'cronometros.json').read_bytes(),before)
            self.assertEqual((current/'HorasJogadas').read_bytes(),b'new program')
            self.assertFalse(recover_moved_data(current))

    def test_recovery_does_not_replace_an_existing_current_library(self):
        from horas_jogadas_qt.linux_compat import recover_moved_data
        with tempfile.TemporaryDirectory() as temporary:
            current=Path(temporary)/'HorasJogadas';current.mkdir();seed_demo(current)
            before=inventory(current);self.assertFalse(recover_moved_data(current));self.assertEqual(inventory(current),before)

    def test_interrupted_recovery_resumes_even_after_some_files_were_copied(self):
        import time
        from horas_jogadas_qt.linux_compat import recover_moved_data,JOURNAL
        with tempfile.TemporaryDirectory() as temporary:
            root=Path(temporary);current=root/'HorasJogadas';current.mkdir()
            previous=root/('HorasJogadas-previous-'+str(int(time.time())));previous.mkdir();seed_demo(previous)
            (previous/'package.json').write_text('{"version":"3.0.1"}')
            (previous/'.horasjogadas-release.json').write_text('{"version":"3.0.1"}')
            replace=os.replace
            def fail(source,dest):
                if Path(dest).name=='registros.json':raise OSError('simulated disk error')
                return replace(source,dest)
            with patch('horas_jogadas_qt.linux_compat.os.replace',side_effect=fail):
                with self.assertRaises(OSError):recover_moved_data(current)
            self.assertTrue((current/JOURNAL).exists());self.assertTrue(recover_moved_data(current))
            for name in ['cronometros.json','registros.json']:
                self.assertEqual((current/name).read_bytes(),(previous/name).read_bytes())
            self.assertFalse((current/JOURNAL).exists())

class SteamHeaderTests(unittest.TestCase):
    def test_import_uses_exact_high_quality_header_from_appdetails(self):
        tiny='https://shared.fastly.steamstatic.com/store_item_assets/steam/apps/42/tiny-hash/capsule_231x87.jpg'
        header='https://shared.fastly.steamstatic.com/store_item_assets/steam/apps/42/other-hash/header.jpg'
        calls=[]
        def opener(request,timeout):
            calls.append(request.full_url)
            if '/api/appdetails?' in request.full_url:
                return io.BytesIO(json.dumps({'42':{'success':True,'data':{'header_image':header}}}).encode())
            self.assertEqual(request.full_url,header);return io.BytesIO(image_bytes())
        data=download(Candidate(42,'Demo',tiny),threading.Event(),opener)
        self.assertFalse(QImage.fromData(data).isNull());self.assertEqual(calls[-1],header)
