# Desenvolvimento

A interface oficial é `app_qt.py` + `horas_jogadas_qt/`, com PySide6 6.8.3. O domínio, a persistência e a implementação Tkinter legada ficam em `horas_jogadas/`; `app.py` continua disponível para compatibilidade.

## Ambiente

Python 3.10–3.13 e sessão gráfica; os pacotes oficiais são construídos com Python 3.12:

```bash
python -m venv .venv
# Ative o ambiente conforme seu sistema.
python -m pip install -r requirements-qt.txt
python app_qt.py --demo
```

`--demo` usa somente dados fictícios. `--review` copia os dados atuais para uma pasta isolada. Sem essas opções, o app usa os registros oficiais e prepara o backup de primeira abertura. Não teste migrações na pasta pessoal real.

## Testes

```bash
python -m unittest discover -s tests -t .
QT_QPA_PLATFORM=offscreen python -m unittest discover -s tests_qt -t .
```

No PowerShell: `$env:QT_QPA_PLATFORM='offscreen'` antes do segundo comando. Os testes cobrem persistência, importação/exportação, cronômetros, paridade de recursos, renderização e preservação dos dados na transição oficial.

### Linux sem interface gráfica

Use `QT_QPA_PLATFORM=offscreen` para testes de widgets. Para validar o pacote executável com uma sessão X11 real:

```bash
sudo apt-get install xvfb xauth libegl1 libxkbcommon-x11-0 libxcb-cursor0 libxcb-xinerama0 libxcb-keysyms1 libxcb-shape0 libxcb-icccm4
xvfb-run -a python scripts/build_release.py
```

## Empacotamento no Windows

```bash
python -m pip install -r requirements-build.txt
python scripts/build_release.py
```

Ou use `build_exe.bat`. A saída fica em `dist/HorasJogadas` e `release/`. Preserve toda a pasta do executável. Para gerar o instalador, instale Inno Setup 6, defina `HORAS_VERSION=3.6.0` e compile `packaging/windows.iss`.

Cada pacote executa `--self-test <resultado.json>` com dados fictícios: abre as cinco telas, valida os assets, grava uma sessão e verifica que o domínio legado consegue relê-la. Esse teste não abre os registros pessoais.

Os builds são nativos, Windows x64 e Ubuntu 22.04 x64. Não há compilação cruzada nem pacote macOS nesta publicação. O workflow baixa os textos de licença oficiais para `build/legal` e os inclui no pacote.

## Testar o controle pelo celular

Os testes Qt exercitam o servidor HTTP real em loopback e as transações com perfis fictícios. O autoteste do executável também verifica os arquivos HTML/CSS/JS, a geração do QR Code, o pareamento, os comandos e uma sessão exata de três segundos no histórico, sem ler os registros pessoais. A conexão permanece desativada fora desses testes.

Para validar a interface no navegador, com Node.js 22 e as dependências Qt instaladas:

```bash
npm install --no-save --package-lock=false playwright@1.56.1
npx playwright install --with-deps chromium
node scripts/verify_phone_browser.cjs --python python --result build-diagnostics/phone-browser.json
node scripts/verify_phone_reconnect.cjs --python python --result build-diagnostics/phone-reconnect.json
node scripts/verify_phone_desktop_browser.cjs --python python --result build-diagnostics/phone-desktop-browser.json
node scripts/verify_phone_management_browser.cjs --python python --result build-diagnostics/phone-management-browser.json
node scripts/verify_companion_browser.cjs --python python --result build-diagnostics/companion-browser.json
```

O script cria um processo Qt com dados sintéticos e uma porta aleatória em `127.0.0.1`, testa comandos, desconexão, nomes com HTML, perda de rede, quatro temas, português/inglês e larguras de 320, 390 e 1040 pixels. `--screenshots <pasta>` salva capturas fictícias. O job `phone-browser` precisa passar antes da publicação. O servidor de produção não usa esse fixture nem permite controlar testes por arquivos.

O teste `verify_companion_browser.cjs` serve `site/celular` em uma origem local confiável e verifica o service worker, recarga offline, pausas, relógio, armazenamento e concorrência entre abas. O arquivo JSON exportado pelo navegador é importado e reimportado em um Controller temporário por `verify_phone_import.py`, verificando duplicatas e preservação de sessões. O contador independente usa HTTPS no GitHub Pages; ele transfere dados por arquivo revisado e não tenta acessar o servidor HTTP da LAN a partir da página HTTPS.

O controle conectado divide as operações em `phone_records.py` (histórico, estatísticas e zerados), `phone_management.py` (preferências, imagens, backups e importações) e `phone_desktop.py` (jogos, cronômetros, recuperação e ações no PC). `phone_control.py` valida revisões e coordena as transações do domínio. Uma alteração no computador invalida formulários antigos; pedidos repetidos têm recibo sem repetir a escrita. A busca de imagens e o atualizador usam tarefas em segundo plano; uploads maiores exigem uma sessão autenticada antes de receber o corpo.

