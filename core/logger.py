import logging
import os
from datetime import datetime


def setup_logger(log_file: str = "errors.log") -> logging.Logger:
    """
    Настраивает логгер для записи ошибок в файл.

    :param log_file: Имя файла лога
    :return: Настроенный экземпляр логгера
    """
    logger = logging.getLogger("media_manager")
    logger.setLevel(logging.INFO)

    # Очищаем старые обработчики, если они есть
    if logger.handlers:
        logger.handlers.clear()

    # Формат сообщений лога
    formatter = logging.Formatter(
        '[%(asctime)s] %(levelname)s: %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )

    # Обработчик для записи в файл
    file_handler = logging.FileHandler(log_file, encoding='utf-8', mode='a')
    file_handler.setLevel(logging.WARNING)
    file_handler.setFormatter(formatter)
    logger.addHandler(file_handler)

    # Обработчик для вывода в консоль (только ошибки)
    console_handler = logging.StreamHandler()
    console_handler.setLevel(logging.ERROR)
    console_handler.setFormatter(formatter)
    logger.addHandler(console_handler)

    return logger


def get_log_file_path() -> str:
    """Возвращает абсолютный путь к файлу лога."""
    return os.path.abspath("errors.log")