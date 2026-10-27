"""Fontes reais, correção de nomes, ícones e compatibilidade dos dados locais."""
import importlib.util
import io
import json
import os
import tempfile
import threading
import unittest
from pathlib import Path
from urllib.parse import parse_qs, urlparse
from unittest.mock import patch

if importlib.util.find_spec('PySide6') is None:
    raise unittest.SkipTest('PySide6 necessário')
os.environ.setdefault('QT_QPA_PLATFORM', 'offscreen')
from PySide6.QtCore import Qt, QEvent, QBuffer, QIODevice
from PySide6.QtGui import QImage, QColor
from PySide6.QtWidgets import QApplication
from PySide6.QtTest import QTest
from horas_jogadas_qt.artwork_sources import search_artwork, image_url_valid, SearchResults
from horas_jogadas_qt.covers import Candidate, CoverStore, download, normalize_image, similarity
from horas_jogadas_qt.cover_dialog import CoverDialog
from horas_jogadas_qt.backup import create_full, read_full, restore_full
from horas_jogadas_qt.controller import Controller
from horas_jogadas_qt.preview import inventory
from horas_jogadas_qt.widgets import GameAvatar
from horas_jogadas_qt import preferences
from horas_jogadas_qt.tasks import Cancelled
from tests_qt import test_covers as cover_tests
candidate = cover_tests.candidate
image_bytes = cover_tests.image_bytes

APP = QApplication.instance() or QApplication([])
GOG_IMAGE = 'https://images.gog-statics.com/' + 'a'*64 + '.jpg'
WIKI_IMAGE = 'https://upload.wikimedia.org/wikipedia/en/8/88/Demo.png'
STEAM_ICON = 'https://shared.fastly.steamstatic.com/steamcommunity/public/images/apps/42/' + 'a'*40 + '.jpg'


def gog(name='Stardew Valley', key=42):
    return {'id': str(key), 'title': name, 'coverHorizontal': GOG_IMAGE,
            'storeLink': 'https://www.gog.com/en/game/stardew_valley'}


def wiki(name='Stardew Valley', key=42, image=True):
    item = {'pageid': key, 'title': name, 'description': '2016 video game'}
    if image:
        item['thumbnail'] = {'source': WIKI_IMAGE}
    return {'query': {'pages': {str(key): item}}}


def response(value):
    return io.BytesIO(json.dumps(value).encode())


