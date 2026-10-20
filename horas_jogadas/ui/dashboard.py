"""Dashboard pintado numa superfície única: títulos, gráficos, filtros e ações."""
from collections import Counter
from datetime import date
from tkinter import messagebox

from .. import stats
from ..constants import COR_ACCENT, COR_TEXTO_SUAVE, FILTROS_STATUS, STATUS_OPCOES
from ..i18n import lista, rotulo_filtro, t, t_status
from ..utils import ellipsizar, formatar_duracao, formatar_hhmmss, horas_curto
from .pagina_desenhada import PaginaDesenhada
from .sessao_dialogo import abrir_dialogo_sessao

PERIODOS = [stats.PERIODO_7_DIAS, stats.PERIODO_8_SEMANAS, stats.PERIODO_6_MESES]


def _qtd_sessoes(n):
    return t('dash.sessao_um') if n == 1 else t('dash.sessoes', n=n)


def _qtd_dias(n):
    return t('dash.dia', n=n) if n == 1 else t('dash.dias', n=n)


def abrir_dashboard(app):
    parent, janela = app.preparar_janela_ou_frame(t('tela.dashboard'))
    if janela:
        parent.geometry('660x780')
    area = PaginaDesenhada(parent, app.scroll)
    area.pack(fill='both', expand=True, padx=8, pady=8)
    estado = {'periodo': PERIODOS[0], 'filtro': 'TODOS'}
    dados = {}

    def preparar():
        sessoes = list(app.repo.sessoes)
        grupos = stats.agrupar_por_jogo([c.jogo for c in app.cronometros], sessoes)
        dados.update(sessoes=sessoes, grupos=grupos, resumo=stats.resumo_geral(grupos, sessoes),
                     sequencias=stats.sequencias(sessoes, date.today()), top=stats.top_jogos(grupos, 5), periodos={})

    def atualizar_dados():
        preparar()
        area.atualizar()

    def escolher(chave, valor):
        estado[chave] = valor
        area.atualizar()

    def excluir(grupo):
        if messagebox.askyesno(t('dlg.confirmar'), t('dash.excluir_registros', nome=grupo.nome), parent=parent):
            app.repo.remover_sessoes_do_grupo(grupo.chave)
            app.recarregar_totais()
            atualizar_dados()

    def pintar(p):
        resumo = dados['resumo']
        longa, mais = resumo.sessao_mais_longa, resumo.jogo_mais_jogado
        atual, maior = dados['sequencias']
        y = p.y
        fundo = p.fundo(6, y, p.largura - 6, y + 1)
        p.texto(18, y + 12, t('dash.resumo'), tamanho=11, negrito=True)
        detalhe = ''
        if longa:
            detalhe = f"{longa.jogo} · {longa.data_dt.strftime(t('fmt.data'))}" if longa.data_dt else longa.jogo
        valores = [
            (t('dash.total'), formatar_duracao(resumo.total_segundos), _qtd_sessoes(resumo.total_sessoes)),
            (t('dash.media'), formatar_duracao(resumo.media_sessao), ''),
            (t('dash.longa'), formatar_duracao(longa.segundos) if longa else '--', detalhe),
            (t('dash.mais_jogado'), mais.nome if mais else '--', formatar_duracao(mais.total) if mais else ''),
            (t('dash.seq_atual'), _qtd_dias(atual), ''),
            (t('dash.maior_seq'), _qtd_dias(maior), ''),
        ]
        colunas = 3 if p.largura >= 720 else 2
        largura = (p.largura - 48) / colunas
        ty = y + 44
        for inicio in range(0, len(valores), colunas):
            altura = 0
            for i, (titulo, valor, extra) in enumerate(valores[inicio:inicio + colunas]):
                x = 22 + i * largura
                h = p.texto(x, ty, titulo, largura - 18, tamanho=9, cor=COR_TEXTO_SUAVE) + 4
                h += p.texto(x, ty + h, valor, largura - 18, tamanho=13, negrito=True) + 4
                if extra:
                    h += p.texto(x, ty + h, extra, largura - 18, tamanho=8, cor=COR_TEXTO_SUAVE)
                altura = max(altura, h)
            ty += altura + 18
        if longa:
            p.botao(22, ty, t('dash.editar_longa'), lambda: abrir_dialogo_sessao(app, parent, longa, atualizar_dados))
            ty += 40
        contagem = Counter(c.status.upper() for c in app.cronometros)
        linha = '    '.join(f'{t_status(status).upper()}: {contagem.get(status.upper(), 0)}' for status in STATUS_OPCOES)
        ty += p.texto(22, ty, linha, p.largura - 44, tamanho=8, cor=COR_TEXTO_SUAVE) + 14
        p.canvas.coords(fundo, 6, y, p.largura - 6, ty)
        p.y = ty + 12

        y = p.y
        fundo = p.fundo(6, y, p.largura - 6, y + 260)
        p.texto(18, y + 12, t('dash.horas'), tamanho=11, negrito=True)
        x = p.largura - sum(max(64, p.medir(t(f'periodo.{k}')) + 20) + 6 for k in PERIODOS) - 18
        by = y + 10
        if x < 220:
            x, by = 18, y + 42
        for chave in PERIODOS:
            x += p.botao(x, by, t(f'periodo.{chave}'), lambda k=chave: escolher('periodo', k), estado['periodo'] == chave) + 6
        topo, base = by + 62, by + 188
        periodo = estado['periodo']
        if periodo not in dados['periodos']:
            dados['periodos'][periodo] = stats.horas_por_periodo(dados['sessoes'], periodo, date.today(),
                dias_semana=lista('dias_semana'), meses_nomes=lista('meses'), formato_semana=t('fmt.semana'))
        barras = dados['periodos'][periodo]
        maximo = max((seg for _, seg in barras), default=0)
        if maximo:
            slot = (p.largura - 48) / len(barras)
            for i, (rotulo, seg) in enumerate(barras):
                cx = 24 + slot * (i + .5)
                if seg:
                    altura = (base - topo) * seg / maximo
                    bw = min(slot * .6, 56)
                    p.fundo(cx - bw / 2, base - altura, cx + bw / 2, base, COR_ACCENT)
                    p.texto(cx - 25, base - altura - 20, horas_curto(seg, t('fmt.decimal')), 50, tamanho=8)
                p.texto(cx - 28, base + 8, rotulo, 56, tamanho=8, cor=COR_TEXTO_SUAVE)
        else:
            p.texto(24, topo + 30, t('dash.sem_periodo'), p.largura - 48, cor=COR_TEXTO_SUAVE)
        p.canvas.coords(fundo, 6, y, p.largura - 6, base + 38)
        p.y = base + 50

        y = p.y
        top = dados['top']
        fundo = p.fundo(6, y, p.largura - 6, y + 1)
        p.texto(18, y + 12, t('dash.top5'), tamanho=11, negrito=True)
        ty = y + 44
        if top:
            nomes = min(max(max(p.medir(g.nome) for g in top) + 24, 120), p.largura * .4)
            x_barra, x_fim = 18 + nomes, p.largura - 100
            for g in top:
                nome = ellipsizar(g.nome, p.fonte(9).measure, nomes - 14)
                p.texto(18, ty, nome, nomes - 10, tamanho=9)
                comprimento = max(2, (x_fim - x_barra) * g.total / max(1, top[0].total))
                p.fundo(x_barra, ty + 2, x_barra + comprimento, ty + 16, COR_ACCENT)
                p.texto(x_barra + comprimento + 6, ty, formatar_duracao(g.total), 88, tamanho=8, cor=COR_TEXTO_SUAVE)
                ty += 28
        else:
            ty += p.texto(18, ty, t('dash.sem_sessoes'), cor=COR_TEXTO_SUAVE)
        p.canvas.coords(fundo, 6, y, p.largura - 6, ty + 12)
        p.y = ty + 24
        p.titulo(t('dash.jogos'))
        x, by = 12, p.y
        for filtro in FILTROS_STATUS:
            w = max(64, p.medir(rotulo_filtro(filtro)) + 20)
            if x + w > p.largura - 12:
                x, by = 12, by + 36
            x += p.botao(x, by, rotulo_filtro(filtro), lambda f=filtro: escolher('filtro', f), estado['filtro'] == filtro) + 6
        p.y = by + 42
        for g in dados['grupos']:
            if estado['filtro'] != 'TODOS' and (g.status or 'DESCONHECIDO').upper() != estado['filtro']:
                continue
            primeira = g.primeira.strftime(t('fmt.data')) if g.primeira else '--'
            ultima = g.ultima.strftime(t('fmt.data_hora')) if g.ultima else '--'
            p.cartao(g.nome, [t('dash.linha_total', tempo=formatar_hhmmss(g.total), sessoes=_qtd_sessoes(g.sessoes)),
                             t('dash.primeira', data=primeira), t('dash.ultima', data=ultima)],
                     [(t('btn.excluir'), lambda grupo=g: excluir(grupo))] if g.sessoes else [],
                     rotulo_filtro((g.status or 'DESCONHECIDO').upper()))

    preparar()
    area.mostrar(pintar)
    return area
