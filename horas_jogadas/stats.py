"""Estatísticas sobre as sessões. Funções puras, sem dependência de interface."""
from dataclasses import dataclass
from datetime import date, datetime, timedelta
from typing import Dict, List, Optional, Sequence, Tuple

from .models import Jogo, Sessao, chave_sessao
from .utils import chave_nome

DIAS_SEMANA = ["Seg", "Ter", "Qua", "Qui", "Sex", "Sáb", "Dom"]
MESES = ["Jan", "Fev", "Mar", "Abr", "Mai", "Jun", "Jul", "Ago", "Set", "Out", "Nov", "Dez"]

PERIODO_7_DIAS = "7d"
PERIODO_8_SEMANAS = "8s"
PERIODO_6_MESES = "6m"


@dataclass
class GrupoJogo:
    """Estatísticas agregadas de um jogo (ou de um grupo de sessões órfãs)."""
    chave: str
    nome: str
    jogo_id: Optional[str]
    status: Optional[str]
    total: int = 0
    sessoes: int = 0
    primeira: Optional[datetime] = None
    ultima: Optional[datetime] = None


@dataclass
class ResumoGeral:
    total_segundos: int
    total_sessoes: int
    media_sessao: float
    sessao_mais_longa: Optional[Sessao]
    jogo_mais_jogado: Optional[GrupoJogo]


def totais_por_jogo_id(sessoes: Sequence[Sessao]) -> Dict[str, int]:
    """Soma de segundos por id de jogo (sessões sem jogo_id são ignoradas)."""
    totais: Dict[str, int] = {}
    for s in sessoes:
        if s.jogo_id:
            totais[s.jogo_id] = totais.get(s.jogo_id, 0) + s.segundos
    return totais


def ultima_sessao_por_jogo_id(sessoes: Sequence[Sessao]) -> Dict[str, datetime]:
    """Data/hora da sessão mais recente de cada jogo (datas inválidas são ignoradas)."""
    ultimas: Dict[str, datetime] = {}
    for s in sessoes:
        dt = s.data_dt
        if s.jogo_id and dt and (s.jogo_id not in ultimas or dt > ultimas[s.jogo_id]):
            ultimas[s.jogo_id] = dt
    return ultimas


def agrupar_por_jogo(jogos: Sequence[Jogo], sessoes: Sequence[Sessao]) -> List[GrupoJogo]:
    """Um grupo por jogo da biblioteca (mesmo sem sessões) + um por jogo órfão (pelo nome).

    Ordenado da sessão mais recente para a mais antiga; jogos sem sessões ficam no fim.
    """
    ids = {j.id for j in jogos}
    grupos: Dict[str, GrupoJogo] = {
        j.id: GrupoJogo(chave=j.id, nome=j.nome, jogo_id=j.id, status=j.status) for j in jogos
    }
    for s in sessoes:
        chave = chave_sessao(s, ids)
        grupo = grupos.get(chave)
        if grupo is None:
            grupo = grupos[chave] = GrupoJogo(chave=chave, nome=s.jogo, jogo_id=None, status=None)
        grupo.total += s.segundos
        grupo.sessoes += 1
        dt = s.data_dt
        if dt:
            if grupo.primeira is None or dt < grupo.primeira:
                grupo.primeira = dt
            if grupo.ultima is None or dt > grupo.ultima:
                grupo.ultima = dt
    return sorted(grupos.values(), key=lambda g: (g.ultima or datetime.min, chave_nome(g.nome)),
                  reverse=True)


def resumo_geral(grupos: Sequence[GrupoJogo], sessoes: Sequence[Sessao]) -> ResumoGeral:
    total = sum(s.segundos for s in sessoes)
    n = len(sessoes)
    mais_longa = max(sessoes, key=lambda s: s.segundos) if sessoes else None
    com_tempo = [g for g in grupos if g.total > 0]
    mais_jogado = max(com_tempo, key=lambda g: g.total) if com_tempo else None
    return ResumoGeral(total, n, (total / n) if n else 0.0, mais_longa, mais_jogado)


