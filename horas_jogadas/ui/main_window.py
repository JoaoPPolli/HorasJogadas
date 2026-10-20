"""Janela principal: biblioteca de jogos, filtros, busca e ordenação."""
import logging
import os
import time
import tkinter as tk
from datetime import datetime
from tkinter import messagebox, ttk
from typing import Dict, List, Optional, Tuple

from ..constants import (
    CARD_LARGURA, CARD_PADDING_X, COR_ACCENT, COR_CARD, COR_TEXTO_SUAVE, FILTROS_STATUS,
    FORMATO_DATA, INTERVALO_BACKUP_S, INTERVALO_HEARTBEAT_S, INTERVALO_SINAL_LOOPS, INTERVALO_UPDATE_MS,
    MAX_COLUNAS, NOME_ARQ_LOG,
    ORDENACAO_PADRAO, ORDENACOES,
)
from .. import i18n, icone_barra, instancia
from ..i18n import rotulo_filtro, t
from ..models import Jogo
from ..stats import ultima_sessao_por_jogo_id
from ..storage import Repositorio
from ..zerados import RepositorioZerados
from ..utils import formatar_hhmmss, normalizar_texto
from .configuracao import abrir_configuracao
from .cronometro_card import Cronometro
from .dashboard import abrir_dashboard
from .historico import abrir_historico
from .theme import aplicar_tema_moderno
from .widgets import GerenciadorScroll, ScrollableFrame
from .zerados import abrir_zerados, editar_registro, mostrar_erro

log = logging.getLogger(__name__)


