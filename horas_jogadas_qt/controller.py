"""Casos de uso Qt reutilizando modelos, validações e arquivos da versão atual."""
import copy
import json
import os
from contextlib import contextmanager
from datetime import datetime
from pathlib import Path
from horas_jogadas.storage import Repositorio, escrever_json_atomico
from horas_jogadas.zerados import RepositorioZerados
from horas_jogadas.constants import FORMATO_DATA
from horas_jogadas.models import EstadoSessao
from .timer import Timer


class StrictRepository(Repositorio):
    def _gravar(self, caminho, dados, backup=True):
        escrever_json_atomico(caminho, dados, backup)
        return True

    def limpar_andamento(self):
        Path(self.arq_andamento).unlink(missing_ok=True)

    def carregar_andamento(self):
        path = Path(self.arq_andamento)
        if not path.exists():
            return []
        raw = json.loads(path.read_text(encoding='utf-8'))
        if not isinstance(raw, list) or not all(isinstance(item, dict) for item in raw):
            raise ValueError('Sessões abertas ilegíveis; o arquivo foi preservado para recuperação.')
        return [EstadoSessao.from_dict(item) for item in raw]


class Controller:
    def __init__(self, folder):
        self.folder = Path(folder)
        self.repo = StrictRepository(str(folder), config_legado='')
        self.config = self.repo.carregar_config()
        self.zerados = RepositorioZerados(str(folder))
        self.timers = {g.id: Timer(g) for g in self.repo.jogos}
        self.undo = []
        self.repo.backup_diario()

    @contextmanager
    def transaction(self):
        """Guarda estado anterior na revisão antes de operações com vários arquivos."""
        names = ['cronometros.json', 'registros.json', 'config.json', 'zerados.json', 'em_andamento.json']
        files = {n: (self.folder / n).read_bytes() if (self.folder / n).exists() else None for n in names}
        state = copy.deepcopy((self.repo.jogos, self.repo.sessoes, self.zerados.registros,
                               self.zerados.automaticos, self.timers, self.undo, self.config))
        # Diário persistente de rollback: se o processo cair, o próximo lançamento restaura.
        journal = self.folder / '.qt-transaction.json'
        if journal.exists():
            raise RuntimeError('Há uma recuperação pendente. Feche e reabra a revisão antes de continuar.')
        escrever_json_atomico(str(journal), {n: data.decode('utf-8') if data is not None else None
                                            for n, data in files.items()}, backup=False)
        try:
            yield
        except Exception:
            self.restore_journal(self.folder)
            (self.repo.jogos, self.repo.sessoes, self.zerados.registros,
             self.zerados.automaticos, self.timers, self.undo, self.config) = state
            for key, timer in self.timers.items():
                timer.game = self.repo.jogo_por_id(key)
            raise
        else:
            journal.unlink()

    @staticmethod
    def restore_journal(folder):
        folder = Path(folder)
        journal = folder / '.qt-transaction.json'
        if not journal.exists():
            return
        files = json.loads(journal.read_text(encoding='utf-8'))
        allowed = {'cronometros.json', 'registros.json', 'config.json', 'zerados.json', 'em_andamento.json'}
        if set(files) != allowed:
            raise ValueError('Diário de recuperação inválido; arquivos preservados para revisão.')
        for name, data in files.items():
            target = folder / name
            if data is None:
                target.unlink(missing_ok=True)
            else:
                temp = folder / (name + '.rollback')
                with temp.open('w', encoding='utf-8', newline='') as f:
                    f.write(data)
                    f.flush()
                    os.fsync(f.fileno())
                os.replace(temp, target)
        journal.unlink()

    def save_pending(self):
        self.repo.salvar_andamento([s for timer in self.timers.values() if (s := timer.state())])

    def add_game(self, name):
        game = self.repo.adicionar_jogo(name)
        self.timers[game.id] = Timer(game)
        return game

    def finish(self, key):
        timer = self.timers[key]
        seconds, start, end, days = timer.finish_values()
        if seconds > 0:
            self.repo.adicionar_sessao(key, timer.game.nome, seconds, start, end, days)
        timer.reset()
        self.save_pending()

    def set_status(self, key, status):
        game = self.repo.jogo_por_id(key)
        previous = game.status
        game.status = status
        self.repo.salvar_jogos(self.repo.jogos)
        if status == 'Zerado' and previous != 'Zerado':
            total = self.repo.totais_por_jogo_id().get(key, 0) + self.timers[key].seconds()
            return self.zerados.registrar_automatico(key, game.nome, total)

    def delete_game(self, key):
        if self.timers[key].pending:
            raise ValueError('Resolva a sessão aberta antes de excluir o jogo.')
        self.repo.salvar_jogos([g for g in self.repo.jogos if g.id != key])
        del self.timers[key]

    def recover(self):
        for state in self.repo.carregar_andamento():
            seconds = state.segundos_recuperaveis()
            if seconds <= 0:
                continue
            game = self.repo.jogo_por_id(state.jogo_id)
            try:
                end = datetime.fromtimestamp(state.ultimo_heartbeat)
            except (ValueError, OSError, OverflowError):
                end = datetime.now()
            try:
                start = datetime.strptime(state.inicio, FORMATO_DATA) if state.inicio else None
            except ValueError:
                start = None
            self.repo.adicionar_sessao(game.id if game else None, game.nome if game else state.jogo,
                                       seconds, start, end, state.dias_recuperaveis())
        self.repo.limpar_andamento()

    def delete_session(self, session):
        index = self.repo.sessoes.index(session)
        if self.repo.remover_sessao(session.sessao_id):
            self.undo.append((index, session))

    def undo_session(self):
        if self.undo:
            index, session = self.undo.pop()
            self.repo.inserir_sessao(index, session)
