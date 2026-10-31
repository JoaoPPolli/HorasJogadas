<div align="center">

# HorasJogadas

**Cada partida conta. Guarde a sua história.**

Cronômetros, biblioteca, histórico, estatísticas e jogos zerados. Interface em português e inglês, com dados no seu computador.

[**Baixar o aplicativo**](https://joaoppolli.github.io/HorasJogadas/) · [Todos os downloads](https://github.com/JoaoPPolli/HorasJogadas/releases/latest) · [Changelog](https://joaoppolli.github.io/HorasJogadas/changelog/) · [Guia de uso](docs/GUIA_DE_USO.md)

</div>

![Biblioteca do HorasJogadas 3.0 com o tema Original](site/assets/library.png)

## Instalar

**Windows 10/11 de 64 bits:** [baixe o instalador](https://github.com/JoaoPPolli/HorasJogadas/releases/latest/download/HorasJogadas-Windows-Setup.exe), abra e siga as instruções. O app aparece no menu Iniciar. Não precisa instalar Python nem executar como administrador.

Prefere sem instalação? [Baixe o ZIP portátil](https://github.com/JoaoPPolli/HorasJogadas/releases/latest/download/HorasJogadas-Windows-Portable.zip), extraia **a pasta inteira** e abra `HorasJogadas.exe` dentro dela.

**Linux x86_64, Ubuntu 22.04 ou compatível:** [baixe o pacote](https://github.com/JoaoPPolli/HorasJogadas/releases/latest/download/HorasJogadas-Linux-x86_64.tar.gz), extraia e execute `./HorasJogadas` dentro da pasta extraída, em uma sessão gráfica. Não precisa de Python. Dependências de sistema estão no [guia de uso](docs/GUIA_DE_USO.md).

Ao abrir o pacote oficial no Linux, o app registra seu ícone e um atalho no menu de aplicativos do usuário, sem sudo. O lançador associa a janela ao ícone no X11 e no Wayland. Se mover a pasta do programa, abra o executável uma vez na nova localização para atualizar o atalho.

Os executáveis não possuem assinatura digital. O Windows pode exibir uma verificação ao abrir um download novo. Os arquivos oficiais estão nas Releases deste repositório; os [SHA-256](https://github.com/JoaoPPolli/HorasJogadas/releases/latest/download/SHA256SUMS.txt) permitem conferir a integridade.

## Já usava a versão anterior?

1. Feche o app antigo antes de abrir o novo.
2. Instale ou extraia a versão 3.4.0.
3. Abra o HorasJogadas: ele usa a **mesma pasta de dados**, sem precisar importar nada.

Antes de carregar registros existentes pela primeira vez, a nova versão cria uma cópia verificada de todos os arquivos de dados em uma pasta vizinha chamada `HorasJogadas-Backups-de-Versao`. Se essa cópia falhar, a abertura é interrompida. Não apague sua pasta de dados.

| Sistema | Dados oficiais |
| --- | --- |
| Windows | `%APPDATA%\HorasJogadas` |
| Linux | `~/HorasJogadas` |

As partidas feitas na **cópia para revisão** continuam separadas: elas não são mescladas automaticamente aos registros oficiais. O instalador e o desinstalador não removem os registros pessoais.

## O que há no app

- Biblioteca com busca, filtros, status e ordenação manual.
- Rolagem automática com o botão central: clique na roda sobre uma página ou lista e mova o mouse para cima ou para baixo. Quanto mais longe do ponto inicial, mais rápido; outro clique ou Esc para parar. Também permite segurar a roda, mover e soltar para encerrar.
- Cronômetros com pausa, recuperação de sessões e ajustes de tempo, inclusive valores negativos e atalhos de minutos.
- Histórico com edição e exportação CSV.
- Estatísticas com jogos ordenados pela sessão mais recente e gráfico dos cinco mais jogados.
- Zerados por ano e mês, campanhas, DLCs, novas jogadas, observações e horas adicionais de platina; importação e exportação TXT.
- Quatro temas: **Escuro minimalista**, **Original** (a paleta roxa da edição anterior), **Violeta** e **Claro**; barra de título nativa escura no Windows compatível.
- Português e inglês, backups completos, restauração e bloqueio para impedir duas instâncias de alterarem a mesma pasta.

## Controle pelo celular

Em **Configurações → Controle pelo celular**, selecione a rede do PC e clique em **Ativar controle pelo celular**. Escaneie o QR Code com a câmera do telefone. Como alternativa, abra o endereço mostrado e digite o código de seis dígitos; QR Code e código expiram em cinco minutos. Não precisa instalar um app no celular.

O painel segue o tema e o idioma do computador. Permite buscar e adicionar jogos, iniciar, pausar, retomar e encerrar sessões. Os comandos usam os mesmos cronômetros e o histórico do PC; bloquear o telefone não interrompe a contagem. Uma sessão só entra no histórico quando você a encerra.

O PC precisa permanecer **ligado, acordado e com o app aberto**, na mesma rede do celular. Use uma rede de confiança: o controle usa HTTP local, sem servidor na nuvem nem abertura de portas no roteador. Se houver várias interfaces de rede, escolha a do Wi-Fi ou cabo que conecta o PC ao celular. Confira o firewall em redes privadas se a página não abrir.

A conexão começa **desativada** a cada abertura do app. Desativá-la não para os cronômetros; **Novo código e desconectar aparelhos** revoga os acessos atuais. Fechar o aplicativo também encerra a conexão. O pareamento não vai para arquivos, backups ou logs. [Guia e solução de problemas](docs/GUIA_DE_USO.md#controle-pelo-celular).

## Capas opcionais

Em **Configurações**, marque **Exibir capas na biblioteca** e salve. A opção começa desativada: o visual compacto continua disponível e desligar as capas não apaga as imagens nem altera seus registros.

Em **Gerenciar capas**, clique em **Buscar capas dos jogos marcados**, confira os títulos sugeridos e escolha **Importar selecionadas**. A busca reúne Steam, GOG e Wikipedia, sem login ou chave de API. Você pode escolher todas as fontes ou uma só. Nomes com erros de digitação são comparados com títulos reconhecidos e pesquisados novamente; correspondências incertas e sequências parecidas precisam de seleção manual; você pode ajustar o texto da busca sem renomear o jogo.

As imagens de alta qualidade são baixadas de uma vez e ficam no computador, funcionando depois sem internet. Só os títulos pesquisados e suas tentativas de correção são enviados às fontes selecionadas, por sua iniciativa. Na busca em todas as fontes, a Wikipedia também ajuda a reconhecer os nomes. Jogos fora do catálogo podem usar uma imagem local. Os backups completos incluem as capas e a preferência de exibição.

## Ícones dos jogos

Em **Configurações → Gerenciar ícones**, busque em lote, confira a prévia e importe os ícones oficiais da Steam ou GOG. Você também pode clicar no quadrado das iniciais ou usar **Escolher ou trocar ícone** no menu do jogo. Uma imagem local é outra opção.

Os ícones substituem as iniciais e funcionam mesmo com capas desativadas. Em **Configurações → Exibir ícones dos jogos**, desmarque e salve para voltar às iniciais sem apagar as imagens. Jogos sem ícone continuam usando as iniciais. Capas e ícones são independentes, funcionam offline depois de importados e acompanham os backups completos. Não há busca automática de imagens ao abrir ou rolar a biblioteca.

## Atualizar

Abra **Configurações → Verificar atualizações**, baixe o pacote e escolha **Instalar e reiniciar**. O app confere o SHA-256 e cria um backup antes de fechar. No Windows, o instalador atualiza a pasta em uso; no Linux, o novo pacote passa por autoteste e a pasta anterior é preservada. A consulta automática de versões pode ser desativada nas Configurações. Não há instalação automática sem confirmação. No Linux, arquivos pessoais que estiverem junto do executável também são preservados, e a versão 3.1 recupera a base caso a atualização 3.0.1 tenha movido a pasta de dados junto do programa. A versão 3.2.1 corrige o ambiente herdado no Linux, confirma a abertura da nova janela e tenta reabrir a versão anterior se a nova encerrar antes de ficar pronta. O ciclo de atualização é testado também em Arch Linux. Erros ficam em `~/.cache/HorasJogadas/updates/v<versão>-<identificador>/update.log` (ou na pasta de cache configurada pelo sistema). A versão 3.0.0 precisa ser atualizada manualmente uma vez para receber esse recurso.

## Executar pelo código

Python 3.10 a 3.13, em uma sessão gráfica:

```bash
git clone https://github.com/JoaoPPolli/HorasJogadas.git
cd HorasJogadas
python -m venv .venv
# Windows: .venv\Scripts\activate
# Linux: source .venv/bin/activate
python -m pip install -r requirements-qt.txt
python app_qt.py
```

No Windows, `Iniciar.bat` prepara um ambiente `.venv_qt` e inicia a edição oficial. `IniciarNovaInterface.bat` continua disponível para abrir uma cópia isolada para revisão.

O lançador antigo `app.py` e o domínio `horas_jogadas/` foram preservados para compatibilidade. A interface oficial agora usa **PySide6/Qt**.

## Desenvolvimento

[Ambiente, testes e empacotamento](docs/DESENVOLVIMENTO.md) · [Modo de revisão](REVISAO_QT.md) · [Mudanças](CHANGELOG.md) · [Colaboração](COLABORACAO.md)

As capturas deste repositório e do site usam dados fictícios. Para relatar um problema, informe versão, sistema e passos para reproduzir, removendo dados pessoais dos anexos.
