from abc import ABC, abstractmethod
from typing import List, Set, Dict, Any


class CloudDriveManager(ABC):
    """Абстрактный базовый класс для работы с облачными хранилищами."""

    @abstractmethod
    def connect(self) -> bool:
        """Проверяет подключение и аутентификацию."""
        pass

    @abstractmethod
    def get_media_file_names_recursive(self, folder_path: str, extensions: Set[str]) -> Set[str]:
        """
        Рекурсивно получает множество имен файлов в папке.
        Используется для быстрого поиска дубликатов по имени.
        """
        pass

    @abstractmethod
    def get_media_file_paths_recursive(self, folder_path: str, extensions: Set[str]) -> List[str]:
        """
        Рекурсивно получает список полных путей к файлам в папке.
        Используется для получения метаданных или удаления.
        """
        pass

    @abstractmethod
    def delete_file(self, file_path: str) -> bool:
        """Удаляет файл по полному пути в облаке."""
        pass

    @abstractmethod
    def get_file_info(self, file_path: str) -> Dict[str, Any]:
        """Получает метаданные файла (например, размер, дату изменения)."""
        pass

    @abstractmethod
    def move_file(self, source_path: str, dest_path: str) -> bool:
        """Перемещает файл внутри облака (используется для папки 'На проверку')."""
        pass