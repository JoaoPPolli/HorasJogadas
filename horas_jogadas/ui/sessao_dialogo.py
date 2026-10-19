"""Diálogo para editar uma sessão do histórico ou adicionar uma sessão manual."""
import tkinter as tk
from datetime import datetime, timedelta
from tkinter import messagebox, ttk
from typing import TYPE_CHECKING, Callable, Optional

from ..edicao_sessao import LIMITE_CONFIRMACAO_S, ErroSessao, validar
from ..i18n import t
from ..models import Sessao
from ..utils import formatar_hhmmss
from .theme import aplicar_tema_moderno

if TYPE_CHECKING:
    from .main_window import App


def abrir_dialogo_sessao(app: "App", parent: tk.Misc, sessao: Optional[Sessao],
                         ao_salvar: Callable[[], None]) -> None:
    """Edita `sessao`; se for None, cria uma sessão manual. `ao_salvar` redesenha a tela que chamou."""
    jogos = list(app.repo.jogos)
    nomes = [j.nome for j in jogos]
    orfao = bool(sessao and sessao.jogo and sessao.jogo not in nomes)       # jogo já removido da biblioteca
    if orfao:
        nomes.append(sessao.jogo)
    if not nomes:
        messagebox.showwarning(t("dlg.aviso"), t("sessao.erro_jogo"), parent=parent)
        return

    jan = tk.Toplevel(parent)
    jan.title(t("sessao.titulo_editar") if sessao else t("sessao.titulo_adicionar"))
    jan.geometry("440x330")
    aplicar_tema_moderno(jan)

    formato_local = t("fmt.data_hora")
    agora = datetime.now()
    fim_inicial = (sessao.data_dt if sessao and sessao.data_dt else agora).replace(second=0, microsecond=0)
    segundos_iniciais = sessao.segundos if sessao else 0

    quadro = ttk.Frame(jan)
    quadro.pack(fill="x", padx=20, pady=(16, 4))
    quadro.grid_columnconfigure(1, weight=1)

    ttk.Label(quadro, text=t("sessao.jogo")).grid(row=0, column=0, sticky="w", pady=6)
    combo = ttk.Combobox(quadro, state="readonly", values=nomes)
    combo.set(sessao.jogo if sessao and sessao.jogo else nomes[0])
    combo.grid(row=0, column=1, sticky="ew", padx=(10, 0))

    ttk.Label(quadro, text=t("sessao.termino", formato=t("sessao.formato"))).grid(row=1, column=0, sticky="w", pady=6)
    ent_termino = ttk.Entry(quadro)
    ent_termino.insert(0, fim_inicial.strftime(formato_local))
    ent_termino.grid(row=1, column=1, sticky="ew", padx=(10, 0))

    ttk.Label(quadro, text=t("sessao.duracao")).grid(row=2, column=0, sticky="w", pady=6)
    linha = ttk.Frame(quadro)
    linha.grid(row=2, column=1, sticky="w", padx=(10, 0))
    campos = []
    h, resto = divmod(segundos_iniciais, 3600)
    for valor, rotulo in ((h, t("tempo.horas")), (resto // 60, t("tempo.minutos")), (resto % 60, t("tempo.segundos"))):
        col = ttk.Frame(linha)
        col.pack(side="left", padx=(0, 8))
        ttk.Label(col, text=rotulo, style="Small.TLabel").pack()
        entrada = ttk.Entry(col, width=5, justify="center")
        entrada.insert(0, str(valor))
        entrada.pack()
        campos.append(entrada)

    ttk.Label(jan, text=t("sessao.dica"), style="Small.TLabel", wraplength=400, justify="left").pack(padx=20, pady=(10, 0), anchor="w")

    def salvar() -> None:
        try:
            fim, duracao = validar(ent_termino.get(), campos[0].get(), campos[1].get(), campos[2].get(),
                                   datetime.now(), formatos_locais=(formato_local,))
        except ErroSessao as e:
            messagebox.showerror(t("dlg.erro"), t(e.chave, formato=t("sessao.formato")), parent=jan)
            return
        if duracao > LIMITE_CONFIRMACAO_S and not messagebox.askyesno(
                t("dlg.confirmar"), t("sessao.confirma_longa", tempo=formatar_hhmmss(duracao)), parent=jan):
            return
        escolhido = combo.get()
        jogo = next((j for j in jogos if j.nome == escolhido), None)
        if jogo is not None:
            jogo_id, nome = jogo.id, jogo.nome
        else:                                                              # manteve o nome de um jogo removido
            jogo_id, nome = (sessao.jogo_id if sessao else None), escolhido
        if sessao is None:
            app.repo.adicionar_sessao(jogo_id, nome, duracao, fim - timedelta(seconds=duracao), fim)
        elif not app.repo.atualizar_sessao(sessao.sessao_id, jogo_id, nome, duracao, fim):
            messagebox.showerror(t("dlg.erro"), t("erro.jogo_nao_encontrado"), parent=jan)
            return
        app.recarregar_totais()
        jan.destroy()
        ao_salvar()

    botoes = ttk.Frame(jan)
    botoes.pack(pady=18)
    ttk.Button(botoes, text=t("btn.salvar"), style="Accent.TButton", command=salvar).pack(side="left", padx=6)
    ttk.Button(botoes, text=t("btn.cancelar"), command=jan.destroy).pack(side="left", padx=6)