class CatalogTests(unittest.TestCase):
    def test_search_returns_each_source_even_when_ids_collide(self):
        def opener(request, timeout):
            host = urlparse(request.full_url).hostname
            if host == 'catalog.gog.com': return response({'products': [gog()]})
            if host == 'en.wikipedia.org': return response(wiki())
            return response({'items': [{'id': 42, 'name': 'Stardew Valley', 'tiny_image': candidate().image_url}]})
        results = search_artwork('Stardew Valley', opener)
        self.assertEqual({item.source for item in results}, {'Steam', 'GOG', 'Wikipedia'})
        self.assertEqual(len({item.cache_key for item in results}), 3)
        self.assertTrue(all(item.score == 1 for item in results))

    def test_fuzzy_wikipedia_title_retries_stores_and_preserves_original_score(self):
        calls = []
        def opener(request, timeout):
            url = request.full_url; calls.append(url); params = parse_qs(urlparse(url).query)
            if 'wikipedia.org' in url:
                self.assertEqual(params['pilicense'], ['any'])
                return response(wiki(image=False) if '~' in params['gsrsearch'][0] else {})
            term = params.get('query', params.get('term', ['']))[0]
            if 'catalog.gog.com' in url:
                return response({'products': [gog()] if term == 'Stardew Valley' else []})
            return response({'items': []})
        results = search_artwork('stardew valey', opener)
        self.assertTrue(any('~' in parse_qs(urlparse(url).query).get('gsrsearch', [''])[0] for url in calls))
        self.assertEqual(results[0].name, 'Stardew Valley')
        self.assertEqual(results[0].score, similarity('stardew valey', 'Stardew Valley'))
        self.assertNotEqual(results[0].score, 1)

    def test_typo_uses_partial_lookup_without_contacting_unselected_sources(self):
        terms = []
        def opener(request, timeout):
            self.assertEqual(urlparse(request.full_url).hostname, 'catalog.gog.com')
            term = parse_qs(urlparse(request.full_url).query)['query'][0]; terms.append(term)
            return response({'products': [gog('Minecraft')] if term == 'minecraf' else []})
        results = search_artwork('minecraftt', opener, source='GOG')
        self.assertEqual(terms, ['minecraftt', 'minecraf'])
        self.assertEqual(results[0].name, 'Minecraft')

    def test_unavailable_source_keeps_other_results_and_reports_warning(self):
        def opener(request, timeout):
            if 'catalog.gog.com' in request.full_url: raise OSError('offline')
            if 'wikipedia.org' in request.full_url: return response(wiki())
            return response({'items': []})
        results = search_artwork('Stardew Valley', opener)
        self.assertEqual(results[0].source, 'Wikipedia')
        self.assertTrue(any('GOG' in error for error in results.warnings))

    def test_store_recognition_corrects_other_sources_without_inflating_score(self):
        queries = []
        def opener(request, timeout):
            url = request.full_url; params = parse_qs(urlparse(url).query)
            term = params.get('query', params.get('term', params.get('gsrsearch', [''])))[0]
            queries.append((urlparse(url).hostname, term))
            if 'catalog.gog.com' in url: return response({'products': [gog()]})
            if 'wikipedia.org' in url: return response(wiki() if term == 'Stardew Valley' else {})
            return response({'items': [{'id': 42, 'name': 'Stardew Valley', 'tiny_image': candidate().image_url}] if term == 'Stardew Valley' else []})
        results = search_artwork('stardew valey', opener)
        self.assertEqual({item.source for item in results}, {'Steam', 'GOG', 'Wikipedia'})
        self.assertTrue(all(item.score == similarity('stardew valey', 'Stardew Valley') for item in results))
        self.assertIn(('store.steampowered.com', 'Stardew Valley'), queries)

    def test_all_sources_failed_is_an_error_and_cancellation_propagates(self):
        with self.assertRaises(ValueError):
            search_artwork('Demo', lambda *a, **k: (_ for _ in ()).throw(OSError('offline')))
        cancel = threading.Event(); cancel.set()
        with self.assertRaises(Cancelled): search_artwork('Demo', cancel=cancel)

    def test_wikipedia_does_not_offer_characters_or_untrusted_images(self):
        value = wiki('Demo'); value['query']['pages']['42']['description'] = 'Character from a video game'
        # Descrição de personagem contém "video game"; não deve virar resultado de jogo.
        results = search_artwork('Demo', lambda *a, **k: response(value), source='Wikipedia')
        self.assertEqual(results, [])

    def test_sequels_keep_numeric_guard_but_arabic_and_roman_match(self):
        self.assertLess(similarity('Hades 2', 'Hades III'), .93)
        self.assertLess(similarity('The Witcher 3', 'The Witcher 2'), .93)
        self.assertLess(similarity('Civilization VI', 'Civilization V'), .93)
        self.assertEqual(similarity('Hades 2', 'Hades II'), 1)

    def test_wikipedia_retains_year_to_distinguish_homonymous_games(self):
        results=search_artwork('Prey',lambda *a,**k:response(wiki('Prey (2017 video game)')),source='Wikipedia')
        self.assertEqual(results[0].name,'Prey (2017)')
        self.assertLess(results[0].score,.93)

    def test_image_host_validation_does_not_accept_spoofed_domains(self):
        for source, good in [('GOG', GOG_IMAGE), ('Wikipedia', WIKI_IMAGE), ('Steam', STEAM_ICON)]:
            item = Candidate(42, 'Demo', good, 1, source)
            kind = 'icon' if source == 'Steam' else 'cover'
            self.assertTrue(image_url_valid(item, good, kind))
            self.assertFalse(image_url_valid(item, good.replace('https://', 'http://'), kind))
            self.assertFalse(image_url_valid(item, good.replace('.com/', '.com.evil.example/').replace('.org/', '.org.evil.example/'), kind))

    def test_gog_and_wikipedia_download_normalized_cover(self):
        for source, url in [('GOG', GOG_IMAGE), ('Wikipedia', WIKI_IMAGE)]:
            data = download(Candidate(42, 'Demo', url, 1, source), threading.Event(), lambda *a, **k: io.BytesIO(image_bytes()))
            self.assertTrue(data.startswith(b'\xff\xd8'))


