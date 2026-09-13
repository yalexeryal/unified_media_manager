import os
import hashlib
import yaml
from pathlib import Path
from typing import Dict, Set, Any

# Размер чанка для чтения файла при хешировании (4 МБ)
# Оптимальный баланс между скоростью и потреблением памяти
CHUNK_SIZE = 4 * 1024 * 1024


def get_file_hash(filepath: str) -> str | None:
    """
    Вычисляет SHA-256 хеш файла, читая его чанками.
    Это позволяет обрабатывать файлы любого размера без переполнения RAM.

    :param filepath: Путь к файлу
    :return: Hex-строка хеша или None, если файл не удалось прочитать
    """
    sha256_hash = hashlib.sha256()
    try:
        with open(filepath, "rb") as f:
            for byte_block in iter(lambda: f.read(CHUNK_SIZE), b""):
                sha256_hash.update(byte_block)
        return sha256_hash.hexdigest()
    except (OSError, PermissionError, IsADirectoryError) as e:
        # Игнорируем файлы, к которым нет доступа, или это не файлы
        return None


def load_config(config_path: str = "config.yaml") -> Dict[str, Any]:
    """
    Загружает и парсит YAML конфигурационный файл.

    :param config_path: Путь к файлу конфигурации
    :return: Словарь с настройками
    """
    try:
        with open(config_path, "r", encoding="utf-8") as f:
            return yaml.safe_load(f)
    except FileNotFoundError:
        print(f"❌ Ошибка: Файл конфигурации '{config_path}' не найден.")
        raise
    except yaml.YAMLError as e:
        print(f"❌ Ошибка парсинга YAML в '{config_path}': {e}")
        raise


def get_extensions(config: Dict[str, Any], category: str) -> Set[str]:
    """
    Возвращает множество расширений файлов для указанной категории.
    Все расширения приводятся к нижнему регистру и начинаются с точки.

    :param config: Загруженный словарь конфигурации
    :param category: 'media' или 'documents'
    :return: Множество строк (например, {'.jpg', '.png'})
    """
    try:
        exts = config.get('extensions', {}).get(category, [])
        return {ext.lower() if ext.startswith('.') else f'.{ext.lower()}' for ext in exts}
    except KeyError:
        print(f"⚠️ Категория '{category}' не найдена в конфигурации расширений.")
        return set()


def get_excluded_folders(config: Dict[str, Any], category: str) -> Set[str]:
    """
    Возвращает множество имен папок, которые следует игнорировать при обходе.
    Все имена приводятся к нижнему регистру для нечувствительного к регистру сравнения.

    :param config: Загруженный словарь конфигурации
    :param category: 'media' или 'documents'
    :return: Множество строк (например, {'windows', '$recycle.bin'})
    """
    try:
        folders = config.get('excluded_folders', {}).get(category, [])
        return {folder.lower() for folder in folders}
    except KeyError:
        print(f"⚠️ Категория '{category}' не найдена в конфигурации исключаемых папок.")
        return set()


def format_size(size_bytes: int) -> str:
    """
    Форматирует размер файла в байтах в читаемый вид (KB, MB, GB).
    """
    for unit in ['B', 'KB', 'MB', 'GB', 'TB']:
        if size_bytes < 1024.0:
            return f"{size_bytes:.2f} {unit}"
        size_bytes /= 1024.0
    return f"{size_bytes:.2f} PB"