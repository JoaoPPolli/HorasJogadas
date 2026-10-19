"""Funções utilitárias sem dependência de interface."""
import os
import sys
import unicodedata
from datetime import date, datetime, timedelta
from typing import Callable, Dict, Hashable, TypeVar

from .constants import FORMATO_DATA, MARCADOR_EMPACOTADO


def resource_path(relative_path: str) -> str:
    """Caminho de um recurso, funcionando também dentro do PyInstaller."""
    base_path = getattr(sys, "_MEIPASS", None) or os.path.abspath(".")
    return os.path.join(base_path, relative_path)


def pasta_do_app() -> str:
    """Pasta onde o app está instalado: a do .exe (congelado) ou a que contém `horas_jogadas/`."""
    if getattr(sys, "frozen", False):
        return os.path.dirname(os.path.abspath(sys.executable))
    return os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def modo_empacotado() -> bool:
    """True no .exe de distribuição (itch.io), onde o código do app vai DENTRO do executável.

    Nesse modo o app não se atualiza sozinho por ZIP (as atualizações chegam pela página/app do itch.io) e
    não carrega código solto da pasta ao lado do .exe.
    """
    base = getattr(sys, "_MEIPASS", None)
    return bool(getattr(sys, "frozen", False) and base and os.path.exists(os.path.join(base, MARCADOR_EMPACOTADO)))


def formatar_hhmmss(segundos: float, simplificado: bool = False) -> str:
    """Formata segundos como 'HH:MM:SS' (ou '3h 12m' se simplificado)."""
    s_int = int(max(0, segundos))
    h = s_int // 3600
    m = (s_int % 3600) // 60
    s = s_int % 60
    if simplificado:
        return f"{h}h {m}m"
    return f"{h:02d}:{m:02d}:{s:02d}"


def chave_nome(nome: str) -> str:
    """Chave de comparação de nomes: sem espaços extras e sem diferença de caixa."""
    return " ".join((nome or "").split()).casefold()


def normalizar_texto(texto: str) -> str:
    """Texto sem acentos, minúsculo e sem espaços nas pontas (para buscas)."""
    decomposto = unicodedata.normalize("NFKD", texto or "")
    sem_acento = "".join(c for c in decomposto if not unicodedata.combining(c))
    return sem_acento.casefold().strip()


def agora_str() -> str:
    return datetime.now().strftime(FORMATO_DATA)


def formatar_duracao(segundos: float) -> str:
    """Duração legível: '2h 05m', '12m 30s' ou '45s'."""
    total = int(max(0, segundos))
    h, resto = divmod(total, 3600)
    m, s = divmod(resto, 60)
    if h:
        return f"{h}h {m:02d}m"
    if m:
        return f"{m}m {s:02d}s"
    return f"{s}s"


def horas_curto(segundos: float, decimal: str = ",") -> str:
    """Rótulo compacto para gráficos: '18m', '1,5h' (ou '1.5h'), '12h'."""
    segundos = max(0, segundos)
    if segundos < 3600:
        return f"{max(1, round(segundos / 60))}m"
    horas = segundos / 3600
    if horas >= 10:
        return f"{horas:.0f}h"
    return f"{horas:.1f}h".replace(".", decimal)


def ellipsizar(texto: str, medir: Callable[[str], int], largura: int) -> str:
    """Corta `texto` com '…' apenas se não couber em `largura` pixels.

    `medir` devolve a largura em pixels de um texto (ex.: `tkinter.font.Font.measure`).
    """
    if medir(texto) <= largura:
        return texto
    baixo, alto = 0, len(texto)
    while baixo < alto:                      # busca binária do maior prefixo que cabe
        meio = (baixo + alto + 1) // 2
        if medir(texto[:meio].rstrip() + "…") <= largura:
            baixo = meio
        else:
            alto = meio - 1
    return texto[:baixo].rstrip() + "…" if baixo else "…"


def repartir_por_dia(inicio: datetime, fim: datetime, segundos: float) -> Dict[date, float]:
    """Reparte `segundos` entre os dias do calendário tocados por [inicio, fim].

    A parte de cada dia é proporcional ao tempo de relógio que o intervalo passou naquele dia.
    Ex.: 22:00 -> 02:00 com 4 h jogadas = 2 h em cada dia. Intervalo vazio/invertido = tudo no dia de `fim`.
    """
    if segundos <= 0:
        return {}
    if fim <= inicio or inicio.date() == fim.date():
        return {fim.date(): float(segundos)}
    total = (fim - inicio).total_seconds()
    resultado: Dict[date, float] = {}
    cursor = inicio
    while cursor.date() < fim.date():
        meia_noite = datetime.combine(cursor.date() + timedelta(days=1), datetime.min.time())
        resultado[cursor.date()] = resultado.get(cursor.date(), 0.0) + segundos * (meia_noite - cursor).total_seconds() / total
        cursor = meia_noite
    resultado[fim.date()] = resultado.get(fim.date(), 0.0) + segundos * (fim - cursor).total_seconds() / total
    return resultado


K = TypeVar("K", bound=Hashable)


def inteiros_somando(valores: Dict[K, float], total: int) -> Dict[K, int]:
    """Converte valores fracionários em inteiros que SOMAM exatamente `total` (método do maior resto).

    Os valores são tratados como proporções (são reescalados para somar `total`). Zeros são omitidos.
    """
    soma = sum(v for v in valores.values() if v > 0)
    if total <= 0 or soma <= 0:
        return {}
    escalados = {k: v * total / soma for k, v in valores.items() if v > 0}
    base = {k: int(v) for k, v in escalados.items()}
    faltam = total - sum(base.values())
    for k in sorted(escalados, key=lambda c: escalados[c] - base[c], reverse=True)[:faltam]:
        base[k] += 1
    return {k: v for k, v in base.items() if v > 0}
