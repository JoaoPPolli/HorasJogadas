"""Lista anual independente, edição e prévia de importação de blocos de notas."""
import os
import re
import tkinter as tk
from dataclasses import replace
from datetime import date
from tkinter import filedialog, messagebox, simpledialog, ttk

from ..constants import COR_BG, COR_CARD, COR_TEXTO
from ..i18n import idioma_atual, t
from ..models import novo_id
from ..zerados import (Conclusao, MESES, MESES_EN, TIPOS, ano_do_texto, duracao_texto,
                       exportar_txt, interpretar_txt, ler_duracao, ler_txt)
from .theme import aplicar_tema_moderno
from .widgets import ScrollableFrame


def meses():
    return MESES_EN if idioma_atual() == 'en' else MESES


def mostrar_erro(parent, erro):
    messagebox.showerror(t('zer.titulo'), t('zer.falha', erro=erro), parent=parent)


def editar_registro(parent, registro, ao_salvar, ano=None):
    """O callback recebe apenas uma conclusão: não há acesso ao repositório de sessões."""
    hoje = date.today()
    base = registro or Conclusao('', ano or hoje.year, hoje.month)
    jan = tk.Toplevel(parent)
    jan.title(t('zer.editar') if registro else t('zer.novo'))
    jan.geometry('600x640')
    jan.minsize(520, 600)
    aplicar_tema_moderno(jan)
    jan.transient(parent.winfo_toplevel())
    quadro = ttk.Frame(jan, padding=18)
    quadro.pack(fill='both', expand=True)
    quadro.columnconfigure(0, weight=1)
    ttk.Label(quadro, text=t('zer.independente'), wraplength=540, style='Small.TLabel').grid(sticky='ew', pady=(0, 12))

    def campo(chave, valor):
        ttk.Label(quadro, text=t(chave)).grid(sticky='w', pady=(8, 3))
        entrada = ttk.Entry(quadro)
        entrada.insert(0, str(valor))
        entrada.grid(sticky='ew')
        return entrada

    nome = campo('zer.nome', base.nome)
    datas = ttk.Frame(quadro)
    datas.grid(sticky='ew', pady=10)
    for coluna in range(3):
        datas.columnconfigure(coluna, weight=1)
    ttk.Label(datas, text=t('zer.ano')).grid(row=0, column=0, sticky='w')
    ttk.Label(datas, text=t('zer.mes')).grid(row=0, column=1, sticky='w')
    ttk.Label(datas, text=t('zer.dia')).grid(row=0, column=2, sticky='w')
    ent_ano = ttk.Entry(datas, width=8)
    ent_ano.insert(0, str(base.ano))
    ent_ano.grid(row=1, column=0, sticky='ew', padx=(0, 8))
    mes = ttk.Combobox(datas, state='readonly', values=meses(), width=14)
    mes.current(base.mes - 1)
    mes.grid(row=1, column=1, sticky='ew', padx=(0, 8))
    dia = ttk.Entry(datas, width=8)
    dia.insert(0, str(base.dia) if base.dia is not None else '')
    dia.grid(row=1, column=2, sticky='ew')
    tempo = campo('zer.tempo', duracao_texto(base.segundos))
    extra = campo('zer.platina', duracao_texto(base.platina_segundos))
    ttk.Label(quadro, text=t('zer.dica_tempo'), style='Small.TLabel', wraplength=540).grid(sticky='ew', pady=6)
    ttk.Label(quadro, text=t('zer.tipo')).grid(sticky='w', pady=(6, 3))
    tipo = ttk.Combobox(quadro, state='readonly', values=[t('zer.tipo.' + x) for x in TIPOS])
    tipo.current(TIPOS.index(base.tipo))
    tipo.grid(sticky='ew')
    ttk.Label(quadro, text=t('zer.notas')).grid(sticky='w', pady=(10, 3))
    notas = tk.Text(quadro, height=4, wrap='word', bg=COR_CARD, fg=COR_TEXTO,
                    insertbackground=COR_TEXTO, font=('Segoe UI', 10), relief='flat')
    notas.insert('1.0', base.notas)
    notas.grid(sticky='nsew')
    quadro.rowconfigure(notas.grid_info()['row'], weight=1)

    def salvar():
        try:
            try:
                valor_ano, valor_dia = int(ent_ano.get()), int(dia.get()) if dia.get().strip() else None
            except ValueError:
                raise ValueError(t('zer.erro_data')) from None
            novo = replace(base, nome=nome.get().strip(), ano=valor_ano, mes=mes.current() + 1,
                           dia=valor_dia, segundos=ler_duracao(tempo.get()),
                           platina_segundos=ler_duracao(extra.get()), notas=notas.get('1.0', 'end-1c').strip(),
                           tipo=TIPOS[tipo.current()]).validar()
            ao_salvar(novo)
        except (ValueError, OSError) as erro:
            mostrar_erro(jan, erro)
            return
        jan.destroy()

    botoes = ttk.Frame(quadro)
    botoes.grid(sticky='e', pady=(16, 0))
    ttk.Button(botoes, text=t('btn.cancelar'), command=jan.destroy).pack(side='left', padx=6)
    ttk.Button(botoes, text=t('btn.salvar'), style='Accent.TButton', command=salvar).pack(side='left')
    nome.focus_set()
    return jan