class IconDataTests(unittest.TestCase):
    def test_steam_icon_uses_official_hash_from_app_hub(self):
        calls = []
        def opener(request, timeout):
            calls.append(request.full_url)
            if 'steamcommunity.com/app/' in request.full_url:
                return io.BytesIO(('<img src="https://evil.example/wrong.png"><div class="apphub_AppIcon"><img src="'+STEAM_ICON+'"></div>').encode())
            self.assertEqual(request.full_url, STEAM_ICON)
            return io.BytesIO(image_bytes())
        data = download(candidate(), threading.Event(), opener, kind='icon')
        self.assertTrue(data.startswith(b'\x89PNG'))
        image = QImage.fromData(data)
        self.assertLessEqual(max(image.width(), image.height()), 256)
        self.assertEqual(len(calls), 2)

    def test_steam_has_no_icon_never_crops_header_as_substitute(self):
        with self.assertRaises(ValueError):
            download(candidate(), threading.Event(), lambda *a, **k: io.BytesIO(b'<html>no icon</html>'), kind='icon')

    def test_gog_icon_uses_product_metadata_and_protocol_relative_url(self):
        calls = []
        def opener(request, timeout):
            calls.append(request.full_url)
            if 'api.gog.com' in request.full_url:
                return response({'images': {'icon': GOG_IMAGE.replace('https:', '')}})
            self.assertEqual(request.full_url, GOG_IMAGE)
            return io.BytesIO(image_bytes())
        item = Candidate(42, 'Demo', GOG_IMAGE, 1, 'GOG')
        self.assertTrue(download(item, threading.Event(), opener, kind='icon').startswith(b'\x89PNG'))
        self.assertEqual(len(calls), 2)

    def test_icon_normalization_preserves_alpha(self):
        image = QImage(80, 80, QImage.Format_ARGB32); image.fill(QColor(0, 0, 0, 0))
        image.setPixelColor(40, 40, QColor('#6456ff'))
        buffer = QBuffer(); buffer.open(QIODevice.WriteOnly); image.save(buffer, 'PNG')
        result = QImage.fromData(normalize_image(bytes(buffer.data()), 'icon'))
        self.assertEqual(result.pixelColor(0, 0).alpha(), 0)
        self.assertEqual(result.pixelColor(40, 40).alpha(), 255)

    def test_cover_and_icon_indices_are_independent_and_backup_restores_both(self):
        from app_qt import seed_demo
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder); seed_demo(root); c = Controller(root); key = c.repo.jogos[0].id
            baseline = inventory(root)
            covers = CoverStore(root); icons = CoverStore(root, 'icon')
            covers.save_many([(key, normalize_image(image_bytes()), {'source': 'local'})])
            icons.save_many([(key, normalize_image(image_bytes(), 'icon'), {'source': 'local'})])
            for name, digest in baseline.items(): self.assertEqual(inventory(root)[name], digest)
            backup = create_full(root); contents = read_full(backup)
            self.assertIn('icons/index.json', contents)
            self.assertTrue(any(name.startswith('icons/') and name.endswith('.png') for name in contents))
            icons.remove(key); self.assertIsNotNone(covers.path(key))
            with c.transaction(): restore_full(root, backup)
            self.assertIsNotNone(CoverStore(root, 'icon').path(key))
            for name, data in contents.items(): self.assertEqual((root/name).read_bytes(), data)
            original_index = (root/'icons/index.json').read_bytes()
            with self.assertRaises(OSError):
                with c.transaction():
                    CoverStore(root, 'icon').remove(key)
                    raise OSError('disk error')
            self.assertEqual((root/'icons/index.json').read_bytes(), original_index)

    def test_old_transaction_journals_are_still_readable(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            names = ['cronometros.json', 'registros.json', 'zerados.json', 'config.json', 'em_andamento.json']
            for extras in [[], ['.qt-preferences.json', 'covers/index.json']]:
                (root/'.qt-transaction.json').write_text(json.dumps({name: None for name in names+extras}))
                Controller.restore_journal(root)
                self.assertFalse((root/'.qt-transaction.json').exists())


class ArtworkUiTests(unittest.TestCase):
    setUp = cover_tests.CoverUiTests.setUp
    tearDown = cover_tests.CoverUiTests.tearDown
    wait = cover_tests.CoverUiTests.wait
    def test_icons_work_without_covers_and_toggle_preserves_timer_and_images(self):
        key = self.c.repo.jogos[0].id; timer = self.c.timers[key]; timer.start()
        store = CoverStore(self.folder, 'icon')
        store.save_many([(key, normalize_image(image_bytes(), 'icon'), {})])
        self.w.refresh(); APP.processEvents()
        avatar = self.w.cards[key].findChild(GameAvatar)
        self.assertFalse(avatar.image.isNull()); self.assertFalse(self.w.covers_enabled)
        with patch.object(self.w, 'manage_icons') as manage:
            QTest.mouseClick(avatar, Qt.LeftButton); manage.assert_called_once_with(key)
        with patch('horas_jogadas_qt.artwork_sources.urlopen', side_effect=AssertionError('network on tick')):
            self.w.tick(); self.w.resize(1100, 820); APP.processEvents()
        self.assertIs(self.w.cards[key].findChild(GameAvatar), avatar)
        self.w.save_settings('dark', 'pt', icons_enabled=False); self.w.navigate('library'); APP.processEvents()
        self.assertTrue(self.w.cards[key].findChild(GameAvatar).image.isNull())
        self.assertIsNotNone(CoverStore(self.folder, 'icon').path(key))
        self.assertIs(self.c.timers[key], timer); self.assertTrue(timer.rodando)
        timer.reset()

    def test_icon_bulk_import_is_separate_and_fuzzy_result_needs_choice(self):
        dialog = CoverDialog(self.w, kind='icon'); dialog.show(); APP.processEvents()
        item = Candidate(42, 'Demo', GOG_IMAGE, .88, 'GOG')
        with patch.object(dialog, 'show_preview'):
            dialog.found([(0, [item], None)])
            self.assertIsNone(dialog.selected(0))
            self.assertFalse(dialog.checked(0))
            dialog.selectors[0].setCurrentIndex(1)
            self.assertTrue(dialog.checked(0))
            with patch('horas_jogadas_qt.cover_dialog.download', return_value=normalize_image(image_bytes(), 'icon')) as downloader:
                dialog.import_selected(); self.wait(dialog)
                downloader.assert_called_once()
                self.assertEqual(downloader.call_args.kwargs, {'kind': 'icon'})
        self.assertIsNotNone(CoverStore(self.folder, 'icon').path(dialog.games[0].id))
        self.assertIsNone(CoverStore(self.folder).path(dialog.games[0].id))
        self.assertEqual(dialog.kind, 'icon'); self.assertEqual(dialog.preview.width(), dialog.preview.height())
        dialog.reject(); dialog.deleteLater(); APP.sendPostedEvents(None, QEvent.DeferredDelete)

    def test_ambiguous_near_identical_titles_need_manual_choice(self):
        dialog = CoverDialog(self.w)
        with patch.object(dialog, 'show_preview'):
            dialog.found([(0, [candidate(42, 'Demo', .95), candidate(43, 'Demo DLC', .94)], None)])
        self.assertIsNone(dialog.selected(0))
        dialog.reject(); dialog.deleteLater()

    def test_same_title_with_different_ids_in_same_store_needs_manual_choice(self):
        dialog = CoverDialog(self.w)
        with patch.object(dialog, 'show_preview'):
            dialog.found([(0, [candidate(42, 'Prey', 1), candidate(43, 'Prey', 1)], None)])
        self.assertIsNone(dialog.selected(0))
        self.assertIn('#42',dialog.selectors[0].itemText(1))
        self.assertIn('#43',dialog.selectors[0].itemText(2))
        dialog.reject(); dialog.deleteLater()
