import sqlite3
import logging

# Настройка логгера
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Имя базы данных
DB_NAME = "music_bot.db"

def create_table():
    """
    Создает таблицы в базе данных, если они не существуют.

    """
    try:
        # Создаем соединение с базой данных (если она не существует, она будет создана)
        with sqlite3.connect(DB_NAME) as db:
            cursor = db.cursor()

            # Создаем таблицу users
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS users (
                    user_id INTEGER PRIMARY KEY,
                    username TEXT,
                    referral_code TEXT UNIQUE,
                    referred_by TEXT,
                    balance REAL DEFAULT 0,
                    status INTEGER,
                    sub TEXT,
                    plan TEXT,
                    auto INTEGER DEFAULT 0,
                    payment_id TEXT                
                );
            ''')
            logger.info("Таблица users создана или уже существует.")

            # Создаем таблицу payments
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS payments (
                    payment_id TEXT PRIMARY KEY,  
                    user_id INTEGER,              
                    sub_type TEXT,                
                    tokens INTEGER,               
                    status TEXT,                  
                    created_at TIMESTAMP          
                );
            ''')
            logger.info("Таблица payments создана или уже существует.")

            # Сохраняем изменения
            db.commit()
            logger.info("Изменения в базе данных сохранены.")

    except sqlite3.Error as e:
        # Логируем ошибку
        logger.error(f"Ошибка при создании таблиц: {e}")
        raise  # Повторно выбрасываем исключение для обработки в вызывающей функции

create_table()