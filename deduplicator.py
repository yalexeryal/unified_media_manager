import os
import hashlib
from pathlib import Path
from typing import Dict, List, Set
from collections import defaultdict
from core.file_utils import get_file_hash, format_size


def find_duplicates_optimized(folder_path: str, extensions: Set[str]) -> Dict[str, List[str]]:
    """
    Двухэтапный поиск дубликатов:
    1. Группируем файлы по размеру (быстрая операция O(N)).
    2. Считаем SHA-256 хеш только для файлов-кандидатов с одинаковым размером.

    :return: Словарь {hash: [list_of_file_paths]} только для групп с >1 файлом.
    """
    print(f"📂 Этап 1: Сканирование '{folder_path}' и группировка по размеру...")

    size_groups = defaultdict(list)
    total_files = 0
    folder = Path(folder_path).resolve()

    for root, _, files in os.walk(folder):
        for filename in files:
            if Path(filename).suffix.lower() not in extensions:
                continue

            filepath = os.path.join(root, filename)
            try:
                file_size = os.path.getsize(filepath)
                if file_size > 0:  # Игнорируем пустые файлы (они все "одинаковы")
                    size_groups[file_size].append(filepath)
                    total_files += 1
            except OSError:
                continue

    # Оставляем только группы, где больше 1 файла (кандидаты на дубли)
    candidates = {size: paths for size, paths in size_groups.items() if len(paths) > 1}
    candidate_count = sum(len(paths) for paths in candidates.values())
    unique_by_size_count = total_files - candidate_count

    print(f"   ✅ Всего файлов проверено: {total_files}")
    print(f"   🔍 Кандидатов на дубли (одинаковый размер): {candidate_count} ({len(candidates)} групп)")
    print(f"   ⏭️  Отсечено как уникальные по размеру: {unique_by_size_count}")

    if candidate_count == 0:
        print("🎉 Дубликатов не найдено!")
        return {}

    print(f"\n🧮 Этап 2: Вычисление SHA-256 для {candidate_count} файлов-кандидатов...")

    hash_groups = defaultdict(list)
    processed = 0

    for size, paths in candidates.items():
        for filepath in paths:
            processed += 1
            if processed % 50 == 0:
                print(f"\r  Вычислено хешей: {processed}/{candidate_count}", end="", flush=True)

            file_hash = get_file_hash(filepath)
            if file_hash:
                hash_groups[file_hash].append(filepath)

    # Оставляем только точные дубликаты (где хеш совпал и файлов > 1)
    exact_duplicates = {h: paths for h, paths in hash_groups.items() if len(paths) > 1}

    print(f"\n   ✅ Найдено точных групп дубликатов: {len(exact_duplicates)}")

    # Вывод статистики по сэкономленному месту
    saved_space = 0
    for paths in exact_duplicates.values():
        # Размер одного файла * (количество дублей)
        saved_space += os.path.getsize(paths[0]) * (len(paths) - 1)

    print(f"   💾 Потенциально освобождаемое место: {format_size(saved_space)}")

    return exact_duplicates