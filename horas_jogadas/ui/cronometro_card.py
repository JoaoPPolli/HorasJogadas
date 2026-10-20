"""Card de cronômetro de um jogo."""
import logging
import time
import tkinter as tk
from datetime import date, datetime, timedelta
from tkinter import messagebox, simpledialog, ttk
from typing import TYPE_CHECKING, Dict, Optional

from ..constants import (
    FORMATO_DATA, PAUSA_ATALHOS_MIN, PAUSA_PADRAO_PARCIAL_MIN, STATUS_OPCOES, STATUS_PADRAO,
)
from ..i18n import t, t_status
from ..models import EstadoSessao, Jogo
from ..utils import formatar_hhmmss, inteiros_somando, repartir_por_dia
from .theme import aplicar_tema_moderno

if TYPE_CHECKING:  # evita import circular
    from .main_window import App

log = logging.getLogger(__name__)


class Cronometro:
    """Card com cronômetro, status e total acumulado de um jogo.

    A duração é medida com `time.monotonic()` (imune a ajustes do relógio); o horário
    real (`time.time()`) só é guardado para a recuperação de sessões após falhas.
    """

    def __init__(self, parent: tk.Misc, jogo: Jogo, app: "App", total_historico: int = 0):
        self.parent = parent
        self.jogo = jogo
        self.app = app
        self.total_historico_base = total_historico

        self.rodando = False
        self.tempo_acumulado = 0.0                   # segundos acumulados (sem o trecho rodando)
        self._inicio_mono = 0.0
        self._retomado_em = 0.0                      # epoch do último "iniciar"
        self._inicio_sessao: Optional[datetime] = None
        self._pausado_em: Optional[float] = None     # epoch do último "pausar" (relógio real)
        self._dias_sessao: Dict[date, float] = {}    # segundos jogados em cada dia do calendário (nesta sessão)
        self._last_pausa_render = ""
        self._last_text_render = "00:00:00"
        self._last_total_render = ""

        self._construir_widgets()
        self.atualizar_label_total_geral()

    # -- propriedades --------------------------------------------------------
    @property
    def nome(self) -> str:
        return self.jogo.nome

    @property
    def status(self) -> str:
        return self.jogo.status

    # -- construção da interface --------------------------------------------
    def _construir_widgets(self) -> None:
        self.frame = ttk.Frame(self.parent, style="Card.TFrame", padding=(10, 8))

        top_row = ttk.Frame(self.frame, style="Card.TFrame")
        top_row.grid(row=0, column=0, columnspan=2, sticky="ew", pady=(0, 5))
        top_row.grid_columnconfigure(1, weight=1)

        self.lbl_status = tk.Label(top_row, text=t_status(self.status).upper(), font=("Segoe UI", 7, "bold"),
                                   padx=6, pady=2, bd=0, cursor="hand2")
        self.lbl_status.pack(side="left")
        self.atualizar_visual_status()

        ttk.Button(top_row, text="❌", width=3, style="Danger.TButton",
                   command=self.excluir_cronometro).pack(side="right")

        self.lbl_nome = ttk.Label(self.frame, text=self.nome, style="CardTitle.TLabel")
        self.lbl_nome.grid(row=1, column=0, columnspan=2, sticky="w")

        self.lbl_tempo = ttk.Label(self.frame, text="00:00:00", font=("Consolas", 14), style="Card.TLabel")
        self.lbl_tempo.grid(row=2, column=0, sticky="w", pady=(2, 0))

        self.lbl_pausa = ttk.Label(self.frame, text="", style="CardPausaSmall.TLabel")
        self.lbl_pausa.grid(row=2, column=1, sticky="e", pady=(2, 0))
        self.lbl_pausa.grid_remove()                             # só aparece enquanto pausado

        self.lbl_total_geral = ttk.Label(self.frame, text="", style="CardSmall.TLabel")
        self.lbl_total_geral.grid(row=3, column=0, sticky="w", pady=(0, 8))

        self.lbl_tempo.bind("<Double-Button-1>", lambda e: self.abrir_dialogo_tempo())
        self.lbl_tempo.bind("<Enter>", lambda e: self.lbl_tempo.configure(cursor="hand2"))
        self.lbl_tempo.bind("<Leave>", lambda e: self.lbl_tempo.configure(cursor=""))

        btns = ttk.Frame(self.frame, style="Card.TFrame")
        btns.grid(row=4, column=0, columnspan=2, sticky="ew")
        self.btn_iniciar = ttk.Button(btns, text=t("card.iniciar"), command=self.iniciar, width=8, style="Accent.TButton")
        self.btn_iniciar.pack(side="left", fill="x", expand=True, padx=2)
        self.btn_pausar = ttk.Button(btns, text=t("card.pausar"), command=self._acao_pausa, width=8, state="disabled")
        self.btn_pausar.pack(side="left", fill="x", expand=True, padx=2)
        self.btn_parar = ttk.Button(btns, text=t("card.parar"), command=self.parar, width=8, state="disabled",
                                    style="Danger.TButton")
        self.btn_parar.pack(side="left", fill="x", expand=True, padx=2)
        self.frame.grid_columnconfigure(0, weight=1)

        self.menu_status = tk.Menu(self.frame, tearoff=0)
        self.menu = tk.Menu(self.frame, tearoff=0)
        self._mover_habilitado = True
        self._construir_menus()
        self.lbl_status.bind("<Button-1>", lambda e: self.menu_status.tk_popup(e.x_root, e.y_root))

        for w in (self.frame, self.lbl_nome, self.lbl_tempo):
            w.bind("<Button-3>", self._on_right_click)

    def _construir_menus(self) -> None:
        """(Re)monta os menus de contexto no idioma atual."""
        self.menu_status.delete(0, "end")
        for s in STATUS_OPCOES:                               # valor salvo = chave canônica
            self.menu_status.add_command(label=t_status(s), command=lambda opt=s: self.mudar_status(opt))
        self.menu.delete(0, "end")
        self.menu.add_command(label=t("menu.tempo"), command=self.abrir_dialogo_tempo)
        self.menu.add_command(label=t("menu.renomear"), command=self.renomear)
        self.menu.add_command(label=t("menu.contar_pausa"), command=self.abrir_dialogo_pausa)
        self.menu.add_separator()
        self.menu.add_cascade(label=t("menu.status"), menu=self.menu_status)
        self.menu.add_separator()
        self.menu.add_command(label=t("menu.topo"), command=lambda: self.app.mover_cronometro(self, "top"))
        self.menu.add_command(label=t("menu.fim"), command=lambda: self.app.mover_cronometro(self, "end"))
        self.definir_mover_habilitado(self._mover_habilitado)
        self._atualizar_item_pausa()

    def _atualizar_item_pausa(self) -> None:
        """'Retomar contando a pausa…' só faz sentido enquanto o cronômetro está pausado."""
        self.menu.entryconfig(t("menu.contar_pausa"), state="normal" if self.pausado else "disabled")

    def aplicar_idioma(self) -> None:
        """Atualiza todos os textos do card para o idioma atual, sem recriá-lo (o cronômetro segue)."""
        self.btn_iniciar.config(text=t("card.iniciar"))
        self.btn_pausar.config(text=t("card.pausar"))
        self.btn_parar.config(text=t("card.parar"))
        self.atualizar_visual_status()
        self._construir_menus()
        self._atualizar_botoes()                          # texto do botão do meio depende do estado
        self._last_total_render = ""
        self._last_pausa_render = ""
        self.atualizar_pausa()
        self.atualizar_label_total_geral()

    def _on_right_click(self, event: tk.Event) -> None:
        try:
            self.menu.tk_popup(event.x_root, event.y_root)
        finally:
            self.menu.grab_release()

    def definir_mover_habilitado(self, habilitado: bool) -> None:
        """Habilita/desabilita 'Mover para topo/fim' (só fazem sentido na ordem manual)."""
        self._mover_habilitado = habilitado
        estado = "normal" if habilitado else "disabled"
        for rotulo in (t("menu.topo"), t("menu.fim")):
            self.menu.entryconfig(rotulo, state=estado)

    # -- status / nome / totais ---------------------------------------------
    def atualizar_visual_status(self) -> None:
        cores = STATUS_OPCOES.get(self.status, STATUS_OPCOES[STATUS_PADRAO])
        self.lbl_status.config(bg=cores["cor_bg"], fg=cores["cor_fg"], text=t_status(self.status).upper())

    def mudar_status(self, novo_status: str) -> None:
        anterior = self.jogo.status
        self.jogo.status = novo_status
        self.atualizar_visual_status()
        self.app.salvar_tudo()
        self.app.reorganizar_grid()
        if novo_status == 'Zerado' and anterior != 'Zerado':
            self.app.registrar_conclusao(self)

    def atualizar_nome(self) -> None:
        self.lbl_nome.config(text=self.nome)

    def renomear(self) -> None:
        novo = simpledialog.askstring(t("renomear.titulo"), t("renomear.msg"), initialvalue=self.nome,
                                      parent=self.frame)
        if novo is None or novo.strip() == self.nome:
            return
        try:
            self.app.renomear_jogo(self, novo)
        except ValueError as e:
            messagebox.showwarning(t("dlg.aviso"), str(e), parent=self.frame)

    def definir_total_historico(self, segundos: int) -> None:
        self.total_historico_base = segundos
        self._last_total_render = ""
        self.atualizar_label_total_geral()

    def tempo_sessao(self) -> float:
        extra = (time.monotonic() - self._inicio_mono) if self.rodando else 0.0
        return max(0.0, self.tempo_acumulado + extra)

    def total_atual(self) -> float:
        """Histórico salvo + sessão em andamento."""
        return self.total_historico_base + self.tempo_sessao()

    def atualizar_label_total_geral(self) -> None:
        txt = t("card.total", tempo=formatar_hhmmss(self.total_atual(), simplificado=True))
        if txt != self._last_total_render:
            self.lbl_total_geral.config(text=txt)
            self._last_total_render = txt

    def atualizar_interface(self, forcar: bool = False) -> None:
        if self.rodando or forcar:
            novo_texto = formatar_hhmmss(self.tempo_sessao())
            if novo_texto != self._last_text_render:
                self.lbl_tempo.config(text=novo_texto)
                self._last_text_render = novo_texto
            self.atualizar_label_total_geral()

    # -- diálogo de ajuste de tempo -----------------------------------------
    def abrir_dialogo_tempo(self) -> None:
        jan = tk.Toplevel(self.frame)
        jan.title(t("tempo.titulo"))
        jan.geometry("340x310")
        aplicar_tema_moderno(jan)
        jan.geometry(f"+{self.frame.winfo_rootx() + 50}+{self.frame.winfo_rooty() + 50}")

        ttk.Label(jan, text=t("tempo.adicionar", nome=self.nome), font=("Segoe UI", 10, "bold")).pack(pady=(10, 4))

        frame_inputs = ttk.Frame(jan)
        frame_inputs.pack(pady=5)

        def criar_input(rotulo: str) -> ttk.Entry:
            f = ttk.Frame(frame_inputs)
            f.pack(side="left", padx=5)
            ttk.Label(f, text=rotulo, style="Small.TLabel").pack()
            entry = ttk.Entry(f, width=5, justify="center")
            entry.insert(0, "0")
            entry.pack()
            return entry

        ent_h, ent_m, ent_s = (criar_input(t("tempo.horas")), criar_input(t("tempo.minutos")),
                               criar_input(t("tempo.segundos")))

        def ler_campos() -> int:
            return int(ent_h.get()) * 3600 + int(ent_m.get()) * 60 + int(ent_s.get())

        def definir_campos(total: int) -> None:
            """Distribui `total` segundos nos campos (se negativo, todos os campos ficam <= 0)."""
            sinal = -1 if total < 0 else 1
            horas, resto = divmod(abs(total), 3600)
            for entry, valor in ((ent_h, horas), (ent_m, resto // 60), (ent_s, resto % 60)):
                entry.delete(0, tk.END)
                entry.insert(0, str(sinal * valor))

        def somar_minutos(minutos: int) -> None:
            try:
                definir_campos(ler_campos() + minutos * 60)
            except ValueError:
                messagebox.showerror(t("dlg.erro"), t("tempo.invalido"), parent=jan)

        # Atalhos "+N min": somam ao que já está nos campos
        atalhos = ttk.Frame(jan)
        atalhos.pack(pady=(6, 2))
        for n in PAUSA_ATALHOS_MIN:
            ttk.Button(atalhos, text=t("tempo.atalho", n=n), width=7,
                       command=lambda minutos=n: somar_minutos(minutos)).pack(side="left", padx=2)

        # Se está pausado: mostra há quanto tempo e permite usar esse valor
        if self.pausado:
            linha_pausa = ttk.Frame(jan)
            linha_pausa.pack(pady=(8, 0))
            lbl_pausa = ttk.Label(linha_pausa, style="Small.TLabel",
                                  text=t("card.pausado_ha", tempo=formatar_hhmmss(self.duracao_pausa())))
            lbl_pausa.pack(side="left", padx=(0, 8))
            ttk.Button(linha_pausa, text=t("tempo.usar"),
                       command=lambda: definir_campos(int(self.duracao_pausa()))).pack(side="left")

            def atualizar_info() -> None:
                if jan.winfo_exists() and self.pausado:
                    lbl_pausa.config(text=t("card.pausado_ha", tempo=formatar_hhmmss(self.duracao_pausa())))
                    jan.after(1000, atualizar_info)
            jan.after(1000, atualizar_info)

        ttk.Label(jan, text=t("tempo.negativo"), style="Small.TLabel").pack(pady=(10, 5))

        def confirmar() -> None:
            try:
                adicionar = ler_campos()
            except ValueError:
                messagebox.showerror(t("dlg.erro"), t("tempo.invalido"), parent=jan)
                return
            antes = self.tempo_acumulado
            self.tempo_acumulado = max(0.0, self.tempo_acumulado + adicionar)
            self._ajustar_dias(self.tempo_acumulado - antes)             # só o que realmente mudou (nunca abaixo de zero)
            if self.tempo_acumulado > 0 and self._inicio_sessao is None:
                self._inicio_sessao = self._agora()
            elif not self.tem_sessao_pendente():
                self._inicio_sessao = None
            self.atualizar_interface(forcar=True)
            self._atualizar_botoes()
            self.app.persistir_andamento()
            jan.destroy()

        ttk.Button(jan, text=t("btn.confirmar"), style="Accent.TButton", command=confirmar).pack(pady=8)

    # -- pausa: contador, botão "Contar pausa" e diálogo ----------------------
    @property
    def pausado(self) -> bool:
        """Pausado de verdade: o usuário pausou (não está rodando) e a sessão continua aberta."""
        return (not self.rodando) and self._pausado_em is not None

    def duracao_pausa(self) -> float:
        """Segundos desde que o cronômetro foi pausado (relógio real, inclui suspensão do PC)."""
        return max(0.0, time.time() - self._pausado_em) if self.pausado else 0.0

    def atualizar_pausa(self) -> None:
        """Atualiza o contador 'Pausado há …' (chamado pelo loop do app, ~5x por segundo)."""
        if not self.pausado:
            return
        texto = t("card.pausado_ha", tempo=formatar_hhmmss(self.duracao_pausa()))
        if texto != self._last_pausa_render:
            self.lbl_pausa.config(text=texto)
            self._last_pausa_render = texto

    def _atualizar_visual_pausa(self) -> None:
        if self.pausado:
            self.lbl_pausa.grid()
            self.lbl_tempo.config(style="CardPausa.TLabel")      # tempo em amarelo enquanto pausado
            self._last_pausa_render = ""
            self.atualizar_pausa()
        else:
            self.lbl_pausa.grid_remove()
            self.lbl_tempo.config(style="Card.TLabel")

    def _acao_pausa(self) -> None:
        """Botão do meio: 'Pausar' enquanto roda; 'Contar pausa' enquanto está pausado."""
        if self.pausado:
            self.abrir_dialogo_pausa()
        else:
            self.pausar()

    def abrir_dialogo_pausa(self) -> None:
        """Retoma o cronômetro contando (tudo ou só uma parte) o tempo em que ficou pausado."""
        if not self.pausado:
            return
        jan = tk.Toplevel(self.frame)
        jan.title(t("pausa.titulo"))
        jan.geometry("380x250")
        aplicar_tema_moderno(jan)
        jan.geometry(f"+{self.frame.winfo_rootx() + 50}+{self.frame.winfo_rooty() + 50}")

        def texto_tempo() -> str:
            return formatar_hhmmss(self.duracao_pausa())

        lbl_info = ttk.Label(jan, text=t("pausa.info", tempo=texto_tempo()), font=("Segoe UI", 11, "bold"))
        lbl_info.pack(pady=(14, 10))

        var_modo = tk.StringVar(value="tudo")
        rb_tudo = ttk.Radiobutton(jan, text=t("pausa.tudo", tempo=texto_tempo()), variable=var_modo, value="tudo")
        rb_tudo.pack(anchor="w", padx=24, pady=3)

        linha_parte = ttk.Frame(jan)
        linha_parte.pack(anchor="w", padx=24, pady=3)
        ttk.Radiobutton(linha_parte, text=t("pausa.parte_antes"), variable=var_modo, value="parte").pack(side="left")
        ent_min = ttk.Entry(linha_parte, width=5, justify="center")
        ent_min.insert(0, str(min(PAUSA_PADRAO_PARCIAL_MIN, max(1, int(self.duracao_pausa() // 60)))))
        ent_min.pack(side="left", padx=6)
        ent_min.bind("<FocusIn>", lambda e: var_modo.set("parte"))
        ttk.Label(linha_parte, text=t("pausa.parte_depois")).pack(side="left")

        def atualizar() -> None:
            if jan.winfo_exists() and self.pausado:
                lbl_info.config(text=t("pausa.info", tempo=texto_tempo()))
                rb_tudo.config(text=t("pausa.tudo", tempo=texto_tempo()))
                jan.after(1000, atualizar)
        jan.after(1000, atualizar)

        def confirmar() -> None:
            if not self.pausado:                                  # retomado por outro caminho enquanto aberto
                jan.destroy()
                return
            total_pausa = int(self.duracao_pausa())
            if var_modo.get() == "tudo":
                contar = total_pausa
            else:
                try:
                    minutos = int(ent_min.get())
                    if minutos < 1:
                        raise ValueError
                except ValueError:
                    messagebox.showerror(t("dlg.erro"), t("pausa.invalido"), parent=jan)
                    return
                contar = min(total_pausa, minutos * 60)          # nunca conta mais do que a pausa real
            self.tempo_acumulado += contar
            fim_pausa = self._agora()
            self._somar_dias(fim_pausa - timedelta(seconds=contar), fim_pausa, contar)
            self.iniciar()
            self.atualizar_interface(forcar=True)
            jan.destroy()

        botoes = ttk.Frame(jan)
        botoes.pack(pady=18)
        ttk.Button(botoes, text=t("pausa.retomar"), style="Accent.TButton", command=confirmar).pack(side="left", padx=6)
        ttk.Button(botoes, text=t("btn.cancelar"), command=jan.destroy).pack(side="left", padx=6)

    # -- tempo por dia (sessões que atravessam a meia-noite) -----------------
    @staticmethod
    def _agora() -> datetime:
        return datetime.fromtimestamp(time.time())

    def _somar_dias(self, inicio: datetime, fim: datetime, segundos: float) -> None:
        """Atribui `segundos` aos dias do calendário tocados por [inicio, fim] (proporcional ao relógio)."""
        for dia, seg in repartir_por_dia(inicio, fim, segundos).items():
            self._dias_sessao[dia] = self._dias_sessao.get(dia, 0.0) + seg

    def _fechar_trecho_rodando(self) -> None:
        """Encerra o trecho em andamento: soma ao acumulado e ao(s) dia(s) em que foi jogado."""
        duracao = time.monotonic() - self._inicio_mono
        self.tempo_acumulado += duracao
        self._somar_dias(datetime.fromtimestamp(self._retomado_em), self._agora(), duracao)

    def _ajustar_dias(self, delta: float) -> None:
        """Ajuste manual de tempo: soma entra em HOJE; subtração sai dos dias mais recentes primeiro."""
        if delta > 0:
            hoje = self._agora().date()
            self._dias_sessao[hoje] = self._dias_sessao.get(hoje, 0.0) + delta
            return
        restante = -delta
        for dia in sorted(self._dias_sessao, reverse=True):
            tira = min(restante, self._dias_sessao[dia])
            self._dias_sessao[dia] -= tira
            restante -= tira
            if restante <= 0:
                break
        self._dias_sessao = {d: v for d, v in self._dias_sessao.items() if v > 0}

    # -- controle do cronômetro ---------------------------------------------
    def tem_sessao_pendente(self) -> bool:
        return self.rodando or self.tempo_acumulado > 0

    def _atualizar_botoes(self) -> None:
        self.btn_iniciar.config(state="disabled" if self.rodando else "normal")
        if self.pausado:                                       # o botão do meio vira "Contar pausa"
            self.btn_pausar.config(text=t("card.contar_pausa"), state="normal")
        else:
            self.btn_pausar.config(text=t("card.pausar"), state="normal" if self.rodando else "disabled")
        self.btn_parar.config(state="normal" if self.tem_sessao_pendente() else "disabled")
        self._atualizar_visual_pausa()
        self._atualizar_item_pausa()

    def iniciar(self) -> None:
        if self.rodando:
            return
        self._inicio_mono = time.monotonic()
        self._retomado_em = time.time()
        self._pausado_em = None
        self.rodando = True
        if self._inicio_sessao is None:
            self._inicio_sessao = self._agora()
        self._atualizar_botoes()
        self.app.persistir_andamento()

    def pausar(self) -> None:
        if not self.rodando:
            return
        self._fechar_trecho_rodando()
        self.rodando = False
        self._pausado_em = time.time()
        self._atualizar_botoes()
        self.atualizar_interface(forcar=True)
        self.app.persistir_andamento()

    def parar(self) -> bool:
        """Encerra a sessão e a grava no histórico. Retorna True se algo foi gravado."""
        if self.rodando:
            self._fechar_trecho_rodando()
            self.rodando = False
        total = int(round(self.tempo_acumulado))
        fim = self._agora()
        inicio = self._inicio_sessao or (fim - timedelta(seconds=total))
        dias = inteiros_somando(self._dias_sessao, total)                # soma exatamente `total`
        self._resetar_sessao()
        if total > 0:
            self.app.registrar_sessao(self, total, inicio, fim, dias or None)
        self.app.persistir_andamento()
        return total > 0

    def descartar(self) -> None:
        """Descarta a sessão atual sem gravar."""
        self._resetar_sessao()
        self.app.persistir_andamento()

    def _resetar_sessao(self) -> None:
        self.rodando = False
        self.tempo_acumulado = 0.0
        self._inicio_sessao = None
        self._pausado_em = None
        self._dias_sessao = {}
        self._last_text_render = "00:00:00"
        self.lbl_tempo.config(text="00:00:00")
        self.atualizar_label_total_geral()
        self._atualizar_botoes()

    def estado(self) -> Optional[EstadoSessao]:
        """Estado serializável da sessão aberta (None se não há sessão pendente)."""
        if not self.tem_sessao_pendente():
            return None
        return EstadoSessao(
            jogo_id=self.jogo.id, jogo=self.nome, acumulado=self.tempo_acumulado,
            rodando=self.rodando, retomado_em=self._retomado_em, ultimo_heartbeat=time.time(),
            inicio=self._inicio_sessao.strftime(FORMATO_DATA) if self._inicio_sessao else None,
            dias={d.isoformat(): v for d, v in self._dias_sessao.items()} or None,
        )

    def excluir_cronometro(self) -> None:
        if not messagebox.askyesno(t("dlg.excluir"), t("excluir.confirma", nome=self.nome)):
            return
        if self.tem_sessao_pendente():
            resp = messagebox.askyesnocancel(
                t("pendente.titulo"),
                t("pendente.msg", nome=self.nome, tempo=formatar_hhmmss(self.tempo_sessao())))
            if resp is None:
                return
            self.parar() if resp else self.descartar()
        self.frame.destroy()
        self.app.remover_cronometro(self)
