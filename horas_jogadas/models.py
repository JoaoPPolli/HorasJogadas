"""Modelos de dados do aplicativo."""
import uuid
from dataclasses import dataclass
from datetime import date, datetime, timedelta
from typing import Any, Dict, Optional, Set

from .constants import FORMATO_DATA, STATUS_OPCOES, STATUS_PADRAO
from .utils import chave_nome, formatar_hhmmss, inteiros_somando, repartir_por_dia


def novo_id() -> str:
    return uuid.uuid4().hex


def normalizar_status(status: Any) -> str:
    """Devolve um status válido (ignora diferenças de caixa)."""
    if isinstance(status, str):
        for valido in STATUS_OPCOES:
            if valido.casefold() == status.strip().casefold():
                return valido
    return STATUS_PADRAO


@dataclass
class Jogo:
    id: str
    nome: str
    status: str = STATUS_PADRAO

    def to_dict(self) -> dict:
        return {"id": self.id, "nome": self.nome, "status": self.status}


@dataclass
class Sessao:
    sessao_id: str
    jogo_id: Optional[str]
    jogo: str
    segundos: int
    tempo: str
    data: str                      # fim da sessão (compatível com o formato antigo)
    inicio: Optional[str] = None
    fim: Optional[str] = None
    dias: Optional[Dict[str, int]] = None    # segundos jogados em cada dia (AAAA-MM-DD); None = não registrado

    @classmethod
    def nova(cls, jogo_id: Optional[str], jogo: str, segundos: int,
             inicio: Optional[datetime], fim: datetime, dias: Optional[Dict[Any, int]] = None) -> "Sessao":
        return cls(
            sessao_id=novo_id(), jogo_id=jogo_id, jogo=jogo, segundos=int(segundos),
            tempo=formatar_hhmmss(segundos), data=fim.strftime(FORMATO_DATA),
            inicio=inicio.strftime(FORMATO_DATA) if inicio else None,
            fim=fim.strftime(FORMATO_DATA), dias=normalizar_dias(dias),
        )

    @property
    def inicio_dt(self) -> Optional[datetime]:
        try:
            return datetime.strptime(self.inicio, FORMATO_DATA) if self.inicio else None
        except (ValueError, TypeError):
            return None

    def segundos_por_dia(self) -> Dict[date, int]:
        """Quanto desta sessão foi jogado em cada dia do calendário (soma = segundos).

        Usa o detalhe gravado (`dias`). Sessões antigas não o têm: se começaram e terminaram em dias
        diferentes (até 36 h de intervalo), reparte proporcionalmente ao tempo de relógio de cada dia;
        senão, tudo vai para o dia em que terminaram.
        """
        if self.segundos <= 0:
            return {}
        if self.dias:
            try:
                detalhado = {date.fromisoformat(k): int(v) for k, v in self.dias.items() if int(v) > 0}
            except (ValueError, TypeError):
                detalhado = {}
            if detalhado:
                return inteiros_somando(detalhado, self.segundos)     # garante soma == segundos
        fim = self.data_dt
        if fim is None:
            return {}
        inicio = self.inicio_dt
        if inicio and inicio < fim and inicio.date() != fim.date() and fim - inicio <= timedelta(hours=36):
            return inteiros_somando(repartir_por_dia(inicio, fim, self.segundos), self.segundos)
        return {fim.date(): self.segundos}

    @property
    def data_dt(self) -> Optional[datetime]:
        """Data/hora de término como datetime, ou None se inválida."""
        try:
            return datetime.strptime(self.data, FORMATO_DATA)
        except (ValueError, TypeError):
            return None

    def to_dict(self) -> dict:
        d = {
            "sessao_id": self.sessao_id, "jogo_id": self.jogo_id, "jogo": self.jogo,
            "segundos": self.segundos, "tempo": self.tempo, "data": self.data,
        }
        if self.inicio:
            d["inicio"] = self.inicio
        if self.fim:
            d["fim"] = self.fim
        if self.dias:
            d["dias"] = self.dias
        return d