class App:
    """Controlador da janela principal."""

    def __init__(self, root: tk.Tk, repo: Optional[Repositorio] = None, trava=None, backend_icone="auto"):
        self.root = root
        root.geometry("950x700")
        aplicar_tema_moderno(root)

        self.trava = trava                                  # trava de instância única (liberada ao reiniciar)
        # selo na barra de tarefas (bolinha vermelha = rodando, pause amarelo = pausado); no-op fora do Windows
        self.sobreposicao = icone_barra.SobreposicaoBarra(
            janela_id=root.winfo_id, descricao=lambda estado: t(f"icone.{estado}"),
            backend=icone_barra.criar_backend() if backend_icone == "auto" else backend_icone)
        self.repo = repo or Repositorio()
        self.zerados = None                       # carregado apenas quando usado; arquivo independente
        self.repo.notificar_erro = lambda msg: messagebox.showerror(t("dlg.erro_salvar"), msg)
        self.config = self.repo.carregar_config()
        i18n.definir_idioma(self.config["idioma"])         # antes de criar qualquer texto
        root.title(t("app.titulo"))
        self._popups: List[tk.Misc] = []
        self._ciclos = 0
        self._ultima_checagem_backup = time.monotonic()
        self.repo.backup_diario()                           # cópia do dia (no máximo uma por dia)
        self.filtro_ativo = "TODOS"
        self.ordenacao = self.config.get("ordenacao", ORDENACAO_PADRAO)
        self.cronometros: List[Cronometro] = []
        self._ultimo_heartbeat = time.monotonic()
        self._colunas_atuais = 0                      # colunas da grade já aplicada
        self._assinatura_grid: Optional[tuple] = None  # (colunas, ids visíveis em ordem)
        self._erro_loop_registrado = False

        self.scroll = GerenciadorScroll(root)
        self.main_container = ttk.Frame(root)
        self.main_container.pack(fill="both", expand=True)
        self.frame_home = ttk.Frame(self.main_container)
        self.frame_conteudo = ttk.Frame(self.main_container)

        self.construir_home()
        self.mostrar_home()

        root.report_callback_exception = self._erro_inesperado
        root.protocol("WM_DELETE_WINDOW", self.ao_fechar)
        root.bind("<Control-f>", self._focar_busca)
        root.bind("<Control-F>", self._focar_busca)

        root.update_idletasks()
        self._mostrar_avisos()
        self._verificar_recuperacao()
        root.after(INTERVALO_UPDATE_MS, self._loop_atualizacao)

    # ------------------------------------------------------------------
    # Construção da home
    # ------------------------------------------------------------------
    def construir_home(self) -> None:
        top = ttk.Frame(self.frame_home)
        top.pack(fill="x", padx=12, pady=10)

        self.entry_nome = ttk.Entry(top)
        self.entry_nome.pack(side="left", fill="x", expand=True, padx=(0, 8))
        self.entry_nome.bind("<Return>", lambda e: self.adicionar_cronometro())
        self.btn_adicionar = ttk.Button(top, text=t("btn.adicionar"), command=self.adicionar_cronometro,
                                        style="Accent.TButton")
        self.btn_adicionar.pack(side="left", padx=2)
        self.btn_historico = ttk.Button(top, text=t("btn.historico"), command=self.abrir_historico)
        self.btn_historico.pack(side="left", padx=2)
        self.btn_dashboard = ttk.Button(top, text=t("btn.dashboard"), command=self.abrir_dashboard)
        self.btn_dashboard.pack(side="left", padx=2)
        self.btn_zerados = ttk.Button(top, text=t('zer.titulo'), command=self.abrir_zerados)
        self.btn_zerados.pack(side='left', padx=2)
        ttk.Button(top, text="⚙️", width=3, command=self.abrir_configuracao).pack(side="left", padx=2)

        barra = ttk.Frame(self.frame_home, padding=(10, 0))
        barra.pack(fill="x")
        self.botoes_filtro: Dict[str, tk.Button] = {}
        for f in FILTROS_STATUS:
            btn = tk.Button(barra, text=rotulo_filtro(f), bg=COR_CARD, fg=COR_TEXTO_SUAVE, relief="flat",
                            font=("Segoe UI", 8, "bold"), cursor="hand2",
                            command=lambda opt=f: self.set_filtro(opt))
            btn.pack(side="left", padx=2, pady=5)
            self.botoes_filtro[f] = btn

        # Ordenação e busca (à direita da barra de filtros)
        self.combo_ordem = ttk.Combobox(barra, state="readonly", width=20,
                                        values=self._rotulos_ordenacao())
        self.combo_ordem.set(t(f"ord.{self.ordenacao}"))
        self.combo_ordem.pack(side="right", padx=(6, 0))
        self.combo_ordem.bind("<<ComboboxSelected>>", self._ao_mudar_ordenacao)
        self.combo_ordem.bind("<MouseWheel>", lambda e: "break")   # não troca opção ao rolar
        self.var_busca = tk.StringVar()
        self.var_busca.trace_add("write", lambda *_: self.reorganizar_grid())
        self.entry_busca = ttk.Entry(barra, textvariable=self.var_busca, width=24)
        self.entry_busca.pack(side="right")
        self.entry_busca.bind("<Escape>", self._limpar_busca)
        self.lbl_busca = ttk.Label(barra, text=t("busca.rotulo"), style="Small.TLabel")
        self.lbl_busca.pack(side="right", padx=(8, 4))

        self.scroll_home = ScrollableFrame(self.frame_home, self.scroll)
        self.scroll_home.pack(fill="both", expand=True, padx=8, pady=(5, 12))
        self.canvas_home = self.scroll_home.canvas
        self.inner_frame = self.scroll_home.interior
        self.barra_zerados = ttk.Frame(self.frame_home, padding=8, style='Card.TFrame')
        self.canvas_home.bind("<Configure>", self._ao_redimensionar, add="+")
        self.lbl_vazio = ttk.Label(self.inner_frame, text="", style="Small.TLabel", font=("Segoe UI", 11))

        self.recriar_cronometros_salvos()
        self.set_filtro("TODOS")

    def mostrar_home(self) -> None:
        self.frame_conteudo.pack_forget()
        self.frame_home.pack(fill="both", expand=True)
        self.root.update_idletasks()               # largura real do canvas antes de medir
        self.reorganizar_grid()

    def mostrar_conteudo(self) -> None:
        self.frame_home.pack_forget()
        self.frame_conteudo.pack(fill="both", expand=True)
        for widget in self.frame_conteudo.winfo_children():
            widget.destroy()

    def preparar_janela_ou_frame(self, titulo: str) -> Tuple[tk.Misc, bool]:
        """Devolve (container, é_toplevel) conforme o modo de navegação configurado."""
        if self.config.get("modo_navegacao") == "navegacao":
            self.mostrar_conteudo()
            header = ttk.Frame(self.frame_conteudo, padding=10)
            header.pack(fill="x")
            ttk.Button(header, text=t("tela.voltar"), command=self.mostrar_home).pack(side="left")
            ttk.Label(header, text=titulo, font=("Segoe UI", 12, "bold")).pack(side="left", padx=15)
            conteudo = ttk.Frame(self.frame_conteudo)
            conteudo.pack(fill="both", expand=True)
            return conteudo, False
        jan = tk.Toplevel(self.root)
        jan.title(titulo)
        jan.geometry("720x520")
        aplicar_tema_moderno(jan)
        self._popups = [p for p in self._popups if p.winfo_exists()] + [jan]
        return jan, True

    def abrir_historico(self) -> None:
        abrir_historico(self)

    def abrir_dashboard(self) -> None:
        abrir_dashboard(self)

    def abrir_configuracao(self) -> None:
        abrir_configuracao(self)

    def obter_zerados(self):
        if self.zerados is None:
            try:
                self.zerados = RepositorioZerados(self.repo.data_dir)
            except (OSError, ValueError) as erro:
                mostrar_erro(self.root, erro)
                return None
            for aviso in self.zerados.avisos:
                messagebox.showwarning(t('zer.titulo'), aviso, parent=self.root)
        return self.zerados

    def abrir_zerados(self):
        return abrir_zerados(self)

    def registrar_conclusao(self, card):
        """Só envia uma cópia. Nada na lista escreve de volta no cronômetro ou nas sessões."""
        repo = self.obter_zerados()
        if repo is None:
            return
        try:
            registro = repo.registrar_automatico(card.jogo.id, card.nome, card.total_atual())
        except (OSError, ValueError) as erro:
            mostrar_erro(self.root, erro)
            return
        for widget in self.barra_zerados.winfo_children():
            widget.destroy()
        texto = t('zer.automatico', nome=registro.nome) if registro else t('zer.existente')
        ttk.Label(self.barra_zerados, text=texto, wraplength=520, style='Card.TLabel').pack(side='left', fill='x', expand=True)
        ttk.Button(self.barra_zerados, text='×', width=3, command=self.barra_zerados.pack_forget).pack(side='right', padx=3)
        ttk.Button(self.barra_zerados, text=t('zer.ver'), command=self.abrir_zerados).pack(side='right', padx=3)
        if registro:
            def atualizar(novo):
                repo.guardar(novo)
                self.root.event_generate('<<ZeradosAlterados>>', when='tail')

            def editar():
                atual = next((r for r in repo.registros if r.id == registro.id), None)
                if atual:
                    editar_registro(self.root, atual, atualizar)

            def desfazer():
                try:
                    repo.excluir(registro.id)
                except (OSError, ValueError) as erro:
                    mostrar_erro(self.root, erro)
                    return
                self.barra_zerados.pack_forget()
                self.root.event_generate('<<ZeradosAlterados>>', when='tail')

            ttk.Button(self.barra_zerados, text=t('hist.editar'), command=editar).pack(side='right', padx=3)
            ttk.Button(self.barra_zerados, text=t('hist.desfazer'), command=desfazer).pack(side='right', padx=3)
        self.barra_zerados.pack(fill='x', padx=12, pady=4, before=self.scroll_home)
        self.root.event_generate('<<ZeradosAlterados>>', when='tail')

    # ------------------------------------------------------------------
    # Idioma
    # ------------------------------------------------------------------
    def aplicar_idioma(self) -> None:
        """Reaplica os textos no idioma atual em toda a tela principal, sem recriar os cards."""
        self.root.title(t("app.titulo"))
        self.btn_adicionar.config(text=t("btn.adicionar"))
        self.btn_historico.config(text=t("btn.historico"))
        self.btn_dashboard.config(text=t("btn.dashboard"))
        self.btn_zerados.config(text=t('zer.titulo'))
        self.barra_zerados.pack_forget()
        for chave, btn in self.botoes_filtro.items():
            btn.config(text=rotulo_filtro(chave))
        self.lbl_busca.config(text=t("busca.rotulo"))
        self.combo_ordem.config(values=self._rotulos_ordenacao())
        self.combo_ordem.set(t(f"ord.{self.ordenacao}"))
        for card in self.cronometros:
            card.aplicar_idioma()
        for popup in self._popups:                       # janelas abertas ficariam em dois idiomas
            if popup.winfo_exists():
                popup.destroy()
        self._popups = []
        self._assinatura_grid = None                     # força atualizar o texto de "lista vazia"
        self.reorganizar_grid()

    # ------------------------------------------------------------------
    # Filtro, busca e ordenação
    # ------------------------------------------------------------------
    def set_filtro(self, filtro: str) -> None:
        self.filtro_ativo = filtro
        for k, btn in self.botoes_filtro.items():
            btn.config(bg=COR_ACCENT if k == filtro else COR_CARD,
                       fg="white" if k == filtro else COR_TEXTO_SUAVE)
        self.reorganizar_grid()

    @staticmethod
    def _rotulos_ordenacao() -> List[str]:
        return [t(f"ord.{k}") for k in ORDENACOES]

    def _focar_busca(self, _event: tk.Event = None) -> str:
        self.entry_busca.focus_set()
        self.entry_busca.select_range(0, tk.END)
        return "break"

    def _limpar_busca(self, _event: tk.Event = None) -> None:
        self.var_busca.set("")
        self.root.focus_set()

    def _ao_mudar_ordenacao(self, _event: tk.Event = None) -> None:
        rotulo = self.combo_ordem.get()
        self.ordenacao = next((k for k in ORDENACOES if t(f"ord.{k}") == rotulo), ORDENACAO_PADRAO)
        self.config["ordenacao"] = self.ordenacao
        self.repo.salvar_config(self.config)
        self._atualizar_mover_nos_cards()
        self.reorganizar_grid()
        self.root.focus_set()

    def _atualizar_mover_nos_cards(self) -> None:
        manual = self.ordenacao == "manual"
        for c in self.cronometros:
            c.definir_mover_habilitado(manual)

    def _cronometros_visiveis(self) -> List[Cronometro]:
        """Aplica filtro de status, busca e ordenação (sem alterar a ordem manual salva)."""
        termo = normalizar_texto(self.var_busca.get())
        lista = [
            c for c in self.cronometros
            if (self.filtro_ativo == "TODOS" or c.status.upper() == self.filtro_ativo)
            and (not termo or termo in normalizar_texto(c.nome))
        ]
        if self.ordenacao == "nome":
            lista.sort(key=lambda c: normalizar_texto(c.nome))
        elif self.ordenacao == "horas":
            lista.sort(key=lambda c: c.total_atual(), reverse=True)
        elif self.ordenacao == "recente":
            ultimas = ultima_sessao_por_jogo_id(self.repo.sessoes)
            lista.sort(key=lambda c: ultimas.get(c.jogo.id, datetime.min), reverse=True)
        return lista

    @staticmethod
    def _calcular_colunas(largura: int) -> int:
        return int(max(1, min(largura // (CARD_LARGURA + CARD_PADDING_X), MAX_COLUNAS)))

    def _ao_redimensionar(self, event: tk.Event) -> None:
        """Só refaz a grade quando o nº de colunas muda (na maioria dos resizes nada é refeito).

        Roda de forma síncrona, dentro do evento, para o Tk não pintar o layout antigo esticado.
        """
        if event.width > 1 and self._calcular_colunas(event.width) != self._colunas_atuais:
            self.reorganizar_grid()

    def reorganizar_grid(self) -> None:
        """Posiciona os cards visíveis, mexendo apenas no que realmente mudou."""
        largura = self.canvas_home.winfo_width()
        if largura <= 1:
            return
        colunas = self._calcular_colunas(largura)
        visiveis = self._cronometros_visiveis()
        assinatura = (colunas, tuple(c.jogo.id for c in visiveis), bool(self.cronometros))
        if assinatura == self._assinatura_grid:
            return                                              # nada mudou: não toca em nenhum widget
        self._assinatura_grid = assinatura

        if colunas != self._colunas_atuais:
            for i in range(MAX_COLUNAS):
                self.inner_frame.grid_columnconfigure(i, weight=1 if i < colunas else 0)
            self._colunas_atuais = colunas

        ids_visiveis = {c.jogo.id for c in visiveis}
        for c in self.cronometros:
            if c.jogo.id not in ids_visiveis:
                c.frame.grid_forget()                          # só some quem saiu do filtro
        if visiveis:
            self.lbl_vazio.grid_forget()
        else:
            self.lbl_vazio.config(text=t("vazio.nenhum") if self.cronometros else t("vazio.biblioteca"))
            self.lbl_vazio.grid(row=0, column=0, columnspan=colunas, pady=40)
        for idx, cron in enumerate(visiveis):                  # grid() em quem já está na grade só o move
            cron.frame.grid(row=idx // colunas, column=idx % colunas, padx=8, pady=8, sticky="nsew")

    # ------------------------------------------------------------------
    # Biblioteca de jogos
    # ------------------------------------------------------------------
    def salvar_tudo(self) -> None:
        self.repo.salvar_jogos([c.jogo for c in self.cronometros])

    def recriar_cronometros_salvos(self) -> None:
        totais = self.repo.totais_por_jogo_id()
        for jogo in self.repo.jogos:
            self._criar_cronometro(jogo, totais)

    def _criar_cronometro(self, jogo: Jogo, totais: Optional[Dict[str, int]] = None,
                          no_topo: bool = False) -> Cronometro:
        totais = totais if totais is not None else self.repo.totais_por_jogo_id()
        card = Cronometro(self.inner_frame, jogo, app=self, total_historico=totais.get(jogo.id, 0))
        card.definir_mover_habilitado(self.ordenacao == "manual")
        if no_topo:
            self.cronometros.insert(0, card)
        else:
            self.cronometros.append(card)
        return card

    def adicionar_cronometro(self) -> None:
        try:
            jogo = self.repo.adicionar_jogo(self.entry_nome.get())
        except ValueError as e:
            messagebox.showwarning(t("dlg.aviso"), str(e))
            return
        self._criar_cronometro(jogo, no_topo=True)          # o repositório também o põe no topo
        self.entry_nome.delete(0, tk.END)
        self.var_busca.set("")                       # garante que o novo card apareça
        if self.filtro_ativo not in ("TODOS", "JOGANDO"):
            self.set_filtro("TODOS")
        self.recarregar_totais()                     # sessões órfãs readotadas, se houver
        self.reorganizar_grid()
        self.canvas_home.yview_moveto(0)             # rola até o topo para mostrar o novo card

    def remover_cronometro(self, card: Cronometro) -> None:
        if card in self.cronometros:
            self.cronometros.remove(card)
        self.salvar_tudo()
        self.reorganizar_grid()

    def renomear_jogo(self, card: Cronometro, novo_nome: str) -> None:
        """Renomeia o jogo e seu histórico. Levanta ValueError se o nome for inválido."""
        self.repo.renomear_jogo(card.jogo.id, novo_nome)
        card.atualizar_nome()
        self.reorganizar_grid()

    def mover_cronometro(self, card: Cronometro, direcao: str) -> None:
        if self.ordenacao != "manual" or card not in self.cronometros or len(self.cronometros) <= 1:
            return
        n = len(self.cronometros)
        idx = self.cronometros.index(card)
        novo = {"up": n - 1 if idx == 0 else idx - 1, "down": 0 if idx == n - 1 else idx + 1,
                "top": 0, "end": n - 1}.get(direcao)
        if novo is None:
            return
        self.cronometros.insert(novo, self.cronometros.pop(idx))
        self.salvar_tudo()
        self.reorganizar_grid()

    # ------------------------------------------------------------------
    # Sessões e totais
    # ------------------------------------------------------------------
    def registrar_sessao(self, card: Cronometro, segundos: int, inicio: datetime, fim: datetime, dias=None) -> None:
        self.repo.adicionar_sessao(card.jogo.id, card.nome, segundos, inicio, fim, dias)
        self.recarregar_totais()

    def recarregar_totais(self) -> None:
        """Recalcula o 'Total Geral' de todos os cards a partir do histórico salvo."""
        totais = self.repo.totais_por_jogo_id()
        for c in self.cronometros:
            c.definir_total_historico(totais.get(c.jogo.id, 0))
        if self.ordenacao in ("horas", "recente"):
            self.reorganizar_grid()

    def persistir_andamento(self) -> None:
        """Grava o estado das sessões abertas (recuperação após crash)."""
        estados = [e for c in self.cronometros if (e := c.estado()) is not None]
        self.repo.salvar_andamento(estados)
        self._ultimo_heartbeat = time.monotonic()

    def liberar_instancia(self) -> None:
        """Solta a trava de instância única (necessário antes de abrir uma nova instância ao reiniciar)."""
        if self.trava is not None:
            self.trava.liberar()

    def _trazer_para_frente(self) -> None:
        """Outra tentativa de abrir o app foi feita: mostra esta janela (mesmo se minimizada)."""
        try:
            self.root.deiconify()
            self.root.lift()
            self.root.attributes("-topmost", True)            # truque para o Windows realmente trazer à frente
            self.root.after(300, lambda: self.root.attributes("-topmost", False))
            self.root.focus_force()
        except tk.TclError:
            log.exception("Não foi possível trazer a janela para a frente")

    def _tarefas_periodicas(self) -> None:
        """Verificações baratas executadas dentro do loop principal."""
        self._ciclos += 1
        if self._ciclos % INTERVALO_SINAL_LOOPS == 0 and instancia.consumir_sinal(self.repo.data_dir):
            self._trazer_para_frente()
        agora = time.monotonic()
        if agora - self._ultima_checagem_backup >= INTERVALO_BACKUP_S:
            self._ultima_checagem_backup = agora
            self.repo.backup_diario()                       # se o app ficou aberto até virar o dia

    def _loop_atualizacao(self) -> None:
        try:
            self._tarefas_periodicas()
            self.sobreposicao.definir(icone_barra.estado_do_icone(self.cronometros))
            alguma_rodando = False
            for c in self.cronometros:
                if c.rodando:
                    alguma_rodando = True
                    c.atualizar_interface()
                elif c.pausado:
                    c.atualizar_pausa()                          # contador "Pausado há …"
            if alguma_rodando and time.monotonic() - self._ultimo_heartbeat >= INTERVALO_HEARTBEAT_S:
                self.persistir_andamento()
        except Exception:                                    # o loop nunca deve morrer
            if not self._erro_loop_registrado:
                log.exception("Erro no loop de atualização")
                self._erro_loop_registrado = True
        finally:
            self.root.after(INTERVALO_UPDATE_MS, self._loop_atualizacao)

    # ------------------------------------------------------------------
    # Inicialização, recuperação e encerramento
    # ------------------------------------------------------------------
    def _mostrar_avisos(self) -> None:
        for aviso in self.repo.pop_avisos():
            messagebox.showwarning(t("dlg.atencao"), aviso)

    def _verificar_recuperacao(self) -> None:
        """Oferece salvar sessões que ficaram abertas por um fechamento inesperado."""
        itens = [(e, e.segundos_recuperaveis()) for e in self.repo.carregar_andamento()]
        itens = [(e, seg) for e, seg in itens if seg > 0]
        if not itens:
            self.repo.limpar_andamento()
            return
        linhas = "\n".join(f"  • {e.jogo} — {formatar_hhmmss(seg)}" for e, seg in itens)
        if messagebox.askyesno(t("recuperar.titulo"), t("recuperar.msg", linhas=linhas)):
            for e, seg in itens:
                jogo = self.repo.jogo_por_id(e.jogo_id)
                try:
                    fim = datetime.fromtimestamp(e.ultimo_heartbeat or time.time())
                except (OverflowError, OSError, ValueError):
                    fim = datetime.now()
                try:
                    inicio = datetime.strptime(e.inicio, FORMATO_DATA) if e.inicio else None
                except ValueError:
                    inicio = None
                self.repo.adicionar_sessao(jogo.id if jogo else None, jogo.nome if jogo else e.jogo,
                                           seg, inicio, fim, e.dias_recuperaveis())
            self.recarregar_totais()
        self.repo.limpar_andamento()

    def resolver_sessoes_pendentes(self, chave_titulo: str = "sair.titulo", chave_msg: str = "sair.msg") -> bool:
        """Pergunta o que fazer com sessões abertas (salvar/descartar/cancelar).

        Devolve False se o usuário cancelou; True se não havia pendências ou foram resolvidas.
        """
        pendentes = [c for c in self.cronometros if c.tem_sessao_pendente()]
        if not pendentes:
            return True
        nomes = ", ".join(f"{c.nome} ({formatar_hhmmss(c.tempo_sessao())})" for c in pendentes[:5])
        if len(pendentes) > 5:
            nomes += t("sair.e_mais", n=len(pendentes) - 5)
        resp = messagebox.askyesnocancel(t(chave_titulo), t(chave_msg, nomes=nomes))
        if resp is None:
            return False
        for c in pendentes:
            c.parar() if resp else c.descartar()
        return True

    def ao_fechar(self) -> None:
        if not self.resolver_sessoes_pendentes():
            return
        self.repo.limpar_andamento()
        self.root.destroy()

    def _erro_inesperado(self, exc_type, exc, tb) -> None:
        log.error("Erro não tratado na interface", exc_info=(exc_type, exc, tb))
        try:
            messagebox.showerror(
                t("erro.inesperado.titulo"),
                t("erro.inesperado.msg", erro=exc, log=os.path.join(self.repo.data_dir, NOME_ARQ_LOG)))
        except tk.TclError:
            pass
