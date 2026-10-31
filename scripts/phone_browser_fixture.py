"""Perfil fictício e servidor loopback para o teste real do controle pelo navegador."""
import argparse
import json
import os
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))


def write_private(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, name = tempfile.mkstemp(prefix='.' + path.name, dir=path.parent)
    try:
        with os.fdopen(fd, 'w', encoding='utf-8') as stream:
            json.dump(value, stream)
        os.replace(name, path)
    finally:
        if os.path.exists(name):
            os.unlink(name)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--control', type=Path, required=True)
    parser.add_argument('--port', type=int, default=0)
    args = parser.parse_args()
    os.environ.setdefault('QT_QPA_PLATFORM', 'offscreen')
    from PySide6.QtCore import QTimer
    from PySide6.QtWidgets import QApplication
    from app_qt import seed_demo
    from horas_jogadas import i18n
    from horas_jogadas_qt import preferences
    from horas_jogadas_qt.controller import Controller
    from horas_jogadas_qt.desktop import configure_application
    from horas_jogadas_qt.theme import apply_theme
    from horas_jogadas_qt.window import Window

    app = QApplication([])
    configure_application(app)
    with tempfile.TemporaryDirectory(prefix='horasjogadas-phone-browser-') as temporary:
        folder = Path(temporary)
        seed_demo(folder)
        preferences.save(folder, theme='original', check_updates=False)
        i18n.definir_idioma('pt')
        apply_theme(app, 'original')
        window = Window(Controller(folder), mode='review')
        window.show()
        window.navigate('settings')
        server = window.phone_control.server
        server.start('127.0.0.1', args.port)

        def connection():
            write_private(args.output, {'url': server.url, 'pairing_url': server.pairing_url,
                                        'code': server.pairing_code})

        connection()
        last = None

        def process_control():
            nonlocal last
            try:
                if not args.control.exists():
                    return
                raw = args.control.read_text(encoding='utf-8')
                if raw == last:
                    return
                data = json.loads(raw)
                last = raw
                if 'theme' in data:
                    window.save_settings(data['theme'], data.get('language', 'pt'))
                if data.get('renew'):
                    server.regenerate_pairing()
                if data.get('invalidate'):
                    window.phone_control.invalidate()
                if data.get('stop'):
                    server.stop()
                if 'size' in data:
                    window.resize(*data['size'])
                if data.get('screenshot'):
                    name = data['screenshot']
                    QTimer.singleShot(100, lambda: window.grab().save(name))
                connection()
                if data.get('quit'):
                    window.closing_allowed = True
                    window.close()
                    app.quit()
            except (OSError, ValueError):
                # O teste escreve via troca atômica; não imprime códigos de pareamento.
                pass

        timer = QTimer()
        timer.timeout.connect(process_control)
        timer.start(100)
        try:
            return app.exec()
        finally:
            server.stop()
            window.closing_allowed = True
            window.timer.stop()
            window.close()


if __name__ == '__main__':
    sys.exit(main())
