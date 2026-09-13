import os
from pathlib import Path
from typing import Dict, List, Set
from core.cloud_base import CloudDriveManager
from core.file_utils import format_size


def compare_pc_and_cloud(
        local_folder: str,
        cloud_folder: str,
        cloud_manager: CloudDriveManager,
        extensions: Set[str]
) -> Dict[str, List[str]]:
    """
    Сравнивает файлы на локальном ПК и в облаке по именам и размерам.

    :param local_folder: Путь к локальной папке
    :param cloud_folder: Путь к папке в облаке
    :param cloud_manager: Экземпляр CloudDriveManager
    :param extensions: Множество расширений для обработки
    :return: Словарь с ключами:
             - 'only_local': файлы только на ПК
             - 'only_cloud': файлы только в облаке
             - 'both_same_size': файлы везде с одинаковым размером
             - 'both_diff_size': файлы везде, но с разным размером
    """
    print(f"\n{'=' * 60}")
    print(f"🔄 Сверка файлов между ПК и Облаком")
    print(f"{'=' * 60}")
    print(f"💻 Локальная папка: {local_folder}")
    print(f"☁️ Облачная папка: {cloud_folder}")
    print(f"{'=' * 60}\n")

    # 1. Сканируем локальную папку
    print(f"📂 Сканирование локальной папки...")
    local_files = {}
    local_path = Path(local_folder).resolve()

    if not local_path.exists():
        print(f"❌ Локальная папка не найдена: {local_folder}")
        return {'only_local': [], 'only_cloud': [], 'both_same_size': [], 'both_diff_size': []}

    for root, _, files in os.walk(local_path):
        for filename in files:
            if Path(filename).suffix.lower() in extensions:
                filepath = os.path.join(root, filename)
                try:
                    size = os.path.getsize(filepath)
                    local_files[filename] = {'path': filepath, 'size': size}
                except OSError:
                    continue

    print(f"   ✅ Найдено локальных файлов: {len(local_files)}")

    # 2. Сканируем облачную папку
    print(f"\n☁️ Сканирование облачной папки...")
    cloud_paths = cloud_manager.get_media_file_paths_recursive(cloud_folder, extensions)
    cloud_files = {}

    for c_path in cloud_paths:
        filename = os.path.basename(c_path)
        info = cloud_manager.get_file_info(c_path)
        size = int(info.get('size', 0)) if info else 0

        # Если файл с таким именем уже есть, добавляем счетчик для уникальности
        base_name = filename
        counter = 1
        while filename in cloud_files:
            stem = Path(base_name).stem
            ext = Path(base_name).suffix
            filename = f"{stem}_{counter}{ext}"
            counter += 1

        cloud_files[filename] = {'path': c_path, 'size': size}

    print(f"   ✅ Найдено облачных файлов: {len(cloud_files)}")

    # 3. Сравниваем
    local_names = set(local_files.keys())
    cloud_names = set(cloud_files.keys())

    only_local = []
    only_cloud = []
    both_same_size = []
    both_diff_size = []

    # Файлы только на ПК
    for name in local_names - cloud_names:
        only_local.append(local_files[name]['path'])

    # Файлы только в облаке
    for name in cloud_names - local_names:
        only_cloud.append(cloud_files[name]['path'])

    # Файлы везде
    for name in local_names & cloud_names:
        l_size = local_files[name]['size']
        c_size = cloud_files[name]['size']

        if l_size == c_size:
            both_same_size.append(f"{name} ({format_size(l_size)})")
        else:
            both_diff_size.append(f"{name} (ПК: {format_size(l_size)}, Облако: {format_size(c_size)})")

    # 4. Вывод результатов
    print(f"\n{'=' * 60}")
    print(f"📊 Результаты сверки:")
    print(f"{'=' * 60}")
    print(f"📁 Только на ПК: {len(only_local)}")
    print(f"☁️ Только в облаке: {len(only_cloud)}")
    print(f"✅ Присутствуют везде (размер совпадает): {len(both_same_size)}")
    print(f"⚠️ Присутствуют везде (размер отличается): {len(both_diff_size)}")
    print(f"{'=' * 60}\n")

    # Показываем первые 10 примеров из каждой категории
    if only_local:
        print(f"📁 Примеры файлов только на ПК:")
        for item in only_local[:10]:
            print(f"  └─ {os.path.basename(item)}")
        if len(only_local) > 10:
            print(f"  ... и еще {len(only_local) - 10} файлов.\n")

    if only_cloud:
        print(f"☁️ Примеры файлов только в облаке:")
        for item in only_cloud[:10]:
            print(f"  └─ {item}")
        if len(only_cloud) > 10:
            print(f"  ... и еще {len(only_cloud) - 10} файлов.\n")

    if both_diff_size:
        print(f"⚠️ Примеры файлов с разным размером:")
        for item in both_diff_size[:10]:
            print(f"  └─ {item}")
        if len(both_diff_size) > 10:
            print(f"  ... и еще {len(both_diff_size) - 10} файлов.\n")

    return {
        'only_local': only_local,
        'only_cloud': only_cloud,
        'both_same_size': both_same_size,
        'both_diff_size': both_diff_size
    }