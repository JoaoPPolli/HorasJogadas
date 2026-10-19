"""Exportação para CSV (abre direto no Excel/Planilhas).

Formato pensado para o Excel: UTF-8 com BOM (acentos corretos) e, em português, separador ';' e
decimal ',' (é o que o Excel do Brasil espera); em inglês, ',' e '.'. Os cabeçalhos seguem o idioma.
"""
import csv
import os
from typing import List, Sequence

from . import stats
from .i18n import t, t_status
from .models import Jogo, Sessao
from .utils import formatar_hhmmss


def _horas(segundos: int) -> str:
    """Horas decimais com 2 casas e o separador decimal do idioma (ex.: '1,25' ou '1.25')."""
    return f"{segundos / 3600:.2f}".replace(".", t("fmt.decimal"))


def _data(valor) -> str:
    return valor.strftime("%Y-%m-%d %H:%M:%S") if valor else ""


def linhas_historico(jogos: Sequence[Jogo], sessoes: Sequence[Sessao]) -> List[List[str]]:
    """Cabeçalho + uma linha por sessão, da mais antiga para a mais recente."""
    status = {j.id: j.status for j in jogos}
    cabecalho = [t("csv.col.jogo"), t("csv.col.status"), t("csv.col.inicio"), t("csv.col.fim"),
                 t("csv.col.segundos"), t("csv.col.duracao"), t("csv.col.horas")]
    linhas = [cabecalho]
    for s in sorted(sessoes, key=lambda x: (x.data_dt is None, x.data_dt or 0, x.sessao_id)):
        st = status.get(s.jogo_id or "")
        linhas.append([
            s.jogo, t_status(st) if st else "", s.inicio or "", s.fim or s.data,
            str(s.segundos), formatar_hhmmss(s.segundos), _horas(s.segundos),
        ])
    return linhas


def linhas_resumo(jogos: Sequence[Jogo], sessoes: Sequence[Sessao]) -> List[List[str]]:
    """Cabeçalho + uma linha por jogo (inclui jogos sem sessões e históricos de jogos removidos)."""
    cabecalho = [t("csv.col.jogo"), t("csv.col.status"), t("csv.col.sessoes"), t("csv.col.total_segundos"),
                 t("csv.col.total"), t("csv.col.horas"), t("csv.col.primeira"), t("csv.col.ultima")]
    linhas = [cabecalho]
    for g in sorted(stats.agrupar_por_jogo(jogos, sessoes), key=lambda x: x.total, reverse=True):
        linhas.append([
            g.nome, t_status(g.status) if g.status else "", str(g.sessoes), str(g.total),
            formatar_hhmmss(g.total), _horas(g.total), _data(g.primeira), _data(g.ultima),
        ])
    return linhas


def gravar_csv(caminho: str, linhas: Sequence[Sequence[str]]) -> int:
    """Grava as linhas de forma atômica. Devolve quantas linhas de dados (sem o cabeçalho) foram escritas."""
    provisorio = caminho + ".tmp"
    try:
        with open(provisorio, "w", encoding="utf-8-sig", newline="") as f:
            csv.writer(f, delimiter=t("csv.sep"), quoting=csv.QUOTE_MINIMAL).writerows(linhas)
        os.replace(provisorio, caminho)
    except OSError:
        try:
            os.remove(provisorio)
        except OSError:
            pass
        raise
    return max(0, len(linhas) - 1)


def exportar_historico(caminho: str, jogos: Sequence[Jogo], sessoes: Sequence[Sessao]) -> int:
    return gravar_csv(caminho, linhas_historico(jogos, sessoes))


def exportar_resumo(caminho: str, jogos: Sequence[Jogo], sessoes: Sequence[Sessao]) -> int:
    return gravar_csv(caminho, linhas_resumo(jogos, sessoes))
