"""Garante uma única janela do app aberta por vez (evita que duas cópias se sobrescrevam).

A trava é um bloqueio de arquivo do sistema operacional: some sozinho se o app fechar ou cair,
então nunca fica "presa". Quem tenta abrir uma segunda cópia deixa um sinal, e a primeira janela
se traz para a frente.
"""
import logging
import os
import time
from typing import Optional

from .constants import NOME_ARQ_SINAL, NOME_ARQ_TRAVA

log = logging.getLogger(__name__)


class TravaInstancia:
    def __init__(self, pasta: str):
        self.pasta = pasta
        self.caminho = os.path.join(pasta, NOME_ARQ_TRAVA)
        self._arquivo: Optional[object] = None

    @property
    def ativa(self) -> bool:
        return self._arquivo is not None

    def _tentar(self) -> bool:
        os.makedirs(self.pasta, exist_ok=True)
        arquivo = open(self.caminho, "a+b")
        try:
            arquivo.seek(0)
            if os.name == "nt":
                import msvcrt
                msvcrt.locking(arquivo.fileno(), msvcrt.LK_NBLCK, 1)
            else:
                import fcntl
                fcntl.flock(arquivo.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
        except OSError:
            arquivo.close()
            return False
        self._arquivo = arquivo
        return True

    def adquirir(self, espera: float = 0.0) -> bool:
        """Tenta assumir a trava. Com `espera`, insiste por esse tempo (ex.: logo após um reinício)."""
        limite = time.monotonic() + espera
        while True:
            try:
                if self._tentar():
                    return True
            except OSError:
                log.exception("Não foi possível criar o arquivo de trava; seguindo sem proteção")
                return True                                  # na dúvida, não impede o usuário de usar o app
            if time.monotonic() >= limite:
                return False
            time.sleep(0.2)

    def liberar(self) -> None:
        arquivo, self._arquivo = self._arquivo, None
        if arquivo is None:
            return
        try:
            arquivo.seek(0)
            if os.name == "nt":
                import msvcrt
                msvcrt.locking(arquivo.fileno(), msvcrt.LK_UNLCK, 1)
            else:
                import fcntl
                fcntl.flock(arquivo.fileno(), fcntl.LOCK_UN)
        except OSError:
            pass
        finally:
            arquivo.close()


def sinalizar_mostrar(pasta: str) -> None:
    """Pede à instância já aberta que traga a janela para a frente."""
    try:
        os.makedirs(pasta, exist_ok=True)
        with open(os.path.join(pasta, NOME_ARQ_SINAL), "w", encoding="utf-8") as f:
            f.write(str(os.getpid()))
    except OSError:
        log.exception("Não foi possível sinalizar a instância existente")


def consumir_sinal(pasta: str) -> bool:
    """True (uma vez) se alguém pediu para a janela vir para a frente."""
    caminho = os.path.join(pasta, NOME_ARQ_SINAL)
    if not os.path.exists(caminho):
        return False
    try:
        os.remove(caminho)
    except OSError:
        pass
    return True
