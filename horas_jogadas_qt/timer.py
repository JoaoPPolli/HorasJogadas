"""Cronômetro independente de widgets; relógio monotônico e distribuição diária."""
import time
import copy
from datetime import datetime, timedelta
from horas_jogadas.constants import FORMATO_DATA
from horas_jogadas.models import EstadoSessao
from horas_jogadas.utils import repartir_por_dia, inteiros_somando


class Timer:
    def __init__(self, game, clock=time):
        self.game, self.clock = game, clock
        self.reset()

    def __deepcopy__(self, memo):
        result = object.__new__(Timer)
        memo[id(self)] = result
        for key, value in self.__dict__.items():
            setattr(result, key, value if key == 'clock' else copy.deepcopy(value, memo))
        return result

    def reset(self):
        self.rodando = False
        self.acumulado = 0.0
        self.inicio = None
        self.retomado = 0.0
        self.mono = 0.0
        self.pausa = None
        self.dias = {}

    @property
    def pausado(self):
        return not self.rodando and self.acumulado > 0 and self.pausa is not None

    @property
    def pending(self):
        return self.rodando or self.acumulado > 0

    def now(self):
        return datetime.fromtimestamp(self.clock.time())

    def seconds(self):
        return max(0, self.acumulado + (self.clock.monotonic() - self.mono if self.rodando else 0))

    def add_days(self, start, end, seconds):
        for day, value in repartir_por_dia(start, end, seconds).items():
            self.dias[day] = self.dias.get(day, 0) + value

    def start(self):
        if self.rodando:
            return
        self.mono, self.retomado = self.clock.monotonic(), self.clock.time()
        self.inicio = self.inicio or self.now()
        self.rodando, self.pausa = True, None

    def pause(self):
        if not self.rodando:
            return
        elapsed = max(0, self.clock.monotonic() - self.mono)
        self.acumulado += elapsed
        self.add_days(datetime.fromtimestamp(self.retomado), self.now(), elapsed)
        self.rodando, self.pausa = False, self.clock.time()

    def adjust(self, delta):
        before = self.acumulado
        self.acumulado = max(0, before + delta)
        actual = self.acumulado - before
        if actual > 0:
            day = self.now().date()
            self.dias[day] = self.dias.get(day, 0) + actual
        elif actual < 0:
            remaining = -actual
            for day in sorted(self.dias, reverse=True):
                taken = min(remaining, self.dias[day])
                self.dias[day] -= taken
                remaining -= taken
        self.dias = {d: s for d, s in self.dias.items() if s > 0}
        if self.acumulado > 0:
            self.inicio = self.inicio or self.now()
        elif not self.rodando:
            self.inicio = None

    def count_pause(self, seconds=None):
        if not self.pausado:
            return
        total = max(0, self.clock.time() - self.pausa)
        count = total if seconds is None else min(total, max(0, seconds))
        self.acumulado += count
        self.add_days(self.now() - timedelta(seconds=count), self.now(), count)
        self.start()

    def finish_values(self):
        self.pause()
        total = int(round(self.acumulado))
        end = self.now()
        return total, self.inicio or end - timedelta(seconds=total), end, inteiros_somando(self.dias, total) or None

    def state(self):
        if not self.pending:
            return None
        return EstadoSessao(self.game.id, self.game.nome, self.acumulado, self.rodando,
                           self.retomado, self.clock.time(),
                           self.inicio.strftime(FORMATO_DATA) if self.inicio else None,
                           {d.isoformat(): s for d, s in self.dias.items()} or None)