@dataclass
class EstadoSessao:
    """Sessão aberta (rodando ou pausada), gravada para recuperação após crash."""
    jogo_id: Optional[str]
    jogo: str
    acumulado: float               # segundos já acumulados (sem contar o trecho rodando)
    rodando: bool
    retomado_em: float             # epoch do último "iniciar"
    ultimo_heartbeat: float        # epoch da última gravação deste estado
    inicio: Optional[str] = None   # início da sessão (texto no FORMATO_DATA)
    dias: Optional[Dict[str, float]] = None   # segundos já acumulados em cada dia (sem o trecho que está rodando)

    def segundos_recuperaveis(self) -> int:
        total = self.acumulado
        if self.rodando:
            total += max(0.0, self.ultimo_heartbeat - self.retomado_em)
        return int(round(max(0.0, total)))

    def dias_recuperaveis(self) -> Optional[Dict[str, int]]:
        """Segundos por dia da sessão recuperável (inclui o trecho que estava rodando, repartido entre os dias)."""
        total = self.segundos_recuperaveis()
        por_dia: Dict[str, float] = dict(self.dias or {})
        if self.rodando and self.ultimo_heartbeat > self.retomado_em:
            try:
                extra = repartir_por_dia(datetime.fromtimestamp(self.retomado_em),
                                         datetime.fromtimestamp(self.ultimo_heartbeat),
                                         self.ultimo_heartbeat - self.retomado_em)
            except (OverflowError, OSError, ValueError):
                extra = {}
            for dia, seg in extra.items():
                por_dia[dia.isoformat()] = por_dia.get(dia.isoformat(), 0.0) + seg
        return inteiros_somando(por_dia, total) or None

    def to_dict(self) -> dict:
        return {
            "jogo_id": self.jogo_id, "jogo": self.jogo, "acumulado": self.acumulado,
            "rodando": self.rodando, "retomado_em": self.retomado_em,
            "ultimo_heartbeat": self.ultimo_heartbeat, "inicio": self.inicio, "dias": self.dias,
        }

    @classmethod
    def from_dict(cls, d: dict) -> "EstadoSessao":
        return cls(
            jogo_id=d.get("jogo_id"), jogo=str(d.get("jogo", "Sem Nome")),
            acumulado=float(d.get("acumulado", 0)), rodando=bool(d.get("rodando", False)),
            retomado_em=float(d.get("retomado_em", 0)),
            ultimo_heartbeat=float(d.get("ultimo_heartbeat", 0)),
            inicio=d.get("inicio"), dias=_dias_float(d.get("dias")),
        )


def normalizar_dias(dias: Optional[Dict[Any, Any]]) -> Optional[Dict[str, int]]:
    """Aceita chaves `date` ou texto AAAA-MM-DD; devolve {texto: segundos>0} ou None se não houver nada válido."""
    if not dias:
        return None
    resultado: Dict[str, int] = {}
    for chave, valor in dias.items():
        try:
            iso = chave.isoformat() if isinstance(chave, date) else date.fromisoformat(str(chave)).isoformat()
            segundos = int(valor)
        except (ValueError, TypeError):
            continue
        if segundos > 0:
            resultado[iso] = resultado.get(iso, 0) + segundos
    return resultado or None


def _dias_float(dias: Any) -> Optional[Dict[str, float]]:
    if not isinstance(dias, dict):
        return None
    try:
        return {str(k): float(v) for k, v in dias.items()} or None
    except (ValueError, TypeError):
        return None


def chave_sessao(sessao: Sessao, ids_validos: Set[str]) -> str:
    """Chave de agrupamento: id do jogo se ele existe; senão, agrupa pelo nome (órfão)."""
    if sessao.jogo_id and sessao.jogo_id in ids_validos:
        return sessao.jogo_id
    return "nome:" + chave_nome(sessao.jogo)
