"""Configuração de logging em arquivo com rotação."""
import logging
import os
from logging.handlers import RotatingFileHandler

from .constants import NOME_ARQ_LOG

_NOME_LOGGER = "horas_jogadas"


def configurar_logging(data_dir: str) -> logging.Logger:
    """Cria (uma única vez) o logger do app gravando em DATA_DIR/app.log."""
    logger = logging.getLogger(_NOME_LOGGER)
    if logger.handlers:
        return logger
    logger.setLevel(logging.INFO)
    try:
        os.makedirs(data_dir, exist_ok=True)
        handler = RotatingFileHandler(
            os.path.join(data_dir, NOME_ARQ_LOG),
            maxBytes=500_000, backupCount=3, encoding="utf-8",
        )
    except OSError:
        handler = logging.StreamHandler()
    handler.setFormatter(logging.Formatter("%(asctime)s [%(levelname)s] %(name)s: %(message)s"))
    logger.addHandler(handler)
    return logger
