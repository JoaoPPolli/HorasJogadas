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
sudo apt-get install xvfb xauth libegl1 libxkbcommon-x11-0 libxcb-cursor0 libxcb-xinerama0
xvfb-run -a python scripts/build_release.py
```

## Empacotamento no Windows

```bash
python -m pip install -r requirements-build.txt
python scripts/build_release.py
```

Ou use `build_exe.bat`. A saída fica em `dist/HorasJogadas` e `release/`. Preserve toda a pasta do executável. Para gerar o instalador, instale Inno Setup 6, defina `HORAS_VERSION=3.0.0` e compile `packaging/windows.iss`.

Cada pacote executa `--self-test <resultado.json>` com dados fictícios: abre as cinco telas, valida os assets, grava uma sessão e verifica que o domínio legado consegue relê-la. Esse teste não abre os registros pessoais.

Os builds são nativos, Windows x64 e Ubuntu 22.04 x64. Não há compilação cruzada nem pacote macOS nesta publicação. O workflow baixa os textos de licença oficiais para `build/legal` e os inclui no pacote.

## Release e site

O workflow `.github/workflows/release.yml` é acionado por tags `v*`, branches `release/**` ou execução manual. A versão vem de `horas_jogadas_qt/release.py`. Ambos os sistemas precisam passar testes e autoteste antes da publicação dos pacotes e dos SHA-256. Depois o site é publicado no GitHub Pages, com origem GitHub Actions.

```bash
python scripts/build_site.py
python -m http.server 8000 --directory build/site
```

O site usa assets locais e links estáveis `releases/latest/download/`. As capturas devem conter apenas dados fictícios. Não versionar `build/`, `dist/`, `release/`, diagnósticos nem dados pessoais.
