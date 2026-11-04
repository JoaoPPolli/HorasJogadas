# Paridade do controle conectado com o aplicativo para PC

Este inventário trata do **controle conectado à mesma instância do PC**. O contador independente de `site/celular` não faz parte desta ampliação. As operações usam os IDs, validações e transações do aplicativo; a interface móvel adapta navegação, formulários, arquivos e confirmações ao toque.

**Navegador** indica execução da interface com Chromium e servidor Qt real, usando um perfil fictício e releitura pela API. **Domínio** indica testes automatizados da operação e de seus dados, sem exigir que todos os caminhos sejam clicados no navegador. **Implementado** indica uma adaptação revisada cujo cenário específico não tem uma asserção independente. Nenhuma dessas evidências substitui a verificação dos pacotes nativos no workflow de release.

Abreviações dos testes:

- **Básico:** `scripts/verify_phone_browser.cjs`, `scripts/verify_phone_reconnect.cjs` e `horas_jogadas_qt/phone_self_test.py`.
- **Painel:** `scripts/verify_phone_desktop_browser.cjs`.
- **Gestão:** `scripts/verify_phone_management_browser.cjs`.
- **Registros:** `tests_qt/test_phone_records.py`.
- **Operações:** `tests_qt/test_phone_desktop.py`.
- **Arquivos:** `tests_qt/test_phone_management.py`.
- **Servidor:** `tests_qt/test_remote_server.py`.

## Biblioteca e cronômetros

| Função no PC | Adaptação no controle conectado | Evidência |
| --- | --- | --- |
| Buscar e adicionar jogos | Campo de busca preservado durante atualização dos contadores | Navegador: Básico |
| Filtrar Todos/Jogando/Zerado/Backlog/Dropado | Seletor acessível ao toque | Navegador: Painel |
| Ordenar manualmente/nome/horas/recente | Seletor e ações de ordem manual; preferência salva no PC | Navegador: Painel; domínio: Operações |
| Renomear jogo e sessões vinculadas | Menu do cartão → Renomear | Navegador: Painel; domínio: Operações |
| Trocar status | Menu do cartão → Status | Navegador: Painel; domínio: Operações |
| Conclusão automática ao trocar para Zerado | Usa `Controller.set_status`, como o PC | Implementado; mesma regra do controlador |
| Mover para início/fim | Ações de ordem manual | Navegador: Painel; domínio: Operações |
| Iniciar/pausar/retomar/encerrar | Controles grandes e resumo ao salvar | Navegador: Básico; autoteste |
| Ajustar horas/minutos/segundos, inclusive negativos | Formulário de ajuste | Navegador: Painel; domínio: Operações |
| Atalhos +5/+10/+15/+30 minutos | Preenchem o formulário; cancelar não altera o cronômetro | Navegador: Painel |
| Usar duração da pausa no ajuste | Consulta a pausa atual e preenche sem retomar antes da confirmação | Navegador: Painel |
| Contar toda pausa ou alguns minutos e retomar | Formulário Contar pausa | Navegador: Painel; domínio: Operações |
| Descartar sessão | Confirmação no celular | Navegador: Painel |
| Excluir jogo com sessão pendente | Escolher salvar/descartar/cancelar antes de excluir | Navegador: Painel; domínio: Operações |
| Favoritos e Jogando agora | Controles anteriores preservados | Navegador: Básico; autoteste |
| Recuperar sessão anterior | Escolha explícita de recuperação/descarte | Domínio: Operações; arquivo preservado até a decisão |

## Histórico e estatísticas

| Função no PC | Adaptação no controle conectado | Evidência |
| --- | --- | --- |
| Consultar histórico | Lista móvel, pesquisa e paginação | Navegador: Painel; domínio: Registros |
| Adicionar/editar sessão e horário | Formulário com jogo, duração e término | Navegador: Painel; domínio: Registros |
| Confirmar sessões longas | Confirmação explícita para duração acima de 24 horas | Navegador: Painel; domínio: Registros |
| Excluir/desfazer exclusão | Botões e confirmação; pilha compartilhada com o PC | Navegador: Painel; domínio: Registros e Operações |
| Apagar todo histórico | Confirmação, cancelamento seguro e backup verificado | Navegador: Painel; domínio: Registros |
| Exportar histórico CSV | Download autenticado no celular | Navegador: Painel; conteúdo comparado ao domínio em Registros |
| Exportar resumo CSV | Download autenticado no celular | Autoteste: rota e arquivo; mesmo exportador do PC |
| Totais, média, sessão mais longa, sequências | Cartões responsivos | Navegador: Painel; cálculos do domínio em Registros |
| Editar sessão mais longa | Abre o formulário compartilhado de edição | Implementado; edição de sessão coberta em Painel e Registros |
| Gráfico 7 dias / 8 semanas / 6 meses | Gráfico adaptado ao celular | Navegador: Painel; domínio: Registros |
| Top cinco mais jogados | Barras de horas sem trilha de progresso | Navegador: Painel; mesmo cálculo `top_jogos` |
| Grupos ordenados pela sessão mais recente | Lista com primeira/última sessão compactas | Domínio: Registros, comparação com `agrupar_por_jogo` |
| Filtrar grupos por status | Seletor | Navegador: Painel; domínio: Registros |
| Excluir histórico de um grupo | Confirmação e backup | Navegador: Painel; domínio: Registros |

