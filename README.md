# Registro de Horas Jogadas

App de desktop (Python + Tkinter, sem dependências externas) para cronometrar e registrar horas jogadas.

## Executar
```
python app.py
```

## Pintura dos blocos (2.6.3)

Dashboard, histórico e zerados desenham seus blocos completos em uma superfície
única. Fundos, títulos, informações e ações se movem juntos, sem remontar controles
filhos a cada rolagem. A página é apresentada depois de concluir o desenho, em vez
de exibir lotes de blocos chegando separadamente.

Os botões desenhados aceitam clique, Tab/Shift+Tab e Enter/Espaço. A área também
aceita as setas, Page Up/Down e Home/End. Os formulários de edição e os dados salvos
mantêm o mesmo funcionamento.

## Rolagem suave (2.6.2)

A roda do mouse agora move as listas em pixels, com transição curta e suave.
Gráficos e textos não recalculam o layout apenas porque a lista foi rolada.
Na versão 2.6.3 a montagem em lotes foi substituída por um desenho único das
páginas para eliminar a apresentação fragmentada.

Instale pelo mesmo botão **Configurações → Atualizar app…**. Os formatos dos
dados e o funcionamento dos cronômetros permanecem compatíveis.

## Zerados por ano (2.6.0)

Abra **🏆 Zerados** ao lado de Histórico e Dash. Escolha o ano para ver as conclusões
agrupadas pelo mês em que terminou. Adicione ou edite nome, ano/mês, dia opcional,
tempo para zerar, horas **adicionais** para platinar, tipo e observações.
O campo de tempo aceita `13h45m`, `40min` ou `01:30:00`; vazio significa desconhecido.

- Ao mudar um cronômetro para **Zerado**, o app copia o nome, a data atual e o tempo
  total (incluindo a sessão aberta) para a lista. Não para nem salva a sessão por conta própria.
- O registro é independente: edições e exclusões na lista não alteram cronômetros,
  sessões, histórico ou dashboard. Alterações posteriores no cronômetro também não
  reescrevem conclusões já registradas.
- Cada cronômetro gera uma entrada automática uma vez. Alternar seu status, inclusive
  após excluir ou desfazer a entrada, não cria duplicatas. Use **Nova jogada** na lista
  para outra campanha e informe o tempo daquela jogada.
- Jogos que já estavam zerados antes do update não recebem uma data inventada.
  Use a importação ou adicione-os manualmente.
- Platina tem duração adicional: 6h35m para zerar + 8h30m para platinar = 15h05m.
  Uma anotação “Platina” sem duração adicional continua sendo apenas uma observação.
- **Importar TXT…** aceita vários arquivos, UTF-8, UTF-16 ou ANSI do Windows, com
  título `ZERADOS EM 2024`, meses como `Março:` e entradas `-Jogo * 13h45m`.
  O ano também pode vir do nome do arquivo ou ser informado. Revise a prévia, edite
  linhas não reconhecidas e selecione as que deseja importar. Repetidos são ignorados.
  Datas com apenas mês continuam sem dia. `(())` identifica experiências sem zerar.
- **Exportar TXT…** salva o ano selecionado. Linhas `@dia:` e `@nota:` preservam dia
  e observações na reimportação. O export não altera nenhum dado do aplicativo.

Tudo fica em `%APPDATA%\HorasJogadas\zerados.json`, com backup automático da gravação
anterior em `zerados.json.bak`. A lista tem armazenamento e recuperação próprios;
o botão de restaurar backups dos jogos/histórico não substitui a lista de zerados.
Para guardar uma cópia legível de cada ano, use **Exportar TXT…**.

Instale o ZIP de atualização em **Configurações → Atualizar app…**. O executável
existente continua compatível; não é necessário refazê-lo para a versão 2.6.0.

## Testes
```
python -m unittest discover -s tests -t .      # biblioteca padrão
pytest                                          # opcional (requirements-dev.txt)
```