def top_jogos(grupos: Sequence[GrupoJogo], n: int = 5) -> List[GrupoJogo]:
    return sorted([g for g in grupos if g.total > 0], key=lambda g: g.total, reverse=True)[:n]


def _dias_com_sessao(sessoes: Sequence[Sessao]) -> List[date]:
    """Dias em que se jogou (uma sessão que atravessa a meia-noite conta os dois dias)."""
    return sorted({dia for s in sessoes for dia in s.segundos_por_dia()})


def sequencias(sessoes: Sequence[Sessao], hoje: Optional[date] = None) -> Tuple[int, int]:
    """(sequência atual, maior sequência) de dias consecutivos com sessão.

    A sequência atual conta se o último dia jogado for hoje ou ontem.
    """
    hoje = hoje or date.today()
    dias = _dias_com_sessao(sessoes)
    if not dias:
        return 0, 0
    maior = atual_corrida = 1
    for anterior, dia in zip(dias, dias[1:]):
        atual_corrida = atual_corrida + 1 if dia - anterior == timedelta(days=1) else 1
        maior = max(maior, atual_corrida)
    # corrida que termina no último dia registrado
    ultima_corrida = 1
    for i in range(len(dias) - 1, 0, -1):
        if dias[i] - dias[i - 1] == timedelta(days=1):
            ultima_corrida += 1
        else:
            break
    atual = ultima_corrida if dias[-1] >= hoje - timedelta(days=1) and dias[-1] <= hoje else 0
    return atual, maior


def _deslocar_mes(ano: int, mes: int, delta: int) -> Tuple[int, int]:
    indice = ano * 12 + (mes - 1) + delta
    return indice // 12, indice % 12 + 1


def horas_por_periodo(sessoes: Sequence[Sessao], periodo: str, hoje: Optional[date] = None,
                      dias_semana: Sequence[str] = DIAS_SEMANA, meses_nomes: Sequence[str] = MESES,
                      formato_semana: str = "%d/%m") -> List[Tuple[str, int]]:
    """Segundos jogados por intervalo: [(rótulo, segundos), ...] do mais antigo ao mais novo.

    - '7d': últimos 7 dias (inclui hoje)
    - '8s': últimas 8 semanas (semanas iniciando na segunda-feira)
    - '6m': últimos 6 meses (inclui o atual)
    O tempo de cada sessão é contado nos dias em que foi jogado (inclusive se atravessou a meia-noite).
    Sessões com data inválida são ignoradas. Os rótulos podem ser traduzidos via `dias_semana`,
    `meses_nomes` e `formato_semana` (strftime); o padrão é português.
    """
    hoje = hoje or date.today()
    datas = [(dia, seg) for s in sessoes for dia, seg in s.segundos_por_dia().items()]

    if periodo == PERIODO_7_DIAS:
        dias = [hoje - timedelta(days=i) for i in range(6, -1, -1)]
        soma = {d: 0 for d in dias}
        for d, seg in datas:
            if d in soma:
                soma[d] += seg
        return [(dias_semana[d.weekday()], soma[d]) for d in dias]

    if periodo == PERIODO_8_SEMANAS:
        segunda_atual = hoje - timedelta(days=hoje.weekday())
        inicios = [segunda_atual - timedelta(weeks=i) for i in range(7, -1, -1)]
        soma = {d: 0 for d in inicios}
        for d, seg in datas:
            inicio = d - timedelta(days=d.weekday())
            if inicio in soma:
                soma[inicio] += seg
        return [(d.strftime(formato_semana), soma[d]) for d in inicios]

    if periodo == PERIODO_6_MESES:
        meses = [_deslocar_mes(hoje.year, hoje.month, -i) for i in range(5, -1, -1)]
        soma = {m: 0 for m in meses}
        for d, seg in datas:
            if (d.year, d.month) in soma:
                soma[(d.year, d.month)] += seg
        return [(f"{meses_nomes[m - 1]}/{a % 100:02d}", soma[(a, m)]) for a, m in meses]

    raise ValueError(f"Período desconhecido: {periodo}")
