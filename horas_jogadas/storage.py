"""Persistência em JSON: escrita atômica, backup, leitura segura e migração.

Toda a interação com arquivos do aplicativo passa por este módulo; a interface
nunca abre os JSON diretamente.
"""
import json
import logging
import os
import shutil
from datetime import datetime, timedelta
from typing import Any, Callable, Dict, List, Optional, Tuple

from .constants import (
    CONFIG_PADRAO, DATA_DIR, IDIOMAS_DISPONIVEIS, NOME_ARQ_ANDAMENTO, NOME_ARQ_CONFIG,
    NOME_ARQ_CRONOMETROS, NOME_ARQ_REGISTROS, ORDENACOES, STATUS_PADRAO,
)
from . import backups
from .i18n import t
from .models import EstadoSessao, Jogo, Sessao, chave_sessao, normalizar_dias, normalizar_status, novo_id
from .stats import totais_por_jogo_id
from .utils import chave_nome, formatar_hhmmss

log = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Funções de baixo nível
# ---------------------------------------------------------------------------
def _carregar_validado(caminho: str, tipo: type) -> Any:
    """Lê um JSON e garante o tipo esperado (list/dict). Levanta OSError/ValueError."""
    with open(caminho, "r", encoding="utf-8") as f:
        dados = json.load(f)
    if not isinstance(dados, tipo):
        raise ValueError(f"conteúdo inesperado (esperado {tipo.__name__})")
    return dados


def escrever_json_atomico(caminho: str, dados: Any, backup: bool = True) -> None:
    """Grava JSON de forma atômica (tmp + fsync + os.replace).

    Se `backup` for verdadeiro e o arquivo atual for um JSON válido, ele é copiado
    para `<arquivo>.bak` antes de ser substituído.
    """
    pasta = os.path.dirname(caminho) or "."
    os.makedirs(pasta, exist_ok=True)
    if backup and os.path.exists(caminho):
        try:
            with open(caminho, "r", encoding="utf-8") as f:
                json.load(f)
            shutil.copy2(caminho, caminho + ".bak")
        except (OSError, ValueError):
            log.warning("Arquivo atual inválido; backup anterior (.bak) mantido: %s", caminho)
    tmp = caminho + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(dados, f, indent=4, ensure_ascii=False)
        f.flush()
        os.fsync(f.fileno())
    os.replace(tmp, caminho)


Aviso = Tuple[str, dict]          # (chave de tradução, valores) — traduzido só ao exibir


def ler_json_seguro(caminho: str, padrao: Callable[[], Any], tipo: type = list
                    ) -> Tuple[Any, Optional[Aviso]]:
    """Lê um JSON sem nunca descartar dados silenciosamente.

    Retorna (dados, aviso). Se o arquivo não existe, devolve o padrão sem aviso.
    Se estiver corrompido: preserva uma cópia como `.corrompido-<data>`, tenta o
    `.bak` e só então recorre ao padrão — sempre devolvendo um aviso para o usuário.
    """
    if not os.path.exists(caminho):
        return padrao(), None
    try:
        return _carregar_validado(caminho, tipo), None
    except (OSError, ValueError) as e:
        log.error("Falha ao ler %s: %s", caminho, e)

    nome = os.path.basename(caminho)
    corrompido = f"{caminho}.corrompido-{datetime.now():%Y%m%d-%H%M%S}"
    try:
        os.replace(caminho, corrompido)
    except OSError:
        try:
            shutil.copy2(caminho, corrompido)
        except OSError:
            log.exception("Não foi possível preservar o arquivo corrompido %s", caminho)
            corrompido = None                                  # vira "(não foi possível...)" ao exibir

    bak = caminho + ".bak"
    if os.path.exists(bak):
        try:
            dados = _carregar_validado(bak, tipo)
            shutil.copy2(bak, caminho)
            log.warning("%s restaurado a partir do backup", nome)
            return dados, ("aviso.restaurado", {"arquivo": nome, "copia": corrompido})
        except (OSError, ValueError):
            log.error("Backup %s também está inválido", bak)

    return padrao(), ("aviso.corrompido", {"arquivo": nome, "copia": corrompido})


