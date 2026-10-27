# HorasJogadas

Aplicativo desktop em Python e PySide6/Qt. Leia README.md antes de alterar o projeto. `app.py` e a interface Tkinter permanecem como implementação legada; preserve a compatibilidade do domínio e dos dados.

## Desenvolvimento

- Interface oficial: `python app_qt.py`; modo isolado: `python app_qt.py --review`; demonstração fictícia: `python app_qt.py --demo`.
- Instale `requirements-qt.txt`. Preserve Python 3.10–3.13 e Windows/Linux.
- Testes do domínio: `python -m unittest discover -s tests -t .`.
- Testes Qt: `QT_QPA_PLATFORM=offscreen python -m unittest discover -s tests_qt -t .` (no Windows, defina a variável no shell).
- Preserve pt/en em `horas_jogadas/i18n.py` e `horas_jogadas_qt/texts.py`.
- Alterações no lançador e empacotamento precisam validar `tests/test_launcher.py`, os testes de transição Qt e o autoteste do executável.

## Dados e atualizações

- Windows: `%APPDATA%\HorasJogadas`; Linux: `~/HorasJogadas`. Use diretórios temporários nos testes.
- Preserve escrita atômica, bloqueio de instância, backups e leitura dos registros existentes.
- A edição oficial cria um backup verificado antes do primeiro carregamento da versão. Nunca mescle silenciosamente dados da revisão.
- Nunca inclua dados pessoais, logs, segredos, executáveis, ZIPs ou `_versoes_anteriores/` nos commits. Imagens públicas devem conter dados fictícios.
- O atualizador legado por ZIP pode alterar código local. Confira as diferenças antes de atualizar com Git.

## Publicação e colaboração

- Confira `git status` antes de começar e concluir. Preserve alterações locais e nunca force o envio.
- Faça commits com propósito claro. Prefira branch própria e revisão por pull request para funcionalidades.
- Rode os testes relevantes e informe falhas existentes.
- `scripts/build_release.py` gera pacotes nativos e executa o autoteste; `scripts/build_site.py` gera o site.
- O workflow release.yml testa Windows/Linux, cria a Release e publica Pages. Publique somente quando autorizado pelo usuário; mantenha versões e tags coerentes.
