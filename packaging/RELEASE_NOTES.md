A versão 3.0.0 traz a interface oficial em PySide6, com navegação lateral, quatro estilos de aparência, lista de Zerados por mês e estatísticas com ordenação recente e Top 5 por horas.

## Baixar e abrir

- **Windows:** baixe `HorasJogadas-Windows-Setup.exe` e execute o instalador. Para usar sem instalar, extraia o ZIP portátil e abra `HorasJogadas.exe`.
- **Linux x86_64 (Ubuntu 22.04+ ou compatível):** extraia o `.tar.gz` e execute `./HorasJogadas` em uma sessão gráfica.
- Os pacotes prontos não precisam de Python instalado. Compare os arquivos com `SHA256SUMS.txt` para verificar a integridade.

## Seus registros

Feche o app antigo antes de abrir a nova versão. A release usa a mesma pasta oficial e os mesmos formatos JSON: `%APPDATA%\HorasJogadas` no Windows e `~/HorasJogadas` no Linux. Ela cria um backup completo antes da primeira leitura e mantém a trava de instância compartilhada com a versão antiga.

A pasta `HorasJogadas-Revisao-Qt` permanece preservada, separada dos registros oficiais. As duas bases não são mescladas automaticamente. Preserve essa cópia se registrou partidas durante a avaliação.

Instalação e dados ficam separados. Desinstalar o aplicativo não remove o histórico. Mantenha também uma cópia externa da pasta de dados com o app fechado.

## Novidades

- Interface Qt com cartões adaptáveis e rolagem nativa.
- Estilo Original com cinza e roxo e tratamento da barra de título do Windows.
- Zerados agrupados por mês e seleção de ano sem cursor de edição.
- Top 5 com barras de horas e lista completa pela sessão mais recente.
- Editor de tempo com horas, minutos, segundos, atalhos, valores negativos e duração da pausa.
- Backups completos, diário de recuperação de gravações e preservação de IDs.
