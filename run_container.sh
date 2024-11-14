#!/bin/bash

# Загрузка переменных из .env
if [ -f .env ]; then
    export $(cat .env | grep -v '^#' | xargs)
else
    echo "Файл .env не найден"
    exit 1
fi

# Проверка обязательных переменных
required_vars=("LABEL_STUDIO_URL" "LABEL_STUDIO_API_KEY" "DATA_DIR" "POSTGRES_HOST" "POSTGRES_DB" "POSTGRES_USER" "POSTGRES_PASSWORD")
for var in "${required_vars[@]}"; do
    if [ -z "${!var}" ]; then
        echo "Ошибка: Переменная $var не установлена"
        exit 1
    fi
done

# Создание сети Docker, если она не существует
docker network inspect labelstudio-network >/dev/null 2>&1 || \
    docker network create labelstudio-network

# Запуск контейнера Label Studio
docker run -d \
    --name custom-label-studio-container \
    --network labelstudio-network \
    -p 8080:8080 \
    -e POSTGRES_HOST=${POSTGRES_HOST} \
    -e POSTGRES_DB=${POSTGRES_DB} \
    -e POSTGRES_USER=${POSTGRES_USER} \
    -e POSTGRES_PASSWORD=${POSTGRES_PASSWORD} \
    -e LABEL_STUDIO_USERNAME=${LABEL_STUDIO_USERNAME} \
    -e LABEL_STUDIO_PASSWORD=${LABEL_STUDIO_PASSWORD} \
    -e LABEL_STUDIO_API_KEY=${LABEL_STUDIO_API_KEY} \
    custom-label-studio:latest

# Запуск контейнера обработчика данных
docker run -d \
    --name labelstudio-dataset-processor \
    --network labelstudio-network \
    --env-file .env \
    -v ${DATA_DIR}:/data \
    labelstudio-dataset-processor