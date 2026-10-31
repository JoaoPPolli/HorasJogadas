# Guia de uso — HorasJogadas 3.0

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

A página usa o tema e o idioma escolhidos no app. Também permite adicionar jogos. Bloquear a tela do celular não pausa o cronômetro: ele roda no PC. Ao retornar ao navegador, a página sincroniza antes de aceitar comandos; comandos com um estado antigo são recusados, sem substituir uma alteração feita no computador. Toques repetidos no mesmo pedido não duplicam sessões.

QR Code e código expiram em cinco minutos. Gere um novo código se necessário; isso desconecta todos os aparelhos pareados. **Desconectar este celular** revoga somente o acesso daquele navegador. As credenciais ficam na memória e o servidor começa desativado em cada abertura do app.

O controle usa HTTP apenas na rede local. Use uma rede de confiança e não encaminhe portas do roteador. Fechar o app desconecta os aparelhos. Desativar a conexão pelo PC ou perder o Wi-Fi do celular não para a contagem; reconecte para consultar o estado real e encerrar a sessão. Este recurso não permite usar o contador com o PC desligado.

**Se não abrir:** confira o endereço atual nas Configurações, selecione a interface correta e confirme que o firewall permite o HorasJogadas em redes privadas. Redes de convidados ou com isolamento entre aparelhos podem bloquear a comunicação. Trocar de rede ou mover o PC para outra conexão exige desativar, atualizar as redes e ativar novamente. Não é necessário alterar os dados nem configurar o PS5.

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

Na primeira abertura da versão 3.0, os arquivos existentes são copiados e conferidos por SHA-256 antes do carregamento. O backup fica em uma pasta vizinha `HorasJogadas-Backups-de-Versao/<versão-data>/`: `data/` guarda os arquivos e `manifest.json` guarda as somas. Falhas interrompem a abertura antes de carregar os registros.

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
