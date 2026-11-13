# Histórico de mudanças

Mudanças conhecidas por versão. A publicação do código e a distribuição de executáveis são etapas separadas.

## 3.9.1

- Corrigido o banner da página do jogo: exibe a imagem inteira com a proporção original, sem ampliação e recorte excessivos em janelas largas. As miniaturas da biblioteca mantêm o formato anterior.
- A roda do mouse deixa de alterar seletores, anos, datas e campos numéricos no app. Sobre esses campos, a roda continua rolando a página quando há conteúdo rolável.
- Listas abertas continuam permitindo rolar as opções e confirmar a escolha por clique. Cliques e navegação por teclado permanecem disponíveis.
- A mesma proteção contra alteração por roda foi aplicada aos campos do controle conectado pelo navegador.
- Recarregar as Configurações conectadas sincroniza o estado antes de permitir novos comandos, evitando conflitos ao criar um backup logo depois.

## 3.9.0

- Retrospectiva mensal ou anual nas Estatísticas, com prévia no tema do app e exportação PNG 1080 × 1350 para compartilhar. Inclui horas, jogos, sessões, zerados, dias jogados e os cinco mais jogados; usa sessões salvas e respeita a distribuição por dia em viradas de mês/ano.
- Página de cada jogo pela biblioteca: contador, totais, média, primeira/última sessão, histórico recente, conclusões, platina e observações. Capas e ícones seguem as preferências existentes.
- Detecção automática opcional: vínculo explícito ao executável, início quando o processo aparece e salvamento ao confirmar seu fechamento. Caminho exato por padrão e modo por nome para Wine/Proton.
- Pausas e encerramentos manuais são respeitados; ajustes de tempo mantêm o salvamento automático. Desativar a detecção preserva a sessão atual para controle manual. Leituras incertas e vínculos ambíguos não encerram ou duplicam sessões.
- Detalhes e retrospectiva também no controle conectado pelo celular, com download do PNG. Vínculos configurados no PC podem ser ativados/desativados pelo painel; a escolha do executável permanece no PC.
- Consulta de processos local e em segundo plano, sem enviar listas de programas. Detecção desativada por padrão e sem execução automática em cópias de revisão.

## 3.8.0

- Botão Usar tempo extra no formulário de Zerados: preenche a platina adicional com o total do contador menos a duração ao zerar, incluindo a sessão aberta, sem somar novamente a cada clique.
- Contador do jogo selecionável; associações automáticas usam o nome exato ou um vínculo já salvo. Nomes ambíguos, várias conclusões do mesmo contador e totais menores que a duração original pedem conferência manual.
- Opção Platina concluída bloqueia o recálculo para preservar o marco após novas partidas; correções manuais e desbloqueio continuam disponíveis.
- Prévia só é gravada ao Salvar. Mesma função disponível no PC e no controle conectado pelo celular; duração original, cronômetros e sessões permanecem preservados.
- Metadados de platina e vínculo salvos de forma compatível com arquivos anteriores e incluídos nos backups completos. Formulário do PC com rolagem para manter os botões acessíveis.

## 3.7.1

- O widget fica oculto imediatamente quando preferências restauradas desativam a integração OBS. Mantidos o padrão branco minimalista e os estilos alternativos.

## 3.7.0

- Integração com OBS em Configurações: widget com fundo transparente para adicionar como Fonte de navegador, sem plugins ou conta.
- Exibe a sessão atual ou o tempo total do jogo; pode seguir o último cronômetro iniciado/retomado ou mostrar um jogo fixo.
- Visual branco e minimalista por padrão; estilos Arcade e Digital como alternativas, cor personalizada e nome do jogo opcional. Horas não reiniciam ao completar 24h.
- O widget acompanha pausas e ajustes do app, oculta o tempo quando perde conexão e reconecta usando o mesmo link.
- Servidor somente de leitura no próprio PC, independente do controle pelo celular; não expõe biblioteca ou histórico nem aceita comandos.
- Desativado por padrão; quando habilitado, volta a funcionar ao abrir a edição oficial. A chave local não acompanha backups ou cópias de revisão.

## 3.6.1

- Nova seção Inicialização nas Configurações: abrir o HorasJogadas ao entrar no Windows ou Linux, sem administrador.
- Opção de ativar o controle pelo celular automaticamente ao abrir o aplicativo, usando a última rede disponível e a porta estável dos aparelhos lembrados.
- A conexão tenta novamente por até um minuto se a rede ainda estiver iniciando. Ambas as opções começam desativadas; cópias de revisão não iniciam serviços nem alteram a inicialização do sistema.
- Preferências também disponíveis nas Configurações do controle conectado. Desmarcar a inicialização remove somente o registro do HorasJogadas.

## 3.6.0

