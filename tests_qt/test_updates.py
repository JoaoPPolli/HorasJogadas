import hashlib
import io
import json
import os
import subprocess
import tempfile
import threading
import unittest
import importlib.util
from pathlib import Path
from unittest.mock import patch
if importlib.util.find_spec('PySide6') is None: raise unittest.SkipTest('PySide6 necessário')
from horas_jogadas_qt import updates,preferences


def payload(version='9.0.0',blob=b'new build'):
    names=['HorasJogadas-Windows-Setup.exe','HorasJogadas-Linux-x86_64.tar.gz','SHA256SUMS.txt']
    return {'tag_name':'v'+version,'body':'Notes','assets':[{'name':n,'size':len(blob),'browser_download_url':'https://github.com/JoaoPPolli/HorasJogadas/releases/download/v'+version+'/'+n} for n in names]}


class UpdateTests(unittest.TestCase):
    def test_stable_version_order_and_invalid_tags(self):
        self.assertGreater(updates.version_tuple('v3.10.0'),updates.version_tuple('3.9.9'))
        for bad in ['v3.1.0-rc1','3.1','https://bad','3.1.0/../']:
            with self.assertRaises(ValueError):updates.version_tuple(bad)
        self.assertIsNone(updates.parse_release(payload('3.0.0'),current='3.0.1'))
        data=payload();data['prerelease']=True;self.assertIsNone(updates.parse_release(data))

    def test_only_official_matching_assets_are_accepted(self):
        data=payload();self.assertEqual(updates.parse_release(data,system='win32').asset_name,'HorasJogadas-Windows-Setup.exe')
        data['assets'][0]['browser_download_url']='https://example.org/installer.exe'
        with self.assertRaises(ValueError):updates.parse_release(data,system='win32')

    def test_hash_and_length_verified_before_exposing_download(self):
        blob=b'executable payload'; release=updates.parse_release(payload(blob=blob),system='win32')
        def opener(request,timeout):
            return io.BytesIO((hashlib.sha256(blob).hexdigest()+'  '+release.asset_name+'\n').encode() if request.full_url.endswith('SHA256SUMS.txt') else blob)
        with tempfile.TemporaryDirectory() as folder:
            path=updates.download(release,folder,threading.Event(),lambda *args:None,opener)
            self.assertEqual(path.read_bytes(),blob)
            def corrupt(request,timeout):
                return opener(request,timeout) if request.full_url.endswith('SHA256SUMS.txt') else io.BytesIO(b'X'*len(blob))
            with self.assertRaises(ValueError):updates.download(release,folder,threading.Event(),lambda *args:None,corrupt)
            self.assertEqual(path.read_bytes(),blob)
            self.assertFalse(list(Path(folder).glob('*.part')))

    def test_cancel_does_not_leave_partial_or_installable_file(self):
        from horas_jogadas_qt.tasks import Cancelled
        release=updates.parse_release(payload(),system='win32');cancel=threading.Event();cancel.set()
        def opener(request,timeout):return io.BytesIO((hashlib.sha256(b'new build').hexdigest()+'  '+release.asset_name+'\n').encode() if request.full_url.endswith('SHA256SUMS.txt') else b'new build')
        with tempfile.TemporaryDirectory() as folder:
            with self.assertRaises(Cancelled):updates.download(release,folder,cancel,lambda *args:None,opener)
            self.assertEqual(list(Path(folder).iterdir()),[])

    def test_windows_installer_uses_current_path_and_restart_without_shell(self):
        with patch('horas_jogadas_qt.updates.subprocess.Popen') as popen:
            updates.launch_update(Path('/tmp/update path/Setup.exe'),executable='/tmp/App with spaces/HorasJogadas.exe',system='win32')
            args=popen.call_args.args[0]
            self.assertIn('/DIR='+str(Path('/tmp/App with spaces/HorasJogadas.exe').resolve().parent),args);self.assertIn('/RESTARTAPP',args)
            self.assertNotIn('shell',popen.call_args.kwargs)

    @unittest.skipIf(os.name=='nt','Helper de atualização Linux')
    def test_linux_atomic_swap_preserves_previous_version_and_external_records(self):
        with tempfile.TemporaryDirectory() as folder:
            root=Path(folder);target=root/"app ' com $ espaços";target.mkdir();staged=root/'staged';staged.mkdir()
            (target/'HorasJogadas').write_text('#!/bin/sh\nexit 0\n');(target/'old.txt').write_text('old')
            (staged/'HorasJogadas').write_text('#!/bin/sh\nexit 0\n');(staged/'HorasJogadas').chmod(0o755)
            data=root/'data';data.mkdir();(data/'registros.json').write_bytes(b'unchanged')
            helper=root/'helper.sh';helper.write_text(updates.LINUX_HELPER)
            subprocess.run(['/bin/sh',str(helper),'2147483647',str(target),str(staged),str(root/'previous'),str(root/'log')],check=True,timeout=10)
            self.assertTrue((target/'HorasJogadas').exists());self.assertEqual((root/'previous'/'old.txt').read_text(),'old')
            self.assertEqual((target/'old.txt').read_text(),'old')
            self.assertEqual((data/'registros.json').read_bytes(),b'unchanged')

    @unittest.skipIf(os.name=='nt','Helper Linux')
    def test_linux_failed_swap_restores_original(self):
        with tempfile.TemporaryDirectory() as folder:
            root=Path(folder);target=root/'app';target.mkdir()
            (target/'HorasJogadas').write_text('#!/bin/sh\nexit 0\n');(target/'HorasJogadas').chmod(0o755)
            (target/'keep').write_bytes(b'old')
            helper=root/'helper.sh';helper.write_text(updates.LINUX_HELPER)
            result=subprocess.run(['/bin/sh',str(helper),'2147483647',str(target),str(root/'missing'),str(root/'previous'),str(root/'log')],capture_output=True,timeout=10)
            self.assertEqual(result.returncode,1);self.assertEqual((target/'keep').read_bytes(),b'old')

    def test_archive_escape_is_rejected_without_touching_current_installation(self):
        import tarfile
        with tempfile.TemporaryDirectory() as folder:
            root=Path(folder);target=root/'app';target.mkdir();(target/'keep').write_bytes(b'old')
            archive=root/'bad.tar.gz'
            with tarfile.open(archive,'w:gz') as tar:
                info=tarfile.TarInfo('HorasJogadas/../../escape');info.size=3;tar.addfile(info,io.BytesIO(b'bad'))
            with self.assertRaises(ValueError):updates.stage_linux(archive,target,'9.0.0')
            self.assertEqual((target/'keep').read_bytes(),b'old');self.assertFalse((root/'escape').exists())
            self.assertFalse(list(root.glob('.horasjogadas-update-*')))

    def test_preferences_merge_preserves_unrelated_settings(self):
        with tempfile.TemporaryDirectory() as folder:
            preferences.save(folder,check_updates=False,theme='original',future_option=True)
            preferences.save(folder,theme='dark')
            self.assertEqual(preferences.read(folder),{'check_updates':False,'theme':'dark','future_option':True})

class UpdateDialogTests(unittest.TestCase):
    def test_check_runs_off_ui_thread_and_reports_latest(self):
        from PySide6.QtWidgets import QApplication,QWidget
        from PySide6.QtCore import QThread,QEvent
        from PySide6.QtTest import QTest
        from horas_jogadas_qt.update_dialog import UpdateDialog
        app=QApplication.instance() or QApplication([])
        parent=QWidget();parent.available_update=None
        dialog=UpdateDialog(parent)
        threads=[]
        def check():
            threads.append(QThread.currentThread());return None
        with patch('horas_jogadas_qt.updates.check_release',side_effect=check):
            dialog.next_step()
            for _ in range(100):
                app.processEvents()
                if not dialog.busy:break
                QTest.qWait(10)
        self.assertFalse(dialog.busy);self.assertNotEqual(threads[0],app.thread())
        self.assertIn(updates.VERSION,dialog.status.text())
        dialog.reject();dialog.deleteLater();parent.deleteLater();app.sendPostedEvents(None,QEvent.DeferredDelete)
