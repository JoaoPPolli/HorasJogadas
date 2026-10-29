"""Identidade X11/Wayland e lançador por usuário, sempre em pastas fictícias."""
import os
import shutil
import subprocess
import sys
import tempfile
import time
import unittest
from pathlib import Path
from unittest.mock import patch

from PySide6.QtGui import QImage, QIcon
from PySide6.QtWidgets import QApplication, QWidget
from horas_jogadas_qt import desktop

APP = QApplication.instance() or QApplication([])


class DesktopTests(unittest.TestCase):
    def test_identity_window_icon_and_all_linux_png_sizes(self):
        icon = desktop.configure_application(APP)
        self.assertEqual(APP.desktopFileName(), desktop.DESKTOP_ID)
        window = QWidget()
        self.assertFalse(window.windowIcon().isNull())
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            desktop.register_linux(icon, root / 'App com espaços' / 'HorasJogadas', root / 'xdg')
            entry = root / 'xdg' / 'applications' / (desktop.DESKTOP_ID + '.desktop')
            self.assertIn('StartupWMClass=HorasJogadas\n', entry.read_text())
            for size in (16, 32, 48):
                image = QImage(str(root / 'xdg' / 'icons' / 'hicolor' / f'{size}x{size}' / 'apps' / (desktop.DESKTOP_ID + '.png')))
                self.assertFalse(image.isNull())
                self.assertEqual((image.width(), image.height()), (size, size))
            if shutil.which('desktop-file-validate'):
                result = subprocess.run(['desktop-file-validate', str(entry)], capture_output=True, text=True)
                self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        window.deleteLater()

    def test_idempotent_registration_and_relocation(self):
        icon = desktop.configure_application(APP)
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            desktop.register_linux(icon, root / 'old' / 'HorasJogadas', root / 'xdg')
            files = list((root / 'xdg').rglob('*'))
            before = {p: p.stat().st_mtime_ns for p in files}
            desktop.register_linux(icon, root / 'old' / 'HorasJogadas', root / 'xdg')
            self.assertEqual(before, {p: p.stat().st_mtime_ns for p in files})
            desktop.register_linux(icon, root / 'new' / 'HorasJogadas', root / 'xdg')
            entry = root / 'xdg' / 'applications' / (desktop.DESKTOP_ID + '.desktop')
            self.assertIn('Exec=' + desktop.desktop_exec(root / 'new' / 'HorasJogadas'), entry.read_text())
            self.assertEqual(len(list((root / 'xdg' / 'applications').iterdir())), 1)

    def test_xdg_location_follows_spec_and_rejects_relative_override(self):
        with patch.dict(os.environ, {'XDG_DATA_HOME': '/tmp/fake-desktop'}):
            self.assertEqual(desktop.data_directory(), Path('/tmp/fake-desktop'))
        with patch.dict(os.environ, {'XDG_DATA_HOME': 'relative'}):
            self.assertEqual(desktop.data_directory(), Path.home() / '.local' / 'share')

    def test_packaged_official_only_and_registration_error_does_not_abort(self):
        with patch.object(desktop.sys, 'platform', 'linux'), patch.object(desktop, 'register_linux') as register:
            with patch.object(desktop.sys, 'frozen', False, create=True):
                desktop.register_official_application(QIcon())
                register.assert_not_called()
            with patch.object(desktop.sys, 'frozen', True, create=True):
                desktop.register_official_application(QIcon())
                register.assert_called_once()
                register.side_effect = PermissionError('fake read-only desktop')
                with self.assertLogs('horas_jogadas', level='WARNING'):
                    desktop.register_official_application(QIcon())

    @unittest.skipUnless(sys.platform.startswith('linux') and shutil.which('gio'), 'GIO Linux necessário')
    def test_real_desktop_launcher_preserves_special_characters_in_path(self):
        icon = desktop.configure_application(APP)
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            folder = root / 'App espaços $ ` " % \\ e aspas\''
            folder.mkdir()
            executable = folder / 'HorasJogadas'
            executable.write_text('#!' + sys.executable + '\nfrom pathlib import Path\nPath(__file__).with_suffix(".started").write_text("ok")\n')
            executable.chmod(0o700)
            desktop.register_linux(icon, executable, root / 'xdg')
            entry = root / 'xdg' / 'applications' / (desktop.DESKTOP_ID + '.desktop')
            process = subprocess.run(['gio', 'launch', str(entry)], capture_output=True, text=True, timeout=10)
            self.assertEqual(process.returncode, 0, process.stdout + process.stderr)
            deadline = time.monotonic() + 5
            marker = executable.with_suffix('.started')
            while not marker.exists() and time.monotonic() < deadline:
                time.sleep(.05)
            self.assertTrue(marker.exists(), 'O lançador deve executar o arquivo com o caminho intacto')

    def test_unsafe_desktop_newline_does_not_write_files(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            with self.assertRaises(ValueError):
                desktop.register_linux(desktop.configure_application(APP), root / 'app\nHidden=true', root / 'xdg')
            self.assertFalse((root / 'xdg').exists())
