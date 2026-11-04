"""Inicialização por usuário, sem administrador e sem alterar registros de jogos."""
import os
import subprocess
import sys
from pathlib import Path
from .desktop import DESKTOP_ID, desktop_quote, write_if_changed
from . import preferences

RUN_KEY = r'Software\Microsoft\Windows\CurrentVersion\Run'
VALUE_NAME = 'HorasJogadas'


def command():
    executable = Path(sys.executable).resolve()
    if getattr(sys, 'frozen', False):
        return [str(executable)]
    if sys.platform == 'win32' and executable.with_name('pythonw.exe').exists():
        executable = executable.with_name('pythonw.exe')
    return [str(executable), str(Path(__file__).resolve().parent.parent / 'app_qt.py')]


def entry_path():
    root = Path(os.environ.get('XDG_CONFIG_HOME', ''))
    if not root.is_absolute():root = Path.home() / '.config'
    return root / 'autostart' / (DESKTOP_ID + '.desktop')


def enabled():
    if sys.platform == 'win32':
        import winreg
        try:
            with winreg.OpenKey(winreg.HKEY_CURRENT_USER, RUN_KEY) as key:
                return winreg.QueryValueEx(key, VALUE_NAME)[0] == subprocess.list2cmdline(command())
        except FileNotFoundError:return False
    if sys.platform.startswith('linux'):
        try:return entry_path().read_text(encoding='utf-8') == linux_entry()
        except FileNotFoundError:return False
    return False


def linux_entry():
    args = command()
    if any(c in arg for arg in args for c in ('\n', '\r', '\x00')):raise ValueError('Invalid startup path')
    return '\n'.join(('[Desktop Entry]', 'Type=Application', 'Name=HorasJogadas',
                      'Exec=/usr/bin/env ' + ' '.join(desktop_quote(arg) for arg in args),
                      'Icon=' + DESKTOP_ID, 'Terminal=false', 'X-GNOME-Autostart-enabled=true', ''))


def set_enabled(value):
    if sys.platform == 'win32':
        import winreg
        with winreg.CreateKey(winreg.HKEY_CURRENT_USER, RUN_KEY) as key:
            if value:winreg.SetValueEx(key, VALUE_NAME, 0, winreg.REG_SZ, subprocess.list2cmdline(command()))
            else:
                try:winreg.DeleteValue(key, VALUE_NAME)
                except FileNotFoundError:pass
    elif sys.platform.startswith('linux'):
        if value:write_if_changed(entry_path(), linux_entry().encode('utf-8'))
        else:entry_path().unlink(missing_ok=True)
    else:raise OSError('Unsupported platform')


def save_options(folder, launch_at_login, phone_auto_start):
    before = enabled()
    changed = before != launch_at_login
    if changed:set_enabled(launch_at_login)
    try:preferences.save(folder, phone_auto_start=phone_auto_start)
    except Exception:
        if changed:set_enabled(before)
        raise
