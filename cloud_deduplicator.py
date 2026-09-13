import os
from typing import Set, Dict, List
from core.cloud_base import CloudDriveManager
from core.file_utils import format_size
from core.logger import setup_logger, get_log_file_path


def deduplicate_cloud_folder(
        cloud_manager: CloudDriveManager,
        primary_folder: str,
        secondary_folder: str,
        extensions: Set[str],
        dry_run: bool = True
) -> Dict[str, List[str]]:
    """
    Ищет и удаляет дубликаты медиафайлов в облаке.
    """
    logger = setup_logger()

    print(f"\n{'=' * 60}")
    print(f"🔍 Поиск дубликатов в облаке")
    print(f"{'=' * 60}")
    print(f"📁 Основная папка (оригиналы): {primary_folder}")
    print(f"📁 Вторичная папка (копии): {secondary_folder}")
    print(f"🔒 Режим: {'ТЕСТОВЫЙ (ничего не удаляется)' if dry_run else 'РЕАЛЬНОЕ УДАЛЕНИЕ'}")
    print(f"{'=' * 60}\n")

    # 1. Сканируем основную папку (нам нужны только имена)
    print(f"📂 Этап 1: Сканирование '{primary_folder}'...")
    primary_names = cloud_manager.get_media_file_names_recursive(primary_folder, extensions)
    print(f"   ✅ Найдено уникальных имен файлов: {len(primary_names)}")

    if len(primary_names) == 0:
        error_msg = f"В папке '{primary_folder}' не найдено файлов с указанными расширениями"
        print(f"\n⚠️ ВНИМАНИЕ: {error_msg}")
        logger.warning(error_msg)
        return {}

    # 2. Сканируем вторичную папку (нам нужны полные пути)
    print(f"\n📂 Этап 2: Сканирование '{secondary_folder}'...")
    secondary_paths = cloud_manager.get_media_file_paths_recursive(secondary_folder, extensions)
    print(f"   ✅ Найдено файлов во вторичной папке: {len(secondary_paths)}")

    # 3. Ищем совпадения по именам
    duplicates = {}
    for file_path in secondary_paths:
        file_name = os.path.basename(file_path)
        if file_name in primary_names:
            if file_name not in duplicates:
                duplicates[file_name] = []
            duplicates[file_name].append(file_path)

    if not duplicates:
        print("\n✨ Дубликатов не найдено. Нечего удалять.")
        return {}

    # 4. Вывод результатов
    total_duplicates = sum(len(paths) for paths in duplicates.values())
    print(f"\n⚠️ Найдено {total_duplicates} дубликатов в {len(duplicates)} группах:")

    # Показываем первые 20 файлов
    shown = 0
    for name, paths in list(duplicates.items())[:20]:
        print(f"  📄 {name}:")
        for path in paths:
            print(f"     └─ {path}")
        shown += len(paths)

    if total_duplicates > shown:
        print(f"  ... и еще {total_duplicates - shown} файлов.")

    # 5. Удаление или перемещение
    if dry_run:
        print(f"\n🛑 ТЕСТОВЫЙ РЕЖИМ. Файлы НЕ были удалены.")
        print("Чтобы начать удаление, измените в .env файле: DRY_RUN=False")
    else:
        print(f"\n🗑️ Начинаем удаление дубликатов...")
        deleted_count = 0
        failed_count = 0

        for name, paths in duplicates.items():
            for file_path in paths:
                if cloud_manager.delete_file(file_path):
                    deleted_count += 1
                    print(f"  ✅ Удалено: {name}")
                else:
                    failed_count += 1
                    error_msg = f"Не удалось удалить файл из облака: {file_path}"
                    logger.error(error_msg)

        print(f"\n{'=' * 60}")
        print(f"🎉 Готово!")
        print(f"  ✅ Удалено файлов: {deleted_count}")
        if failed_count > 0:
            print(f"  ❌ Ошибок при удалении: {failed_count}")
            log_path = get_log_file_path()
            print(f"  📋 Подробный лог ошибок: {log_path}")
        print(f"{'=' * 60}")

    return duplicates