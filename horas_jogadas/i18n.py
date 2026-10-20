"""Internacionalização simples (Português do Brasil / English).

Os dados gravados em disco (ex.: status "Jogando") continuam sendo as chaves canônicas em
português; só o que é exibido ao usuário é traduzido.
"""
from typing import Dict, List

from .constants import IDIOMA_PADRAO, IDIOMAS_DISPONIVEIS

_idioma = IDIOMA_PADRAO

TEXTOS: Dict[str, Dict[str, object]] = {
    "pt": {
        "app.titulo": "Registro de Horas Jogadas",
        # --- botões e rótulos gerais
        "btn.adicionar": "Adicionar", "btn.historico": "Histórico", "btn.dashboard": "Dash",
        "btn.confirmar": "Confirmar", "btn.excluir": "Excluir", "btn.salvar": "Salvar",
        "busca.rotulo": "🔎 Buscar (Ctrl+F)",
        "vazio.nenhum": "Nenhum jogo encontrado.",
        "vazio.biblioteca": "Sua biblioteca está vazia. Digite um nome acima e clique em Adicionar.",
        "tela.voltar": "← Voltar", "tela.historico": "Histórico de Jogatinas",
        "tela.dashboard": "Dashboard", "tela.config": "Configurações",
        # --- títulos de caixas de diálogo
        "dlg.erro_salvar": "Erro ao salvar", "dlg.aviso": "Aviso", "dlg.atencao": "Atenção",
        "dlg.erro": "Erro", "dlg.confirmar": "Confirmar", "dlg.sucesso": "Sucesso",
        "dlg.excluir": "Excluir",
        # --- recuperação / saída / erros
        "recuperar.titulo": "Recuperar sessões",
        "recuperar.msg": "O app foi encerrado sem salvar estas sessões:\n\n{linhas}\n\n"
                         "Deseja salvá-las no histórico?\n(Sim = recuperar, Não = descartar)",
        "sair.titulo": "Sair",
        "sair.msg": "Há sessões não salvas: {nomes}.\n\nSalvar as sessões no histórico antes de sair?\n\n"
                    "Sim = salvar e sair\nNão = descartar e sair\nCancelar = voltar ao app",
        "sair.e_mais": " e mais {n}",
        "erro.inesperado.titulo": "Erro inesperado",
        "erro.inesperado.msg": "Ocorreu um erro inesperado:\n{erro}\n\nDetalhes em: {log}",
        # --- ordenação, filtros e status
        "ord.manual": "Ordem manual", "ord.nome": "Nome (A–Z)", "ord.horas": "Mais horas",
        "ord.recente": "Jogado recentemente",
        "filtro.TODOS": "TODOS", "filtro.JOGANDO": "JOGANDO", "filtro.ZERADO": "ZERADO",
        "filtro.BACKLOG": "BACKLOG", "filtro.DROPADO": "DROPADO", "filtro.DESCONHECIDO": "DESCONHECIDO",
        "status.Jogando": "Jogando", "status.Zerado": "Zerado", "status.Backlog": "Backlog",
        "status.Dropado": "Dropado",
        # --- card do cronômetro
        "card.iniciar": "Iniciar", "card.pausar": "Pausar", "card.parar": "Parar",
        "card.total": "Total Geral: {tempo}",
        "menu.tempo": "➕ Adicionar/Editar Tempo", "menu.renomear": "✏️ Renomear",
        "menu.status": "🏷️ Mudar Status", "menu.topo": "Mover para topo", "menu.fim": "Mover para fim",
        "renomear.titulo": "Renomear jogo", "renomear.msg": "Novo nome:",
        "tempo.titulo": "Editar Tempo", "tempo.adicionar": "Adicionar tempo a: {nome}",
        "tempo.horas": "Horas", "tempo.minutos": "Minutos", "tempo.segundos": "Segundos",
        "tempo.negativo": "Use negativo para remover", "tempo.invalido": "Digite apenas números inteiros.",
        "excluir.confirma": "Excluir '{nome}'?",
        "pendente.titulo": "Sessão não salva",
        "pendente.msg": "'{nome}' tem {tempo} de sessão não salva.\n\nSalvar no histórico antes de excluir?",
        # --- histórico
        "hist.sem_nome": "<sem nome>", "hist.mais": "Carregar mais ({n} restantes)",
        "hist.vazio": "Nenhuma sessão registrada ainda.",
        "hist.apagar_tudo_confirma": "Apagar TODO o histórico?",
        "hist.apagar_tudo": "🗑️ Apagar TODO histórico",
        # --- dashboard
        "dash.resumo": "📊 Resumo da Biblioteca", "dash.total": "⏱ Total geral",
        "dash.sessoes": "{n} sessões", "dash.sessao_um": "1 sessão",
        "dash.media": "📏 Média por sessão", "dash.longa": "🏆 Sessão mais longa",
        "dash.mais_jogado": "🎮 Mais jogado", "dash.seq_atual": "🔥 Sequência atual",
        "dash.maior_seq": "📅 Maior sequência", "dash.dia": "{n} dia", "dash.dias": "{n} dias",
        "dash.horas": "📈 Horas jogadas", "periodo.7d": "7 dias", "periodo.8s": "8 semanas",
        "periodo.6m": "6 meses", "dash.sem_periodo": "Sem sessões neste período",
        "dash.top5": "🥇 Top 5 jogos", "dash.sem_sessoes": "Sem sessões registradas.",
        "dash.jogos": "📚 Jogos", "dash.linha_total": "⏱ Total: {tempo}  ·  {sessoes}",
        "dash.primeira": "📅 Primeira: {data}", "dash.ultima": "📅 Última: {data}",
        "dash.excluir_registros": "Apagar TODOS os registros de '{nome}'?",
        # --- configurações
        "cfg.modo": "Modo de Navegação:", "cfg.janelas": "Janelas (Pop-ups)",
        "cfg.navegacao": "Navegação (Tela Única)", "cfg.idioma": "Idioma / Language:",
        "cfg.salva": "Configuração salva!",
        # --- repositório (mensagens mostradas ao usuário)
        "erro.nome_vazio": "Digite um nome para o registro.",
        "erro.nome_duplicado": "Já existe um jogo chamado '{nome}'.",
        "erro.jogo_nao_encontrado": "Jogo não encontrado.",
        "erro.gravar": "Não foi possível salvar '{arquivo}':\n{erro}",
        "aviso.restaurado": "O arquivo '{arquivo}' estava corrompido e foi restaurado a partir do "
                            "último backup.\nA cópia danificada foi guardada em:\n{copia}",
        "aviso.corrompido": "O arquivo '{arquivo}' estava corrompido e não havia backup válido.\n"
                            "A cópia danificada foi preservada em:\n{copia}\n"
                            "O app iniciará com este arquivo vazio.",
        "aviso.sem_copia": "(não foi possível preservar uma cópia)",
        # --- pausa (card)
        "card.pausado_ha": "Pausado há {tempo}", "card.contar_pausa": "⏱ Contar pausa",
        "menu.contar_pausa": "⏱ Retomar contando a pausa…",
        "pausa.titulo": "Contar o tempo da pausa", "pausa.info": "Pausado há {tempo}",
        "pausa.tudo": "Toda a pausa ({tempo})", "pausa.parte_antes": "Só os últimos",
        "pausa.parte_depois": "min da pausa", "pausa.retomar": "Retomar", "btn.cancelar": "Cancelar",
        "pausa.invalido": "Digite um número inteiro de minutos (1 ou mais).",
        "tempo.usar": "Usar este tempo", "tempo.atalho": "+{n} min",
        # --- atualização do app
        "cfg.versao": "Versão {versao}", "cfg.atualizar": "Atualizar app…",
        "cfg.restaurar": "↩ Restaurar versão anterior",
        "atu.titulo": "Atualizar", "atu.escolher": "Selecione o ZIP da atualização",
        "atu.filtro_zip": "Arquivos ZIP", "atu.todos": "Todos os arquivos",
        "atu.invalido": "Este arquivo não parece ser uma atualização válida do app:\n\n{erro}",
        "atu.confirma": "Atualizar da versão {atual} para a {nova}?\n\nO app será reiniciado. Seus jogos e "
                        "histórico não são alterados.\nA versão atual fica guardada e pode ser restaurada.",
        "atu.mesma": "A versão selecionada ({nova}) é a mesma que está instalada.\n\nReinstalar mesmo assim?",
        "atu.antiga": "A versão selecionada ({nova}) é mais antiga que a instalada ({atual}).\n\nInstalar mesmo assim?",
        "atu.falha": "Não foi possível atualizar. Nada foi alterado.\n\n{erro}",
        "atu.concluida": "App atualizado para a versão {versao}!",
        "atu.sessoes.titulo": "Atualizar",
        "atu.sessoes.msg": "Para atualizar, o app precisa reiniciar. Há sessões não salvas: {nomes}.\n\n"
                           "Salvar as sessões no histórico antes?\n\nSim = salvar e atualizar\n"
                           "Não = descartar e atualizar\nCancelar = não atualizar",
        "atu.restaurar_confirma": "Restaurar a versão anterior ({versao})?\n\nO app será reiniciado. "
                                  "A versão atual ({atual}) ficará guardada.",
        "atu.sem_backup": "Não há versão anterior guardada.",
        "atu.erro.empacotado": "Esta versão é distribuída pelo itch.io e é atualizada por lá (o código vai dentro do .exe).",
        "cfg.atualizacoes_itch": "As atualizações chegam pelo itch.io: baixe a versão nova na página do app\n"
                                 "(ou deixe o app do itch.io atualizar automaticamente).",
        "atu.reabrir": "Atualizado para a versão {versao}.\n\nNão consegui reabrir sozinho: feche e abra o app novamente.",
        "atu.erro.nao_zip": "O arquivo não é um ZIP válido ou está corrompido.",
        "atu.erro.sem_pacote": "Não encontrei a pasta 'horas_jogadas' dentro do ZIP.",
        "atu.erro.faltando": "Arquivo obrigatório ausente no ZIP: {arquivo}",
        "atu.erro.sintaxe": "Erro de sintaxe em {arquivo} (linha {linha}).",
        "atu.erro.inseguro": "O ZIP contém um caminho inseguro: {arquivo}",
        "atu.erro.sem_versao": "Não consegui ler a versão do pacote (__version__).",
        # --- exportação CSV
        "csv.sep": ";", "csv.filtro": "Arquivos CSV", "csv.arquivo_historico": "historico",
        "csv.arquivo_resumo": "resumo", "csv.col.jogo": "Jogo", "csv.col.status": "Status",
        "csv.col.inicio": "Início", "csv.col.fim": "Fim", "csv.col.segundos": "Segundos",
        "csv.col.duracao": "Duração", "csv.col.horas": "Horas", "csv.col.sessoes": "Sessões",
        "csv.col.total_segundos": "Total (segundos)", "csv.col.total": "Tempo total",
        "csv.col.primeira": "Primeira sessão", "csv.col.ultima": "Última sessão",
        # --- dados, backups e desfazer
        "dados.titulo": "Dados e backups:", "dados.exportar_historico": "📤 Exportar histórico (CSV)…",
        "dados.exportar_resumo": "📤 Exportar resumo por jogo (CSV)…", "dados.backups": "🗂 Backups…",
        "dados.salvar_como": "Salvar arquivo CSV",
        "dados.csv_salvo": "Arquivo salvo em:\n{caminho}\n\n{linhas} linhas exportadas.",
        "dados.csv_erro": "Não foi possível salvar o arquivo:\n{erro}",
        "bk.titulo": "Backups", "bk.criar_agora": "Criar backup agora", "bk.criado": "Backup criado.",
        "bk.nada_para_copiar": "Ainda não há dados para copiar.",
        "bk.vazio": "Nenhum backup ainda. O primeiro é criado automaticamente na próxima vez que o app abrir.",
        "bk.tipo.diario": "Diário", "bk.tipo.antes_de_apagar": "Automático, antes de apagar",
        "bk.tipo.manual": "Manual", "bk.tipo.antes_de_restaurar": "Automático, antes de restaurar",
        "bk.resumo": "{jogos} jogos · {sessoes} sessões · {total}", "bk.restaurar": "Restaurar",
        "bk.ajuda": "Cópias dos seus jogos e histórico. Restaurar substitui os dados atuais "
                    "(uma cópia deles é guardada antes) e reinicia o app.",
        "bk.restaurar_confirma": "Restaurar o backup de {data}?\n\n{resumo}\n\nSeus dados atuais serão "
                                 "substituídos (uma cópia deles é guardada antes) e o app vai reiniciar.",
        "bk.falha": "Não foi possível restaurar:\n{erro}",
        "bk.reabrir": "Backup restaurado.\n\nNão consegui reabrir sozinho: feche e abra o app novamente.",
        "bk.sessoes.titulo": "Restaurar backup",
        "bk.sessoes.msg": "Para restaurar, o app precisa reiniciar. Há sessões não salvas: {nomes}.\n\n"
                          "Salvar as sessões no histórico antes?\n\nSim = salvar e restaurar\n"
                          "Não = descartar e restaurar\nCancelar = não restaurar",
        "hist.excluida": "Sessão excluída.", "hist.excluidas": "{n} sessões excluídas.",
        "hist.desfazer": "↩ Desfazer",
        # --- selo da barra de tarefas
        "icone.rodando": "Cronômetro rodando", "icone.pausado": "Cronômetro pausado",
        # --- editar / adicionar sessão
        "hist.editar": "✏️ Editar", "hist.adicionar": "➕ Adicionar sessão",
        "hist.longa_aviso": "⚠ sessão muito longa: confira",
        "sessao.titulo_editar": "Editar sessão", "sessao.titulo_adicionar": "Adicionar sessão manual",
        "sessao.jogo": "Jogo:", "sessao.termino": "Término ({formato}):", "sessao.formato": "dd/mm/aaaa hh:mm",
        "sessao.duracao": "Duração:",
        "sessao.dica": "Se a sessão atravessar a meia-noite, o tempo é dividido entre os dias no gráfico.",
        "sessao.erro_data": "Data/hora inválida. Use {formato} (ou AAAA-MM-DD hh:mm).",
        "sessao.erro_duracao": "Digite a duração com números inteiros (mínimo 1 segundo).",
        "sessao.erro_futuro": "O término não pode estar no futuro.",
        "sessao.erro_jogo": "Adicione ou escolha um jogo primeiro.",
        "sessao.confirma_longa": "Essa duração tem mais de 24 horas ({tempo}). Tem certeza?",
        "dash.editar_longa": "✏️ Editar sessão",
        # --- formatos e listas
        "fmt.data": "%d/%m/%Y", "fmt.data_hora": "%d/%m/%Y %H:%M", "fmt.semana": "%d/%m",
        "fmt.decimal": ",",
        "dias_semana": ["Seg", "Ter", "Qua", "Qui", "Sex", "Sáb", "Dom"],
        "meses": ["Jan", "Fev", "Mar", "Abr", "Mai", "Jun", "Jul", "Ago", "Set", "Out", "Nov", "Dez"],
    },
    "en": {
        "app.titulo": "Game Time Tracker",
        "btn.adicionar": "Add", "btn.historico": "History", "btn.dashboard": "Dashboard",
        "btn.confirmar": "Confirm", "btn.excluir": "Delete", "btn.salvar": "Save",
        "busca.rotulo": "🔎 Search (Ctrl+F)",
        "vazio.nenhum": "No games found.",
        "vazio.biblioteca": "Your library is empty. Type a name above and click Add.",
        "tela.voltar": "← Back", "tela.historico": "Play History",
        "tela.dashboard": "Dashboard", "tela.config": "Settings",
        "dlg.erro_salvar": "Save error", "dlg.aviso": "Warning", "dlg.atencao": "Attention",
        "dlg.erro": "Error", "dlg.confirmar": "Confirm", "dlg.sucesso": "Success",
        "dlg.excluir": "Delete",
        "recuperar.titulo": "Recover sessions",
        "recuperar.msg": "The app was closed without saving these sessions:\n\n{linhas}\n\n"
                         "Do you want to save them to the history?\n(Yes = recover, No = discard)",
        "sair.titulo": "Exit",
        "sair.msg": "There are unsaved sessions: {nomes}.\n\nSave the sessions to the history before exiting?\n\n"
                    "Yes = save and exit\nNo = discard and exit\nCancel = back to the app",
        "sair.e_mais": " and {n} more",
        "erro.inesperado.titulo": "Unexpected error",
        "erro.inesperado.msg": "An unexpected error occurred:\n{erro}\n\nDetails in: {log}",
        "ord.manual": "Manual order", "ord.nome": "Name (A–Z)", "ord.horas": "Most hours",
        "ord.recente": "Recently played",
        "filtro.TODOS": "ALL", "filtro.JOGANDO": "PLAYING", "filtro.ZERADO": "COMPLETED",
        "filtro.BACKLOG": "BACKLOG", "filtro.DROPADO": "DROPPED", "filtro.DESCONHECIDO": "UNKNOWN",
        "status.Jogando": "Playing", "status.Zerado": "Completed", "status.Backlog": "Backlog",
        "status.Dropado": "Dropped",
        "card.iniciar": "Start", "card.pausar": "Pause", "card.parar": "Stop",
        "card.total": "Total: {tempo}",
        "menu.tempo": "➕ Add/Edit Time", "menu.renomear": "✏️ Rename",
        "menu.status": "🏷️ Change Status", "menu.topo": "Move to top", "menu.fim": "Move to bottom",
        "renomear.titulo": "Rename game", "renomear.msg": "New name:",
        "tempo.titulo": "Edit Time", "tempo.adicionar": "Add time to: {nome}",
        "tempo.horas": "Hours", "tempo.minutos": "Minutes", "tempo.segundos": "Seconds",
        "tempo.negativo": "Use a negative value to remove", "tempo.invalido": "Enter whole numbers only.",
        "excluir.confirma": "Delete '{nome}'?",
        "pendente.titulo": "Unsaved session",
        "pendente.msg": "'{nome}' has {tempo} of unsaved session time.\n\nSave it to the history before deleting?",
        "hist.sem_nome": "<unnamed>", "hist.mais": "Load more ({n} remaining)",
        "hist.vazio": "No sessions recorded yet.",
        "hist.apagar_tudo_confirma": "Delete the ENTIRE history?",
        "hist.apagar_tudo": "🗑️ Delete ENTIRE history",
        "dash.resumo": "📊 Library Summary", "dash.total": "⏱ Total time",
        "dash.sessoes": "{n} sessions", "dash.sessao_um": "1 session",
        "dash.media": "📏 Average per session", "dash.longa": "🏆 Longest session",
        "dash.mais_jogado": "🎮 Most played", "dash.seq_atual": "🔥 Current streak",
        "dash.maior_seq": "📅 Longest streak", "dash.dia": "{n} day", "dash.dias": "{n} days",
        "dash.horas": "📈 Hours played", "periodo.7d": "7 days", "periodo.8s": "8 weeks",
        "periodo.6m": "6 months", "dash.sem_periodo": "No sessions in this period",
        "dash.top5": "🥇 Top 5 games", "dash.sem_sessoes": "No sessions recorded.",
        "dash.jogos": "📚 Games", "dash.linha_total": "⏱ Total: {tempo}  ·  {sessoes}",
        "dash.primeira": "📅 First: {data}", "dash.ultima": "📅 Last: {data}",
        "dash.excluir_registros": "Delete ALL records for '{nome}'?",
        "cfg.modo": "Navigation mode:", "cfg.janelas": "Windows (Pop-ups)",
        "cfg.navegacao": "Navigation (Single Screen)", "cfg.idioma": "Idioma / Language:",
        "cfg.salva": "Settings saved!",
        "erro.nome_vazio": "Enter a name for the entry.",
        "erro.nome_duplicado": "A game named '{nome}' already exists.",
        "erro.jogo_nao_encontrado": "Game not found.",
        "erro.gravar": "Could not save '{arquivo}':\n{erro}",
        "aviso.restaurado": "The file '{arquivo}' was corrupted and has been restored from the "
                            "latest backup.\nThe damaged copy was kept at:\n{copia}",
        "aviso.corrompido": "The file '{arquivo}' was corrupted and there was no valid backup.\n"
                            "The damaged copy was preserved at:\n{copia}\n"
                            "The app will start with this file empty.",
        "aviso.sem_copia": "(a copy could not be preserved)",
        "card.pausado_ha": "Paused for {tempo}", "card.contar_pausa": "⏱ Count pause",
        "menu.contar_pausa": "⏱ Resume counting the pause…",
        "pausa.titulo": "Count the paused time", "pausa.info": "Paused for {tempo}",
        "pausa.tudo": "The whole pause ({tempo})", "pausa.parte_antes": "Only the last",
        "pausa.parte_depois": "min of the pause", "pausa.retomar": "Resume", "btn.cancelar": "Cancel",
        "pausa.invalido": "Enter a whole number of minutes (1 or more).",
        "tempo.usar": "Use this time", "tempo.atalho": "+{n} min",
        "cfg.versao": "Version {versao}", "cfg.atualizar": "Update app…",
        "cfg.restaurar": "↩ Restore previous version",
        "atu.titulo": "Update", "atu.escolher": "Select the update ZIP",
        "atu.filtro_zip": "ZIP files", "atu.todos": "All files",
        "atu.invalido": "This file doesn't look like a valid app update:\n\n{erro}",
        "atu.confirma": "Update from version {atual} to {nova}?\n\nThe app will restart. Your games and "
                        "history are not changed.\nThe current version is kept and can be restored.",
        "atu.mesma": "The selected version ({nova}) is the same as the installed one.\n\nReinstall anyway?",
        "atu.antiga": "The selected version ({nova}) is older than the installed one ({atual}).\n\nInstall anyway?",
        "atu.falha": "Could not update. Nothing was changed.\n\n{erro}",
        "atu.concluida": "App updated to version {versao}!",
        "atu.sessoes.titulo": "Update",
        "atu.sessoes.msg": "To update, the app needs to restart. There are unsaved sessions: {nomes}.\n\n"
                           "Save the sessions to the history first?\n\nYes = save and update\n"
                           "No = discard and update\nCancel = don't update",
        "atu.restaurar_confirma": "Restore the previous version ({versao})?\n\nThe app will restart. "
                                  "The current version ({atual}) will be kept.",
        "atu.sem_backup": "There is no previous version saved.",
        "atu.erro.empacotado": "This version is distributed through itch.io and is updated there (the code is inside the .exe).",
        "cfg.atualizacoes_itch": "Updates come through itch.io: download the new version from the app's page\n"
                                 "(or let the itch.io app update it automatically).",
        "atu.reabrir": "Updated to version {versao}.\n\nI could not reopen it automatically: please close and open the app again.",
        "atu.erro.nao_zip": "The file is not a valid ZIP or it is corrupted.",
        "atu.erro.sem_pacote": "Could not find the 'horas_jogadas' folder inside the ZIP.",
        "atu.erro.faltando": "Required file missing from the ZIP: {arquivo}",
        "atu.erro.sintaxe": "Syntax error in {arquivo} (line {linha}).",
        "atu.erro.inseguro": "The ZIP contains an unsafe path: {arquivo}",
        "atu.erro.sem_versao": "Could not read the package version (__version__).",
        "csv.sep": ",", "csv.filtro": "CSV files", "csv.arquivo_historico": "history",
        "csv.arquivo_resumo": "summary", "csv.col.jogo": "Game", "csv.col.status": "Status",
        "csv.col.inicio": "Start", "csv.col.fim": "End", "csv.col.segundos": "Seconds",
        "csv.col.duracao": "Duration", "csv.col.horas": "Hours", "csv.col.sessoes": "Sessions",
        "csv.col.total_segundos": "Total (seconds)", "csv.col.total": "Total time",
        "csv.col.primeira": "First session", "csv.col.ultima": "Last session",
        "dados.titulo": "Data and backups:", "dados.exportar_historico": "📤 Export history (CSV)…",
        "dados.exportar_resumo": "📤 Export per-game summary (CSV)…", "dados.backups": "🗂 Backups…",
        "dados.salvar_como": "Save CSV file",
        "dados.csv_salvo": "File saved to:\n{caminho}\n\n{linhas} rows exported.",
        "dados.csv_erro": "Could not save the file:\n{erro}",
        "bk.titulo": "Backups", "bk.criar_agora": "Create backup now", "bk.criado": "Backup created.",
        "bk.nada_para_copiar": "There is no data to copy yet.",
        "bk.vazio": "No backups yet. The first one is created automatically the next time the app opens.",
        "bk.tipo.diario": "Daily", "bk.tipo.antes_de_apagar": "Automatic, before deleting",
        "bk.tipo.manual": "Manual", "bk.tipo.antes_de_restaurar": "Automatic, before restoring",
        "bk.resumo": "{jogos} games · {sessoes} sessions · {total}", "bk.restaurar": "Restore",
        "bk.ajuda": "Copies of your games and history. Restoring replaces the current data "
                    "(a copy of it is kept first) and restarts the app.",
        "bk.restaurar_confirma": "Restore the backup from {data}?\n\n{resumo}\n\nYour current data will be "
                                 "replaced (a copy of it is kept first) and the app will restart.",
        "bk.falha": "Could not restore:\n{erro}",
        "bk.reabrir": "Backup restored.\n\nI could not reopen it automatically: please close and open the app again.",
        "bk.sessoes.titulo": "Restore backup",
        "bk.sessoes.msg": "To restore, the app needs to restart. There are unsaved sessions: {nomes}.\n\n"
                          "Save the sessions to the history first?\n\nYes = save and restore\n"
                          "No = discard and restore\nCancel = don't restore",
        "hist.excluida": "Session deleted.", "hist.excluidas": "{n} sessions deleted.",
        "hist.desfazer": "↩ Undo",
        "icone.rodando": "Timer running", "icone.pausado": "Timer paused",
        "hist.editar": "✏️ Edit", "hist.adicionar": "➕ Add session",
        "hist.longa_aviso": "⚠ very long session: please check",
        "sessao.titulo_editar": "Edit session", "sessao.titulo_adicionar": "Add manual session",
        "sessao.jogo": "Game:", "sessao.termino": "End ({formato}):", "sessao.formato": "mm/dd/yyyy hh:mm",
        "sessao.duracao": "Duration:",
        "sessao.dica": "If the session crosses midnight, the time is split between the days in the chart.",
        "sessao.erro_data": "Invalid date/time. Use {formato} (or YYYY-MM-DD hh:mm).",
        "sessao.erro_duracao": "Enter the duration as whole numbers (at least 1 second).",
        "sessao.erro_futuro": "The end can't be in the future.",
        "sessao.erro_jogo": "Add or choose a game first.",
        "sessao.confirma_longa": "This duration is longer than 24 hours ({tempo}). Are you sure?",
        "dash.editar_longa": "✏️ Edit session",
        "fmt.data": "%m/%d/%Y", "fmt.data_hora": "%m/%d/%Y %H:%M", "fmt.semana": "%m/%d",
        "fmt.decimal": ".",
        "dias_semana": ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"],
        "meses": ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"],
    },
}


