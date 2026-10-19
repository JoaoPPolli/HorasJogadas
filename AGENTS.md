# HorasJogadas

Aplicativo desktop em Python e Tkinter para registrar horas jogadas. Leia README.md antes de alterar o projeto.

## Desenvolvimento

- Execute o aplicativo com `python app.py`.
- Execute os testes com `python -m unittest discover -s tests -t .`.
- O aplicativo usa a biblioteca padrão; pytest é opcional para desenvolvimento.
- Preserve a compatibilidade com Python 3.10 e com o Windows.
- Mantenha as traduções de português e inglês em `horas_jogadas/i18n.py` consistentes.
- Ao modificar o lançador, imports ou empacotamento, verifique `tests/test_launcher.py` e a necessidade de recriar o executável.

## Dados e atualizações

- Os dados reais ficam em `%APPDATA%\HorasJogadas` no Windows. Use diretórios temporários nos testes.
- Preserve a escrita atômica, os backups e a compatibilidade de leitura dos dados existentes.
- Nunca inclua dados pessoais, logs, segredos, executáveis, ZIPs ou `_versoes_anteriores/` nos commits.
- O atualizador por ZIP altera o código local. Antes de atualizar com Git, verifique as diferenças locais e preserve o trabalho existente.

## Colaboração

- Confira `git status` antes de começar e antes de concluir.
- Faça alterações pequenas, com commits que expliquem o propósito.
- Para mudanças de funcionalidade, prefira uma branch própria e revisão por pull request.
- Rode os testes relevantes e informe o resultado, inclusive falhas existentes.
- Não sobrescreva alterações locais do usuário nem force o envio ao GitHub.
