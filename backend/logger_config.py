import logging
import sys
import os


def setup_logger(name: str = None) -> logging.Logger:
    """Настраивает и возвращает логгер с заданным именем"""

    # Уровень логирования из ENV (по умолчанию INFO)
    log_level = os.getenv("LOG_LEVEL", "INFO").upper()

    # Настройка форматирования
    formatter = logging.Formatter(
        '%(asctime)s|%(name)s|%(levelname)s|%(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )

    # Создаём обработчик для вывода в stdout
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setFormatter(formatter)

    # Получаем или создаём логгер
    logger = logging.getLogger(name or __name__)
    logger.setLevel(getattr(logging, log_level, logging.INFO))

    # Добавляем обработчик, если его ещё нет
    if not logger.handlers:
        logger.addHandler(console_handler)

    return logger


# Создаём корневой логгер для всего приложения
app_logger = setup_logger("generator_backend")