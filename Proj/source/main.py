import json
import network
import time
from machine import Pin
import urequests
import logging
import machine
import hashlib
import ucryptolib
import ubinascii

# Инициализация логгера из прикрепленного модуля logging.py[cite: 1]
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

def get_aes_key():
    logger.debug("Вход в функцию get_aes_key")
    try:
        hw_id = machine.unique_id()
        key = hashlib.sha256(hw_id + b"MY_CUSTOM_SALT").digest()
        logger.debug("Выход из функцию get_aes_key (Успех)")
        return key
    except Exception as e:
        logger.exception("Ошибка при генерации AES-ключа: %s", e)
        logger.debug("Выход из функцию get_aes_key (Ошибка)")
        return None

def decrypt_password(encoded_pwd):
    logger.debug("Вход в функцию decrypt_password")
    try:
        key = get_aes_key()
        if not key:
            return None
        encrypted = ubinascii.a2b_base64(encoded_pwd)
        cipher = ucryptolib.aes(key, 1)
        padded = cipher.decrypt(encrypted)
        unpadded = padded[:-padded[-1]]
        password = unpadded.decode('utf-8')
        logger.info("Пароль успешно расшифрован")
        logger.debug("Выход из функции decrypt_password (Успех)")
        return password
    except Exception as e:
        logger.exception("Ошибка при дешифровке пароля: %s", e)
        logger.debug("Выход из функцию decrypt_password (Ошибка)")
        return None

def scan_and_select_wifi(configured_networks):
    logger.debug("Вход в функцию scan_and_select_wifi")
    try:
        wlan = network.WLAN(network.STA_IF)
        wlan.active(True)
        
        logger.info("Запуск сканирования доступных Wi-Fi сетей...")
        scanned_networks = wlan.scan() # Возвращает кортежи: (ssid, bssid, channel, RSSI, authmode, hidden)
        
        best_ssid = None
        best_enc_pwd = None
        max_rssi = -999
        
        # Создаем словарь для быстрого поиска пароля по SSID из конфигурации
        net_map = {net["ssid"]: net["password_enc"] for net in configured_networks}
        
        for net in scanned_networks:
            ssid_raw = net[0]
            rssi = net[3]
            try:
                ssid_str = ssid_raw.decode('utf-8')
            except Exception:
                ssid_str = str(ssid_raw)
                
            logger.debug("Обнаружена сеть: %s с уровнем сигнала RSSI: %d", ssid_str, rssi)
            
            if ssid_str in net_map:
                if rssi > max_rssi:
                    max_rssi = rssi
                    best_ssid = ssid_str
                    best_enc_pwd = net_map[ssid_str]
                    
        if best_ssid:
            logger.info("Выбрана оптимальная сеть: %s (RSSI: %d)", best_ssid, max_rssi)
            logger.debug("Выход из функции scan_and_select_wifi (Успех)")
            return best_ssid, best_enc_pwd
        else:
            logger.warning("Ни одна из сетей из файла конфигурации не обнаружена в эфире")
            logger.debug("Выход из функции scan_and_select_wifi (Сети не найдены)")
            return None, None
            
    except Exception as e:
        logger.exception("Ошибка в процессе сканирования Wi-Fi сетей: %s", e)
        logger.debug("Выход из функции scan_and_select_wifi (Исключение)")
        return None, None

def connect_wifi(ssid, password):
    logger.debug("Вход в функцию connect_wifi [ssid=%s]", ssid)
    try:
        wlan = network.WLAN(network.STA_IF)
        wlan.active(True)
        if not wlan.isconnected():
            logger.info("Подключение к Wi-Fi сети: %s...", ssid)
            wlan.connect(ssid, password)
            
            timeout = 15
            while not wlan.isconnected() and timeout > 0:
                time.sleep(1)
                timeout -= 1
                logger.debug("Ожидание подключения... (осталось %d сек)", timeout)
            
            if not wlan.isconnected():
                logger.error("Таймаут подключения к сети %s", ssid)
                logger.debug("Выход из функции connect_wifi (Таймаут)")
                return False

        logger.info("Успешное подключение! IP-адрес: %s", wlan.ifconfig()[0])
        logger.debug("Выход из функции connect_wifi (Успех)")
        return True
    except Exception as e:
        logger.exception("Системная ошибка при подключении к Wi-Fi: %s", e)
        logger.debug("Выход из функции connect_wifi (Исключение)")
        return False

def call_rest_api(api_url):
    logger.debug("Вход в функцию call_rest_api [url=%s]", api_url)
    response = None
    try:
        logger.info("Инициация GET-запроса к %s", api_url)
        response = urequests.get(api_url)
        logger.info("Запрос выполнен. HTTP Код: %s", response.status_code)
        logger.debug("Ответ сервера: %s", response.text)
    except OSError as e:
        logger.error("Сетевая ошибка или сервер недоступен: %s", e)
    except Exception as e:
        logger.exception("Непредвиденная ошибка при вызове REST API: %s", e)
    finally:
        if response:
            try:
                response.close()
                logger.debug("Соединение с сервером закрыто")
            except Exception as close_err:
                logger.error("Ошибка при закрытии соединения: %s", close_err)
    logger.debug("Выход из функции call_rest_api")

def main():
    logger.debug("Вход в функцию main")
    try:
        logger.info("Инициализация системы...")
        
        config = load_config()
        if not config:
            logger.error("Остановка приложения: нет конфигурации.")
            return

        networks_list = config.get("wifi_networks", [])
        api_url = config.get("api_url")
        button_pin_num = config.get("hardware_button_pin", 13)

        if not networks_list or not api_url:
            logger.error("Остановка приложения: в конфиге отсутствуют wifi_networks или api_url.")
            return

        # Сканируем эфир и выбираем сеть с наилучшим сигналом
        ssid, encoded_password = scan_and_select_wifi(networks_list)
        if not ssid or not encoded_password:
            logger.error("Остановка приложения: не удалось определить подходящую сеть.")
            return

        plain_password = decrypt_password(encoded_password)
        if not plain_password:
            logger.error("Остановка приложения: ошибка расшифровки пароля.")
            return

        if not connect_wifi(ssid, plain_password):
            logger.error("Остановка приложения: сбой подключения к Wi-Fi.")
            del plain_password
            return

        del plain_password

        try:
            btn = Pin(button_pin_num, Pin.IN, Pin.PULL_UP)
            logger.info("Пин кнопки (GPIO %d) успешно настроен", button_pin_num)
        except Exception as e:
            logger.exception("Ошибка инициализации GPIO: %s", e)
            return

        logger.info("Система ожидает нажатия кнопки...")
        last_press_time = 0
        debounce_delay = 300

        while True:
            try:
                if not btn.value():
                    current_time = time.ticks_ms()
                    if time.ticks_diff(current_time, last_press_time) > debounce_delay:
                        logger.info(">>> Кнопка нажата, запуск REST API")
                        call_rest_api(api_url)
                        last_press_time = time.ticks_ms()
                time.sleep(0.05)
            except Exception as e:
                logger.exception("Ошибка в цикле опроса: %s", e)
                time.sleep(2)

    except Exception as e:
        logger.exception("Критическая ошибка в main(): %s", e)
    finally:
        logger.debug("Выход из функции main")
        logger.info("Работа приложения завершена.")

if __name__ == "__main__":
    main()