Os testes `verify_phone_desktop_browser.cjs` e `verify_phone_management_browser.cjs` exercitam as cinco páginas, formulários, conflitos, importações, exportações, backups e preferências contra um processo Qt com dados fictícios. Downloads de imagens e consultas de versões usam respostas sintéticas nesse fixture. A instalação real continua coberta pelo ciclo nativo de atualização dos pacotes; testes do painel não instalam uma atualização na máquina de desenvolvimento. A matriz de recursos e adaptações está em [Controle conectado: paridade](CONTROLE_CELULAR_PARIDADE.md).

Aparelhos lembrados ficam em `.phone-devices.json`, com hashes e escrita atômica. Esse arquivo não acompanha backups, cópias de revisão ou commits. Os favoritos ficam nas preferências Qt e acompanham os backups normais. O cache do service worker contém apenas os arquivos públicos da interface; incremente sua versão ao alterar esses arquivos. Não use `skipWaiting` para substituir uma página durante uma sessão ativa.

## Release e site

O workflow `.github/workflows/release.yml` é acionado por tags `v*`, branches `release/**` ou execução manual. A versão vem de `horas_jogadas_qt/release.py`. Ambos os sistemas precisam passar testes e autoteste antes da publicação dos pacotes e dos SHA-256. Depois o site é publicado no GitHub Pages, com origem GitHub Actions.

```bash
python scripts/build_site.py
python -m http.server 8000 --directory build/site
```

O site usa assets locais e links estáveis `releases/latest/download/`. As capturas devem conter apenas dados fictícios. Não versionar `build/`, `dist/`, `release/`, diagnósticos nem dados pessoais.

## Widget OBS

`obs.py` reutiliza o transporte HTTP limitado do controle conectado em um servidor separado, preso ao loopback. As rotas expõem apenas HTML/CSS/JS e o estado do timer selecionado, sem operações de escrita. A chave em `.obs-key` permanece local e não acompanha backups ou cópias de revisão. `obs_card.py` configura o widget na interface Qt; os arquivos em `assets/obs` são incluídos pelo empacotamento.

Valide as regras do cronômetro e as rotas com `python -m unittest tests_qt.test_obs`. `node scripts/verify_obs_browser.cjs --python python` verifica transparência, padrão branco, estilos, pausa, reconexão e independência do controle pelo celular no Chromium. O autoteste nativo também confere os assets e o endpoint autorizado dentro do pacote.

## Platina adicional

O cálculo compartilhado em `horas_jogadas_qt/platinum.py` é somente de leitura: usa o total salvo do contador mais a sessão aberta, subtraindo a duração da conclusão. O formulário confirma a gravação. Referências ambíguas e múltiplas conclusões do mesmo contador exigem conferência manual; nunca tente deduzir a campanha por aproximação de nome.

`Conclusao.platina_concluida` e `jogo_id` são serializados em metadados na raiz de `zerados.json`, mantendo os registros individuais legíveis por versões anteriores. Preserve esses campos ao desfazer exclusões, editar e restaurar backups. Uma nova jogada reinicia a marca de platina concluída. Valide com `python -m unittest tests_qt.test_platinum tests_qt.test_phone_records` e `node scripts/verify_phone_desktop_browser.cjs --python python`.

## Retrospectiva, detalhes e detecção

`insights.py` consulta sessões e conclusões sem mutação; retrospectivas usam `Sessao.segundos_por_dia()` para respeitar viradas de mês/ano e não somam horas de Zerados ao histórico. `recap_image.py` desenha o PNG localmente e usa `QSaveFile` na exportação. `phone_insights.py` fornece os mesmos dados e PNG ao painel autenticado; não transmite caminhos de executáveis.

`detection.py` consulta psutil em um `Task` fora da thread dos widgets. O estado transitório `present/owned` impede retomar uma sessão encerrada ou pausada manualmente. Só timers iniciados pelo serviço são encerrados automaticamente; duas leituras de ausência confirmam o fechamento. Falhas de leitura e processos ambíguos preservam o estado. Reconfigurar outros jogos mantém a propriedade das sessões existentes; trocar controlador ou desativar um vínculo deixa o timer anterior sob controle manual. Não remova a limpeza do cache do psutil: `exec` no Linux pode trocar o executável sem trocar o PID.

Os vínculos são preferências locais explícitas. Revisões não iniciam a consulta automática. Nunca execute o caminho configurado, envie listas de processos à rede ou altere timers existentes para tentar deduzir horas anteriores à observação.

Valide com `python -m unittest tests_qt.test_detection tests_qt.test_insights` e `node scripts/verify_insights_browser.cjs --python python`. O autoteste do pacote confere geração do PNG, detalhes e extensão nativa de consulta de processos.
