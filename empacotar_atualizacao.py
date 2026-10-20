"""Gera ZIP de código para Configurações > Atualizar app; não empacota dados ou executáveis."""
import argparse
import os
import zipfile

from horas_jogadas import __version__
from horas_jogadas.constants import ARQUIVOS_DE_APOIO
from horas_jogadas.updater import inspecionar_zip


def empacotar(destino: str) -> str:
    raiz = os.path.dirname(os.path.abspath(__file__))
    os.makedirs(os.path.dirname(os.path.abspath(destino)), exist_ok=True)
    with zipfile.ZipFile(destino, 'w', zipfile.ZIP_DEFLATED) as pacote:
        pasta = os.path.join(raiz, 'horas_jogadas')
        for base, dirs, arquivos in os.walk(pasta):
            dirs[:] = sorted(d for d in dirs if d != '__pycache__')
            for nome in sorted(arquivos):
                if nome.endswith('.py'):
                    caminho = os.path.join(base, nome)
                    pacote.write(caminho, os.path.relpath(caminho, raiz).replace(os.sep, '/'))
        for nome in ARQUIVOS_DE_APOIO:
            caminho = os.path.join(raiz, nome)
            if os.path.isfile(caminho):
                pacote.write(caminho, nome)
    info = inspecionar_zip(destino)
    if info.versao != __version__:
        raise RuntimeError('Versão do pacote não confere')
    return os.path.abspath(destino)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--saida', default=os.path.join('release', f'HorasJogadas-v{__version__}-atualizacao.zip'))
    args = parser.parse_args()
    print(empacotar(args.saida))