TEXTOS['pt'].update({
    'zer.titulo': '🏆 Zerados', 'zer.adicionar': '+ Adicionar registro',
    'zer.importar': 'Importar TXT…', 'zer.exportar': 'Exportar TXT…',
    'zer.independente': 'Sua lista pessoal. Edições aqui não alteram cronômetros, histórico ou dashboard.',
    'zer.ano': 'Ano:', 'zer.mes': 'Mês:', 'zer.dia': 'Dia (opcional):',
    'zer.nome': 'Jogo / DLC:', 'zer.tempo': 'Tempo para zerar:',
    'zer.platina': 'Horas adicionais para platinar:',
    'zer.notas': 'Observações (jogada, personagem, 100%, platina…):',
    'zer.tipo': 'Tipo:', 'zer.tipo.zerado': 'Zerado', 'zer.tipo.experiencia': 'Joguei bastante (não zerado)',
    'zer.dica_tempo': 'Ex.: 13h45m, 40min ou 01:30:00. Vazio = tempo não informado.',
    'zer.novo': 'Novo registro', 'zer.editar': 'Editar registro', 'zer.rejogada': 'Nova jogada',
    'zer.vazio': 'Nenhum registro neste ano. Adicione um jogo ou importe seu bloco de notas.',
    'zer.resumo': '{n} conclusões · {extras} experiências sem zerar',
    'zer.resumo_ano': 'Resumo de {ano}', 'zer.resumo_jogos': 'Jogos zerados',
    'zer.resumo_dlcs': 'DLCs concluídas', 'zer.resumo_tempo': 'Tempo registrado',
    'zer.resumo_platina': 'Platina (horas adicionais)',
    'zer.resumo_detalhe': '{registros} registros · {experiencias} experiências sem zerar · {sem_tempo} sem tempo informado',
    'zer.resumo_dica': 'Somente tempos informados, incluindo platina e experiências. Cada jogada conta separadamente.',
    'zer.dlc_opcao': 'DLC / expansão', 'zer.erro_dlc': 'Informe sim ou não para a categoria DLC.',
    'zer.sem_tempo': 'Tempo não informado', 'zer.tempo_linha': 'Zerado em: {tempo}',
    'zer.extra_linha': 'Platina: +{tempo} adicionais', 'zer.total_linha': 'Total: {tempo}',
    'zer.excluir': 'Excluir “{nome}” desta lista? Os cronômetros e o histórico não serão alterados.',
    'zer.salvo': 'Registro salvo.', 'zer.excluido': 'Registro excluído.',
    'zer.automatico': '“{nome}” adicionado aos zerados.', 'zer.ver': 'Ver lista',
    'zer.existente': 'Este cronômetro já foi registrado. Use “Nova jogada” na lista para outra conclusão.',
    'zer.falha': 'Não foi possível concluir a operação na lista de zerados:\n{erro}',
    'zer.erro_nome': 'Informe o nome do jogo.', 'zer.erro_tempo': 'Tempo inválido. Use 13h45m, 40min ou HH:MM:SS, sem valores negativos.',
    'zer.erro_data': 'Informe um ano, mês e dia válidos. O dia pode ficar vazio.',
    'zer.erro_futuro': 'A conclusão não pode estar no futuro.',
    'zer.erro_arquivo': 'O arquivo zerados.json está inválido ou tem uma versão não compatível. Ele foi preservado; restaure uma cópia válida antes de editar a lista.',
    'zer.recuperado': 'A lista foi recuperada do backup. O arquivo com problema foi preservado em:\n{caminho}',
    'zer.txt_grande': 'O TXT deve ter no máximo 2 MB.',
    'zer.import_sem_data': 'Não foi possível identificar o ano ou o mês. Edite esta linha antes de importar.',
    'zer.import_formato': 'Formato não reconhecido. Edite esta linha antes de importar.',
    'zer.import_ano': 'Qual é o ano deste arquivo?\n{nome}',
    'zer.import_titulo': 'Revisar importação', 'zer.import_dica': 'Revise as linhas. Duplo clique alterna a seleção; use Editar para corrigir. Só as linhas selecionadas serão importadas.',
    'zer.import_linha': 'Arquivo / linha', 'zer.import_jogo': 'Registro', 'zer.import_estado': 'Situação',
    'zer.import_pronto': 'Pronto', 'zer.import_duplicado': 'Já existe / repetido', 'zer.import_revisar': 'Revisar',
    'zer.import_alternar': 'Selecionar / desmarcar', 'zer.import_confirmar': 'Importar selecionados',
    'zer.import_vazio': 'Nenhuma linha para importar.', 'zer.import_selecao': 'Selecione pelo menos um registro válido.',
    'zer.import_resultado': '{n} registros importados. Repetidos foram ignorados.',
    'zer.import_contagem': '{n} selecionados · {pendentes} precisam de revisão',
    'zer.import_omitidos': '{n} linhas ainda precisam de revisão e não serão importadas. Continuar só com as selecionadas?',
    'zer.exportado': 'Lista exportada para:\n{caminho}', 'zer.txt': 'Bloco de notas (TXT)',
})
TEXTOS['en'].update({
    'zer.titulo': '🏆 Completed', 'zer.adicionar': '+ Add entry',
    'zer.importar': 'Import TXT…', 'zer.exportar': 'Export TXT…',
    'zer.independente': 'Your personal list. Edits here do not change timers, session history or dashboard.',
    'zer.ano': 'Year:', 'zer.mes': 'Month:', 'zer.dia': 'Day (optional):',
    'zer.nome': 'Game / DLC:', 'zer.tempo': 'Time to complete:',
    'zer.platina': 'Additional hours for platinum:',
    'zer.notas': 'Notes (playthrough, character, 100%, platinum…):',
    'zer.tipo': 'Type:', 'zer.tipo.zerado': 'Completed', 'zer.tipo.experiencia': 'Played enough (not completed)',
    'zer.dica_tempo': 'E.g. 13h45m, 40min or 01:30:00. Blank = time unknown.',
    'zer.novo': 'New entry', 'zer.editar': 'Edit entry', 'zer.rejogada': 'New playthrough',
    'zer.vazio': 'No entries for this year. Add a game or import your text file.',
    'zer.resumo': '{n} completions · {extras} experiences without finishing',
    'zer.resumo_ano': '{ano} summary', 'zer.resumo_jogos': 'Games completed',
    'zer.resumo_dlcs': 'DLCs completed', 'zer.resumo_tempo': 'Recorded time',
    'zer.resumo_platina': 'Platinum (additional hours)',
    'zer.resumo_detalhe': '{registros} entries · {experiencias} unfinished experiences · {sem_tempo} with unknown time',
    'zer.resumo_dica': 'Known times only, including platinum and experiences. Each playthrough counts separately.',
    'zer.dlc_opcao': 'DLC / expansion', 'zer.erro_dlc': 'Enter yes or no for the DLC category.',
    'zer.sem_tempo': 'Time unknown', 'zer.tempo_linha': 'Completed in: {tempo}',
    'zer.extra_linha': 'Platinum: +{tempo} additional', 'zer.total_linha': 'Total: {tempo}',
    'zer.excluir': 'Delete “{nome}” from this list? Timers and history will not change.',
    'zer.salvo': 'Entry saved.', 'zer.excluido': 'Entry deleted.',
    'zer.automatico': '“{nome}” added to completed games.', 'zer.ver': 'View list',
    'zer.existente': 'This timer was already recorded. Use “New playthrough” in the list for another completion.',
    'zer.falha': 'Could not complete the operation in the completed games list:\n{erro}',
    'zer.erro_nome': 'Enter a game name.', 'zer.erro_tempo': 'Invalid time. Use 13h45m, 40min or HH:MM:SS, without negative values.',
    'zer.erro_data': 'Enter a valid year, month and day. The day may be blank.',
    'zer.erro_futuro': 'The completion cannot be in the future.',
    'zer.erro_arquivo': 'zerados.json is invalid or uses an unsupported version. It was preserved; restore a valid copy before editing the list.',
    'zer.recuperado': 'The list was recovered from its backup. The damaged file was preserved at:\n{caminho}',
    'zer.txt_grande': 'The TXT must be no larger than 2 MB.',
    'zer.import_sem_data': 'Could not identify the year or month. Edit this line before importing.',
    'zer.import_formato': 'Unrecognized format. Edit this line before importing.',
    'zer.import_ano': 'Which year is this file for?\n{nome}',
    'zer.import_titulo': 'Review import', 'zer.import_dica': 'Review the lines. Double click to toggle selection; use Edit to fix an entry. Only selected lines will be imported.',
    'zer.import_linha': 'File / line', 'zer.import_jogo': 'Entry', 'zer.import_estado': 'Status',
    'zer.import_pronto': 'Ready', 'zer.import_duplicado': 'Already exists / repeated', 'zer.import_revisar': 'Review',
    'zer.import_alternar': 'Select / deselect', 'zer.import_confirmar': 'Import selected',
    'zer.import_vazio': 'No lines to import.', 'zer.import_selecao': 'Select at least one valid entry.',
    'zer.import_resultado': '{n} entries imported. Duplicates were skipped.',
    'zer.import_contagem': '{n} selected · {pendentes} need review',
    'zer.import_omitidos': '{n} lines still need review and will not be imported. Continue with the selected lines only?',
    'zer.exportado': 'List exported to:\n{caminho}', 'zer.txt': 'Text file (TXT)',
})


