# HorasJogadas 3.2.1 — correção de instalar e reiniciar no Linux

Corrige o ambiente herdado pelo atualizador Linux, que podia fazer o app fechar sem abrir a nova versão, especialmente em sistemas baseados em Arch, como CachyOS.

- Ferramentas do sistema usam as bibliotecas do sistema; a nova versão inicia com seu próprio ambiente PyInstaller.
- Preserva as variáveis da sessão gráfica X11/Wayland e os caminhos de bibliotecas personalizados anteriores à abertura do app.
- A nova janela confirma a abertura. Se o processo encerrar antes de ficar pronto, o auxiliar tenta restaurar e abrir a versão anterior, mantendo as duas cópias dos arquivos.
- Erros da troca e do reinício são registrados em `update.log` na pasta de cache daquele download.
- Testes de atualização real, desde o executável empacotado até a reabertura da janela, em Ubuntu e Arch Linux antes de publicar.

**Se a atualização anterior fechou o app e ele não voltou:** baixe o pacote Linux pelo navegador, feche qualquer instância aberta e extraia em uma pasta nova. Abra `HorasJogadas` nessa pasta. Não apague `~/HorasJogadas`: seus registros continuam na mesma pasta de dados. O atualizador antigo precisa desta instalação manual uma vez para receber a correção.

Capas, ícones e registros da 3.2 continuam compatíveis. Windows: instalador ou ZIP portátil. Linux x86_64: `HorasJogadas-Linux-x86_64.tar.gz`. Não precisa instalar Python. Confira `SHA256SUMS.txt`.