## Zerados

| Função no PC | Adaptação no controle conectado | Evidência |
| --- | --- | --- |
| Selecionar ano e agrupar por mês | Seletor e grupos mensais | Navegador: Painel; domínio: Registros |
| Resumo de jogos/DLCs/horas/platina | Cartões de resumo | Navegador: Painel; domínio: Registros |
| Criar/editar conclusão | Nome, ano, mês, dia opcional, duração opcional, platina, tipo, DLC, notas | Navegador: Painel; domínio: Registros |
| Registrar experiência sem zerar | Campo de tipo; mesma validação do domínio | Implementado; formulário compartilhado |
| Nova jogada | Novo registro, preservando o original | Navegador: Painel; domínio: Registros |
| Excluir/desfazer | Confirmação e desfazer, com pilha compartilhada | Navegador: Painel; domínio: Registros e Operações |
| Importar TXT com revisão | Arquivo/texto, ano, avisos e seleção das linhas | Navegador: Painel; domínio: Registros |
| Exportar TXT | Download autenticado por ano | Navegador: Painel; conteúdo comparado ao exportador em Registros |

## Configurações, imagens e manutenção

| Função no PC | Adaptação no controle conectado | Evidência |
| --- | --- | --- |
| Tema e idioma | Quatro temas e PT/EN; alterações refletidas no PC e celular | Navegador: Gestão; rollback em Arquivos |
| Consulta automática de versões | Preferência explícita | Domínio: Arquivos; mesmo formulário de preferências |
| Ativar/desativar capas e ícones independentemente | Preferências do PC, preservando imagens | Navegador: Gestão; preferências e imagens em Arquivos |
| Buscar capas/ícones em fontes públicas | Busca explícita, resultados, prévia e importação em lote | Navegador: Gestão com fonte sintética; tarefas e conflitos em Arquivos |
| Escolher imagem local e remover imagem | Arquivo do celular validado/normalizado no PC | Navegador: Gestão; domínio: Arquivos |
| Exportar biblioteca | Download autenticado compatível com o contador independente | Navegador: Básico; autoteste |
| Criar backup completo | Cópia verificada no PC | Navegador: Gestão; domínio: Arquivos |
| Baixar backup e importar para restauração | Arquivo verificado, prévia, cancelar e confirmar | Navegador: Gestão; segurança e rollback em Arquivos |
| Restaurar backup completo existente no PC | Escolha por ID emitido pelo app; cópia preventiva | Navegador: Gestão |
| Restaurar backup legado | Lista por identificação segura; cancelar e confirmar | Navegador: Gestão; preservação dos zerados verificada |
| Criar cópia isolada para teste | Preparação de uma cópia do perfil atual no PC, sem mesclar | Domínio: Operações; não inicia outra janela automaticamente |
| Abrir pasta dos dados | Ação abre a pasta conhecida no PC | Domínio: Operações, abertura do sistema simulada |
| Importar sessões do contador independente | Upload JSON, revisão, escolha de destino e deduplicação | Navegador: Gestão; mesmo importador do PC |
| Verificar atualizações | Consulta assíncrona e estado/progresso no celular | Navegador: Gestão; domínio: Operações |
| Baixar/instalar atualização | Pacote oficial, confirmação, backup, encerrar e reiniciar o PC | Domínio: Operações com instalação simulada; ciclo dos botões em Gestão; validação nativa obrigatória no workflow |
| Listar/remover aparelhos | Lista adaptada; revogação individual e geral | Navegador: Gestão e Básico; autorização em Servidor |
| Desativar controle | Fecha conexões preservando aparelhos lembrados e cronômetros | Navegador: Gestão; domínio: Operações |

## Segurança e limites da validação

Os testes usam apenas dados e imagens fictícios. As fontes de arte e a versão disponível são substituídas por respostas sintéticas nos testes de interface; não baixam artes públicas nem instalam atualizações reais. O workflow de release continua responsável por construir e verificar os pacotes Windows/Linux e executar os ciclos nativos de atualização.

Servidor e testes de domínio verificam autorização de rotas, limites de upload, IDs de comandos sem repetição, conflitos com alterações no PC, confirmações, rollback de falha de gravação e caminhos de arquivo seguros. ZIPs passam por validação de hashes, arquivos duplicados e caminhos; credenciais de aparelhos ficam fora dos backups. A restauração resolve sessões pendentes antes de substituir dados.

Painel e Gestão verificam PT/EN, quatro temas e larguras de 320, 390 e desktop, sem rolagem horizontal. O navegador verifica erros JavaScript e violações da política de conteúdo. Os testes existentes de reconexão preservam o acesso lembrado, QR expirado, autorização renovada e revogação.

Atalhos de teclado e a roda do mouse correspondem a busca, botões e rolagem por toque no celular. Escolhas de arquivo usam upload/download; abrir pasta, preparar cópia de teste e instalar atualização atuam no computador conectado. O PC continua precisando estar ligado e com o aplicativo aberto.
