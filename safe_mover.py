import os
import shutil
from pathlib import Path
from typing import Dict, List
from core.logger import setup_logger, get_log_file_path


def move_duplicates_to_review(duplicates: Dict[str, List[str]], review_folder: str) -> int:
    """
    Перемещает дубликаты в папку 'На_проверку', сохраняя первый файл как оригинал.
    """
    logger = setup_logger()

    review_path = Path(review_folder).resolve()
    review_path.mkdir(parents=True, exist_ok=True)

    moved_count = 0
    failed_count = 0

    print(f"\n📦 Начало безопасного перемещения дубликатов в: {review_path}")

    for hash_val, paths in duplicates.items():
        # Считаем первый файл оригиналом, остальные — дублями для перемещения
        keep_path = paths[0]
        duplicates_to_move = paths[1:]

        for dup_path in duplicates_to_move:
            try:
                filename = Path(dup_path).name
                stem = Path(dup_path).stem
                ext = Path(dup_path).suffix

                # Формируем путь назначения. Если файл с таким именем уже есть, добавляем счетчик
                dest = review_path / filename
                counter = 1
                while dest.exists():
                    dest = review_path / f"{stem}_{counter}{ext}"
                    counter += 1

                # Перемещаем файл
                shutil.move(dup_path, dest)
                moved_count += 1

            except Exception as e:
                failed_count += 1
                error_msg = f"Не удалось переместить файл: {dup_path}. Причина: {e}"
                logger.error(error_msg)

    print("=" * 50)
    print(f"✅ Успешно перемещено файлов: {moved_count}")
    if failed_count > 0:
        print(f"❌ Ошибок при перемещении: {failed_count}")
        log_path = get_log_file_path()
        print(f"📋 Подробный лог ошибок: {log_path}")
    print(f"📁 Проверьте папку: {review_path}")
    print(
        "💡 Совет: Подержите файлы здесь несколько дней. Если все работает корректно, удалите эту папку вручную для окончательной очистки.")
    print("=" * 50)

    return moved_count