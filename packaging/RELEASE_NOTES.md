# HorasJogadas 3.1.1 — correção de certificados no Linux

Corrige o erro `CERTIFICATE_VERIFY_FAILED: unable to get local issuer certificate` ao verificar atualizações em pacotes Linux que não encontram os certificados raiz da máquina.

- Inclui certificados de confiança no executável, sem depender dos caminhos do computador usado para compilar.
- Mantém a verificação de certificados e de nomes dos servidores, além de preservar os certificados locais do sistema.
- Corrige também o download das atualizações e o acesso às capas da Steam.
- O executável Linux é testado com os certificados do sistema indisponíveis.

Se a versão anterior não consegue verificar atualizações, baixe esta versão pelo navegador, feche o app e extraia o pacote em uma pasta nova. Não apague `~/HorasJogadas`: os registros continuam nessa pasta. Não precisa instalar Python.

Windows: instalador ou ZIP portátil. Linux x86_64: `HorasJogadas-Linux-x86_64.tar.gz`. Confira `SHA256SUMS.txt`.
