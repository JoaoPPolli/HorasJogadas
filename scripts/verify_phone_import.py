"""Confere o arquivo real exportado pelo navegador em uma base sintética do PC."""
import json
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from horas_jogadas_qt.controller import Controller
from horas_jogadas_qt.phone_import import load_mobile, import_mobile


def verify(path):
    records = load_mobile(path)
    with tempfile.TemporaryDirectory(prefix='horas-phone-import-check-') as temporary:
        controller = Controller(Path(temporary))
        game = controller.add_game('Registro anterior — demonstração')
        old = controller.repo.adicionar_sessao(game.id, game.nome, 120, None, controller.timers[game.id].now())
        preserved = old.to_dict()
        timer = controller.timers[game.id]; timer.start()
        first = import_mobile(controller, records)
        current = (Path(temporary) / 'registros.json').read_bytes()
        second = import_mobile(controller, records)
        if (first['imported'] != len(records) or second['imported'] != 0
                or second['skipped'] != len(records)
                or (Path(temporary) / 'registros.json').read_bytes() != current
                or controller.repo.sessoes[0].to_dict() != preserved
                or controller.timers[game.id] is not timer or not timer.rodando):
            raise RuntimeError('A importação não preservou a sessão anterior ou duplicou registros')
        return {'ok': True, 'imported': first['imported'], 'duplicate_safe': True, 'existing_records_preserved': True}


if __name__ == '__main__':
    print(json.dumps(verify(sys.argv[1])))