def abrir_zerados(app):
    repo = app.obter_zerados()
    if repo is None:
        return
    parent, janela = app.preparar_janela_ou_frame(t('zer.titulo'))
    if janela:
        parent.geometry('820x650')
        parent.minsize(650, 460)
    topo = ttk.Frame(parent, padding=(12, 10))
    topo.pack(fill='x')
    ttk.Label(topo, text=t('zer.ano')).pack(side='left', padx=(0, 6))
    ano = ttk.Combobox(topo, width=7, state='readonly')
    ano.set(str(date.today().year))
    ano.pack(side='left')
    ttk.Label(parent, text=t('zer.independente'), style='Small.TLabel', wraplength=680).pack(anchor='w', padx=12)
    resumo = ttk.Label(parent, style='Small.TLabel')
    resumo.pack(anchor='w', padx=12, pady=(8, 0))
    area = ScrollableFrame(parent, app.scroll)
    area.pack(fill='both', expand=True, padx=8, pady=8)
    rodape = ttk.Frame(parent, padding=(12, 6))
    rodape.pack(fill='x')
    mensagem = ttk.Label(rodape, style='Small.TLabel')
    mensagem.pack(side='left')
    ultima_exclusao = []

    def avisar():
        app.root.event_generate('<<ZeradosAlterados>>', when='tail')

    def guardar(registro):
        repo.guardar(registro)
        ano.set(str(registro.ano))
        mensagem.config(text=t('zer.salvo'))
        renderizar()
        avisar()

    def desfazer():
        if ultima_exclusao:
            try:
                guardar(ultima_exclusao[-1])
            except (ValueError, OSError) as erro:
                mostrar_erro(parent, erro)
                return
            ultima_exclusao.clear()
            btn_desfazer.pack_forget()

    btn_desfazer = ttk.Button(rodape, text=t('hist.desfazer'), command=desfazer)

    def excluir(registro):
        if not messagebox.askyesno(t('zer.titulo'), t('zer.excluir', nome=registro.nome), parent=parent):
            return
        try:
            repo.excluir(registro.id)
        except (OSError, ValueError) as erro:
            mostrar_erro(parent, erro)
            return
        ultima_exclusao[:] = [registro]
        btn_desfazer.pack(side='right')
        mensagem.config(text=t('zer.excluido'))
        renderizar()
        avisar()

    def nova_jogada(registro):
        hoje = date.today()
        novo = replace(registro, id=novo_id(), ano=hoje.year, mes=hoje.month, dia=None,
                       segundos=None, platina_segundos=None, notas='', origem='manual')
        editar_registro(parent, novo, guardar)

    def renderizar(_event=None):
        if not parent.winfo_exists():
            return
        anos = sorted({date.today().year, int(ano.get())} | {r.ano for r in repo.registros}, reverse=True)
        ano.config(values=[str(a) for a in anos])
        registros = [r for r in repo.registros if r.ano == int(ano.get())]
        n = sum(r.tipo == 'zerado' for r in registros)
        resumo.config(text=t('zer.resumo', n=n, extras=len(registros) - n))
        area.limpar()
        if not registros:
            ttk.Label(area.interior, text=t('zer.vazio'), wraplength=600, style='Small.TLabel').pack(padx=12, pady=35)
        for mes in range(1, 13):
            itens = [r for r in registros if r.mes == mes]
            if not itens:
                continue
            ttk.Label(area.interior, text=meses()[mes - 1], font=('Segoe UI', 11, 'bold')).pack(anchor='w', padx=8, pady=(14, 4))
            for r in itens:
                bloco = ttk.Frame(area.interior, style='Card.TFrame', padding=12)
                bloco.pack(fill='x', padx=6, pady=4)
                bloco.columnconfigure(0, weight=1)
                nome = ttk.Label(bloco, text=r.nome, style='CardTitle.TLabel', wraplength=480)
                nome.grid(row=0, column=0, sticky='w')
                detalhes = [t('zer.tempo_linha', tempo=duracao_texto(r.segundos)) if r.segundos is not None else t('zer.sem_tempo')]
                if r.platina_segundos is not None:
                    detalhes.append(t('zer.extra_linha', tempo=duracao_texto(r.platina_segundos)))
                    if r.segundos is not None:
                        detalhes.append(t('zer.total_linha', tempo=duracao_texto(r.segundos + r.platina_segundos)))
                if r.dia is not None:
                    detalhes.append(date(r.ano, r.mes, r.dia).strftime(t('fmt.data')))
                if r.tipo != 'zerado':
                    detalhes.append(t('zer.tipo.' + r.tipo))
                if r.notas:
                    detalhes.append(r.notas)
                info = ttk.Label(bloco, text='\n'.join(detalhes), style='Card.TLabel', wraplength=480)
                info.grid(row=1, column=0, sticky='w', pady=(6, 0))
                acoes = ttk.Frame(bloco, style='Card.TFrame')
                acoes.grid(row=0, column=1, rowspan=2, sticky='ne', padx=(12, 0))
                ttk.Button(acoes, text=t('hist.editar'), command=lambda item=r: editar_registro(parent, item, guardar)).pack(fill='x')
                ttk.Button(acoes, text=t('zer.rejogada'), command=lambda item=r: nova_jogada(item)).pack(fill='x', pady=4)
                ttk.Button(acoes, text=t('btn.excluir'), command=lambda item=r: excluir(item)).pack(fill='x')
                bloco.bind('<Configure>', lambda e, a=nome, b=info: (a.configure(wraplength=max(180, e.width - 160)), b.configure(wraplength=max(180, e.width - 160))))

    def exportar():
        caminho = filedialog.asksaveasfilename(parent=parent, title=t('zer.exportar'), defaultextension='.txt',
                                              initialfile=f'Zerados em {ano.get()}.txt', filetypes=[(t('zer.txt'), '*.txt')])
        if caminho:
            try:
                with open(caminho, 'w', encoding='utf-8-sig') as arq:
                    arq.write(exportar_txt(repo.registros, int(ano.get())))
            except OSError as erro:
                mostrar_erro(parent, erro)
                return
            messagebox.showinfo(t('zer.titulo'), t('zer.exportado', caminho=caminho), parent=parent)

    ttk.Button(topo, text=t('zer.adicionar'), style='Accent.TButton', command=lambda: editar_registro(parent, None, guardar, int(ano.get()))).pack(side='left', padx=10)
    ttk.Button(topo, text=t('zer.importar'), command=lambda: importar_arquivos(app, parent, repo, avisar)).pack(side='left', padx=3)
    ttk.Button(topo, text=t('zer.exportar'), command=exportar).pack(side='left', padx=3)
    ano.bind('<<ComboboxSelected>>', renderizar)
    vinculo = app.root.bind('<<ZeradosAlterados>>', renderizar, add='+')

    def limpar(event):
        if event.widget == parent:
            app.root.unbind('<<ZeradosAlterados>>', vinculo)

    parent.bind('<Destroy>', limpar, add='+')
    renderizar()
    return parent


