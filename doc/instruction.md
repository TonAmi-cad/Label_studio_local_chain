# Label Studio Dataset Processor

## Описание проекта
Этот проект представляет собой систему для обработки и управления наборами данных в Label Studio с использованием локального хранилища файлов. Проект реализован на Python с использованием Docker для контейнеризации.

## Основные компоненты

### 1. Менеджер хранилища (StorageManager)
- Управление локальным хранилищем файлов
- Синхронизация данных  
- Валидация хранилища
- CRUD операции с хранилищами

### 2. Основной скрипт (main.py)
- Инициализация и настройка хранилища
- Обработка ошибок
- Логирование операций

### 3. Скрипт ожидания сервисов (wait-for-services.py)  
- Проверка доступности Label Studio
- Мониторинг сетевых подключений
- Управление зависимостями сервисов

## Требования
- Python 3.9+
- Docker
- Label Studio
- Переменные окружения

### Обязательные переменные окружения
```env
LABEL_STUDIO_URL
LABEL_STUDIO_USERNAME
LABEL_STUDIO_PASSWORD
LABEL_STUDIO_API_KEY
LABEL_STUDIO_PROJECT_NAME

LABEL_STUDIO_LOCAL_FILES_SERVING_ENABLED
LABEL_STUDIO_LOCAL_FILES_DOCUMENT_ROOT

# Директория для хранения изображений (относительно DOCUMENT_ROOT внутри контейнера)
DATA_DIR
DATA_VOLUME_PATH
```

## Установка и запуск

1. Клонируйте репозиторий
2. Создайте файл `.env` с необходимыми переменными окружения
3. Соберите Docker-образ:
```bash
docker build -t labelstudio-dataset-processor .
```

4. Запустите контейнер:
```bash 
./run_container.sh
```

## Структура проекта
```
├── scripts/
│   ├── __init__.py
│   ├── main.py
│   ├── storage_manager.py
│   └── wait-for-services.py
├── Dockerfile
├── requirements.txt  
├── run_container.sh
└── LICENSE
```

## Лицензия
Проект распространяется под лицензией GNU Lesser General Public License v2.1. Подробности в файле LICENSE.

## Особенности реализации
- Автоматическая синхронизация файлов
- Отказоустойчивость с использованием retry-механизмов
- Подробное логирование операций
- Проверка здоровья сервисов
- Контейнеризация с использованием Docker

## Безопасность
- Проверка обязательных переменных окружения
- Валидация путей и прав доступа
- Безопасное хранение учетных данных

## Поддержка и контрибьюция
Для сообщения об ошибках или предложения улучшений создавайте issues в репозитории проекта.

## Примечания по развертыванию
- Убедитесь, что Label Studio доступен и настроен
- Проверьте права доступа к директориям хранения данных
- Настройте сетевое взаимодействие между контейнерами
- Проверьте корректность переменных окружения

## Подъем нескольких хранилищ
Для запуска нескольких хранилищ необходимо запустить несколько контейнеров с разными переменными окружения.

LABEL_STUDIO_PROJECT_NAME
DATA_DIR
DATA_VOLUME_PATH

и дополнить docker-compose.yml
например
```
services:
  storage-manager-1:
    build: .
    environment:
      - LABEL_STUDIO_URL=${LABEL_STUDIO_URL}
      - LABEL_STUDIO_PROJECT_NAME=${LABEL_STUDIO_PROJECT_NAME_1}
      - DATA_DIR=${DATA_DIR_1}
      - DATA_VOLUME_PATH=${DATA_VOLUME_PATH_1}
    volumes:
      - ${DATA_VOLUME_PATH_1}:${LABEL_STUDIO_LOCAL_FILES_DOCUMENT_ROOT}/${DATA_DIR_1}

  storage-manager-2:
    build: .
    environment:
      - LABEL_STUDIO_URL=${LABEL_STUDIO_URL}
      - LABEL_STUDIO_PROJECT_NAME=${LABEL_STUDIO_PROJECT_NAME_2}
      - DATA_DIR=${DATA_DIR_2}
      - DATA_VOLUME_PATH=${DATA_VOLUME_PATH_2}
    volumes:
      - ${DATA_VOLUME_PATH_2}:${LABEL_STUDIO_LOCAL_FILES_DOCUMENT_ROOT}/${DATA_DIR_2}
```

так же необходимо создать соответствующие папки по примеру в Dockerfile