import os
import sys
import argparse
from dotenv import load_dotenv
from core.file_utils import load_config, get_extensions, get_excluded_folders
from core.cloud_mailru import MailRuCloudManager
from core.cloud_yandex import YandexCloudManager
from core.cloud_google import GoogleDriveManager
from local_collector import collect_files
from cloud_deduplicator import deduplicate_cloud_folder
from pc_cloud_comparator import compare_pc_and_cloud
from deduplicator import find_duplicates_optimized
from report_generator import generate_html_report
from safe_mover import move_duplicates_to_review


def get_cloud_manager(provider: str):
    """Создает экземпляр CloudDriveManager в зависимости от провайдера."""
    if provider.lower() == 'mailru':
        login = os.getenv("CLOUD_LOGIN", "")
        password = os.getenv("CLOUD_PASSWORD", "")
        if not login or not password:
            print("❌ Ошибка: Укажите CLOUD_LOGIN и CLOUD_PASSWORD в .env файле")
            sys.exit(1)
        return MailRuCloudManager(login, password)

    elif provider.lower() == 'yandex':
        token = os.getenv("CLOUD_YANDEX_TOKEN", "")
        if not token:
            print("❌ Ошибка: Укажите CLOUD_YANDEX_TOKEN в .env файле")
            sys.exit(1)
        return YandexCloudManager(token)

    elif provider.lower() == 'google':
        creds_file = os.getenv("CLOUD_GOOGLE_CREDENTIALS_FILE", "credentials.json")
        return GoogleDriveManager(credentials_file=creds_file)

    else:
        print(f"❌ Ошибка: Неизвестный провайдер '{provider}'. Используйте: mailru, yandex, google")
        sys.exit(1)


def main():
    # Загружаем переменные окружения из .env
    load_dotenv()

    # Загружаем конфигурацию
    try:
        config = load_config()
    except Exception as e:
        print(f"❌ Ошибка загрузки конфигурации: {e}")
        sys.exit(1)

    # Парсим аргументы командной строки
    parser = argparse.ArgumentParser(
        description="Unified Media Manager - инструмент для сбора, дедупликации и синхронизации файлов",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Примеры использования:
  python main.py collect_local --category media
  python main.py dedup_cloud --provider mailru --category media
  python main.py compare_pc_cloud --provider yandex --category documents
  python main.py audit_local --folder D:/Media --category media
        """
    )

    parser.add_argument(
        "action",
        choices=["collect_local", "dedup_cloud", "compare_pc_cloud", "audit_local"],
        help="Действие для выполнения"
    )

    parser.add_argument(
        "--provider",
        choices=["mailru", "yandex", "google"],
        default="mailru",
        help="Облачный провайдер (по умолчанию: mailru)"
    )

    parser.add_argument(
        "--category",
        choices=["media", "documents"],
        default="media",
        help="Категория файлов (по умолчанию: media)"
    )

    parser.add_argument(
        "--folder",
        type=str,
        help="Путь к папке для действия audit_local"
    )

    args = parser.parse_args()

    # Получаем настройки из конфига
    extensions = get_extensions(config, args.category)
    excluded_folders = get_excluded_folders(config, args.category)

    # Получаем флаг DRY_RUN из .env
    dry_run = os.getenv("DRY_RUN", "True").lower() in ("true", "1", "yes")

    # Выполняем выбранное действие
    if args.action == "collect_local":
        print(f"\n🚀 Запуск: Сбор {args.category} файлов с локального диска\n")

        source_key = f"LOCAL_{args.category.upper()}_SOURCE"
        dest_key = f"LOCAL_{args.category.upper()}_DEST"

        source = os.getenv(source_key)
        dest = os.getenv(dest_key)

        if not source or not dest:
            print(f"❌ Ошибка: Укажите {source_key} и {dest_key} в .env файле")
            sys.exit(1)

        collect_files({
            'source_dir': source,
            'destination_dir': dest,
            'extensions': extensions,
            'excluded_folders': excluded_folders
        })

    elif args.action == "dedup_cloud":
        print(f"\n🚀 Запуск: Очистка дубликатов {args.category} в облаке ({args.provider})\n")

        cloud_manager = get_cloud_manager(args.provider)

        if not cloud_manager.connect():
            print(f"❌ Ошибка подключения к {args.provider}. Проверьте учетные данные в .env")
            sys.exit(1)

        primary_folder = os.getenv("CLOUD_PRIMARY_FOLDER", "/фото")
        secondary_folder = os.getenv("CLOUD_SECONDARY_FOLDER", "/copy/фото")

        deduplicate_cloud_folder(
            cloud_manager=cloud_manager,
            primary_folder=primary_folder,
            secondary_folder=secondary_folder,
            extensions=extensions,
            dry_run=dry_run
        )

    elif args.action == "compare_pc_cloud":
        print(f"\n🚀 Запуск: Сверка {args.category} файлов между ПК и Облаком ({args.provider})\n")

        cloud_manager = get_cloud_manager(args.provider)

        if not cloud_manager.connect():
            print(f"❌ Ошибка подключения к {args.provider}. Проверьте учетные данные в .env")
            sys.exit(1)

        local_folder = os.getenv("COMPARE_LOCAL_FOLDER")
        cloud_folder = os.getenv("COMPARE_CLOUD_FOLDER", "/фото")

        if not local_folder:
            print("❌ Ошибка: Укажите COMPARE_LOCAL_FOLDER в .env файле")
            sys.exit(1)

        compare_pc_and_cloud(
            local_folder=local_folder,
            cloud_folder=cloud_folder,
            cloud_manager=cloud_manager,
            extensions=extensions
        )

    elif args.action == "audit_local":
        print(f"\n🚀 Запуск: Визуальная проверка дубликатов в локальной папке\n")

        folder = args.folder
        if not folder:
            print("❌ Ошибка: Укажите --folder для действия audit_local")
            sys.exit(1)

        # 1. Находим дубликаты
        duplicates = find_duplicates_optimized(folder, extensions)

        if not duplicates:
            print("\n🎉 Дубликатов не найдено!")
            return

        # 2. Генерируем HTML-отчет
        generate_html_report(duplicates, "duplicates_report.html")

        # 3. Спрашиваем подтверждение
        print("\n" + "=" * 60)
        print("👁️ Откройте файл 'duplicates_report.html' в браузере для визуальной проверки.")
        print("=" * 60)

        if dry_run:
            print("\n🛑 ТЕСТОВЫЙ РЕЖИМ (DRY_RUN=True). Файлы НЕ будут перемещены.")
            print("Чтобы начать перемещение, измените в .env: DRY_RUN=False")
        else:
            response = input("\n⚠️ Вы уверены, что хотите переместить дубликаты в папку 'На_проверку'? (да/нет): ")
            if response.lower() in ('да', 'yes', 'y', 'д'):
                review_folder = os.getenv("REVIEW_FOLDER", "D:/На_проверку")
                move_duplicates_to_review(duplicates, review_folder)
            else:
                print("❌ Операция отменена пользователем.")


if __name__ == "__main__":
    main()