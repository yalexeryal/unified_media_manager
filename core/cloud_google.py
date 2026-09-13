import os
import time
from typing import List, Set, Dict, Any
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
from .cloud_base import CloudDriveManager

# Scope для доступа к файлам Google Drive
SCOPES = ['https://www.googleapis.com/auth/drive']


class GoogleDriveManager(CloudDriveManager):
    def __init__(self, credentials_file: str = "credentials.json", token_file: str = "token.json"):
        self.credentials_file = credentials_file
        self.token_file = token_file
        self.service = None
        self._creds = None

    def _get_credentials(self):
        if os.path.exists(self.token_file):
            self._creds = Credentials.from_authorized_user_file(self.token_file, SCOPES)

        if not self._creds or not self._creds.valid:
            if self._creds and self._creds.expired and self._creds.refresh_token:
                self._creds.refresh(Request())  # type: ignore
            else:
                if not os.path.exists(self.credentials_file):
                    raise FileNotFoundError(
                        f"Файл {self.credentials_file} не найден. Скачайте его из Google Cloud Console.")
                flow = InstalledAppFlow.from_client_secrets_file(self.credentials_file, SCOPES)
                self._creds = flow.run_local_server(port=0)

            with open(self.token_file, 'w', encoding='utf-8') as token:
                token.write(self._creds.to_json())

        return self._creds

    def connect(self) -> bool:
        try:
            creds = self._get_credentials()
            self.service = build('drive', 'v3', credentials=creds)
            # Простая проверка: запрашиваем информацию о диске
            self.service.about().get(fields="storageQuota").execute()
            return True
        except Exception as e:
            print(f"❌ Ошибка подключения к Google Drive: {e}")
            return False

    def _get_folder_id(self, folder_path: str) -> str | None:
        """Преобразует путь вида '/фото/отпуск' в ID папки Google Drive."""
        if folder_path == '/' or not folder_path:
            return 'root'

        parts = [p for p in folder_path.split('/') if p]
        current_id = 'root'

        for part in parts:
            try:
                # Ищем папку с таким именем внутри текущей
                query = f"name='{part}' and mimeType='application/vnd.google-apps.folder' and '{current_id}' in parents and trashed=false"
                results = self.service.files().list(q=query, spaces='drive', fields="files(id, name)").execute()
                items = results.get('files', [])
                if not items:
                    return None  # Папка не найдена
                current_id = items[0]['id']
            except HttpError:
                return None
        return current_id

    def _traverse_recursive(self, folder_path: str, extensions: Set[str], return_paths: bool) -> List[str] | Set[str]:
        folder_id = self._get_folder_id(folder_path)
        if not folder_id:
            print(f"⚠️ Папка '{folder_path}' не найдена в Google Drive.")
            return set() if not return_paths else []

        results = set() if not return_paths else []
        query = f"mimeType!='application/vnd.google-apps.folder' and '{folder_id}' in parents and trashed=false"

        # Для рекурсивного обхода нам нужно получить все файлы во всех подпапках.
        # В Google Drive проще запросить все файлы, которые находятся ВНУТРИ иерархии этой папки.
        # Но API не поддерживает рекурсивный поиск по имени папки напрямую без сложных запросов.
        # Поэтому мы сделаем рекурсивный обход вручную, как в WebDAV, но через API.

        queue = [folder_id]
        path_cache = {folder_id: folder_path.rstrip('/')}  # Кэш путей для return_paths=True

        while queue:
            current_id = queue.pop(0)
            current_path = path_cache.get(current_id, "")

            page_token = None
            while True:
                try:
                    time.sleep(0.1)  # Защита от quota exceeded
                    response = self.service.files().list(
                        q=f"'{current_id}' in parents and trashed=false",
                        spaces='drive',
                        fields="nextPageToken, files(id, name, mimeType, size)",
                        pageToken=page_token
                    ).execute()

                    for item in response.get('files', []):
                        name = item['name']
                        mime = item['mimeType']
                        item_id = item['id']

                        if mime == 'application/vnd.google-apps.folder':
                            queue.append(item_id)
                            if return_paths:
                                path_cache[item_id] = f"{current_path}/{name}"
                        else:
                            ext = os.path.splitext(name)[1].lower()
                            if ext in extensions:
                                if return_paths:
                                    results.append(f"{current_path}/{name}")  # type: ignore
                                else:
                                    results.add(name)  # type: ignore

                    page_token = response.get('nextPageToken')
                    if not page_token:
                        break
                except HttpError as e:
                    print(f"  ⚠️ Ошибка API при обходе {current_path}: {e}")
                    break

        return results

    def get_media_file_names_recursive(self, folder_path: str, extensions: Set[str]) -> Set[str]:
        return self._traverse_recursive(folder_path, extensions, return_paths=False)  # type: ignore

    def get_media_file_paths_recursive(self, folder_path: str, extensions: Set[str]) -> List[str]:
        return self._traverse_recursive(folder_path, extensions, return_paths=True)  # type: ignore

    def delete_file(self, file_path: str) -> bool:
        # В Google Drive удаление по пути сложнее, нужен ID.
        # Для упрощения, здесь мы предполагаем, что file_path передается как полный путь,
        # и мы должны сначала найти его ID. В реальном use-case лучше передавать ID.
        # Для совместимости интерфейса реализуем поиск по имени в родительской папке.
        try:
            parent_dir = os.path.dirname(file_path) or '/'
            file_name = os.path.basename(file_path)
            parent_id = self._get_folder_id(parent_dir)

            if not parent_id:
                return False

            query = f"name='{file_name}' and '{parent_id}' in parents and trashed=false"
            results = self.service.files().list(q=query, spaces='drive', fields="files(id)").execute()
            items = results.get('files', [])

            if items:
                self.service.files().delete(fileId=items[0]['id']).execute()
                return True
            return False
        except Exception as e:
            print(f"  ❌ Ошибка удаления {file_path}: {e}")
            return False

    def get_file_info(self, file_path: str) -> Dict[str, Any]:
        try:
            parent_dir = os.path.dirname(file_path) or '/'
            file_name = os.path.basename(file_path)
            parent_id = self._get_folder_id(parent_dir)

            if not parent_id:
                return {}

            query = f"name='{file_name}' and '{parent_id}' in parents and trashed=false"
            results = self.service.files().list(q=query, spaces='drive', fields="files(size)").execute()
            items = results.get('files', [])

            if items:
                return {'size': items[0].get('size', 0)}
            return {}
        except Exception:
            return {}

    def move_file(self, source_path: str, dest_path: str) -> bool:
        print(f"  ⚠️ Перемещение в Google Drive требует сложной логики (смена родителей). Реализовано заглушкой.")
        # Для полноценной реализации нужно: 1. Найти ID файла. 2. Найти ID целевой папки.
        # 3. service.files().update(fileId=id, addParents=dest_id, removeParents=source_id)
        return False