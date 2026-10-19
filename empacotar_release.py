"""Gera o pacote de DISTRIBUIÇÃO (itch.io): só o executável + suas bibliotecas + LEIAME, com checksums.

Uso (normalmente via build_itch.bat):
    python empacotar_release.py                  # ambiente limpo, build, autoteste do .exe, pacote
    python empacotar_release.py --rodar-testes   # também roda os testes unitários (opcional; precisa da pasta tests/ atual)
    python empacotar_release.py --sem-venv       # usa o Python atual em vez de criar um ambiente limpo
    python empacotar_release.py --so-empacotar PASTA_DIST   # só monta o pacote a partir de um build existente

Resultado em  release/:
    HorasJogadas/                       <- esta pasta é o que o `butler push` envia
    HorasJogadas-vX.Y.Z-windows.zip     <- este ZIP serve para upload manual / testes
    SHA256.txt                          <- checksums do ZIP e do .exe
Nada do código-fonte (app.py, horas_jogadas/, tests, .bat) vai para o pacote.
"""
import argparse
import hashlib
import os
import re
import shutil
import string
import subprocess
import sys
import tempfile
import venv
import zipfile
from typing import Dict, List, Optional, Sequence, Tuple

RAIZ = os.path.dirname(os.path.abspath(__file__))
NOME = "HorasJogadas"
MARCADOR = "empacotado.flag"
PASTA_TRABALHO = "build_release"          # temporária (PyInstaller escreve aqui); apagada no fim
PASTA_SAIDA = "release"
PASTA_VENV = ".venv_release"

# Manifesto do app do itch.io: https://itch.io/docs/itch/integrating/manifest.html  (fica na raiz do que é enviado)
MANIFESTO_ITCH = f'''[[actions]]
name = "play"
path = "{NOME}.exe"
'''

# Nada disto pode ir para o pacote que os jogadores baixam
NOMES_PROIBIDOS = {"app.py", "horas_jogadas", "tests", "README.md", "requirements-dev.txt", "build_exe.bat",
                   "build_itch.bat", "Iniciar.bat", "empacotar_release.py", "LEIAME_release.txt",
                   "_versoes_anteriores", PASTA_VENV, PASTA_TRABALHO, ".git"}


# ---------------------------------------------------------------------------
# Funções puras (testadas em tests/test_empacotamento.py)
# ---------------------------------------------------------------------------
def ler_versao(raiz: str = RAIZ) -> str:
    with open(os.path.join(raiz, "horas_jogadas", "__init__.py"), encoding="utf-8") as f:
        achado = re.search(r"""__version__\s*=\s*["']([^"']+)["']""", f.read())
    if not achado:
        raise SystemExit("Não encontrei __version__ em horas_jogadas/__init__.py")
    return achado.group(1)


def sha256_arquivo(caminho: str) -> str:
    h = hashlib.sha256()
    with open(caminho, "rb") as f:
        for bloco in iter(lambda: f.read(1024 * 1024), b""):
            h.update(bloco)
    return h.hexdigest()


def python_do_venv(pasta_venv: str) -> str:
    return os.path.join(pasta_venv, "Scripts", "python.exe") if os.name == "nt" else os.path.join(pasta_venv, "bin", "python")


def comando_pyinstaller(raiz: str, python: str, trabalho: str, icone: Optional[str] = None) -> List[str]:
    """Linha de comando do PyInstaller para o build de distribuição.

    - onedir (pasta): menos alertas de antivírus que o "um arquivo só" e abre mais rápido;
    - noupx: não comprime o executável (compressão tipo UPX é gatilho clássico de falso positivo);
    - collect-submodules: o código do app vai DENTRO do executável;
    - empacotado.flag: avisa ao app que está em modo de distribuição.
    """
    cmd = [python, "-m", "PyInstaller", "--noconfirm", "--clean", "--onedir", "--windowed", "--noupx",
           "--paths", raiz, "--name", NOME, "--collect-submodules", "horas_jogadas",
           "--add-data", f"{os.path.join(trabalho, MARCADOR)}{os.pathsep}."]
    if icone:
        cmd += ["--icon", icone, "--add-data", f"{icone}{os.pathsep}."]
    cmd += ["--distpath", os.path.join(trabalho, "dist"), "--workpath", os.path.join(trabalho, "work"),
            "--specpath", trabalho, os.path.join(raiz, "app.py")]
    return cmd


