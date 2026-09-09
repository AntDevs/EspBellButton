import json
import network
import time
from machine import Pin
import urequests
import logging  # Импортируем прикрепленный модуль logging.py

# Инициализация логгера
# Устанавливаем уровень DEBUG, чтобы видеть логи входа/выхода из функций
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger("app")

def load_config(filename="config.json"):
    logger.debug("Вход в функцию load_config [filename=%s]", filename)
    try:
        with open(filename, 'r') as f:
            config = json.load(f)
        logger.info("Конфигурация успешно загружена из %s", filename)
        logger.debug("Выход из функции load_config (Успех)")
        return config
    except Exception as e:
        logger.exception("Критическая ошибка при чтении файла конфигурации: %s", e)
        logger.debug("Выход из функции load_config (Ошибка)")
        return None

def connect_wifi(ssid, password):
    logger.debug("Вход в функцию connect_wifi [ssid=%s]", ssid)
    try:
        wlan = network.WLAN(network.STA_IF)
        wlan.active(True)
        if not wlan.isconnected():
            logger.info("Попытка подключения к Wi-Fi сети: %s...", ssid)
            wlan.connect(ssid, password)
            
            # Добавлен таймаут для предотвращения бесконечного зависания
            timeout = 15
            while not wlan.isconnected() and timeout > 0:
                time.sleep(1)
                timeout -= 1
                logger.debug("Ожидание сети... (осталось %d сек)", timeout)
            
            if not wlan.isconnected():
                logger.error("Таймаут подключения к Wi-Fi. Проверьте SSID и пароль.")
                logger.debug("Выход из функции connect_wifi (Ошибка таймаута)")
                return False

        logger.info("Успешное подключение к Wi-Fi! IP: %s", wlan.ifconfig()[0])
        logger.debug("Выход из функции connect_wifi (Успех)")
        return True
    except Exception as e:
        logger.exception("Аппаратная/системная ошибка при настройке Wi-Fi: %s", e)
        logger.debug("Выход из функции connect_wifi (Исключение)")
        return False

def call_rest_api(api_url):
    logger.debug("Вход в функцию call_rest_api [url=%s]", api_url)
    response = None
    try:
        logger.info("Инициация GET-запроса к %s", api_url)
        response = urequests.get(api_url)
        
        # Логируем результат
        logger.info("Запрос выполнен. HTTP Код: %s", response.status_code)
        logger.debug("Ответ от сервера: %s", response.text)
        
    except OSError as e:
        logger.error("Сетевая ошибка или сервер недоступен: %s", e)
    except Exception as e:
        # exception() автоматически извлечет и распечатает traceback
        logger.exception("Непредвиденная ошибка при вызове REST API: %s", e)
    finally:
        # Обязательно закрываем сокет во избежание утечек памяти
        if response:
            try:
                response.close()
                logger.debug("Соединение с сервером API закрыто")
            except Exception as close_err:
                logger.error("Ошибка при закрытии соединения: %s", close_err)
    
    logger.debug("Выход из функции call_rest_api")

def main():
    logger.debug("Вход в функцию main")
    try:
        logger.info("Инициализация системы...")
        
        # 1. Чтение конфигурации
        config = load_config()
        if not config:
            logger.error("Остановка приложения: невозможно загрузить конфигурацию.")
            return

        ssid = config.get("wifi", {}).get("ssid")
        password = config.get("wifi", {}).get("password")
        api_url = config.get("api", {}).get("url")
        button_pin_num = config.get("hardware", {}).get("button_pin", 13)

        if not ssid or not api_url:
            logger.error("Остановка приложения: в конфигурации отсутствуют обязательные ключи (ssid или api_url).")
            return

        # 2. Подключение к сети
        if not connect_wifi(ssid, password):
            logger.error("Остановка приложения: нет подключения к сети.")
            return

        # 3. Настройка железа
        try:
            btn = Pin(button_pin_num, Pin.IN, Pin.PULL_UP)
            logger.info("Пин кнопки (GPIO %d) настроен с внутренней подтяжкой (PULL_UP)", button_pin_num)
        except Exception as e:
            logger.exception("Ошибка конфигурации GPIO: %s", e)
            return

        # 4. Основной цикл
        logger.info("Система переведена в режим ожидания аппаратных прерываний (нажатия).")
        last_press_time = 0
        debounce_delay = 300 

        while True:
            try:
                if not btn.value():
                    current_time = time.ticks_ms()
                    if time.ticks_diff(current_time, last_press_time) > debounce_delay:
                        logger.info(">>> Событие: Зафиксировано нажатие кнопки")
                        call_rest_api(api_url)
                        last_press_time = time.ticks_ms()
                time.sleep(0.05)
            except Exception as e:
                logger.exception("Ошибка в основном цикле опроса: %s", e)
                # Пауза при ошибке, чтобы логгер не спамил в консоль 1000 раз в секунду
                time.sleep(2) 
                
    except Exception as e:
        logger.exception("Критическая ошибка на уровне main(): %s", e)
    finally:
        logger.debug("Выход из функции main")
        logger.info("Приложение завершило работу.")

if __name__ == "__main__":
    main()