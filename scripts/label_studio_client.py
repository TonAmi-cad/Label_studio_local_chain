from label_studio_sdk import Client
import logging
from typing import Dict, Any, Optional
from tenacity import retry, stop_after_attempt, wait_exponential
import os
from dotenv import load_dotenv
import time
import subprocess
import json

load_dotenv()

logger = logging.getLogger(__name__)

class LabelStudioManager:
    def __init__(self, url: str = None, api_key: str = None):
        # Проверка конфигурации перед инициализацией
        self.validate_env_config()

        # Более надежное определение URL
        self.url = url or os.getenv('LABEL_STUDIO_URL') or os.getenv('LABEL_STUDIO_URL')
        self.api_key = api_key or os.getenv('LABEL_STUDIO_API_KEY')
        
        if not self.url or not self.api_key:
            raise ValueError("URL и API ключ должны быть установлены в .env")
        
        self.client = self._initialize_client()
        self.project_name = os.getenv('LABEL_STUDIO_PROJECT_NAME', 'Default Project')
        self.project = self._get_or_create_project()

    @classmethod
    def validate_env_config(cls):
        """
        Проверка корректности конфигурации Label Studio в .env
        """
        required_vars = [
            'LABEL_STUDIO_URL', 
            'LABEL_STUDIO_API_KEY', 
            'LABEL_STUDIO_USERNAME', 
            'LABEL_STUDIO_PASSWORD',
            'LABEL_STUDIO_PROJECT_NAME'
        ]
        
        missing_vars = [var for var in required_vars if not os.getenv(var)]
        
        if missing_vars:
            logger.error(f"Отсутствуют обязательные переменные: {', '.join(missing_vars)}")
            raise ValueError(f"Не все обязательные переменные установлены: {missing_vars}")
        
        logger.info("Конфигурация Label Studio в .env проверена успешно")
        return True

    def validate_connection(self):
        try:
            version = self.client.check_connection()
            logger.info(f"Подключение к Label Studio установлено. Версия: {version}")
            return True
        except Exception as e:
            logger.error(f"Ошибка подключения к Label Studio: {e}")
            return False

    @retry(stop=stop_after_attempt(5), wait=wait_exponential(multiplier=2, min=4, max=30))
    def _initialize_client(self) -> Client:
        try:
            # Используем только URL и API ключ
            client = Client(
                url=self.url, 
                api_key=self.api_key
            )
            logger.info("Успешное подключение к Label Studio")
            return client
        except Exception as e:
            logger.error(f"Ошибка подключения к Label Studio: {e}")
            raise

    def get_project_name(self, project_id=None):
        """
        Получает имя проекта по его ID или текущего проекта.
        
        :param project_id: Необязательный ID проекта. Если не указан, используется текущий проект.
        :return: Название проекта
        """
        try:
            # Если ID не передан, используем текущий проект
            if project_id is None:
                logger.debug("ID проекта не указан, используем текущий проект")
                if not self.project or 'id' not in self.project:
                    logger.info("Текущий проект не инициализирован, пытаемся создать")
                    self.project = self._get_or_create_project()
                project_id = self.project['id']
            
            logger.debug(f"Получение имени проекта для ID: {project_id}")
            
            # Получаем детали проекта по ID
            project_details = self.client.get_project(project_id)
            project_name = project_details.get('title', '')
            
            logger.info(f"Успешно получено имя проекта: {project_name}")
            return project_name
        
        except Exception as e:
            logger.error(f"Ошибка получения имени проекта для ID {project_id}: {e}", exc_info=True)
            return None

    def normalize_project_name(self, name):
        """
        Нормализует имя проекта для корректного сравнения.
        
        :param name: Исходное имя проекта
        :return: Нормализованное имя
        """
        try:
            # Проверка входных данных
            if not name:
                logger.warning("Передано пустое имя проекта")
                return ''
            
            # Нормализация
            normalized_name = name.strip().lower().replace(' ', '')
            
            logger.debug(f"Нормализация имени: '{name}' -> '{normalized_name}'")
            return normalized_name
        
        except Exception as e:
            logger.error(f"Ошибка нормализации имени проекта: {e}", exc_info=True)
            return name  # Возвращаем оригинальное имя в случае ошибки

    def is_project_name_match(self, project_name, target_name):
        """
        Проверяет соответствие имен проектов с учетом нормализации.
        
        :param project_name: Имя проекта для сравнения
        :param target_name: Целевое имя проекта
        :return: Boolean - совпадают ли имена
        """
        try:
            # Проверка входных данных
            if not project_name or not target_name:
                logger.warning(f"Одно из имен пустое. project_name: {project_name}, target_name: {target_name}")
                return False
            
            # Нормализация и сравнение
            normalized_project_name = self.normalize_project_name(project_name)
            normalized_target_name = self.normalize_project_name(target_name)
            
            result = normalized_project_name == normalized_target_name
            
            logger.debug(
                f"Сравнение имен проектов: "
                f"'{project_name}' (normalized: '{normalized_project_name}') vs "
                f"'{target_name}' (normalized: '{normalized_target_name}') = {result}"
            )
            
            return result
        
        except Exception as e:
            logger.error(f"Ошибка сравнения имен проектов: {e}", exc_info=True)
            return False

    def _get_or_create_project(self) -> Any:
        """Получение или создание проекта"""
        try:
            # Получаем список проектов
            projects = self.client.get_projects()
            
            # Ищем проект с совпадающим именем
            matching_project = next(
                (project for project in projects 
                 if self.is_project_name_match(project.title, self.project_name)), 
                None
            )
            
            # Если проект найден - возвращаем его
            if matching_project:
                logger.info(f"Найден существующий проект: {matching_project.title}")
                return {
                    'id': matching_project.id,
                    'title': matching_project.title
                }
            
            # Создаем новый проект, если не найден
            new_project = self.client.create_project(
                title=self.project_name,
                label_config=self._get_label_config()
            )
            
            logger.info(f"Создан новый проект: {self.project_name}")
            
            # Возвращаем словарь с данными проекта
            return {
                'id': new_project.id,
                'title': new_project.title
            }
        
        except Exception as e:
            logger.error(f"Ошибка при получении/создании проекта: {e}")
            raise

    def _get_label_config(self):
        """Генерация конфигурации раметки"""
        return """
        <View>
            <Image name="image" value="$image"/>
            <Choices name="choice" toName="image">
                <Choice value="drone"/>
                <Choice value="not_drone"/>
            </Choices>
        </View>
        """

    def create_project(self, title, label_config):
        """Создание нового проекта"""
        try:
            # Создаем новый проект напрямую
            project = self.client.create_project(
                title=title, 
                label_config=label_config
            )
            logger.info(f"Создан новый проект: {title}")
            return project
        except Exception as e:
            logger.error(f"Ошибка создания проекта: {e}")
            raise

    def create_task(self, task_data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Создание задачи в Label Studio"""
        try:
            # Используем метод create_tasks напрямую у клиента
            response = self.client.create_tasks(
                tasks=[task_data['data']], 
                project_id=self.project['id']
            )
            
            # Возвращаем первую задачу из списка
            return response[0] if response else None
        except Exception as e:
            logger.error(f"Ошибка создания задачи в Label Studio: {e}")
            raise

    def create_tasks_batch(self, tasks, project_id):
        """Пакетное создание задач"""
        try:
            created_tasks = self.client.create_tasks_batch(
                tasks, 
                project_id=project_id
            )
            return created_tasks
        except Exception as e:
            logger.error(f"Ошибка создания пакета задач: {e}")
            raise

    def get_project_id(self):
        """
        Возвращает ID проекта, инициализируя его при необходимости
        """
        if not self.project or 'id' not in self.project:
            self.project = self._get_or_create_project()
        return self.project['id']

    def create_local_storage(self, storage_title: str, storage_path: str):
        """Создание локального хранилища"""
        try:
            storage = self.client.create_local_storage(
                title=os.getenv('LABEL_STUDIO_PROJECT_NAME'),
                project_id=self.project['id'],
                path=storage_path
            )
            logger.info(f"Создано локальное хранилище: {storage_title}")
            return storage
        except Exception as e:
            logger.error(f"Ошибка создания локального хранилища: {e}")
            raise

    def sync_local_storage(self, storage_id: int):
        """Синхронизация локального хранилища"""
        try:
            sync_response = self.client.sync_local_storage(storage_id)
            logger.info(f"Синхронизация хранилища {storage_id}: {sync_response}")
            return sync_response
        except Exception as e:
            logger.error(f"Ошибка синхронизации локального хранилища: {e}")
            raise

    def get_local_storage(self, storage_id: int):
        """Получение информации о локальном хранилище"""
        try:
            storage_info = self.client.get_local_storage(storage_id)
            logger.info(f"Получена информация о хранилище {storage_id}")
            return storage_info
        except Exception as e:
            logger.error(f"Ошибка получения информации о локальном хранилище: {e}")
            raise

    def setup_local_import_storage(
        self, 
        local_path: str = None, 
        title: str = "Local File Storage",
        regex_filter: str = r".*\.(jpg|jpeg|png)",
        use_blob_urls: bool = True
    ):
        """Настройка локального хранилища для импорта файлов"""
        try:
            # Используем только относительный путь
            storage_path = 'augmented_images'
            
            # Создаем директорию внутри DOCUMENT_ROOT
            document_root = os.getenv('LABEL_STUDIO_LOCAL_FILES_DOCUMENT_ROOT', '/data/files')
            full_path = os.path.join(document_root, storage_path)
            
            # Создаем директорию если её нет
            os.makedirs(full_path, exist_ok=True)
            logger.info(f"Проверена/создана директория: {full_path}")
            
            payload = {
                "title": title,
                "path": storage_path,  # Используем относительный путь
                "regex_filter": regex_filter,
                "use_blob_urls": use_blob_urls,
                "presign": False,
                "project": self.project['id']
            }

            response = self.client.client.make_request(
                "POST", 
                f"/api/storages/localfiles", 
                json=payload
            )

            storage_info = response.json()
            logger.info(f"Создано локальное хранилище: {storage_info}")
            
            return storage_info

        except Exception as e:
            logger.error(f"Ошибка создания локального хранилища: {e}")
            raise

    def sync_local_storage(self, storage_id: int):
        """
        Синхронизация локального хранилища
        
        :param storage_id: ID хранилища для синхронизации
        :return: Результат синхронизации
        """
        try:
            sync_url = f"/api/storages/localfiles/{storage_id}/sync"
            response = self.client.client.make_request("POST", sync_url)
            
            sync_result = response.json()
            logger.info(f"Синхронизация хранилища {storage_id}: {sync_result}")
            
            return sync_result

        except Exception as e:
            logger.error(f"Ошибка синхронизации локального хранилища: {e}")
            raise

    def monitor_storage_import(self, storage_id):
        """
        Мониторинг импорта локального хранилища
        """
        try:
            # Получение статистики импорта
            stats_url = f"/api/storages/localfiles/{storage_id}/stats"
            response = self.client.client.make_request("GET", stats_url)
            
            stats = response.json()
            logger.info(f"Статистика импорта: {stats}")
            
            return stats
        except Exception as e:
            logger.error(f"Ошибка получения статистики: {e}")
            raise