def importar_arquivos(app, parent, repo, ao_importar):
    caminhos = filedialog.askopenfilenames(parent=parent, title=t('zer.importar'), filetypes=[(t('zer.txt'), '*.txt')])
    if not caminhos:
        return
    itens = []
    for caminho in caminhos:
        try:
            texto = ler_txt(caminho)
            ano = ano_do_texto(texto)
            if ano is None:
                match = re.search(r'\b(19\d{2}|20\d{2})\b', os.path.basename(caminho))
                ano = int(match[1]) if match else simpledialog.askinteger(t('zer.importar'), t('zer.import_ano', nome=os.path.basename(caminho)),
                                                                       parent=parent, minvalue=1900, maxvalue=date.today().year)
                if ano is None:
                    continue
            itens.extend((os.path.basename(caminho), item) for item in interpretar_txt(texto, ano))
        except (OSError, ValueError, UnicodeError) as erro:
            mostrar_erro(parent, erro)
    if not itens:
        messagebox.showinfo(t('zer.importar'), t('zer.import_vazio'), parent=parent)
        return
    return revisar_importacao(parent, repo, itens, ao_importar)


def revisar_importacao(parent, repo, itens, ao_importar):
    jan = tk.Toplevel(parent)
    jan.title(t('zer.import_titulo'))
    jan.geometry('880x640')
    jan.minsize(640, 480)
    aplicar_tema_moderno(jan)
    jan.transient(parent.winfo_toplevel())
    ttk.Label(jan, text=t('zer.import_dica'), wraplength=780).pack(fill='x', padx=14, pady=12)
    quadro = ttk.Frame(jan)
    quadro.pack(fill='both', expand=True, padx=14)
    estilo = ttk.Style()
    estilo.configure('Zerados.Treeview', background=COR_CARD, fieldbackground=COR_CARD, foreground=COR_TEXTO, rowheight=28)
    estilo.map('Zerados.Treeview', background=[('selected', '#5c5cff')], foreground=[('selected', 'white')])
    tabela = ttk.Treeview(quadro, columns=('sel', 'fonte', 'nome', 'estado'), show='headings', selectmode='browse', style='Zerados.Treeview')
    for coluna, nome, largura in [('sel', '✓', 40), ('fonte', t('zer.import_linha'), 160), ('nome', t('zer.import_jogo'), 320), ('estado', t('zer.import_estado'), 160)]:
        tabela.heading(coluna, text=nome)
        tabela.column(coluna, width=largura, minwidth=35, stretch=coluna == 'nome')
    barra = ttk.Scrollbar(quadro, orient='vertical', command=tabela.yview)
    horizontal = ttk.Scrollbar(quadro, orient='horizontal', command=tabela.xview)
    tabela.configure(yscrollcommand=barra.set, xscrollcommand=horizontal.set)
    quadro.columnconfigure(0, weight=1)
    quadro.rowconfigure(0, weight=1)
    tabela.grid(row=0, column=0, sticky='nsew')
    barra.grid(row=0, column=1, sticky='ns')
    horizontal.grid(row=1, column=0, sticky='ew')
    detalhe = tk.Text(jan, height=5, wrap='word', bg=COR_BG, fg=COR_TEXTO, relief='flat', font=('Segoe UI', 10))
    detalhe.pack(fill='x', padx=14, pady=8)
    contagem = ttk.Label(jan, style='Small.TLabel')
    contagem.pack(anchor='w', padx=14)
    duplicados = set()

    def atualizar():
        anterior = tabela.selection()
        tabela.delete(*tabela.get_children())
        assinaturas = {r.assinatura() for r in repo.registros}
        duplicados.clear()
        for i, (fonte, item) in enumerate(itens):
            r = item.registro
            estado = 'zer.import_revisar' if item.aviso or r is None else 'zer.import_pronto'
            if r and not item.aviso:
                if r.assinatura() in assinaturas:
                    duplicados.add(i)
                    item.selecionado = False
                    estado = 'zer.import_duplicado'
                else:
                    assinaturas.add(r.assinatura())
            tabela.insert('', 'end', iid=str(i), values=('☑' if item.selecionado else '☐', f'{fonte}:{item.linha}', r.nome if r else item.texto, t(estado)))
        contagem.config(text=t('zer.import_contagem', n=sum(x.selecionado for _, x in itens), pendentes=sum(bool(x.aviso or not x.registro) for _, x in itens)))
        if anterior:
            tabela.selection_set(anterior[0])
        selecionar()

    def selecionar(_event=None):
        ids = tabela.selection()
        detalhe.config(state='normal')
        detalhe.delete('1.0', 'end')
        if ids:
            _, item = itens[int(ids[0])]
            texto = item.texto
            if item.registro:
                r = item.registro
                texto += f'\n{meses()[r.mes - 1]} / {r.ano} · {duracao_texto(r.segundos) or t("zer.sem_tempo")}'
                if r.platina_segundos is not None:
                    texto += '\n' + t('zer.extra_linha', tempo=duracao_texto(r.platina_segundos))
            if item.aviso:
                texto += '\n' + item.aviso
            detalhe.insert('1.0', texto)
        detalhe.config(state='disabled')

    def alternar(_event=None):
        ids = tabela.selection()
        if ids:
            idx = int(ids[0])
            item = itens[idx][1]
            if item.registro and not item.aviso and idx not in duplicados:
                item.selecionado = not item.selecionado
                atualizar()

    def editar():
        ids = tabela.selection()
        if not ids:
            return
        item = itens[int(ids[0])][1]
        base = item.registro
        if base is None:
            hoje = date.today()
            base = Conclusao('', hoje.year, hoje.month, notas=item.texto, origem='txt')

        def guardar(registro):
            item.registro, item.aviso, item.selecionado = registro, '', True
            atualizar()

        editar_registro(jan, base, guardar)

    def confirmar():
        selecionados = [x.registro for _, x in itens if x.selecionado and x.registro and not x.aviso]
        if not selecionados:
            messagebox.showinfo(t('zer.importar'), t('zer.import_selecao'), parent=jan)
            return
        pendentes = sum(bool(x.aviso or not x.registro) for _, x in itens)
        if pendentes and not messagebox.askyesno(t('zer.importar'), t('zer.import_omitidos', n=pendentes), parent=jan):
            return
        try:
            n = repo.importar(selecionados)
        except (OSError, ValueError) as erro:
            mostrar_erro(jan, erro)
            return
        jan.destroy()
        ao_importar()
        messagebox.showinfo(t('zer.importar'), t('zer.import_resultado', n=n), parent=parent)

    botoes = ttk.Frame(jan, padding=12)
    botoes.pack(fill='x')
    ttk.Button(botoes, text=t('zer.import_alternar'), command=alternar).pack(side='left', padx=3)
    ttk.Button(botoes, text=t('hist.editar'), command=editar).pack(side='left', padx=3)
    ttk.Button(botoes, text=t('btn.cancelar'), command=jan.destroy).pack(side='right', padx=3)
    ttk.Button(botoes, text=t('zer.import_confirmar'), style='Accent.TButton', command=confirmar).pack(side='right', padx=3)
    tabela.bind('<<TreeviewSelect>>', selecionar)
    tabela.bind('<Double-1>', alternar)
    tabela.bind('<space>', alternar)
    atualizar()
    return jan
