# Trabalhar no HorasJogadas

## Pasta de trabalho

Use a pasta que contém `app.py`, `horas_jogadas/` e `.git` como projeto local no Codex. Assim, as próximas conversas podem trabalhar diretamente no código e consultar o histórico.

O GitHub guarda os commits enviados. Alterações feitas no computador só chegam ao GitHub depois de um commit e um push. Alterações feitas no GitHub precisam ser trazidas para a pasta local antes de continuar.

## Fluxo recomendado

1. Confira as alterações locais com `git status`.
2. Com a pasta sem alterações pendentes, atualize a branch principal com `git pull --ff-only`.
3. Para uma melhoria, crie uma branch: `git switch -c melhoria/nome-da-melhoria`.
4. Altere o código e rode `python -m unittest discover -s tests -t .`.
5. Revise as diferenças, faça um commit e envie a branch ao GitHub.
6. Revise o pull request antes de integrar a mudança à `main`.

Você pode pedir ao Codex para executar essas etapas com você.

## O que vai para o GitHub

Código-fonte, testes, ícone, documentação e scripts de empacotamento. O `.gitignore` exclui executáveis, pacotes gerados, versões anteriores, dados pessoais, logs e credenciais. Executáveis e ZIPs podem ser distribuídos separadamente em releases quando você decidir publicar uma versão.

Se usar a integração GitHub em outra conversa, confira se ela tem acesso a este repositório privado. A permissão da integração e o acesso à pasta local são configurações distintas.

## Atualizador do aplicativo

O atualizador por ZIP também pode mudar os arquivos desta pasta. Sempre revise essas mudanças antes de usar Git. Não descarte diferenças locais automaticamente.

Seus jogos e sessões ficam em `%APPDATA%\HorasJogadas` e não são incluídos no repositório. Mantenha os backups desses dados pelo próprio aplicativo.
