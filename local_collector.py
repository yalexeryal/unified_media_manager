import os
import shutil
from pathlib import Path
from typing import Dict, Set
from core.file_utils import get_file_hash
from core.logger import setup_logger, get_log_file_path


def collect_files(config: Dict) -> None:
    """
    Основная функция сбора файлов с локального диска.

    :param config: Словарь с ключами:
                   - 'source_dir': str (откуда собирать)
                   - 'destination_dir': str (куда копировать)
                   - 'extensions': Set[str] (разрешенные расширения)
                   - 'excluded_folders': Set[str] (игнорируемые папки)
    """
    logger = setup_logger()

    source_path = Path(config['source_dir']).resolve()
    dest_path = Path(config['destination_dir']).resolve()

    if not source_path.is_dir():
        error_msg = f"Исходная папка не найдена: {config['source_dir']}"
        print(f"❌ Ошибка: {error_msg}")
        logger.error(error_msg)
        return

    dest_path.mkdir(parents=True, exist_ok=True)

    exts = config.get('extensions', set())
    excluded = config.get('excluded_folders', set())

    # Путь к индексу хешей для быстрого поиска дубликатов
    index_path = dest_path / ".hash_index.txt"
    existing_hashes = set()
    if index_path.exists():
        try:
            with open(index_path, 'r', encoding='utf-8') as f:
                existing_hashes = {line.strip() for line in f if line.strip()}
        except OSError as e:
            error_msg = f"Не удалось прочитать индекс хешей: {e}"
            print(f"⚠️ {error_msg}")
            logger.warning(error_msg)

    copied_count, skipped_count, error_count = 0, 0, 0

    # Подсчет общего количества файлов для прогресс-бара (приблизительный)
    total_files_estimate = sum(len(files) for _, _, files in os.walk(source_path))
    processed = 0

    print(f"📂 Начинаю сканирование: {source_path}")
    print(f"🎯 Цель: {dest_path}")

    for root, dirs, files in os.walk(source_path):
        # Фильтрация исключаемых папок "на лету" (изменяем dirs in-place)
        dirs[:] = [d for d in dirs if d.lower() not in excluded]

        for filename in files:
            processed += 1
            if processed % 100 == 0 or processed == total_files_estimate:
                print(f"\r  Прогресс: обработано {processed}/{total_files_estimate} файлов...", end="", flush=True)

            filepath = os.path.join(root, filename)
            ext = Path(filename).suffix.lower()

            if ext not in exts:
                continue

            file_hash = get_file_hash(filepath)
            if not file_hash:
                error_count += 1
                error_msg = f"Не удалось прочитать файл (нет доступа или поврежден): {filepath}"
                logger.error(error_msg)
                continue

            if file_hash in existing_hashes:
                skipped_count += 1
                continue

            # Формирование уникального имени файла в целевой папке
            destination_filepath = dest_path / filename
            counter = 1
            while destination_filepath.exists():
                stem = Path(filename).stem
                suffix = Path(filename).suffix
                new_name = f"{stem}_{counter}{suffix}"
                destination_filepath = dest_path / new_name
                counter += 1

            try:
                shutil.copy2(filepath, destination_filepath)
                # Добавляем хеш в индекс и в память
                with open(index_path, 'a', encoding='utf-8') as f:
                    f.write(file_hash + '\n')
                existing_hashes.add(file_hash)
                copied_count += 1
            except (shutil.SameFileError, PermissionError, OSError) as e:
                error_count += 1
                error_msg = f"Ошибка копирования: {filepath} -> {destination_filepath}. Причина: {e}"
                logger.error(error_msg)

    print("\n" + "=" * 50)
    print("✅ Сбор завершен!")
    print(f"  📥 Уникальных файлов скопировано: {copied_count}")
    print(f"  ⏭️  Пропущено дублей: {skipped_count}")
    print(f"  ⚠️  Ошибок доступа/чтения: {error_count}")
    print(f"  📁 Все файлы находятся в: {dest_path}")

    if error_count > 0:
        log_path = get_log_file_path()
        print(f"  📋 Подробный лог ошибок: {log_path}")

    print("=" * 50)