def _achar(pasta: str, nome: str) -> bool:
    return any(nome in arquivos or nome in dirs for _, dirs, arquivos in os.walk(pasta))


def verificar_release(pasta_app: str) -> List[str]:
    """Lista de problemas do pacote (vazia = pronto para publicar)."""
    problemas = []
    if not os.path.isfile(os.path.join(pasta_app, f"{NOME}.exe")):
        problemas.append(f"{NOME}.exe não está na pasta do pacote")
    if not _achar(pasta_app, MARCADOR):
        problemas.append(f"falta {MARCADOR}: o .exe não saberia que está em modo de distribuição")
    for raiz, dirs, arquivos in os.walk(pasta_app):
        for nome in dirs + arquivos:
            if nome in NOMES_PROIBIDOS or nome.lower().endswith(".bat"):
                problemas.append(f"não deveria ir para o público: {os.path.relpath(os.path.join(raiz, nome), pasta_app)}")
    return problemas


def montar_release(raiz: str, dist_app: str, saida: str, versao: str) -> Dict[str, str]:
    """Copia o build para release/, escreve o LEIAME, cria o ZIP e os checksums. Devolve os caminhos."""
    pacote = os.path.join(saida, NOME)
    shutil.rmtree(saida, ignore_errors=True)
    os.makedirs(saida)
    shutil.copytree(dist_app, pacote)
    with open(os.path.join(raiz, "LEIAME_release.txt"), encoding="utf-8") as f:
        leiame = string.Template(f.read()).safe_substitute(versao=versao)
    with open(os.path.join(pacote, "LEIAME.txt"), "w", encoding="utf-8", newline="\r\n") as f:
        f.write(leiame)

    with open(os.path.join(pacote, ".itch.toml"), "w", encoding="utf-8", newline="\n") as f:
        f.write(MANIFESTO_ITCH)                    # diz ao app do itch.io qual arquivo abrir (precisa estar na raiz)

    problemas = verificar_release(pacote)
    if problemas:
        raise SystemExit("Pacote inválido:\n  - " + "\n  - ".join(problemas))

    caminho_zip = os.path.join(saida, f"{NOME}-v{versao}-windows.zip")
    with zipfile.ZipFile(caminho_zip, "w", zipfile.ZIP_DEFLATED) as z:
        for pasta, _, arquivos in os.walk(pacote):
            for nome in sorted(arquivos):
                caminho = os.path.join(pasta, nome)
                z.write(caminho, os.path.join(NOME, os.path.relpath(caminho, pacote)))
    exe = os.path.join(pacote, f"{NOME}.exe")
    caminho_sha = os.path.join(saida, "SHA256.txt")
    with open(caminho_sha, "w", encoding="utf-8", newline="\n") as f:        # mesmo formato do `sha256sum`
        f.write(f"{sha256_arquivo(caminho_zip)}  {os.path.basename(caminho_zip)}\n")
        f.write(f"{sha256_arquivo(exe)}  {NOME}.exe\n")
    return {"pasta": pacote, "zip": caminho_zip, "sha256": caminho_sha, "exe": exe}


def executar_autoteste(prefixo_comando: Sequence[str], timeout: int = 180) -> Tuple[bool, str]:
    """Roda `<exe> --verificar <arquivo>`: o app importa tudo e abre/fecha uma janela. (ok, texto)."""
    with tempfile.TemporaryDirectory() as tmp:
        destino = os.path.join(tmp, "verificacao.txt")
        try:
            r = subprocess.run(list(prefixo_comando) + ["--verificar", destino], timeout=timeout, cwd=tmp,
                               capture_output=True, text=True)
        except (OSError, subprocess.TimeoutExpired) as e:
            return False, f"não foi possível executar o autoteste: {e}"
        try:
            with open(destino, encoding="utf-8") as f:
                texto = f.read()
        except OSError:
            return False, f"o autoteste não gerou resultado (código {r.returncode}). {r.stderr[-400:]}"
        return (r.returncode == 0 and texto.startswith("OK") and "empacotado=True" in texto), texto


