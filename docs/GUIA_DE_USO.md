# Guia de uso — HorasJogadas 3.0

## Instalar e atualizar

Use a [página de download](https://joaoppolli.github.io/HorasJogadas/). No Windows, o instalador cria um atalho no menu Iniciar; o ZIP portátil deve ser extraído por inteiro. Nenhum dos pacotes precisa de Python.

No Linux x86_64, extraia o `.tar.gz`, abra um terminal na pasta e execute `./HorasJogadas`. É necessária uma sessão gráfica. Em Ubuntu 22.04 ou superior, se faltar alguma biblioteca Qt/X11, instale:

```bash
sudo apt-get install libegl1 libxkbcommon-x11-0 libxcb-cursor0 libxcb-xinerama0
```

Os pacotes não são assinados digitalmente. Baixe somente das Releases oficiais. Atualizações são feitas por um novo instalador ou por extração em uma pasta nova. Feche o app antigo antes. A desinstalação remove o aplicativo, sem remover os registros pessoais.

## Biblioteca e cronômetros

Clique em **Adicionar jogo**. Use busca, filtros de status e ordenação para organizar os cartões. No cartão, **Iniciar** começa uma sessão, **Pausar** interrompe a contagem e **Parar** salva a sessão no histórico.

O menu do cartão permite renomear, ajustar o tempo, trocar status e excluir. O ajuste de tempo aceita horas, minutos e segundos, valores negativos para remover e atalhos de +5, +10, +15 e +30 minutos. Confira o valor antes de confirmar. Dê dois cliques no tempo para abrir o ajuste.

`Ctrl+F` abre a busca; `Esc` limpa o filtro. Se uma sessão ficou pendente depois de um encerramento inesperado, o app oferece a recuperação na próxima abertura.

## Histórico

Consulte as sessões, filtre por jogo e período, edite ou exclua registros e exporte CSV. Edições atualizam os totais da biblioteca e das estatísticas.

## Estatísticas

O gráfico mostra as horas dos cinco jogos mais jogados. A lista de jogos abaixo segue a atividade mais recente e mostra total, quantidade de sessões, primeira e última sessão. Excluir o histórico de um jogo remove suas sessões; confirme com cuidado e mantenha backups.

## Zerados por ano

Esta lista é independente dos cronômetros e do histórico. Selecione o ano e consulte os meses. Adicione ou edite campanhas concluídas, datas, duração, observações, DLCs, experiências e tempo adicional de platina. **Nova jogada** registra outra conclusão sem substituir a anterior.

O resumo anual soma os valores informados: jogos e DLCs concluídos, duração registrada e platina adicional. Tempo desconhecido não vira duração inventada. Importe TXT com prévia e exporte cada ano para guardar uma cópia legível. É possível desfazer a exclusão mais recente enquanto essa opção estiver disponível.

## Aparência e idioma

Em **Configurações**, escolha **Escuro minimalista** ou **Original**, inspirado no cinza e roxo do app anterior. A barra de título acompanha o tema em versões compatíveis do Windows. Idiomas disponíveis: português e inglês.

## Dados, backups e recuperação

Windows: `%APPDATA%\HorasJogadas`. Linux: `~/HorasJogadas`. Não mova nem apague essa pasta durante uma atualização.

Na primeira abertura da versão 3.0, os arquivos existentes são copiados e conferidos por SHA-256 antes do carregamento. O backup fica em uma pasta vizinha `HorasJogadas-Backups-de-Versao/<versão-data>/`: `data/` guarda os arquivos e `manifest.json` guarda as somas. Falhas interrompem a abertura antes de carregar os registros.

Em Configurações, crie backups completos, valide-os e restaure quando necessário. Restaurar substitui o estado atual; o app cria uma cópia preventiva. Para uma cópia manual, feche o app e copie **toda a pasta de dados**, incluindo `zerados.json` e arquivos de sessão pendente.

Não abra versões antigas e novas ao mesmo tempo na mesma pasta: o bloqueio de instância impede a escrita concorrente. Revisões usam uma cópia separada. Partidas feitas nela não voltam automaticamente para o histórico oficial.

## Problemas

Informe a versão, o sistema e os passos em uma [issue](https://github.com/JoaoPPolli/HorasJogadas/issues). O arquivo `app.log` pode ajudar, mas revise informações pessoais antes de compartilhar. Não envie sua pasta de dados publicamente.
