"""Autoteste do pacote pronto: somente dados fictícios em diretório temporário."""
import json
import os
import tempfile
from pathlib import Path
from PySide6.QtWidgets import QApplication
from PySide6.QtGui import QImage
from horas_jogadas.storage import Repositorio
from horas_jogadas import i18n
from .controller import Controller
from .preview import prepare_preview, inventory
from .theme import apply_theme, translate_standard_controls
from .window import Window
from .time_dialog import TimeDialog
from .release import VERSION


def run_self_test(result_path):
    from app_qt import seed_demo
    result = {'version':VERSION,'ok':False}
    app = QApplication.instance() or QApplication(['HorasJogadas-self-test'])
    try:
        if os.environ.get('HORASJOGADAS_NETWORK_SELFTEST')=='1':
            from .network import urlopen,ssl_context
            import ssl
            if os.environ.get('HORASJOGADAS_NO_SYSTEM_CA_SELFTEST')=='1':
                if ssl.create_default_context().get_ca_certs():raise RuntimeError('A simulação ainda contém certificados do sistema')
                result['system_ca_unavailable']=True
            context=ssl_context()
            result['portable_ca_count']=len(context.get_ca_certs())
            if context.verify_mode!=ssl.CERT_REQUIRED or not context.check_hostname:
                raise RuntimeError('Validação TLS desativada')
            from .updates import check_release,API
            def authenticated_api(request,timeout):
                token=os.environ.get('GH_TOKEN')
                if token and request.full_url==API:request.add_header('Authorization','Bearer '+token)
                return urlopen(request,timeout=timeout)
            check_release(opener=authenticated_api)
            result['updater_https']=True
        with tempfile.TemporaryDirectory(prefix='horasjogadas-selftest-') as temporary:
            source=Path(temporary)/'source'; source.mkdir(); seed_demo(source)
            before=inventory(source)
            c=Controller(prepare_preview(source,Path(temporary)/'review'))
            i18n.definir_idioma('pt'); apply_theme(app,'original'); translate_standard_controls(app,'pt')
            window=Window(c,mode='review')
            try:
                window.show(); app.processEvents()
                for page in ('library','history','stats','completed','settings'):
                    window.navigate(page); app.processEvents()
                    if window.grab().isNull(): raise RuntimeError('Falha ao desenhar '+page)
                svg=Path(__file__).with_name('assets')/'down-dark.svg'
                if QImage(str(svg)).isNull(): raise RuntimeError('Renderizador SVG ou assets ausentes')
                window.navigate('library'); app.processEvents()
                game=c.repo.jogos[0]
                with c.transaction():
                    c.timers[game.id].adjust(90)
                    c.finish(game.id)
                if Repositorio(str(c.folder)).sessoes[-1].segundos != 90:
                    raise RuntimeError('Persistência do cronômetro falhou')
                dialog=TimeDialog(window,game.id); dialog.show(); app.processEvents(); dialog.reject()
                from PySide6.QtCore import QBuffer,QIODevice
                from PySide6.QtGui import QColor
                from .covers import CoverStore,normalize_image
                from .cover_widget import GameCover
                from .cover_dialog import CoverDialog
                from . import preferences
                fixture=QImage(460,215,QImage.Format_RGB32);fixture.fill(QColor('#6555bb'))
                image_buffer=QBuffer();image_buffer.open(QIODevice.WriteOnly);fixture.save(image_buffer,'PNG')
                CoverStore(c.folder).save_many([(game.id,normalize_image(bytes(image_buffer.data())),{'source':'self-test'})])
                preferences.save(c.folder,covers_enabled=True)
                window.refresh();app.processEvents()
                cover=window.cards[game.id].findChild(GameCover)
                if cover is None or cover.image.isNull():raise RuntimeError('Capa JPEG não foi carregada')
                covers_dialog=CoverDialog(window,game.id);covers_dialog.show();app.processEvents()
                if covers_dialog.grab().isNull():raise RuntimeError('Janela de capas não foi desenhada')
                covers_dialog.reject();covers_dialog.deleteLater()
                preferences.save(c.folder,covers_enabled=False);window.refresh();app.processEvents()
                if window.cards[game.id].findChildren(GameCover):raise RuntimeError('Não foi possível desativar as capas')
                result.update(covers=True,covers_optional=True)

                if before != inventory(source): raise RuntimeError('A origem do teste foi alterada')
                result.update(ok=True,pages=5,seconds_saved=90,source_unchanged=True,svg=True)
            finally:
                window.closing_allowed=True; window.timer.stop(); window.close()
                window.deleteLater(); app.processEvents()
    except Exception as error:
        result['error']=str(error)
    Path(result_path).write_text(json.dumps(result,indent=2),encoding='utf-8')
    return 0 if result['ok'] else 1