- Controle conectado pelo celular ampliado com cinco páginas: Biblioteca, Histórico, Estatísticas, Zerados e Configurações, com navegação adaptada a telas pequenas e os quatro temas do app.
- Biblioteca com filtros, ordenação, favoritos, renomeação, status, reorganização manual e exclusão; ajustes positivos e negativos de tempo, atalhos de minutos e inclusão do tempo de pausa.
- Histórico com adição, edição, exclusão, desfazer e exportação CSV; estatísticas por período, jogos por atividade recente, gráfico dos mais jogados e exportação de resumo.
- Zerados com campanhas, DLCs, experiências, novas jogadas, datas, observações e platina adicional; importação TXT com conferência e exportação por ano.
- Configurações do PC pelo celular: aparência, idioma, capas e ícones, busca e importação de imagens em lote, imagens locais e gerenciamento dos aparelhos lembrados.
- Backups completos criados no PC, download para o celular e restauração com conferência; importação revisada de sessões do contador independente, sem duplicar registros já importados.
- Consulta, download e instalação de atualizações do aplicativo do PC pelo painel conectado, com confirmação, validação do pacote e backup; acesso à pasta de dados, cópia para revisão e recuperação de sessões pendentes.
- Alterações conferem o estado do PC antes de salvar; formulários antigos não substituem edições recentes. Operações de restauração e exclusões abrangentes criam cópia preventiva.
- Registros e formatos existentes preservados, assim como a reconexão de aparelhos lembrados. O contador offline continua separado e não recebe alterações nesta versão.

## 3.5.1

- Corrigida a perda do aparelho lembrado ao reabrir o endereço original de um QR Code expirado: a autorização salva é usada antes de tentar novo pareamento.
- Sessões temporárias expiradas renovam a conexão sem apagar a autorização duradoura; falhas transitórias ao consultar o estado também preservam o acesso salvo.
- Comandos interrompidos por autenticação não são repetidos automaticamente. A desconexão explícita e a revogação continuam removendo os acessos.
- Testes com fechamento e reabertura completa do navegador verificam QR expirado, autorização persistente, recuperação de sessão e revogação.

## 3.5.0

- Controle pelo celular com modo Jogando agora, botões grandes, favoritos e resumo ao encerrar a sessão.
- Capas e ícones locais no painel, respeitando as preferências do PC e sem downloads externos durante a navegação.
- Aparelhos lembrados por até 30 dias, endereço de porta estável, reconexão e revogação individual nas Configurações; autorizações não acompanham backups ou cópias de revisão.
- Contador instalável no celular pelo site, com quatro temas, favoritos e funcionamento offline após a primeira abertura, inclusive com o PC desligado.
- Sessões do celular preservadas ao recarregar, proteção entre abas, revisão de alterações no relógio e exportação sem apagar registros.
- Importação revisada no PC com escolha dos jogos, backup verificado, transação e prevenção de duplicatas; exportação da biblioteca para preparar o celular.
- Testes reais dos dois painéis no navegador e do arquivo exportado até o histórico do PC, além dos autotestes nativos de Windows/Linux.

## 3.4.0

- Controle pelo celular nas Configurações, desativado por padrão, com seleção da rede, QR Code e código temporário.
- Página responsiva com as quatro paletas e os idiomas do app; busca e adição de jogos, iniciar, pausar, retomar e encerrar sessões.
- Comandos usam os cronômetros e as transações do PC; validação de estado e pedidos repetidos evita encerrar uma sessão diferente ou duplicar registros.
- Pareamento local com expiração, revogação individual ou de todos os aparelhos e encerramento ao fechar o app. Sem credenciais nos dados e backups.
- Testes HTTP reais, testes do navegador e autoteste do pacote verificam pareamento, comandos, histórico e preservação dos dados.

## 3.3.2

- Ícone do aplicativo associado ao lançador Linux, com identificador de desktop consistente para X11 e Wayland.
- O pacote oficial registra automaticamente o atalho no menu do usuário e os ícones PNG do tema, sem sudo e sem alterar os registros.
- Atalho atualizado ao abrir o executável em outra pasta; caminhos com espaços e caracteres especiais são preservados.
- Autotestes verificam o ícone da janela X11, o lançador e os ícones após a atualização e o reinício nativo em Ubuntu e Arch Linux.

## 3.3.1

- Removido o marcador fixo desenhado no ponto inicial da rolagem automática. Apenas o cursor do mouse indica a direção.
- Mantidos os controles de velocidade, clique para cancelar, Esc e o modo de segurar e soltar a roda.

## 3.3.0

- Rolagem automática vertical com o botão central nas páginas e listas do app, incluindo diálogos com listas roláveis.
- Direção e velocidade controladas pela distância do mouse ao ponto inicial, com indicador visual e cursor de direção.
- Clique para ativar e outro clique ou Esc para parar; também aceita segurar a roda, mover e soltar para encerrar.
- Interrompe ao sair da janela, mudar de página, fechar ou perder o foco. Cliques usados para cancelar não acionam botões por baixo.
- Campos de edição preservam a colagem pelo botão central no Linux; os cronômetros e os registros permanecem independentes da rolagem.

