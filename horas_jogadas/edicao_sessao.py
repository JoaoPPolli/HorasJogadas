"""Validação (sem interface) dos dados digitados ao editar ou adicionar uma sessão."""
from datetime import datetime, timedelta
from typing import Optional, Sequence, Tuple

FORMATOS_ISO = ("%Y-%m-%d %H:%M:%S", "%Y-%m-%d %H:%M")
LIMITE_CONFIRMACAO_S = 24 * 3600          # acima disso o app pede confirmação (erro de digitação é comum)
LIMITE_AVISO_S = 12 * 3600                # acima disso o histórico marca a sessão com um aviso


class ErroSessao(ValueError):
    """Dado inválido; `chave` é a chave de tradução da mensagem (ex.: 'sessao.erro_data')."""

    def __init__(self, chave: str):
        super().__init__(chave)
        self.chave = chave


def interpretar_data_hora(texto: str, formatos_locais: Sequence[str] = ()) -> Optional[datetime]:
    """Aceita o formato do idioma (ex.: 10/10/2026 03:00) e também o ISO (2026-10-10 03:00[:00])."""
    texto = " ".join((texto or "").split())
    for formato in tuple(formatos_locais) + FORMATOS_ISO:
        try:
            return datetime.strptime(texto, formato)
        except ValueError:
            continue
    return None


def validar(termino: str, horas: str, minutos: str, segundos: str, agora: datetime,
            formatos_locais: Sequence[str] = ()) -> Tuple[datetime, int]:
    """Devolve (término, duração em segundos) ou levanta ErroSessao com a mensagem certa."""
    fim = interpretar_data_hora(termino, formatos_locais)
    if fim is None:
        raise ErroSessao("sessao.erro_data")
    try:
        partes = [int(x) if str(x).strip() else 0 for x in (horas, minutos, segundos)]
    except ValueError:
        raise ErroSessao("sessao.erro_duracao") from None
    if min(partes) < 0:
        raise ErroSessao("sessao.erro_duracao")
    duracao = partes[0] * 3600 + partes[1] * 60 + partes[2]
    if duracao < 1:
        raise ErroSessao("sessao.erro_duracao")
    if fim > agora + timedelta(minutes=1):
        raise ErroSessao("sessao.erro_futuro")
    return fim, duracao