## Estrutura
```
app.py                       lançador (o .exe é feito a partir dele; carrega horas_jogadas/)
build_exe.bat                cria o HorasJogadas.exe (só 1 vez)
Iniciar.bat                  abre o app sem o .exe (usa pythonw)
horas_jogadas/
  constants.py               constantes, cores, nomes de arquivos
  models.py                  dataclasses Jogo, Sessao, EstadoSessao
  storage.py                 Repositorio: escrita atômica, backup, leitura segura, migração
  stats.py                   estatísticas (funções puras)
  utils.py                   formatação e normalização de texto
  i18n.py                    traduções (Português do Brasil / English)
  main.py                    inicialização (chamada pelo lançador)
  updater.py                 atualização por ZIP, backup e restauração do código
  backups.py                 backups dos dados (diário, antes de apagar, manual)
  instancia.py               trava de instância única
  icone_barra.py             selo no ícone da barra de tarefas (🔴 rodando / ⏸ pausado)
  edicao_sessao.py           validação da edição/adição manual de sessões
  exportacao.py              exportação para CSV
  logging_setup.py           log em DATA_DIR/app.log (com rotação)
  ui/                        theme, widgets (ScrollableFrame), card, janela principal,
                             histórico, dashboard, configurações
tests/                       testes de storage, stats e utils
```

## Onde ficam os dados
`%APPDATA%\HorasJogadas` (Windows) ou `~/HorasJogadas`:

| Arquivo | Conteúdo |
|---|---|
| `cronometros.json` | biblioteca de jogos (com `id`, `nome`, `status`) |
| `registros.json` | sessões (`sessao_id`, `jogo_id`, `jogo`, `segundos`, `tempo`, `data`, `inicio`, `fim`) |
| `config.json` | modo de navegação, ordenação e idioma (`pt` ou `en`) |
| `backups/` | cópias dos dados: `diario/` (7 últimos dias), `antes_de_apagar/`, `manual/`, `antes_de_restaurar/` |
| `app.lock` | trava que impede abrir o app duas vezes ao mesmo tempo |
| `em_andamento.json` | sessões abertas, para recuperação após falha (some quando tudo é salvo) |
| `*.bak` | backup da versão anterior de cada arquivo |
| `*.pre-migracao` | cópia do arquivo original antes da migração para o formato novo |
| `*.corrompido-AAAAMMDD-HHMMSS` | cópia preservada de um arquivo que ficou ilegível |
| `app.log` | log de erros |

Arquivos do formato antigo (lista de nomes em `cronometros.json`, registros sem `jogo_id`) são migrados automaticamente na primeira abertura.

## Idioma
Em **Configurações → Idioma / Language** escolha Português (Brasil) ou English. A troca é imediata (sem reiniciar e sem
interromper cronômetros em andamento) e fica salva em `config.json`. Os dados em disco não mudam com o idioma
(ex.: o status continua gravado como `Zerado`), então os arquivos funcionam nos dois idiomas.

Para adicionar um idioma: inclua um código em `IDIOMAS_DISPONIVEIS` (`constants.py`) e um dicionário completo em
`TEXTOS` (`i18n.py`); `tests/test_i18n.py` falha se faltar alguma chave ou marcador.

## Instalação e atualizações

**Uma vez só** (para ter o `.exe`): dê dois cliques em `build_exe.bat`. Ele gera `HorasJogadas.exe` nesta mesma pasta.
(Se preferir não usar `.exe`, use `Iniciar.bat`.) Se houver um `icon.ico` na pasta, ele vira o ícone do app.

**Atualizar** (sempre que receber um ZIP novo):
1. Abra o app → **Configurações → Atualizar app…**
2. Escolha o ZIP baixado (a janela já abre na pasta Downloads).
3. Confirme. O app valida o arquivo, guarda a versão atual, troca o código e **reinicia sozinho**.

