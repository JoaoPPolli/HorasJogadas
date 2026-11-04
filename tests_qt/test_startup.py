"""Registro de inicialização em destinos isolados e reversão de falhas."""
import tempfile
import unittest
from pathlib import Path
from unittest.mock import MagicMock, patch
from horas_jogadas_qt import startup, preferences

class StartupTests(unittest.TestCase):
    def test_linux_entry_is_opt_in_quoted_and_removable(self):
        with tempfile.TemporaryDirectory() as folder, patch.object(startup.sys, 'platform', 'linux'), patch.dict(startup.os.environ, {'XDG_CONFIG_HOME':folder}), patch.object(startup, 'command', return_value=['/test/My % Game/app', '/test/a"$b.py']):
            self.assertFalse(startup.enabled())
            startup.set_enabled(True)
            self.assertTrue(startup.enabled())
            content=startup.entry_path().read_text()
            self.assertIn('My %% Game',content)
            self.assertNotIn('sudo',content)
            startup.set_enabled(False)
            self.assertFalse(startup.enabled())

    def test_windows_registers_only_current_user_and_quotes_command(self):
        registry=MagicMock(); registry.HKEY_CURRENT_USER='current-user'; registry.REG_SZ=1
        with patch.object(startup.sys,'platform','win32'), patch.dict('sys.modules', {'winreg':registry}), patch.object(startup,'command',return_value=[r'C:\My App\HorasJogadas.exe']):
            startup.set_enabled(True)
            registry.CreateKey.assert_called_with('current-user',startup.RUN_KEY)
            registry.SetValueEx.assert_called_once_with(registry.CreateKey.return_value.__enter__.return_value,'HorasJogadas',0,1,'"C:\\My App\\HorasJogadas.exe"')
            startup.set_enabled(False)
            registry.DeleteValue.assert_called_once()

    def test_failed_preference_write_restores_registration(self):
        with patch.object(startup,'enabled',return_value=False), patch.object(startup,'set_enabled') as change, patch.object(preferences,'save',side_effect=OSError('disk full')):
            with self.assertRaises(OSError):startup.save_options('/unused', True, True)
            self.assertEqual([c.args for c in change.call_args_list],[(True,),(False,)])
