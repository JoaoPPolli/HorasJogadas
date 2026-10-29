"""Identidade da janela e integração do pacote Linux com o desktop do usuário."""
import logging
import os
import sys
import tempfile
from pathlib import Path

DESKTOP_ID = 'io.github.JoaoPPolli.HorasJogadas'


def configure_application(app):
    from PySide6.QtGui import QIcon
    # Wayland associa app_id ao nome do arquivo .desktop, sem a extensão.
    app.setDesktopFileName(DESKTOP_ID)
    icon = QIcon(str(Path(__file__).resolve().parent.parent / 'icon.ico'))
    app.setWindowIcon(icon)
    return icon


def data_directory():
    configured = Path(os.environ.get('XDG_DATA_HOME', ''))
    return configured if configured.is_absolute() else Path.home() / '.local' / 'share'


def desktop_quote(value):
    # Exec usa a sintaxe desktop-entry, não a de um shell. % é um field code;
    # os outros caracteres precisam sobreviver também ao escape da chave.
    escaped = str(value).replace('%', '%%')
    for char in ('\\', '"', '`', '$'):
        escaped = escaped.replace(char, '\\' + char)
    return '"' + escaped.replace('\\', '\\\\') + '"'


def desktop_exec(executable):
    # GIO verifica o executável antes de expandir %%; env evita que essa
    # verificação rejeite instalações em pastas contendo um % literal.
    return '/usr/bin/env ' + desktop_quote(executable)


def write_if_changed(path, content):
    path.parent.mkdir(parents=True, exist_ok=True)
    if path.is_file() and path.read_bytes() == content:
        return False
    fd, temporary = tempfile.mkstemp(prefix='.' + path.name + '-', dir=path.parent)
    try:
        with os.fdopen(fd, 'wb') as stream:
            stream.write(content)
        os.replace(temporary, path)
    finally:
        if os.path.exists(temporary):
            os.unlink(temporary)
    return True


def register_linux(icon, executable, data_home=None):
    """Registra só o usuário atual; não escreve no pacote nem nos registros."""
    from PySide6.QtCore import QBuffer, QIODevice
    executable = Path(executable).resolve()
    if any(char in str(executable) for char in ('\n', '\r', '\x00')):
        raise ValueError('Caminho inválido para o lançador Linux')
    if icon.isNull():
        raise ValueError('Ícone do aplicativo ausente')
    root = Path(data_home) if data_home is not None else data_directory()
    theme = root / 'icons' / 'hicolor'
    changed = False
    for size in (16, 32, 48):
        buffer = QBuffer()
        buffer.open(QIODevice.WriteOnly)
        if not icon.pixmap(size, size).save(buffer, 'PNG'):
            raise ValueError('Não foi possível converter o ícone do aplicativo')
        changed |= write_if_changed(theme / f'{size}x{size}' / 'apps' / (DESKTOP_ID + '.png'),
                                    bytes(buffer.data()))
    if changed:
        # Invalida caches do tema sem executar ferramentas/bibliotecas do sistema.
        os.utime(theme, None)
    entry = '\n'.join((
        '[Desktop Entry]', 'Type=Application', 'Version=1.0', 'Name=HorasJogadas',
        'Comment=Track your gaming time', 'Comment[pt_BR]=Seu diário de jogos',
        'Exec=' + desktop_exec(executable), 'Icon=' + DESKTOP_ID,
        'Terminal=false', 'Categories=Game;Utility;', 'StartupNotify=false',
        'StartupWMClass=HorasJogadas', '',
    ))
    write_if_changed(root / 'applications' / (DESKTOP_ID + '.desktop'), entry.encode('utf-8'))


def register_official_application(icon):
    if sys.platform.startswith('linux') and getattr(sys, 'frozen', False):
        try:
            register_linux(icon, sys.executable)
        except (OSError, ValueError):
            # Uma pasta XDG sem permissão não deve impedir a abertura dos jogos.
            logging.getLogger('horas_jogadas').warning('Não foi possível registrar o ícone no desktop Linux', exc_info=True)