# ---------------------------------------------------------------------------
# Repositório
# ---------------------------------------------------------------------------
class Repositorio:
    """Fonte única de verdade para jogos, sessões, estado em andamento e config."""

    def __init__(self, data_dir: Optional[str] = None, config_legado: Optional[str] = None):
        self.data_dir = data_dir or DATA_DIR
        os.makedirs(self.data_dir, exist_ok=True)
        self.arq_sessoes = os.path.join(self.data_dir, NOME_ARQ_REGISTROS)
        self.arq_jogos = os.path.join(self.data_dir, NOME_ARQ_CRONOMETROS)
        self.arq_config = os.path.join(self.data_dir, NOME_ARQ_CONFIG)
        self.arq_andamento = os.path.join(self.data_dir, NOME_ARQ_ANDAMENTO)
        self._config_legado = (config_legado if config_legado is not None
                               else os.path.join(os.getcwd(), NOME_ARQ_CONFIG))

        self._avisos: List[Aviso] = []                    # avisos para mostrar ao iniciar
        self.notificar_erro: Optional[Callable[[str], None]] = None
        self.jogos: List[Jogo] = []
        self.sessoes: List[Sessao] = []
        self._carregar()

    # -- avisos / erros ------------------------------------------------------
    def pop_avisos(self) -> List[str]:
        """Avisos pendentes já traduzidos para o idioma ativo no momento da chamada."""
        avisos, self._avisos = self._avisos, []
        textos = []
        for chave, valores in avisos:
            valores = dict(valores)
            if valores.get("copia") is None:
                valores["copia"] = t("aviso.sem_copia")
            textos.append(t(chave, **valores))
        return textos

    def _gravar(self, caminho: str, dados: Any, backup: bool = True) -> bool:
        try:
            escrever_json_atomico(caminho, dados, backup=backup)
            return True
        except OSError as e:
            log.exception("Erro ao gravar %s", caminho)
            if self.notificar_erro:
                self.notificar_erro(t("erro.gravar", arquivo=os.path.basename(caminho), erro=e))
            return False

    # -- carga e migração ----------------------------------------------------
    def _carregar(self) -> None:
        raw_jogos, aviso = ler_json_seguro(self.arq_jogos, list, list)
        if aviso:
            self._avisos.append(aviso)
        raw_sessoes, aviso = ler_json_seguro(self.arq_sessoes, list, list)
        if aviso:
            self._avisos.append(aviso)

        self.jogos, jogos_mudaram = self._migrar_jogos(raw_jogos)
        self.sessoes, sessoes_mudaram = self._migrar_sessoes(raw_sessoes, self.jogos)

        if jogos_mudaram:
            self._guardar_pre_migracao(self.arq_jogos)
            self._gravar(self.arq_jogos, [j.to_dict() for j in self.jogos])
        if sessoes_mudaram:
            self._guardar_pre_migracao(self.arq_sessoes)
            self._gravar(self.arq_sessoes, [s.to_dict() for s in self.sessoes])

    @staticmethod
    def _guardar_pre_migracao(caminho: str) -> None:
        """Guarda, uma única vez, uma cópia do arquivo original antes de migrá-lo."""
        destino = caminho + ".pre-migracao"
        if os.path.exists(caminho) and not os.path.exists(destino):
            try:
                shutil.copy2(caminho, destino)
            except OSError:
                log.exception("Não foi possível criar cópia pré-migração de %s", caminho)

    @staticmethod
    def _migrar_jogos(raw: List[Any]) -> Tuple[List[Jogo], bool]:
        jogos: List[Jogo] = []
        mudou = False
        ids_vistos = set()
        for item in raw:
            if isinstance(item, str):                      # formato antigo
                nome = item.strip()
                mudou = True
                if nome:
                    jogos.append(Jogo(novo_id(), nome, STATUS_PADRAO))
                continue
            if not isinstance(item, dict):
                log.warning("Entrada de jogo ignorada (formato desconhecido): %r", item)
                mudou = True
                continue
            nome = str(item.get("nome") or "").strip()
            if not nome:
                nome, mudou = "Sem Nome", True
            jid = item.get("id")
            if not isinstance(jid, str) or not jid or jid in ids_vistos:
                jid, mudou = novo_id(), True
            status = normalizar_status(item.get("status"))
            if status != item.get("status"):
                mudou = True
            ids_vistos.add(jid)
            jogos.append(Jogo(jid, nome, status))
        return jogos, mudou

    @staticmethod
    def _migrar_sessoes(raw: List[Any], jogos: List[Jogo]) -> Tuple[List[Sessao], bool]:
        por_nome: Dict[str, Jogo] = {}
        for j in jogos:
            por_nome.setdefault(chave_nome(j.nome), j)
        sessoes: List[Sessao] = []
        mudou = False
        ids_vistos = set()
        for reg in raw:
            if not isinstance(reg, dict):
                log.warning("Registro ignorado (formato desconhecido): %r", reg)
                mudou = True
                continue
            nome = str(reg.get("jogo") or "Sem Nome")
            try:
                segundos = int(reg.get("segundos", 0))
            except (TypeError, ValueError):
                log.warning("Registro com 'segundos' inválido tratado como 0: %r", reg)
                segundos = 0
            tempo = reg.get("tempo")
            if not tempo:
                tempo, mudou = formatar_hhmmss(segundos), True
            sid = reg.get("sessao_id")
            if not isinstance(sid, str) or not sid or sid in ids_vistos:
                sid, mudou = novo_id(), True
            ids_vistos.add(sid)
            if "jogo_id" not in reg:
                mudou = True
            jid = reg.get("jogo_id")
            if jid is None:
                encontrado = por_nome.get(chave_nome(nome))
                if encontrado:
                    jid, mudou = encontrado.id, True
            sessoes.append(Sessao(
                sessao_id=sid, jogo_id=jid, jogo=nome, segundos=segundos, tempo=str(tempo),
                data=str(reg.get("data") or ""), inicio=reg.get("inicio"), fim=reg.get("fim"),
                dias=normalizar_dias(reg.get("dias")),
            ))
        return sessoes, mudou

    # -- jogos ---------------------------------------------------------------
    def jogo_por_id(self, jogo_id: Optional[str]) -> Optional[Jogo]:
        return next((j for j in self.jogos if j.id == jogo_id), None)

    def validar_nome(self, nome: str, ignorar_id: Optional[str] = None) -> str:
        """Devolve o nome limpo ou levanta ValueError (vazio ou duplicado)."""
        limpo = " ".join((nome or "").split())
        if not limpo:
            raise ValueError(t("erro.nome_vazio"))
        chave = chave_nome(limpo)
        for j in self.jogos:
            if j.id != ignorar_id and chave_nome(j.nome) == chave:
                raise ValueError(t("erro.nome_duplicado", nome=j.nome))
        return limpo

    def salvar_jogos(self, jogos: List[Jogo]) -> None:
        """Substitui a lista de jogos (a ordem recebida é a ordem manual salva)."""
        self.jogos = list(jogos)
        self._gravar(self.arq_jogos, [j.to_dict() for j in self.jogos])

    def adicionar_jogo(self, nome: str, status: str = STATUS_PADRAO) -> Jogo:
        """Cria um jogo no TOPO da lista. Sessões órfãs com o mesmo nome (de um jogo excluído)
        são readotadas."""
        limpo = self.validar_nome(nome)
        jogo = Jogo(novo_id(), limpo, normalizar_status(status))
        self.jogos.insert(0, jogo)
        ids = {j.id for j in self.jogos}
        chave = chave_nome(limpo)
        adotadas = 0
        for s in self.sessoes:
            if s.jogo_id not in ids and chave_nome(s.jogo) == chave:
                s.jogo_id, s.jogo = jogo.id, jogo.nome
                adotadas += 1
        self._gravar(self.arq_jogos, [j.to_dict() for j in self.jogos])
        if adotadas:
            log.info("%d sessão(ões) órfã(s) readotada(s) por '%s'", adotadas, jogo.nome)
            self._salvar_sessoes()
        return jogo

    def renomear_jogo(self, jogo_id: str, novo_nome: str) -> str:
        """Renomeia o jogo e todas as sessões vinculadas. Levanta ValueError se inválido."""
        jogo = self.jogo_por_id(jogo_id)
        if jogo is None:
            raise ValueError(t("erro.jogo_nao_encontrado"))
        limpo = self.validar_nome(novo_nome, ignorar_id=jogo_id)
        jogo.nome = limpo
        for s in self.sessoes:
            if s.jogo_id == jogo_id:
                s.jogo = limpo
        self._gravar(self.arq_jogos, [j.to_dict() for j in self.jogos])
        self._salvar_sessoes()
        return limpo

    # -- sessões -------------------------------------------------------------
    def _salvar_sessoes(self) -> None:
        self._gravar(self.arq_sessoes, [s.to_dict() for s in self.sessoes])

    def adicionar_sessao(self, jogo_id: Optional[str], nome: str, segundos: int,
                         inicio: Optional[datetime], fim: datetime, dias=None) -> Sessao:
        sessao = Sessao.nova(jogo_id, nome, segundos, inicio, fim, dias)
        self.sessoes.append(sessao)
        self._salvar_sessoes()
        return sessao

    def atualizar_sessao(self, sessao_id: str, jogo_id: Optional[str], nome: str, segundos: int, fim: datetime) -> bool:
        """Edita uma sessão: jogo, duração e término. O início é recalculado (término - duração) e o
        detalhe por dia é descartado (será repartido pelo intervalo). Devolve False se a sessão não existe."""
        atual = next((s for s in self.sessoes if s.sessao_id == sessao_id), None)
        if atual is None:
            return False
        nova = Sessao.nova(jogo_id, nome, segundos, fim - timedelta(seconds=segundos), fim)
        nova.sessao_id = atual.sessao_id
        self.sessoes[self.sessoes.index(atual)] = nova
        self._salvar_sessoes()
        return True

    def remover_sessao(self, sessao_id: str) -> bool:
        antes = len(self.sessoes)
        self.sessoes = [s for s in self.sessoes if s.sessao_id != sessao_id]
        if len(self.sessoes) == antes:
            return False
        self._salvar_sessoes()
        return True

    def inserir_sessao(self, indice: int, sessao: Sessao) -> None:
        """Recoloca uma sessão na posição original (usado pelo 'Desfazer' do histórico)."""
        if any(s.sessao_id == sessao.sessao_id for s in self.sessoes):
            return
        self.sessoes.insert(max(0, min(indice, len(self.sessoes))), sessao)
        self._salvar_sessoes()

    def remover_sessoes_do_grupo(self, chave: str) -> int:
        """Remove todas as sessões de um grupo do dashboard (id do jogo ou 'nome:...').

        Antes de apagar, guarda um backup automático ('antes_de_apagar')."""
        ids = {j.id for j in self.jogos}
        alvo = [s for s in self.sessoes if chave_sessao(s, ids) == chave]
        if not alvo:
            return 0
        self._backup_de_seguranca("apagar-jogo")
        self.sessoes = [s for s in self.sessoes if chave_sessao(s, ids) != chave]
        self._salvar_sessoes()
        return len(alvo)

    def limpar_sessoes(self) -> None:
        """Apaga todo o histórico. Antes, guarda um backup automático ('antes_de_apagar')."""
        if self.sessoes:
            self._backup_de_seguranca("apagar-historico")
        self.sessoes = []
        self._salvar_sessoes()

    # -- backups -------------------------------------------------------------
    def _backup_de_seguranca(self, motivo: str) -> None:
        """Rede de segurança de operações destrutivas: uma falha aqui não impede a operação."""
        try:
            backups.criar_backup(self.data_dir, "antes_de_apagar", motivo)
        except OSError:
            log.exception("Não foi possível criar o backup de segurança (%s)", motivo)

    def backup_diario(self) -> Optional[str]:
        """Cria o backup do dia se ainda não existe (barato: só olha se a pasta do dia já está lá)."""
        try:
            return backups.backup_diario(self.data_dir)
        except OSError:
            log.exception("Não foi possível criar o backup diário")
            return None

    def criar_backup_manual(self) -> Optional[str]:
        return backups.criar_backup(self.data_dir, "manual")

    def listar_backups(self) -> List[backups.InfoBackup]:
        return backups.listar_backups(self.data_dir)

    def restaurar_backup(self, info: backups.InfoBackup) -> None:
        """Restaura o backup nos arquivos. O app precisa ser reiniciado em seguida para recarregar."""
        backups.restaurar_backup(self.data_dir, info.caminho)
        self.limpar_andamento()

    def totais_por_jogo_id(self) -> Dict[str, int]:
        return totais_por_jogo_id(self.sessoes)

    # -- sessões em andamento (recuperação após falha) ------------------------
    def salvar_andamento(self, estados: List[EstadoSessao]) -> None:
        if not estados:
            self.limpar_andamento()
            return
        self._gravar(self.arq_andamento, [e.to_dict() for e in estados], backup=False)

    def carregar_andamento(self) -> List[EstadoSessao]:
        if not os.path.exists(self.arq_andamento):
            return []
        try:
            raw = _carregar_validado(self.arq_andamento, list)
            return [EstadoSessao.from_dict(d) for d in raw if isinstance(d, dict)]
        except (OSError, ValueError, TypeError):
            log.exception("Estado em andamento ilegível; ignorado")
            return []

    def limpar_andamento(self) -> None:
        try:
            if os.path.exists(self.arq_andamento):
                os.remove(self.arq_andamento)
        except OSError:
            log.exception("Não foi possível remover %s", self.arq_andamento)

    # -- configuração --------------------------------------------------------
    def carregar_config(self) -> Dict[str, Any]:
        self._migrar_config_legado()
        dados, aviso = ler_json_seguro(self.arq_config, dict, dict)
        if aviso:
            self._avisos.append(aviso)
        cfg = dict(CONFIG_PADRAO)
        cfg.update({k: v for k, v in dados.items() if k in CONFIG_PADRAO})
        if cfg["modo_navegacao"] not in ("janelas", "navegacao"):
            cfg["modo_navegacao"] = CONFIG_PADRAO["modo_navegacao"]
        if cfg["ordenacao"] not in ORDENACOES:
            cfg["ordenacao"] = CONFIG_PADRAO["ordenacao"]
        if cfg["idioma"] not in IDIOMAS_DISPONIVEIS:
            cfg["idioma"] = CONFIG_PADRAO["idioma"]
        return cfg

    def salvar_config(self, cfg: Dict[str, Any]) -> None:
        self._gravar(self.arq_config, cfg)

    def _migrar_config_legado(self) -> None:
        """Copia o config.json antigo (salvo na pasta atual) para o DATA_DIR, uma vez."""
        legado = self._config_legado
        if (not legado or os.path.exists(self.arq_config) or not os.path.exists(legado)
                or os.path.abspath(legado) == os.path.abspath(self.arq_config)):
            return
        try:
            shutil.copy2(legado, self.arq_config)
            log.info("config.json migrado de %s", legado)
        except OSError:
            log.exception("Falha ao migrar config.json legado")
