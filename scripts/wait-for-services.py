import os
import logging
import requests
import time
import sys
import socket

from dotenv import load_dotenv
load_dotenv()

logging.basicConfig(level=logging.INFO, 
                    format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def check_network_connectivity(host):
    """Проверка сетевой связности с хостом"""
    try:
        socket.gethostbyname(host)
        return True
    except socket.error:
        logger.error(f"Не удается разрешить DNS для хоста: {host}")
        return False

def wait_for_label_studio():
    url = os.getenv('LABEL_STUDIO_URL') or os.getenv('LABEL_STUDIO_URL')
    if not url:
        logger.error("LABEL_STUDIO_URL не установлен")
        return False
    
    max_retries = 120
    retry_interval = 5

    for i in range(max_retries):
        try:
            logger.info(f"Проверка доступности Label Studio: {url}")
            
            response = requests.get(
                f"{url}/api/health", 
                timeout=10,
                headers={'Accept': 'application/json'}
            )
            
            if response.status_code == 200:
                logger.info(f"Label Studio готов к работе по адресу: {url}")
                return True
            else:
                logger.warning(f"Неожиданный статус-код: {response.status_code}")
        
        except requests.exceptions.RequestException as e:
            logger.warning(f"Ожидание Label Studio... Попытка {i+1}/{max_retries}. Ошибка: {e}")
        
        time.sleep(retry_interval)
    
    logger.error("Label Studio не запустился")
    return False

def get_network_info():
    services = [
        'label-studio', 
        'dataset-processor'
    ]
    for service in services:
        try:
            ip = socket.gethostbyname(service)
            logger.info(f"Резолв {service}: {ip}")
        except socket.error:
            logger.warning(f"Не удалось разрешить {service}")

def wait_for_services():
    logger.info("Проверка сервисов. Переменные окружения:")
    logger.info(f"LABEL_STUDIO_URL: {os.getenv('LABEL_STUDIO_URL')}")
    
    services_ready = {
        'label_studio': wait_for_label_studio()
    }
    
    if not all(services_ready.values()):
        failed_services = [s for s, ready in services_ready.items() if not ready]
        logger.error(f"Не удалось дождаться запуска сервисов: {', '.join(failed_services)}")
        sys.exit(1)

if __name__ == "__main__":
    get_network_info()
    wait_for_services()