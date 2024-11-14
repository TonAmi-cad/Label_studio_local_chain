import os
import logging
from label_studio_client import LabelStudioManager
from typing import Dict, Any, Optional
from tenacity import retry, stop_after_attempt, wait_exponential

logger = logging.getLogger(__name__)

class StorageManager:
    def __init__(self, label_studio_client: LabelStudioManager):
        self.client = label_studio_client
        
        # Используем правильный корневой путь из переменных окружения
        self.document_root = os.getenv('LABEL_STUDIO_LOCAL_FILES_DOCUMENT_ROOT', '/data/files')
        # Путь для хранения файлов должен быть внутри document_root
        self.data_dir = os.path.join(self.document_root, 'augmented_images')
        
        # Проверяем и создаем директории
        self.validate_paths()

    def validate_paths(self):
        """Проверка и создание необходимых путей"""
        try:
            # Создаем корневую директорию если её нет
            if not os.path.exists(self.document_root):
                logger.info(f"Создание корневой директории: {self.document_root}")
                os.makedirs(self.document_root, exist_ok=True)
            
            # Создаем директорию для файлов
            if not os.path.exists(self.data_dir):
                logger.info(f"Создание директории для файлов: {self.data_dir}")
                os.makedirs(self.data_dir, exist_ok=True)
                
            # Проверяем права доступа
            os.chmod(self.document_root, 0o755)
            os.chmod(self.data_dir, 0o755)
            
        except Exception as e:
            logger.error(f"Ошибка при создании директорий: {e}")
            raise

    @retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=4, max=10))
    def create_storage(self) -> Dict[str, Any]:
        """Создание локального хранилища"""
        try:
            project_id = self.client.get_project_id()
            
            # Используем абсолютный путь внутри контейнера
            storage_path = '/data/files/augmented_images'  # Абсолютный путь
            
            payload = {
                "type": "localfiles",
                "title": os.getenv('LABEL_STUDIO_PROJECT_NAME', 'Local Images Storage'),
                "path": storage_path,  # Используем абсолютный путь
                "regex_filter": r".*\.(jpg|jpeg|png)",
                "use_blob_urls": True,
                "presign": False,
                "project": project_id
            }
            
            logger.info(f"Создание хранилища с параметрами: {payload}")
            
            response = self.client.client.make_request(
                "POST",
                f"/api/storages/localfiles",
                json=payload
            )
            
            storage_info = response.json()
            logger.info(f"Создано локальное хранилище: {storage_info}")
            return storage_info
            
        except Exception as e:
            logger.error(f"Ошибка создания хранилища: {e}")
            raise

    def sync_storage(self, storage_id: int, scan_all: bool = False):
        """Синхронизация хранилища"""
        try:
            # Сначала проверяем существование директории
            if not os.path.exists(self.data_dir):
                raise ValueError(f"Directory {self.data_dir} does not exist")
            
            # Проверяем наличие файлов
            files = os.listdir(self.data_dir)
            if not files:
                logger.warning(f"Directory {self.data_dir} is empty")
            
            logger.info(f"Found {len(files)} files in {self.data_dir}")
            
            # Выполняем синхронизацию через API
            sync_url = f"/api/storages/localfiles/{storage_id}/sync"
            response = self.client.client.make_request(
                "POST", 
                sync_url,
                json={
                    "scan_all": scan_all,
                    "project": self.client.get_project_id(),
                    "params": {
                        "path": self.data_dir,
                        "regex_filter": r".*\.(jpg|jpeg|png)"
                    }
                }
            )
            
            sync_result = response.json()
            logger.info(f"Синхронизация хранилища {storage_id}: {sync_result}")
            return sync_result
            
        except Exception as e:
            logger.error(f"Ошибка синхронизации хранилища: {e}")
            raise

    def validate_storage(self, storage_id: int):
        """Валидация хранилища и проверка доступа к файлам"""
        logger.info(f"Начало валидации хранилища {storage_id}")
        
        try:
            # Сначала проверяем существование хранилища
            storages = self.list_storages()
            if not any(s['id'] == storage_id for s in storages):
                raise ValueError(f"Storage with ID {storage_id} does not exist")
            
            # Проверяем содержимое директорий
            for path in [self.document_root, self.data_dir]:
                logger.info(f"Проверка директории {path}")
                try:
                    files = os.listdir(path)
                    logger.info(f"Файлы в {path}: {files[:10]}...")
                    logger.info(f"Всего файлов: {len(files)}")
                    logger.info(f"Права доступа: {oct(os.stat(path).st_mode)[-3:]}")
                except Exception as e:
                    logger.error(f"Ошибка при проверке директории {path}: {e}")

            # Используем правильный эндпоинт для валидации
            response = self.client.client.make_request(
                'GET',  # Изменено с POST на GET
                f'/api/storages/localfiles/{storage_id}',  # Изменен эндпоинт
                params={'validate': 'true'}  # Добавлен параметр validate
            )
            validation_result = response.json()
            logger.info(f"Результат валидации: {validation_result}")
            return validation_result
            
        except Exception as e:
            logger.error(f"Ошибка при валидации хранилища: {e}")
            raise
        
    def list_storages(self):
        """Получение списка хранилищ"""
        try:
            # Получаем ID проекта
            project_id = self.client.get_project_id()
            
            # Добавляем project_id в URL запроса
            response = self.client.client.make_request(
                "GET", 
                f"/api/storages/localfiles?project={project_id}"
            )
            return response.json()
        except Exception as e:
            logger.error(f"Ошибка получения списка хранилищ: {e}")
            raise

    def delete_storage(self, storage_id: int):
        """Удаление хранилища"""
        try:
            response = self.client.client.make_request(
                "DELETE", 
                f"/api/storages/localfiles/{storage_id}"
            )
            return response.status_code == 204
        except Exception as e:
            logger.error(f"Ошибка удаления хранилища: {e}")
            raise

    def update_storage(self, 
        storage_id: int,
        title: str = None,
        path: str = None,
        regex_filter: str = None,
        use_blob_urls: bool = None,
        presign: bool = None,
        description: str = None
    ):
        """Обновление параметров хранилища"""
        try:
            payload = {k: v for k, v in {
                'title': title,
                'path': path,
                'regex_filter': regex_filter,
                'use_blob_urls': use_blob_urls,
                'presign': presign,
                'description': description
            }.items() if v is not None}
            
            response = self.client.client.make_request(
                "PATCH",
                f"/api/storages/localfiles/{storage_id}",
                json=payload
            )
            return response.json()
        except Exception as e:
            logger.error(f"Ошибка обновления хранилища: {e}")
            raise
