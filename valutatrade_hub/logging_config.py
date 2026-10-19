"""Настройка логирования приложения ValutaTrade Hub."""

import logging
from logging.handlers import RotatingFileHandler
from pathlib import Path

_MAIN_FORMAT = "%(asctime)s %(levelname)s %(name)s %(message)s"
_PARSER_FORMAT = (
    "%(asctime)s %(levelname)s [%(name)s] "
    "%(filename)s:%(lineno)d %(message)s"
)
_DATE_FORMAT = "%Y-%m-%dT%H:%M:%S"

_CONFIGURED = False
_PARSER_LOGGER_NAME = "valutatrade_hub.parser"


def setup_logging(
    log_file: str = "logs/actions.log",
    level: str = "INFO",
) -> None:
    """Настроить actions.log + консоль."""
    global _CONFIGURED
    if _CONFIGURED:
        return

    log_path = Path(log_file)
    log_path.parent.mkdir(parents=True, exist_ok=True)

    root = logging.getLogger()
    root.setLevel(logging.DEBUG)

    formatter = logging.Formatter(_MAIN_FORMAT, datefmt=_DATE_FORMAT)

    file_handler = RotatingFileHandler(
        log_path,
        maxBytes=1_000_000,
        backupCount=3,
        encoding="utf-8",
    )
    file_handler.setLevel(level.upper())
    file_handler.setFormatter(formatter)

    console_handler = logging.StreamHandler()
    console_handler.setLevel(level.upper())
    console_handler.setFormatter(formatter)

    root.addHandler(file_handler)
    root.addHandler(console_handler)

    _configure_parser_logger()

    _CONFIGURED = True


def _configure_parser_logger() -> None:
    """Настроить логгер Parser Service — только файл, без консоли."""
    parser_logger = logging.getLogger(_PARSER_LOGGER_NAME)

    if parser_logger.handlers:
        return

    parser_logger.setLevel(logging.DEBUG)

    log_path = Path("logs/parser.log")
    log_path.parent.mkdir(parents=True, exist_ok=True)

    formatter = logging.Formatter(_PARSER_FORMAT, datefmt=_DATE_FORMAT)

    file_handler = RotatingFileHandler(
        log_path,
        maxBytes=1_000_000,
        backupCount=3,
        encoding="utf-8",
    )
    file_handler.setLevel(logging.DEBUG)
    file_handler.setFormatter(formatter)

    parser_logger.addHandler(file_handler)
    parser_logger.propagate = False


def attach_console_handler() -> logging.Handler:
    parser_logger = logging.getLogger(_PARSER_LOGGER_NAME)

    console_handler = logging.StreamHandler()
    console_handler.setLevel(logging.INFO)
    console_handler.setFormatter(
        logging.Formatter("%(levelname)s: %(message)s")
    )

    parser_logger.addHandler(console_handler)
    return console_handler


def detach_console_handler(handler: logging.Handler) -> None:
    parser_logger = logging.getLogger(_PARSER_LOGGER_NAME)
    parser_logger.removeHandler(handler)


def get_logger(name: str) -> logging.Logger:
    return logging.getLogger(name)