# ---------------------------------------------------------------------------
# Orquestração (precisa de internet para baixar o PyInstaller; não é coberta pelos testes unitários)
# ---------------------------------------------------------------------------
def _rodar(cmd: Sequence[str], titulo: str, cwd: str) -> None:
    print(f"\n>>> {titulo}\n    {' '.join(cmd)}\n", flush=True)
    if subprocess.run(list(cmd), cwd=cwd).returncode != 0:
        raise SystemExit(f"\nFALHOU: {titulo}")


def construir(args: argparse.Namespace) -> None:
    versao = ler_versao()
    trabalho = os.path.join(RAIZ, PASTA_TRABALHO)
    saida = os.path.join(RAIZ, PASTA_SAIDA)

    if args.so_empacotar:
        dist_app = os.path.abspath(args.so_empacotar)
    else:
        if args.sem_venv:
            python = sys.executable
        else:
            pasta_venv = os.path.join(RAIZ, PASTA_VENV)
            shutil.rmtree(pasta_venv, ignore_errors=True)
            print(f">>> Criando ambiente limpo em {PASTA_VENV} (só o Python + PyInstaller, menos falsos positivos)")
            venv.create(pasta_venv, with_pip=True)
            python = python_do_venv(pasta_venv)
        _rodar([python, "-m", "pip", "install", "--upgrade", "pip", "pyinstaller"], "Instalando PyInstaller", RAIZ)
        if args.rodar_testes:
            _rodar([python, "-m", "unittest", "discover", "-s", "tests", "-t", "."], "Rodando os testes do app", RAIZ)

        shutil.rmtree(trabalho, ignore_errors=True)
        os.makedirs(trabalho)
        with open(os.path.join(trabalho, MARCADOR), "w", encoding="utf-8") as f:
            f.write("1")
        icone = os.path.join(RAIZ, "icon.ico")
        _rodar(comando_pyinstaller(RAIZ, python, trabalho, icone if os.path.exists(icone) else None),
               "Gerando o executável (pode levar alguns minutos)", RAIZ)
        dist_app = os.path.join(trabalho, "dist", NOME)

    exe = os.path.join(dist_app, f"{NOME}.exe")
    if os.name == "nt" and os.path.exists(exe):
        print("\n>>> Autoteste: abrindo o .exe gerado para ver se ele funciona de verdade")
        ok, texto = executar_autoteste([exe])
        print("    resultado:", texto.strip().splitlines()[0] if texto.strip() else "(vazio)")
        if not ok:
            raise SystemExit("\nO .exe gerado NÃO passou no autoteste. NÃO publique.\n" + texto)
    else:
        print("\n(autoteste do .exe pulado: só roda no Windows)")

    resultado = montar_release(RAIZ, dist_app, saida, versao)
    if not args.so_empacotar:
        shutil.rmtree(trabalho, ignore_errors=True)
    print("\n" + "=" * 70)
    print(f"PRONTO!  Versão {versao}")
    print(f"  Pasta para o butler/itch app : {resultado['pasta']}")
    print(f"  ZIP (upload manual/testes)   : {resultado['zip']}")
    print(f"  Checksums                    : {resultado['sha256']}")
    print("\nPróximo passo (substitua SEU_USUARIO e SEU_JOGO):")
    print(f'  butler push "{resultado["pasta"]}" SEU_USUARIO/SEU_JOGO:windows --userversion {versao}')
    print("=" * 70)


def main(argv: Optional[Sequence[str]] = None) -> None:
    p = argparse.ArgumentParser(description="Gera o pacote de distribuição para o itch.io")
    p.add_argument("--rodar-testes", action="store_true", help="roda também os testes unitários antes do build")
    p.add_argument("--sem-venv", action="store_true")
    p.add_argument("--so-empacotar", metavar="PASTA_DIST")
    construir(p.parse_args(argv))


if __name__ == "__main__":
    main()
