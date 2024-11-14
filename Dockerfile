FROM python:3.9-slim

WORKDIR /app

# Установка необходимых зависимостей
RUN apt-get update -o Acquire::Connection::Timeout=10 \
    && apt-get install -y \
    gcc \
    && rm -rf /var/lib/apt/lists/*

# Создание директории для логов
RUN mkdir -p /app/logs && chmod 777 /app/logs

# Копирование .env файла (опционально)
COPY .env .env

# Установка python-dotenv
RUN pip install python-dotenv

# Установка Python-зависимостей
COPY requirements.txt .
RUN pip install --default-timeout=100 --no-cache-dir -r requirements.txt

# Копирование скриптов и создание пакета
COPY scripts/ /app/scripts/
RUN touch /app/scripts/__init__.py

# Добавление директории в PYTHONPATH
ENV PYTHONPATH=/app/scripts

# Добавление curl для healthcheck
RUN apt-get update && apt-get install -y curl

# Создание директории для данных
RUN mkdir -p /data && chmod 777 /data

# Использование ARG для переменных сборки
ARG DATA_DIR=/data
ENV DATA_DIR=${DATA_DIR}

# Точка входа через скрипт ожидания
ENTRYPOINT ["sh", "-c", "python scripts/wait-for-services.py && python scripts/main.py"]

HEALTHCHECK --interval=60s --timeout=30s --start-period=120s --retries=5 \
    CMD curl -f http://localhost:8000/health || exit 1

RUN mkdir -p /data/augmented_images