import os
import time
from typing import List, Set, Dict, Any
from webdav3.client import Client
from webdav3.exceptions import RemoteResourceNotFound
from .cloud_base import CloudDriveManager


class YandexCloudManager(CloudDriveManager):
    def __init__(self, token: str, timeout: int = 60):
        # Яндекс.Диск принимает OAuth-токен в качестве пароля или через специальный параметр
        self.client = Client({
            'webdav_hostname': "https://webdav.yandex.ru",
            'webdav_login': "oauth",  # Фиктивное имя для WebDAV
            'webdav_password': token,  # OAuth токен
            'webdav_root': "",
            'timeout': timeout
        })

    def connect(self) -> bool:
        try:
            return self.client.check()
        except Exception:
            return False

    def _list_folder_safe(self, folder_path: str) -> List[str]:
        for attempt in range(3):
            try:
                time.sleep(0.15)
                return self.client.list(folder_path)
            except RemoteResourceNotFound:
                return []
            except Exception:
                if attempt == 2:
                    return []
                time.sleep(1.5)
        return []

    def _traverse_recursive(self, folder_path: str, extensions: Set[str], return_paths: bool) -> List[str] | Set[str]:
        results = set() if not return_paths else []
        queue = [folder_path]

        while queue:
            current = queue.pop(0)
            for item in self._list_folder_safe(current):
                item_clean = item.rstrip('/')
                if item_clean.startswith('.') or item_clean.startswith('~'):
                    continue

                full_path = f"{current}/{item_clean}"

                if '.' in item_clean and not item_clean.startswith('.'):
                    ext = os.path.splitext(item_clean)[1].lower()
                    if ext in extensions:
                        if return_paths:
                            results.append(full_path)  # type: ignore
                        else:
                            results.add(item_clean)  # type: ignore
                else:
                    queue.append(full_path)

        return results

    def get_media_file_names_recursive(self, folder_path: str, extensions: Set[str]) -> Set[str]:
        return self._traverse_recursive(folder_path, extensions, return_paths=False)  # type: ignore

    def get_media_file_paths_recursive(self, folder_path: str, extensions: Set[str]) -> List[str]:
        return self._traverse_recursive(folder_path, extensions, return_paths=True)  # type: ignore

    def delete_file(self, file_path: str) -> bool:
        try:
            time.sleep(0.2)
            self.client.clean(file_path)
            return True
        except Exception as e:
            from core.logger import setup_logger
            logger = setup_logger()
            error_msg = f"Ошибка удаления из облака {file_path}: {e}"
            logger.error(error_msg)
            return False

    def get_file_info(self, file_path: str) -> Dict[str, Any]:
        try:
            return self.client.info(file_path)
        except Exception:
            return {}

    def move_file(self, source_path: str, dest_path: str) -> bool:
        try:
            self.client.move(source_path, dest_path)
            return True
        except Exception as e:
            from core.logger import setup_logger
            logger = setup_logger()
            error_msg = f"Ошибка перемещения в облаке {source_path} -> {dest_path}: {e}"
            logger.error(error_msg)
            return False