## 3.2.2

- Corrigidos o alinhamento e o espaçamento dos seletores nas listas de capas e ícones, evitando sobreposição entre linhas.
- Prévia com texto completo em várias linhas, margens para as imagens e alinhamento dos botões de imagem local e remoção.
- Removida do FAQ do site a pergunta sobre registros da versão de revisão.

## 3.2.1

- Corrigido o ambiente herdado pelo atualizador Linux: comandos do sistema e a nova versão não usam as bibliotecas privadas da instalação anterior.
- Reinício independente do PyInstaller, preservando a sessão gráfica X11/Wayland e os caminhos de bibliotecas personalizados do sistema.
- A nova janela confirma a abertura; se encerrar antes de ficar pronta, o auxiliar tenta restaurar e reabrir a versão anterior, preservando ambas as cópias.
- Erros do reinício e da troca de arquivos ficam em update.log na pasta do download, em vez de serem descartados.
- Testes do ciclo real de atualização e reinício do executável Linux em Ubuntu e Arch antes de publicar.

## 3.2.0

- Busca de capas em Steam, GOG e Wikipedia, com filtro por fonte e identificação em cada resultado.
- Reconhecimento de erros de digitação, busca aproximada e nova tentativa com o título reconhecido; resultados incertos e sequências semelhantes continuam exigindo escolha manual.
- Busca, prévia e importação em lote de ícones oficiais da Steam e GOG para substituir as iniciais dos jogos.
- Ícones independentes das capas, com acesso pelo cartão e pelas Configurações, imagem local com transparência e opção de voltar às iniciais sem apagar imagens.
- Cache offline e backups completos incluem ícones; registros, capas e diários de recuperação anteriores permanecem compatíveis.
- Falhas em uma fonte não descartam sugestões das demais. A biblioteca não faz buscas de imagem ao abrir ou rolar.

## 3.1.1

- Corrigida a verificação de atualizações no Linux quando o pacote não encontra os certificados raiz do sistema.
- Certificados de confiança incluídos no aplicativo, mantendo a validação HTTPS e os certificados locais do sistema.
- A mesma correção vale para downloads de atualizações e importação de capas da Steam.
- Autoteste do executável Linux verifica o acesso HTTPS com os certificados do sistema indisponíveis.

## 3.1.0

- Capas opcionais, desativadas por padrão, preservando o layout compacto.
- Busca na Steam com revisão de correspondências, prévia e importação em lote sem chave de API.
- Imagens oficiais de alta qualidade, cache offline, troca/remoção e opção de arquivo local.
- Backups completos incluem capas e preferências; diário de recuperação permanece compatível com as versões anteriores.
- Linux: preserva arquivos pessoais na pasta do app e recupera dados movidos pela versão 3.0.1 quando app e dados estavam juntos.

## 3.0.1

- Atualizações no app, download em segundo plano, validação SHA-256 e backup antes de instalar.
- Verificação automática opcional e reinício após atualização nos pacotes Windows/Linux.

## 3.0.0

- Interface oficial PySide6/Qt com navegação lateral, temas Escuro minimalista e Original, e barra de título escura no Windows compatível.
- Biblioteca, histórico, estatísticas e Zerados preservando o domínio e os formatos de dados existentes.
- Estatísticas por atividade recente, gráfico de horas, meses agrupados e seletores de ano sem edição de texto.
- Ajuste de tempo completo, atalhos de minutos, backups completos e cópia isolada para revisão.
- Backup verificado antes do primeiro carregamento dos dados oficiais.
- Instalador e pacote portátil Windows x64, pacote Linux x86_64, autoteste dos executáveis e página pública de download.

## 2.7.0

- Resumo anual em Zerados: jogos, DLCs, tempo registrado e horas adicionais de platina.
- Marcação manual de DLC/expansão, com etiqueta na lista e metadado `@dlc: sim` no TXT.
- Reimportação do TXT original sem duplicar uma conclusão já categorizada no app.
- Busca: clique fora mantém o filtro, `Esc` limpa e libera o campo e `Ctrl+F` retorna a ele.

## 2.6.4

- Atualização dos cronômetros acompanha a precisão exibida, reduzindo trabalho repetido.
- Telas roláveis agrupam medições de layout e evitam recalcular larguras que não mudaram.

## 2.6.0

- Lista de Zerados independente, organizada por ano e mês, com dia opcional.
- Registros manuais, novas jogadas, experiências e tempo adicional de platina.
- Registro automático ao mudar um cronômetro para Zerado, evitando duplicatas ao alternar status.
- Importação TXT com prévia e exportação por ano.
- Armazenamento em `zerados.json` e backup próprio da gravação anterior.

## 2.5.0

Versão anteriormente presente no repositório: biblioteca com cronômetros, histórico, dashboard, edição de sessões, CSV, traduções, backups e atualizador por ZIP.
