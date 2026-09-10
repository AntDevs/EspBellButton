import machine
import hashlib
import ucryptolib
import ubinascii
import logging

# Настройка логгера для утилиты шифрования
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger("encrypt_util")

def get_aes_key():
    logger.debug("Вход в функцию get_aes_key")
    try:
        hw_id = machine.unique_id()
        key = hashlib.sha256(hw_id + b"MY_CUSTOM_SALT").digest()
        logger.info("AES-ключ успешно сгенерирован на основе уникального ID устройства")
        logger.debug("Выход из функции get_aes_key (Успех)")
        return key
    except Exception as e:
        logger.exception("Критическая ошибка при генерации AES-ключа: %s", e)
        logger.debug("Выход из функции get_aes_key (Ошибка)")
        return None

def pad(s):
    logger.debug("Вход в функцию pad [length=%d]", len(s))
    try:
        pad_len = 16 - (len(s) % 16)
        padded_data = s + bytes([pad_len] * pad_len)
        logger.debug("Выход из функцию pad (Успех)")
        return padded_data
    except Exception as e:
        logger.exception("Ошибка при добавлении паддинга: %s", e)
        logger.debug("Выход из функцию pad (Ошибка)")
        raise

def encrypt_wifi_password(password_str):
    logger.debug("Вход в функцию encrypt_wifi_password")
    try:
        if not password_str:
            logger.error("Передан пустой пароль для шифрования")
            return None

        key = get_aes_key()
        if not key:
            logger.error("Не удалось получить ключ шифрования")
            return None

        logger.info("Начало процесса шифрования пароля")
        padded_pwd = pad(password_str.encode('utf-8'))
        
        cipher = ucryptolib.aes(key, 1) # 1 = Режим ECB
        encrypted = cipher.encrypt(padded_pwd)
        
        encoded_pwd = ubinascii.b2a_base64(encrypted).decode('utf-8').strip()
        logger.info("Пароль успешно зашифрован и закодирован в Base64")
        logger.debug("Выход из функции encrypt_wifi_password (Успех)")
        return encoded_pwd
        
    except Exception as e:
        logger.exception("Непредвиденная ошибка в процессе шифрования пароля: %s", e)
        logger.debug("Выход из функции encrypt_wifi_password (Ошибка)")
        return None

def main(password_str=None):
    logger.debug("Вход в функцию main [password_provided=%s]", bool(password_str))
    try:
        if not password_str:
            logger.error("Пароль не передан в функцию main()")
            return None

        logger.info("Запуск процесса шифрования переданного пароля...")
        encrypted_result = encrypt_wifi_password(password_str)
        
        if encrypted_result:
            # Выводим результат через INFO-уровень логгера вместо print
            logger.info("=== РЕЗУЛЬТАТ ШИФРОВАНИЯ ===")
            logger.info("Скопируйте эту строку в config.json в поле 'wifi_password_enc':")
            logger.info("%s", encrypted_result)
        else:
            logger.error("Процесс шифрования завершился неудачно.")
            
    except Exception as e:
        logger.exception("Критическая ошибка на уровне main(): %s", e)
    finally:
        logger.debug("Выход из функции main")
        logger.info("Утилита шифрования завершила работу.")

if __name__ == "__main__":
    main()