# Histórico de mudanças

Mudanças conhecidas por versão. A publicação do código e a distribuição de executáveis são etapas separadas.

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
