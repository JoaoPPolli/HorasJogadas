"""HorasJogadas: interface oficial Qt, com modo de revisão opcional e isolado."""
import argparse
import json
import sys
import tempfile
from pathlib import Path


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--review', action='store_true', help='Usa uma cópia de revisão dos dados')
    parser.add_argument('--self-test', metavar='RESULTADO', help='Valida o pacote com dados fictícios e grava o resultado')
    from horas_jogadas_qt.release import VERSION
    parser.add_argument('--version', action='version', version='HorasJogadas '+VERSION)
    parser.add_argument('--source', help='Pasta dos dados atuais, usada apenas como origem da cópia')
    parser.add_argument('--review-dir', help='Pasta separada dos dados de revisão')
    parser.add_argument('--demo', action='store_true', help='Usa dados fictícios, sem ler os registros atuais')
    args = parser.parse_args(argv)
    try:
        from PySide6.QtCore import QTimer
        from PySide6.QtGui import QIcon
        from PySide6.QtWidgets import QApplication, QMessageBox
    except ImportError:
        print('Instale a interface com: python -m pip install -r requirements-qt.txt', file=sys.stderr)
        return 1
    if args.self_test:
        from horas_jogadas_qt.self_test import run_self_test
        return run_self_test(args.self_test)
    from horas_jogadas.constants import DATA_DIR
    from horas_jogadas import i18n
    from horas_jogadas.instancia import TravaInstancia, sinalizar_mostrar
    from horas_jogadas.logging_setup import configurar_logging
    from horas_jogadas_qt.preview import prepare_preview
    from horas_jogadas_qt.controller import Controller
    from horas_jogadas_qt.release import prepare_official_data, VERSION
    from horas_jogadas_qt.theme import apply_theme, translate_standard_controls
    from horas_jogadas_qt.window import Window
    app = QApplication(sys.argv[:1])
    review_mode = bool(args.review or args.review_dir or args.source or args.demo)
    app.setApplicationName('HorasJogadas — Revisão' if review_mode else 'HorasJogadas')
    app.setOrganizationName('HorasJogadas')
    demo_temp = None
    lock = None
    log_folder = None
    version_backup = None
    try:
        source = Path(args.source or DATA_DIR).expanduser().resolve()
        destination = Path(args.review_dir).expanduser() if args.review_dir else source.parent / 'HorasJogadas-Revisao-Qt'
        if args.demo:
            demo_temp = tempfile.TemporaryDirectory(prefix='horasjogadas-demo-')
            source = Path(demo_temp.name) / 'source'
            source.mkdir()
            seed_demo(source)
            if not args.review_dir:
                destination = Path(demo_temp.name) / 'review'
        folder = prepare_preview(source, destination) if review_mode else source
        folder.mkdir(parents=True, exist_ok=True)
        # A versão oficial compartilha app.lock com a antiga; revisão usa outra pasta.
        lock = TravaInstancia(str(folder))
        if not lock.adquirir() or not lock.ativa:
            sinalizar_mostrar(str(folder))
            QMessageBox.information(None, 'HorasJogadas', 'O aplicativo já está aberto ou a pasta não pode ser bloqueada. Feche a versão antiga antes de abrir esta.')
            return 1
        if not review_mode:
            if sys.platform.startswith('linux') and getattr(sys,'frozen',False) and folder==Path(sys.executable).resolve().parent:
                from horas_jogadas_qt.linux_compat import recover_moved_data
                recover_moved_data(folder)
            version_backup = prepare_official_data(folder)
        Controller.restore_journal(folder)
        configurar_logging(str(folder))
        log_folder = folder
        c = Controller(folder)
        i18n.definir_idioma(c.config['idioma'])
        try:
            theme = json.loads((folder / '.qt-preferences.json').read_text(encoding='utf-8')).get('theme','dark')
        except (ValueError,OSError):
            theme = 'dark'
        apply_theme(app,theme)
        translate_standard_controls(app,c.config['idioma'])
        icon = Path(__file__).parent / 'icon.ico'
        if icon.exists():
            app.setWindowIcon(QIcon(str(icon)))
        window = Window(c,lock,mode='review' if review_mode else 'release')
        window.show()
        def ready():
            if version_backup:
                QMessageBox.information(window,'HorasJogadas','Seus registros foram preservados. Um backup completo anterior à atualização foi criado em:\n'+str(version_backup))
            for warning in c.repo.pop_avisos() + c.zerados.avisos:
                QMessageBox.warning(window, 'HorasJogadas', warning)
            window.recovery_prompt()
        QTimer.singleShot(0,ready)
        return app.exec()
    except Exception as error:
        QMessageBox.critical(None,'HorasJogadas',str(error))
        return 1
    finally:
        if lock:
            lock.liberar()
        if log_folder:
            # Windows não permite remover o arquivo do demo enquanto o logger o mantém aberto.
            import logging
            logger = logging.getLogger('horas_jogadas')
            for handler in list(logger.handlers):
                filename = getattr(handler,'baseFilename',None)
                if filename and Path(filename).resolve().parent == log_folder.resolve():
                    handler.flush(); handler.close(); logger.removeHandler(handler)
        if demo_temp:
            demo_temp.cleanup()


def seed_demo(folder):
    from datetime import datetime, timedelta, date
    from horas_jogadas.storage import Repositorio
    from horas_jogadas.zerados import RepositorioZerados, Conclusao
    repo = Repositorio(str(folder), config_legado='')
    for index, (name, status, hours) in enumerate(reversed([
        ('Hollow Knight','Jogando',42.5), ('Stardew Valley','Jogando',28),
        ('Celeste','Zerado',9.75), ('Outer Wilds','Zerado',18),
        ('Hades','Backlog',0), ('Sea of Stars','Backlog',0)])):
        game = repo.adicionar_jogo(name,status)
        if hours:
            end = datetime.now().replace(hour=20,minute=0,second=0,microsecond=0) - timedelta(days=index+1)
            repo.adicionar_sessao(game.id,name,int(hours*3600),end-timedelta(hours=hours),end)
    zerados = RepositorioZerados(str(folder))
    today = date.today()
    for record in [Conclusao('Celeste',today.year,1,35100,dia=18),
                   Conclusao('Outer Wilds',today.year,2,64800,dia=8),
                   Conclusao('Echoes of the Eye',today.year,2,43200,dia=23,dlc=True),
                   Conclusao('A Short Hike',today.year,3,10800,dia=15,platina_segundos=3600)]:
        if date(record.ano,record.mes,record.dia or 1) <= today:
            zerados.guardar(record)


if __name__ == '__main__':
    sys.exit(main())
