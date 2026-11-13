"""Perfil fictício e servidor loopback para o teste real do controle pelo navegador."""
import argparse
import json
import os
import sys
import tempfile
import time
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
    from PySide6.QtCore import QTimer, QBuffer, QIODevice
    from PySide6.QtGui import QImage, QColor, QPainter
    from PySide6.QtWidgets import QApplication
    from app_qt import seed_demo
    from horas_jogadas import i18n
    from horas_jogadas_qt import preferences
    from horas_jogadas_qt.controller import Controller
    from horas_jogadas_qt.desktop import configure_application
    from horas_jogadas_qt.theme import apply_theme
    from horas_jogadas_qt.window import Window
    from horas_jogadas_qt.covers import CoverStore, normalize_image

    app = QApplication([])
    configure_application(app)
    with tempfile.TemporaryDirectory(prefix='horasjogadas-phone-browser-') as temporary:
        folder = Path(temporary)
        seed_demo(folder)
        preferences.save(folder, theme='original', check_updates=False)
        # Imagens inteiramente sintéticas: nenhuma arte de jogo acompanha o teste.
        sample = QImage(460, 215, QImage.Format_RGB32)
        sample.fill(QColor('#383052'))
        painter = QPainter(sample)
        painter.fillRect(0, 145, 460, 70, QColor('#705ee8'))
        painter.fillRect(285, 0, 175, 145, QColor('#49596e'))
        painter.end()
        data = QBuffer(); data.open(QIODevice.WriteOnly); sample.save(data, 'PNG')
        fixture_png = bytes(data.data())
        controller = Controller(folder)
        game = next(item for item in controller.repo.jogos if item.nome == 'Hollow Knight')
        CoverStore(folder).save_many([(game.id, normalize_image(bytes(data.data())), {'source': 'browser-test'})])
        CoverStore(folder, 'icon').save_many([(game.id, normalize_image(bytes(data.data()), 'icon'), {'source': 'browser-test'})])
        i18n.definir_idioma('pt')
        apply_theme(app, 'original')
        window = Window(controller, mode='review')
        window.show()
        window.navigate('settings')
        server = window.phone_control.server
        server.start('127.0.0.1', args.port)

        control_nonce = None

        def connection():
            write_private(args.output, {'url': server.url, 'pairing_url': server.pairing_url,
                                        'code': server.pairing_code, 'control_nonce': control_nonce, 'obs_url': window.obs_control.url})

        connection()
        last = None

        def process_control():
            nonlocal last, control_nonce
            try:
                if not args.control.exists():
                    return
                raw = args.control.read_text(encoding='utf-8')
                if raw == last:
                    return
                data = json.loads(raw)
                last = raw
                control_nonce = data.get('nonce')
                if 'theme' in data:
                    window.save_settings(data['theme'], data.get('language', 'pt'))
                if 'covers_enabled' in data or 'icons_enabled' in data:
                    preferences.save(folder, **{key: data[key] for key in ('covers_enabled', 'icons_enabled') if key in data})
                    window.refresh()
                if 'obs' in data:
                    window.obs_control.save(data['obs'])
                if 'obs_seconds' in data:
                    timer = window.c.timers[game.id]; timer.reset(); timer.adjust(data['obs_seconds'])
                if data.get('obs_action'):
                    if data['obs_action'] == 'stop_phone':server.stop()
                    else:getattr(window.c.timers[game.id], data['obs_action'])()
                if data.get('detect_profile'):
                    from horas_jogadas_qt.detection import save_profile
                    save_profile(window,game.id,True,str(folder/'SyntheticGame.exe'),'path')
                if data.get('renew'):
                    server.regenerate_pairing()
                if data.get('restart'):
                    port = server.server.serverPort()
                    server.stop()
                    server.start('127.0.0.1', port)
                if data.get('invalidate'):
                    window.phone_control.invalidate()
                if data.get('stub_artwork'):
                    from horas_jogadas_qt import artwork_sources
                    from horas_jogadas_qt.covers import Candidate
                    artwork_sources.search_artwork = lambda title, **kwargs: artwork_sources.SearchResults([
                        Candidate(42, title, 'https://shared.fastly.steamstatic.com/store_item_assets/steam/apps/42/header.jpg', 1.0)])
                    artwork_sources.download_artwork = lambda candidate, cancel, **kwargs: normalize_image(fixture_png, kwargs.get('kind', 'cover'))
                if data.get('stub_update'):
                    from horas_jogadas_qt import updates
                    updates.check_release = lambda: updates.Release('99.0.0', 'Atualização sintética de teste',
                        'https://github.com/JoaoPPolli/HorasJogadas/releases/download/v99.0.0/HorasJogadas-Linux-x86_64.tar.gz',
                        1, 'https://github.com/JoaoPPolli/HorasJogadas/releases/download/v99.0.0/SHA256SUMS.txt',
                        'HorasJogadas-Linux-x86_64.tar.gz')
                if data.get('expire_pairing'):
                    server._pairing_deadline = time.monotonic() - 1
                if data.get('expire_sessions'):
                    for session in server._sessions.values():
                        session['expires'] = 0
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
