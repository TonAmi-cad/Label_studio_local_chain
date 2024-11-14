import os
import logging
from dotenv import load_dotenv
from label_studio_client import LabelStudioManager
from storage_manager import StorageManager

# Настройка логирования
logging.basicConfig(
    level=logging.INFO, 
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def setup_local_storage():
    """
    Основная функция настройки локального хранилища в Label Studio
    """
    try:
        # Загрузка переменных окружения
        load_dotenv()
        
        # Проверка необходимых переменных окружения
        required_vars = [
            'LABEL_STUDIO_LOCAL_FILES_SERVING_ENABLED',
            'LABEL_STUDIO_LOCAL_FILES_DOCUMENT_ROOT'
        ]
        
        missing_vars = [var for var in required_vars if not os.getenv(var)]
        if missing_vars:
            logger.error(f"Отсутствуют обязательные переменные окружения: {missing_vars}")
            return None

        # Инициализация менеджера Label Studio
        ls_manager = LabelStudioManager()

        # Проверка подключения к Label Studio
        if not ls_manager.validate_connection():
            logger.error("Не удалось установить подключение к Label Studio")
            return None

        # Убедимся что проект создан и получим его ID
        project_id = ls_manager.get_project_id()
        logger.info(f"Получен ID проекта: {project_id}")

        # Инициализация менеджера хранилища
        storage_manager = StorageManager(ls_manager)

        # Получаем список существующих хранилищ
        existing_storages = storage_manager.list_storages()
        logger.info(f"Существующие хранилища: {existing_storages}")

        # Создаем новое хранилище только если нет существующих
        if not existing_storages:
            storage_info = storage_manager.create_storage()
            storage_id = storage_info['id']
            logger.info(f"Создано новое хранилище с ID: {storage_id}")
        else:
            storage_id = existing_storages[0]['id']
            logger.info(f"Используется существующее хранилище с ID: {storage_id}")
        
        # Валидируем хранилище
        validation_result = storage_manager.validate_storage(storage_id)
        
        # Добавляем синхронизацию после валидации
        logger.info("Начинаем синхронизацию хранилища...")
        sync_result = storage_manager.sync_storage(storage_id, scan_all=True)
        logger.info(f"Результат синхронизации: {sync_result}")
        
        return storage_id, validation_result, sync_result
        
    except Exception as e:
        logger.error(f"Ошибка настройки локального хранилища: {e}")
        raise

def main():
    """
    Основная точка входа в приложение
    """
    try:
        # Настройка локального хранилища
        storage_result = setup_local_storage()
        
        if storage_result:
            storage_id, validation_result, sync_result = storage_result
            logger.info(f"""
            Локальное хранилище успешно настроено:
            - ID хранилища: {storage_id}
            - Валидация: {validation_result}
            - Синхронизация: {sync_result}
            """)
        else:
            logger.warning("Не удалось настроить локальное хранилище")

    except Exception as e:
        logger.error(f"Критическая ошибка в основной функции: {e}", exc_info=True)

if __name__ == "__main__":
    main()