Você não apaga nem substitui nenhuma pasta. Seus jogos e histórico ficam em `%APPDATA%\HorasJogadas` e não são alterados.

- **Voltar atrás:** Configurações → **↩ Restaurar versão anterior** (guarda as 3 últimas, em `_versoes_anteriores/`).
- **Segurança:** o ZIP é validado antes (integridade, caminhos, arquivos obrigatórios e sintaxe de todos os `.py`).
  Se algo falhar durante a troca, tudo volta ao estado anterior. Se a versão nova nem abrir, o lançador oferece
  restaurar a anterior automaticamente.
- **Quando refazer o `.exe`:** só se o `app.py` (lançador) ou as bibliotecas do Python usadas mudarem. O teste
  `tests/test_launcher.py` avisa se o código passar a precisar de algo que o `.exe` não inclui.

## Segurança dos dados
- **Instância única:** abrir o app de novo não cria outra janela: a que já está aberta vem para a frente. (Duas janelas
  poderiam sobrescrever os dados uma da outra.)
- **Backups automáticos:** uma cópia por dia (guarda 7) e uma cópia **antes de qualquer exclusão em massa**
  (apagar todo o histórico ou os registros de um jogo).
- **Desfazer:** ao excluir uma sessão no Histórico aparece "↩ Desfazer" por 10 segundos.
- **Restaurar:** Configurações → **🗂 Backups…** lista as cópias (com jogos, sessões e horas) e restaura a escolhida.
  Antes de restaurar, os dados atuais também são guardados. Há ainda o botão "Criar backup agora".

## Exportar CSV
Configurações (ou a tela de Histórico) → **Exportar histórico (CSV)…** ou **Exportar resumo por jogo (CSV)…**.
Em português o arquivo usa `;` e vírgula decimal (abre certo no Excel do Brasil); em inglês, `,` e ponto.

## Ícone e selo na barra de tarefas
O app usa o `icon.ico` que estiver ao lado do `.exe` (ou embutido, na versão do itch.io) em todas as janelas.
Como no OBS, o botão do app na barra de tarefas do Windows ganha um **selo** sobre o ícone original:
**🔴 bolinha vermelha** = há um cronômetro rodando · **⏸ pause amarelo** = nenhum rodando, mas há um pausado ·
**sem selo** = nada ativo. (Se houver um rodando e outro pausado, vale o vermelho.) Só aparece no Windows.

## Sessões que atravessam a meia-noite
O gráfico "Horas jogadas" (e a sequência de dias) conta o tempo no dia em que ele foi **realmente jogado**: uma sessão
que começou na sexta às 19h e terminou no sábado às 3h tem a parte da sexta na sexta e a parte do sábado no sábado.
- **Sessões novas:** o app acumula o tempo por dia enquanto o cronômetro roda (inclusive ao contar uma pausa ou
  ajustar o tempo à mão, e na recuperação depois de uma queda) e grava o detalhe em `registros.json` (campo `dias`).
- **Sessões antigas** (sem o detalhe): se começaram e terminaram em dias diferentes (até 36 h de intervalo), o tempo é
  repartido proporcionalmente ao relógio de cada dia; se não há horário de início, ou o intervalo é maior, fica no dia em que terminou.

## Corrigir e adicionar sessões
- **Histórico → ✏️ Editar:** muda jogo, duração e término de qualquer sessão. Sessões acima de 12 h ganham o aviso
  "⚠ sessão muito longa: confira". **Histórico → ➕ Adicionar sessão** lança uma sessão manual com data (para quando
  você esqueceu de ligar o timer).
- **Dashboard → "Sessão mais longa" → ✏️ Editar sessão:** abre direto a sessão suspeita.
- Ao editar, o início passa a ser (término − duração) e o tempo é repartido pelos dias que esse intervalo toca.
- Durações acima de 24 h pedem confirmação, e o término não pode estar no futuro.
