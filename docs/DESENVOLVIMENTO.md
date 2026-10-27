# Desenvolvimento

[← Voltar ao início](../README.md)

## Requisitos

- Python **3.10+**, preservando a compatibilidade com Python 3.10 e Windows.
- Tkinter/Tcl/Tk para a interface. Não é uma dependência instalável via pip.
- Nenhuma dependência externa obrigatória em tempo de execução.
- pytest opcional (`requirements-dev.txt`); PyInstaller apenas para empacotar.

## Ambiente local

Na raiz do projeto:

```bash
python -m venv .venv
```

Ative no Windows (PowerShell):

```powershell
.venv\Scripts\Activate.ps1
```

Ou no Linux/macOS:

```bash
source .venv/bin/activate
```

```bash
python -m pip install -r requirements-dev.txt
python app.py
```

Para rodar somente os testes com a biblioteca padrão, não é necessário instalar `requirements-dev.txt`.

## Testes

```bash
python -m unittest discover -s tests -t .
python -m pytest
```

As suítes cobrem persistência, estatísticas, utilitários, traduções, lançador, atualizador e Lista de Zerados. Algumas verificações simulam corrupção, disco cheio e falha de gravação: mensagens de erro nesses cenários são esperadas; confira o resultado final do executor.

O workflow [Testes Python](../.github/workflows/tests.yml) configura a suíte unittest em Windows e Linux, com Python 3.10 e 3.12. Uma execução local não comprova que a matriz remota passou; confira a aba Actions após o envio.

### Conferir o lançador

```bash
python app.py --verificar verificacao.txt
```

Exija status zero e arquivo começando por `OK`. O comando importa o aplicativo e abre/fecha uma janela Tk. Remova o arquivo após a conferência. O autoteste não substitui a validação funcional das telas.

### Linux sem interface gráfica

No Debian/Ubuntu, com permissão de administração:

```bash
sudo apt-get install python3-tk xvfb xauth
xvfb-run -a python3 app.py --verificar /tmp/horasjogadas-verificacao.txt
cat /tmp/horasjogadas-verificacao.txt
```

No ambiente de nuvem preparado para este projeto, o auxiliar local permite executar:

```bash
cd /workspace/HorasJogadas
/workspace/.horasjogadas-cloud/run-gui .venv/bin/python app.py
```

Esse caminho pertence ao ambiente de nuvem e não à instalação comum. Cada tarefa já é isolada: use o checkout existente, sem criar worktree, salvo se solicitado.

Para testes funcionais, use `Repositorio(data_dir=...)` com uma pasta temporária. Para iniciar o app completo com dados isolados, defina `APPDATA` para uma pasta temporária **antes** de executar Python. Xvfb fornece uma tela virtual, sem prévia web.

## Mapa do código

| Caminho | Responsabilidade |
| --- | --- |
| `app.py` | Lançador, autoteste e recuperação de falha após atualização. |
| `horas_jogadas/main.py` | Logging, instância única e inicialização. |
| `horas_jogadas/constants.py` | Constantes, arquivos, cores e opções. |
| `horas_jogadas/models.py` | Jogos, sessões e validação dos modelos. |
| `horas_jogadas/storage.py` | Persistência, migração, escrita atômica e recuperação. |
| `horas_jogadas/stats.py`, `utils.py` | Estatísticas, formatação e divisão do tempo por dia. |
| `horas_jogadas/zerados.py` | Conclusões, resumo anual, TXT e armazenamento independente. |
| `horas_jogadas/i18n.py` | Textos em português e inglês. |
| `horas_jogadas/backups.py`, `updater.py` | Backups dos dados e atualização/restauração do código. |
| `horas_jogadas/exportacao.py`, `edicao_sessao.py` | CSV e validação de sessões manuais/editadas. |
| `horas_jogadas/instancia.py`, `icone_barra.py`, `logging_setup.py` | Instância única, selo no Windows e logs. |
| `horas_jogadas/ui/` | Tema, widgets, cartões e telas do aplicativo. |
| `tests/` | Testes automatizados com diretórios temporários. |
| `empacotar_release.py`, `build_*.bat` | Build e validação dos pacotes Windows. |

## Traduções e compatibilidade

Mantenha chaves e marcadores de português e inglês em sincronia. Para adicionar um idioma, atualize `IDIOMAS_DISPONIVEIS` em `constants.py` e `TEXTOS` em `i18n.py`; execute `tests/test_i18n.py`.

Ao alterar importações, lançador ou empacotamento, execute `tests/test_launcher.py`. O executável precisa conhecer as bibliotecas do código carregado dinamicamente. Testes em Linux não validam o `.exe`, o SmartScreen ou o selo da barra de tarefas do Windows.

## Empacotamento no Windows

### Lançador com código ao lado

Execute `build_exe.bat`. Ele instala/atualiza o PyInstaller e gera um executável a partir de `app.py`, que carrega `horas_jogadas/` ao lado dele. Essa edição permite atualizar o código por ZIP no app.

### Pacote de distribuição

```powershell
python empacotar_release.py --rodar-testes
```

Ou execute `build_itch.bat`. O empacotador prepara o ambiente, reúne o código, executa verificações e gera os resultados em `release/`. Leia a saída e valide em Windows antes de distribuir. Não envie executáveis ou ZIPs para commits.

O pacote de distribuição embute o código e tem um fluxo de atualização diferente; veja [Atualizar o aplicativo](GUIA_DE_USO.md#atualizar-o-aplicativo).

## Antes de enviar mudanças

1. Confira `git status` e preserve trabalho local.
2. Use uma branch e commits com propósito claro.
3. Rode testes e valide telas afetadas com dados temporários.
4. Revise o diff: não inclua dados, logs, segredos, builds ou executáveis.
5. Abra uma revisão, conforme o [guia de colaboração](../COLABORACAO.md).
