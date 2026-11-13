# Guia de uso — HorasJogadas 3.6

## Instalar e atualizar

Use a [página de download](https://joaoppolli.github.io/HorasJogadas/). No Windows, o instalador cria um atalho no menu Iniciar; o ZIP portátil deve ser extraído por inteiro. Nenhum dos pacotes precisa de Python.

No Linux x86_64, extraia o `.tar.gz`, abra um terminal na pasta e execute `./HorasJogadas`. É necessária uma sessão gráfica. Em Ubuntu 22.04 ou superior, se faltar alguma biblioteca Qt/X11, instale:

```bash
sudo apt-get install libegl1 libxkbcommon-x11-0 libxcb-cursor0 libxcb-xinerama0 libxcb-keysyms1 libxcb-shape0 libxcb-icccm4
```

Os pacotes não são assinados digitalmente. Baixe somente das Releases oficiais. A partir da versão 3.0.1, use Configurações → Verificar atualizações: baixe e escolha Instalar e reiniciar. O pacote é validado por SHA-256 e os registros recebem um backup antes do encerramento. A verificação de versões ao abrir é opcional. A versão 3.0.0 precisa receber este recurso por uma instalação manual inicial. Feche o app antigo antes. A desinstalação remove o aplicativo, sem remover os registros pessoais.

No Linux, a partir da 3.3.2, abrir o pacote oficial registra o ícone e o atalho do HorasJogadas no menu do usuário, sem sudo. O mesmo identificador associa o ícone à janela no X11 e no Wayland. Se mover a pasta do programa, abra o executável uma vez na nova pasta para atualizar o atalho. Os arquivos ficam em `$XDG_DATA_HOME/applications` e `$XDG_DATA_HOME/icons/hicolor` (por padrão, `~/.local/share`). Não é necessário alterar a pasta dos registros.

## Biblioteca e cronômetros

Clique em **Adicionar jogo**. Use busca, filtros de status e ordenação para organizar os cartões. No cartão, **Iniciar** começa uma sessão, **Pausar** interrompe a contagem e **Parar** salva a sessão no histórico.

O menu do cartão permite renomear, ajustar o tempo, trocar status e excluir. O ajuste de tempo aceita horas, minutos e segundos, valores negativos para remover e atalhos de +5, +10, +15 e +30 minutos. Confira o valor antes de confirmar. Dê dois cliques no tempo para abrir o ajuste.

`Ctrl+F` abre a busca; `Esc` limpa o filtro. Se uma sessão ficou pendente depois de um encerramento inesperado, o app oferece a recuperação na próxima abertura.

## Controle pelo celular

Use para contar partidas no PS5 ou em outro console enquanto estiver longe do teclado.

1. Mantenha PC e celular na mesma rede Wi-Fi (o PC também pode usar cabo), com o computador ligado e acordado.
2. No HorasJogadas, abra **Configurações → Controle pelo celular**. Se houver mais de uma rede, escolha a interface da sua rede doméstica e clique em **Ativar controle pelo celular**.
3. Escaneie o QR Code com a câmera do celular. Ou copie o endereço exibido, abra no navegador do telefone e digite o código temporário de seis dígitos.
4. Escolha o jogo, inicie a sessão e jogue. Use Pausar e Retomar quando necessário. **Encerrar e salvar** grava o tempo no histórico do PC.

A página usa o tema e o idioma escolhidos no app. Bloquear a tela do celular não pausa o cronômetro: ele roda no PC. Ao retornar ao navegador, a página sincroniza antes de aceitar comandos; comandos com um estado antigo são recusados, sem substituir uma alteração feita no computador. Toques repetidos no mesmo pedido não duplicam sessões.

O painel conectado tem cinco páginas na navegação inferior:

- **Biblioteca:** busque e filtre jogos, escolha a ordenação e use o menu de cada cartão para renomear, trocar status, ajustar tempo, contar a pausa, reorganizar ou excluir. Os atalhos de minutos preenchem o ajuste; confira e salve. Ao excluir um jogo com sessão aberta, escolha antes salvar ou descartar o tempo.
- **Histórico:** adicione ou edite sessões, filtre a lista, exclua e desfaça a exclusão mais recente. Use **Exportar CSV** para baixar o arquivo no celular. Apagar todo o histórico pede confirmação e cria backup.
- **Estatísticas:** escolha o período do gráfico, consulte os mais jogados e a lista pela atividade recente, filtre por status e exporte o resumo CSV. Excluir o histórico de um jogo também exige confirmação e backup.
- **Zerados:** selecione o ano e registre campanhas, DLCs, experiências, novas jogadas, data, observações e tempo adicional de platina. A lista continua independente do histórico. Importe TXT com conferência dos registros ou exporte o ano para o celular.
- **Configurações:** altere tema, idioma, exibição de capas e ícones e verificação automática de versões. Busque imagens em lote ou envie uma imagem do celular, confira a prévia e importe. Crie backups no PC, baixe uma cópia no telefone e confira um backup antes de restaurar; escolha o destino das sessões abertas quando solicitado. Arquivos de sessões do contador independente também podem ser importados com revisão.

Em Configurações, os aparelhos lembrados podem ter o acesso removido individualmente. **No computador** abre a pasta de dados no PC ou prepara uma cópia isolada do perfil atual para revisão, sem transferir a pasta para o celular. A recuperação de sessões pendentes permite salvar ou descartar o tempo antes de continuar.

**Atualizar pelo controle:** em **Configurações → Sempre em dia**, verifique a versão, baixe e confirme **Instalar e reiniciar**. A instalação acontece no computador usando o atualizador do pacote oficial, com validação e backup. O app do PC fecha e reinicia; depois, ative o controle novamente no PC. A execução pelo código-fonte permite consultar versões, mas a instalação integrada depende do pacote oficial.

As preferências alteradas pelo telefone também mudam no PC. Se os dados mudarem enquanto um formulário estiver aberto, confira a versão atual antes de tentar salvar novamente. Uma janela de edição aberta no computador pode precisar ser concluída para liberar a operação. Após atualizar o aplicativo, **recarregue a página do controle no celular**.

QR Code e código expiram em cinco minutos. Gere um novo código se necessário; isso desconecta todos os aparelhos pareados, inclusive os lembrados. **Desconectar este celular** revoga somente o acesso daquele navegador. O servidor começa desativado em cada abertura do app.

O painel tem favoritos, imagens que respeitam as preferências do PC e o modo **Jogando agora**, com os controles grandes no início da tela. Ao encerrar, o resumo mostra o tempo salvo e o acumulado do jogo. Em **Atalho na tela inicial**, veja como deixar o endereço do controle à mão.

**Lembrar este aparelho** é opcional e vale por até 30 dias. Use em um celular seu e em uma rede de confiança. Depois de ativar a conexão no computador, o navegador pode reconectar sem digitar outro código. O endereço usa uma porta estável; se o IP do PC mudar, abra o novo endereço e pareie novamente. Em Configurações, **Aparelhos lembrados → Remover acesso** revoga somente o aparelho escolhido. Desativar ou fechar o app não apaga esses aparelhos, mas impede o controle enquanto a conexão estiver desligada. Tokens temporários ficam na memória; o arquivo de aparelhos contém somente hashes, fora das cópias de dados e dos backups.

O controle usa HTTP apenas na rede local. Use uma rede de confiança e não encaminhe portas do roteador. Fechar o app desconecta os aparelhos. Desativar a conexão pelo PC ou perder o Wi-Fi do celular não para a contagem; reconecte para consultar o estado real e encerrar a sessão. Para jogar sem o computador ligado, use o contador independente abaixo.

**Se não abrir:** confira o endereço atual nas Configurações, selecione a interface correta e confirme que o firewall permite o HorasJogadas em redes privadas. Redes de convidados ou com isolamento entre aparelhos podem bloquear a comunicação. Trocar de rede ou mover o PC para outra conexão exige desativar, atualizar as redes e ativar novamente. Não é necessário alterar os dados nem configurar o PS5.

## Jogar com o PC desligado

Em **Configurações → Jogar com o PC desligado → Preparar contador no celular**, escaneie o QR Code do contador independente. Ou abra [o contador do celular](https://joaoppolli.github.io/HorasJogadas/celular/) diretamente. Abra uma vez com internet e espere **Pronto para usar offline**. No Android, use Instalar ou Adicionar à tela inicial; no iPhone, abra no Safari e use Compartilhar → Adicionar à Tela de Início.

Escolha um nome de jogo e inicie. O contador continua ao bloquear a tela, permite pausas e recupera a sessão ao recarregar. Os dados ficam no navegador do celular, independentemente do PC. Duas abas não podem editar a sessão ao mesmo tempo. Se detectar uma mudança grande no relógio, o app pede para conferir o tempo antes de salvar.

Em **Personalizar e preparar**, escolha o tema e idioma, importe uma biblioteca e, se o navegador permitir, peça proteção do armazenamento local. A biblioteca pode ser exportada nas Configurações do PC ou em **Exportar biblioteca** no controle local. Importá-la não apaga jogos nem sessões anteriores do celular.

Depois de encerrar, marque as sessões desejadas e toque em **Exportar selecionadas**. Envie o arquivo JSON para o PC pelo meio que preferir. No app do computador, abra **Configurações → Jogar com o PC desligado → Importar sessões do celular**, confira as datas, durações e jogos de destino e importe somente o que desejar. A prévia não altera registros; cancelar preserva tudo. A importação cria um backup verificado e não duplica sessões que já entraram antes, mesmo que você as tenha editado no PC.

Exportar mantém a cópia no celular. Guarde o arquivo antes de limpar os dados do navegador ou trocar de aparelho. O modo independente não usa conta, nuvem nem envia suas sessões pela internet. A transferência é revisada por arquivo; o controle local e o contador offline não fundem sessões automaticamente.

## Rolar páginas com o botão central

Clique na roda do mouse sobre o conteúdo de uma página ou lista e solte. Mova o mouse para cima ou para baixo para controlar a direção e a velocidade: quanto mais distante do ponto do clique, mais rápido. Clique novamente ou pressione **Esc** para parar.

Também é possível segurar a roda, mover e soltar para encerrar a rolagem. Sair da janela, mudar de página ou abrir outra janela interrompe o modo. Campos de texto mantêm o comportamento normal do botão central, inclusive a colagem no Linux.

## Histórico

Consulte as sessões, filtre por jogo e período, edite ou exclua registros e exporte CSV. Edições atualizam os totais da biblioteca e das estatísticas.

## Estatísticas

O gráfico mostra as horas dos cinco jogos mais jogados. A lista de jogos abaixo segue a atividade mais recente e mostra total, quantidade de sessões, primeira e última sessão. Excluir o histórico de um jogo remove suas sessões; confirme com cuidado e mantenha backups.

## Zerados por ano

Esta lista é independente dos cronômetros e do histórico. Selecione o ano e consulte os meses. Adicione ou edite campanhas concluídas, datas, duração, observações, DLCs, experiências e tempo adicional de platina. **Nova jogada** registra outra conclusão sem substituir a anterior.

O resumo anual soma os valores informados: jogos e DLCs concluídos, duração registrada e platina adicional. Tempo desconhecido não vira duração inventada. Importe TXT com prévia e exporte cada ano para guardar uma cópia legível. É possível desfazer a exclusão mais recente enquanto essa opção estiver disponível.

## Aparência e idioma

Em **Configurações**, escolha **Escuro minimalista**, **Original** (cinza e roxo do app anterior), **Violeta** ou **Claro**. A barra de título acompanha o tema em versões compatíveis do Windows. Idiomas disponíveis: português e inglês.

## Dados, backups e recuperação

Windows: `%APPDATA%\HorasJogadas`. Linux: `~/HorasJogadas`. Não mova nem apague essa pasta durante uma atualização.

Na primeira abertura de cada nova versão oficial, os arquivos existentes são copiados e conferidos por SHA-256 antes do carregamento. O backup fica em uma pasta vizinha `HorasJogadas-Backups-de-Versao/<versão-data>/`: `data/` guarda os arquivos e `manifest.json` guarda as somas. Falhas interrompem a abertura antes de carregar os registros.

Em Configurações, crie backups completos, valide-os e restaure quando necessário. Restaurar substitui o estado atual; o app cria uma cópia preventiva. Para uma cópia manual, feche o app e copie **toda a pasta de dados**, incluindo `zerados.json` e arquivos de sessão pendente.

Não abra versões antigas e novas ao mesmo tempo na mesma pasta: o bloqueio de instância impede a escrita concorrente. Revisões usam uma cópia separada. Partidas feitas nela não voltam automaticamente para o histórico oficial.

## Problemas

Informe a versão, o sistema e os passos em uma [issue](https://github.com/JoaoPPolli/HorasJogadas/issues). O arquivo `app.log` pode ajudar, mas revise informações pessoais antes de compartilhar. Não envie sua pasta de dados publicamente.

## Capas na biblioteca

As capas são opcionais e começam desativadas. Em Configurações, ative **Exibir capas na biblioteca** e salve. Desativar restaura os cartões compactos e preserva as imagens salvas.

Abra **Gerenciar capas** e use **Buscar capas dos jogos marcados**. Jogos sem imagem começam marcados. Confira os resultados: o app seleciona automaticamente apenas correspondências seguras e permite escolher manualmente os demais títulos, ajustar a busca por jogo, ver uma prévia e importar as imagens selecionadas em lote.

Escolha **Todas as fontes**, **Steam**, **GOG** ou **Wikipedia**. A busca tenta reconhecer erros de digitação, compara títulos e consulta novamente as lojas quando encontra uma correção. Você confere o jogo e a fonte antes de importar; jogos parecidos e sequências incertas precisam de escolha manual. As fontes não exigem conta nem chave. Só os títulos pesquisados e as tentativas de correção são enviados; tempos e histórico ficam locais. A arte de alta qualidade é obtida pela URL oficial do jogo e guardada localmente para uso offline. Jogos ausentes do catálogo podem receber uma imagem JPG/PNG/WebP local.

Clicar na capa ou usar o menu do cartão abre a troca de imagem. Remover uma capa não remove o jogo nem suas sessões. Backups completos incluem as imagens referenciadas e as preferências; backups antigos de registros continuam compatíveis.


## Ícones no lugar das iniciais

Abra **Configurações → Gerenciar ícones** ou clique no quadrado de iniciais do cartão. Também existe **Escolher ou trocar ícone** no menu de cada jogo. Busque os jogos marcados, confira as sugestões da Steam e GOG, veja a prévia quadrada e importe os escolhidos. São ícones próprios do jogo; a busca não recorta as capas para simular ícones. Se a fonte não tiver um ícone, tente a outra fonte ou escolha uma imagem local, inclusive PNG transparente.

Capas e ícones são independentes: os ícones funcionam no visual compacto. Desative **Exibir ícones dos jogos** e salve para voltar às iniciais sem apagar as imagens. Remover um ícone não afeta capa, jogo, histórico nem cronômetro. As imagens ficam em `icons/` na pasta de dados, e os backups completos incluem seus arquivos e índice. As capas existentes continuam em `covers/`.

## Inicialização automática

Em **Configurações → Inicialização**, escolha **Abrir HorasJogadas ao entrar no computador** e/ou **Ativar controle pelo celular ao abrir o app** e clique em **Salvar**. As opções começam desativadas e valem para a edição oficial. O início com o sistema vale para o usuário atual no Windows e Linux, sem administrador; desmarque e salve para remover. Mantenha a pasta do programa no mesmo lugar.

O controle usa a última rede escolhida quando disponível, ou outra rede local ativa. Se a rede ainda estiver iniciando, tenta novamente por até um minuto. Celulares lembrados podem reconectar; aparelhos novos precisam parear. O PC precisa estar ligado e acordado. As mesmas opções estão nas Configurações do painel conectado.

## Widget para OBS

Em **Configurações → Widget para OBS**, marque **Ativar widget do OBS neste computador**, escolha o jogo, o tempo exibido e a aparência, e clique em **Salvar**. **Seguir o cronômetro em execução** acompanha o último jogo iniciado ou retomado; você também pode fixar um jogo. Escolha entre sessão atual e tempo total (histórico mais a sessão aberta).

Clique em **Copiar link para o OBS**. No OBS Studio, adicione **Fontes → + → Navegador**, cole o link e configure **600 × 180** pixels, ou **600 × 240** com o nome do jogo. Preserve o CSS padrão do OBS para o fundo transparente. A opção **Abrir prévia** mostra o resultado no navegador. Ajuste o tamanho da fonte na cena do OBS.

O padrão é branco e Minimalista. Arcade e Digital são alternativas; todos aceitam cor no formato `#RRGGBB`. As alterações aparecem sem recadastrar a fonte. O timer pausa e retoma junto com o app, sem reiniciar horas ao completar um dia. Se o app fechar ou a conexão falhar, o widget fica oculto em poucos segundos e volta ao reconectar.

O app e o OBS devem estar **no mesmo computador**, Windows ou Linux. A conexão é local e somente de leitura, sem controle de gravação ou transmissão. Não depende do controle pelo celular. O link continua válido ao reabrir o app; quando habilitado, o widget inicia junto com a edição oficial. A cópia de revisão só ativa o widget manualmente. A chave local não é exportada nos backups.

## Calcular a platina adicional

Em **Zerados → Editar**, confira a **Duração** de quando zerou, escolha o **Contador do jogo** correspondente e clique em **Usar tempo extra**. Com 16h ao zerar e 20h35 no contador, a prévia preenche 4h35 em **Platina adicional**. O total inclui a sessão aberta. Clicar novamente substitui o valor pela diferença atual, sem duplicar horas. Clique em **Salvar** para confirmar ou **Cancelar** para descartar.

Ao terminar os troféus, marque **Platina concluída** e salve. O botão de cálculo fica bloqueado, preservando o tempo da platina se você jogar mais depois. Você pode corrigir o valor manualmente ou desmarcar a opção para recalcular. A função também está no controle conectado pelo celular.

Se houver várias conclusões do mesmo contador, informe o extra manualmente para não misturar campanhas. Confira o contador e a duração se o total for menor que o tempo ao zerar; o valor existente permanece preservado. Os metadados de vínculo e platina concluída acompanham os backups completos; a exportação TXT continua no formato de tempos já existente.

## Retrospectiva e página do jogo

Em **Estatísticas → Retrospectiva**, escolha o ano e o mês (ou **Ano inteiro**), confira a prévia e use **Salvar imagem PNG**. A imagem tem 1080 × 1350 pixels e segue o tema e idioma do app. Ela contém jogos e tempos pessoais: confira a prévia antes de compartilhar. A exportação acontece no seu dispositivo, sem envio automático. Somente sessões salvas entram nas horas; conclusões são contadas separadamente, sem somar novamente duração de campanha ou platina. Sessões que atravessam meses e anos são distribuídas conforme os dias registrados.

Na biblioteca, clique no nome do jogo ou use **Mais ações → Página do jogo**. A página reúne o timer, tempo salvo, sessões, média, primeira/última partida e conclusões com platina e observações. Mostra as últimas 100 sessões; o histórico completo continua disponível em Histórico. No PC, duplo clique numa sessão abre sua edição.

Na **Página do jogo → Retrospectiva do jogo**, a imagem contém somente as sessões salvas daquele jogo no período escolhido: tempo, sessões, dias jogados, média e maior sessão, além da evolução por mês ou por dia. A primeira e a última data também se referem ao período. O nome do jogo aparece na imagem e no arquivo PNG. A retrospectiva geral continua em Estatísticas.

Os detalhes e as duas retrospectivas também estão no controle conectado: menu do jogo → **Página do jogo → Retrospectiva do jogo**, ou **Estatísticas → Retrospectiva** para todos os jogos, com download do PNG.

## Detecção automática de jogos

Na página do jogo ou em **Configurações → Detecção automática de jogos**, escolha **Configurar detecção**. Selecione o executável real do jogo, marque **Detectar este jogo automaticamente** e salve. Não selecione Steam, outro launcher ou o próprio HorasJogadas. O modo **Caminho exato** é o recomendado para Windows e jogos Linux nativos. No Wine/Proton, o modo **Nome do executável** oferece uma alternativa; use um nome específico para evitar ambiguidades. Nem todo launcher ou ambiente restringido permite identificar o processo; nesses casos, use o contador manual.

O HorasJogadas precisa ficar aberto. A consulta ocorre em segundo plano a cada 2 segundos; o fechamento é confirmado em duas verificações. A contagem começa quando o processo é observado, sem inventar tempo anterior à abertura do app. Vários processos do mesmo jogo pertencem à mesma sessão; ela só é salva quando todos fecham.

A detecção só encerra contadores que ela mesma iniciou. Pausar ou encerrar manualmente impede um novo início enquanto o mesmo jogo continuar aberto. Ajustes de tempo continuam sendo incluídos no salvamento automático. Sessões já abertas ou pausadas não são sobrescritas. Ao desativar a detecção, o contador atual continua disponível para controle manual.

O controle geral nas Configurações permite suspender a detecção sem esquecer os vínculos. No celular, você pode ativar/desativar um vínculo já configurado; a seleção do executável é feita no PC. Nenhuma lista de processos é enviada à rede ou salva em relatórios. A função começa desativada e cópias de revisão nunca iniciam a consulta automaticamente.

## Rolagem e seletores

A roda do mouse rola o conteúdo sem trocar o valor de seletores, anos, datas ou campos numéricos. Com a lista aberta, a roda navega pelas opções; clique para confirmar. Botões, digitação e navegação por teclado continuam disponíveis. Na página do jogo, o banner preserva a proporção da imagem e mostra a arte inteira, inclusive em janelas largas.