def definir_idioma(codigo: str) -> None:
    """Define o idioma ativo; códigos desconhecidos voltam ao padrão."""
    global _idioma
    _idioma = codigo if codigo in IDIOMAS_DISPONIVEIS else IDIOMA_PADRAO


def idioma_atual() -> str:
    return _idioma


def t(chave: str, **valores) -> str:
    """Texto traduzido. Cai no português e, por fim, na própria chave se não existir."""
    texto = TEXTOS[_idioma].get(chave)
    if texto is None:
        texto = TEXTOS[IDIOMA_PADRAO].get(chave, chave)
    texto = str(texto)
    return texto.format(**valores) if valores else texto


def lista(chave: str) -> List[str]:
    """Lista traduzida (ex.: dias da semana, meses)."""
    valor = TEXTOS[_idioma].get(chave) or TEXTOS[IDIOMA_PADRAO][chave]
    return list(valor)  # type: ignore[arg-type]


def t_status(status: str) -> str:
    """Nome exibido de um status canônico (ex.: 'Zerado' -> 'Completed')."""
    return t(f"status.{status}") if f"status.{status}" in TEXTOS[IDIOMA_PADRAO] else status


def rotulo_filtro(chave: str) -> str:
    """Rótulo exibido de um filtro de status (chave canônica em maiúsculas, ex.: 'ZERADO')."""
    return t(f"filtro.{chave}") if f"filtro.{chave}" in TEXTOS[IDIOMA_PADRAO] else chave
