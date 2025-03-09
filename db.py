#For work with DB
#import asyncpg
import asyncio
import aiosqlite
import datetime
from datetime import datetime,timedelta
import logging
from dotenv import load_dotenv
import os
from payments import create_auto_payment

# Настройка логирования
logging.basicConfig(
    level=logging.INFO,  # Уровень логирования (INFO, DEBUG, WARNING, ERROR, CRITICAL)
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',  # Формат логов
    handlers=[
        logging.FileHandler('logs/bot.log'),  # Логи записываются в файл bot.log
        logging.StreamHandler()  # Логи также выводятся в консоль (опционально)
    ]
)
logger = logging.getLogger(__name__)

DB_NAME = 'music_bot.db'

async def create_table():
    # Создаем соединение с базой данных (если она не существует, она будет создана)
    async with aiosqlite.connect(DB_NAME) as db:
        # Создаем таблицу
        await db.execute('''CREATE TABLE IF NOT EXISTS users (
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
);''')
        await db.commit()

async def add_auto(user_id, payment_id):
    try:
        async with aiosqlite.connect(DB_NAME) as db:
            # Проверяем, существует ли пользователь
            cursor = await db.execute('SELECT * FROM users WHERE user_id = ?', (user_id,))
            user_exists = await cursor.fetchone()
            await cursor.close()

            if not user_exists:
                print(f"Пользователь с ID {user_id} не найден.")
                return False

            # Обновляем данные пользователя
            await db.execute('''
                UPDATE users 
                SET auto = 1, payment_id = ? 
                WHERE user_id = ?
            ''', (payment_id, user_id))

            # Сохраняем изменения
            await db.commit()
            print(f"Данные пользователя {user_id} успешно обновлены.")
            return True

    except aiosqlite.Error as e:
        # Логируем ошибку
        print(f"Ошибка при обновлении данных пользователя: {e}")
        return False
    
async def un_auto(user_id):
    async with aiosqlite.connect(DB_NAME) as db:
        try:
                print(1)
                # Проверяем, существует ли пользователь
                cursor = await db.execute('SELECT * FROM users WHERE user_id = ?', (user_id,))
                user_exists = await cursor.fetchone()
                await cursor.close()

                if not user_exists:
                    print(f"Пользователь с ID {user_id} не найден.")
                    return False

                # Обновляем данные пользователя
                await db.execute('UPDATE users SET auto = 0 WHERE user_id = ?', (user_id,))

                # Сохраняем изменения
                await db.commit()
                print(f"Данные пользователя {user_id} успешно обновлены.")
                return True

        except aiosqlite.Error as e:
            # Логируем ошибку
            print(f"Ошибка при обновлении данных пользователя: {e}")
            return False

async def user_check(user):
    async with aiosqlite.connect(DB_NAME) as db:
        async with db.execute('SELECT * FROM users WHERE user_id = (?)', (user.id, )) as cursor:
            user_data = await cursor.fetchall()
            await db.commit()
            return user_data

async def insert_table(user,referral_code,referred_by,balance,status):
        async with aiosqlite.connect(DB_NAME) as db:
            async with db.execute('INSERT INTO users (user_id, username,referral_code,referred_by, balance,status) VALUES (?,?,?,?,?,?) ', 
                                  (user.id,user.username,referral_code,referred_by,balance,status )) as cursor:
                user_data = await cursor.fetchall()
                await db.commit()
                return user_data
            
async def add_referal(referrer_code, user_id):
    async with aiosqlite.connect(DB_NAME) as db:
        # Проверяем, использовал ли уже пользователь реферальный код
        async with db.execute('SELECT referred_by FROM users WHERE user_id = ?', (user_id,)) as cursor:
            existing_referrer = await cursor.fetchone()
        
        if existing_referrer and existing_referrer[0] is not None:
            print(f"Пользователь {user_id} уже использовал реферальный код.")
            return  # Прекращаем выполнение, если код уже использован

        # Получаем данные о пригласившем пользователе
        async with db.execute('SELECT username FROM users WHERE referral_code = ?', (referrer_code,)) as cursor:
            user_data = await cursor.fetchone()
        
        if user_data:
            referrer_username = user_data[0]  # Извлекаем username реферера

            # Обновляем поле referred_by у нового пользователя (только если оно пустое)
            await db.execute('UPDATE users SET referred_by = ? WHERE user_id = ?', (referrer_username, user_id))
            
            # Начисляем бонус пригласившему пользователю
            await db.execute('UPDATE users SET balance = balance + ? WHERE username = ?', (1, referrer_username))
            
            # Сохраняем изменения
            await db.commit()

async def get_referal(user_id):
    async with aiosqlite.connect(DB_NAME) as db:
        try:
            # Получаем реферальный код пользователя
            async with db.execute('SELECT referral_code FROM users WHERE user_id = ?', (user_id,)) as cursor:
                user_data = await cursor.fetchone()

            if not user_data:
                return []  # Если пользователя нет в БД

            referrer_code = user_data[0]  # Извлекаем реферальный код

            # Получаем список приглашенных пользователей
            async with db.execute('SELECT username FROM users WHERE referred_by = ? LIMIT 10', (referrer_code,)) as ref_cursor:
                referred_users = await ref_cursor.fetchall()

            # Фильтруем None и заменяем его на "[Без имени]"
            return [user[0] if user[0] is not None else "[Без имени]" for user in referred_users]

        except Exception as e:
            print(f"Ошибка при получении рефералов: {e}")
            return []  # В случае ошибки возвращаем пустой список

async def get_ref_url(user_id):
    async with aiosqlite.connect(DB_NAME) as db:
        try:
            # Получаем реферальный код пользователя
            async with db.execute('SELECT referral_code FROM users WHERE user_id = ?', (user_id,)) as cursor:
                user_data = await cursor.fetchone()

            referrer_code = user_data[0]  # Извлекаем реферальный код

            return referrer_code

        except Exception as e:
            print(f"Ошибка при получении ссылки: {e}")
            return []  # В случае ошибки возвращаем пустой список
        
async def get_balance(user_id):
    async with aiosqlite.connect(DB_NAME) as db:
        try:
            # Получаем реферальный код пользователя
            async with db.execute('SELECT balance FROM users WHERE user_id = ?', (user_id,)) as cursor:
                user_data = await cursor.fetchone()

            balance = user_data[0]  # Извлекаем баланс

            return balance

        except Exception as e:
            print(f"Ошибка при получении баланса: {e}")
            return []  # В случае ошибки возвращаем пустой список
                

     
async def deduct_tokens(user_id, amount=1):
    async with aiosqlite.connect(DB_NAME) as db:
        await db.execute('UPDATE users SET balance = balance - ? WHERE user_id = ?', (amount, user_id))
        await db.commit()

async def give_tokens(user_id, amount=1):
    async with aiosqlite.connect(DB_NAME) as db:
        await db.execute('UPDATE users SET balance = balance + ? WHERE user_id = ?', (amount, user_id))
        await db.commit()

async def check_status(user_id):
    async with aiosqlite.connect(DB_NAME) as db:
        try:
            async with db.execute('SELECT status FROM users WHERE user_id = ?', (user_id,)) as cursor:
                user_data = await cursor.fetchone()

            if user_data is None:
                # Пользователь не найден
                return False

            status = user_data[0]
            return status == 1  # Возвращаем True, если статус равен 1, иначе False

        except Exception as e:
            print(f"Ошибка при проверке статуса: {e}")
            return False  # В случае ошибки возвращаем False
        
async def ban(user_id):
    async with aiosqlite.connect(DB_NAME) as db:
        await db.execute('UPDATE users SET status = ? WHERE user_id = ?', (0,user_id))
        await db.commit()

async def unban(user_id):
    async with aiosqlite.connect(DB_NAME) as db:
        await db.execute('UPDATE users SET status = ? WHERE user_id = ?', (1,user_id))
        await db.commit()

async def check_all():
    """
    Возвращает количество пользователей в базе данных.
    В случае ошибки возвращает 0.
    """
    async with aiosqlite.connect(DB_NAME) as db:
        try:
            # Выполняем запрос для получения всех пользователей
            async with db.execute('SELECT * FROM users') as cursor:
                user_data = await cursor.fetchall()
                return len(user_data)  # Возвращаем количество пользователей
        except Exception as e:
            # Логируем ошибку и возвращаем 0
            print(f"Ошибка при выполнении запроса: {e}")
            return 0

async def check_ref(ref):
    async with aiosqlite.connect(DB_NAME) as db:
        try:
            async with db.execute('SELECT username FROM users WHERE referral_code = ?', (ref,)) as cursor:
                user_data = await cursor.fetchone()

            if user_data is None:
                # Пользователь не найден
                return False

            username = user_data[0]
            return username  # Возвращаем True, если статус равен 1, иначе False

        except Exception as e:
            print(f"Ошибка при проверке статуса: {e}")
            return False  # В случае ошибки возвращаем False
        
async def get_subsc(date: str,plan:str ,user_id: int) -> bool:
    """
    Обновляет дату подписки и план для пользователя.

    :param date: Новая дата подписки.
    :param plan: Новый план подписки.
    :param user_id: Идентификатор пользователя.
    :return: True, если обновление прошло успешно, иначе False.
    """
    try:
        async with aiosqlite.connect(DB_NAME) as db:
            await db.execute(
                'UPDATE users SET sub = ?, plan = ? WHERE user_id = ?',
                (date,plan, user_id)
            )
            await db.commit()
            
            return True

    except Exception as e:
        
        return False

async def check_subsc(id):
    async with aiosqlite.connect(DB_NAME) as db:
        cursor = await db.execute('SELECT sub FROM users WHERE user_id = ?', (id,))
        user_data = await cursor.fetchone()
        
        if user_data and user_data[0]:  # Проверка на None
            try:
                end_date = datetime.strptime(user_data[0], '%Y-%m-%d').date()  # Преобразование строки в дату
                return datetime.today().date() <= end_date  # Сравниваем даты
            except ValueError:
                return False  # Если дата в БД повреждена, вернуть False
        
        return False
    
async def check_plan(id):
    async with aiosqlite.connect(DB_NAME) as db:
        cursor = await db.execute('SELECT plan FROM users WHERE user_id = ?', (id,))
        user_data = await cursor.fetchone()
        
        if user_data and user_data[0]:  # Проверка на None
            try:
               
                return user_data
            except ValueError:
                return False  # Если дата в БД повреждена, вернуть False
        
        return False    
    

async def check_and_issue_tokens():
    """
    Проверяет подписку пользователей и начисляет токены в зависимости от плана.
    """
    try:
        
        async with aiosqlite.connect(DB_NAME) as db:
            # Получаем текущую дату
            today = datetime.now().date()

            # Выбираем пользователей с активной подпиской
            cursor = await db.execute(
                'SELECT user_id, plan FROM users WHERE sub >= ?',
                (today,)
            )
            users = await cursor.fetchall()
            print(users)
            # Начисляем токены в зависимости от плана
            for user_id, plan in users:
                
                tokens = 0
                if plan == "start":
                    tokens = 20
                elif plan == "master":
                    tokens = 60
                elif plan == "year":
                    # Проверяем, что текущий день месяца совпадает с днем начала подписки
                    # (например, если подписка началась 15 числа, то начисляем 15 числа каждого месяца)
                    user_cursor = await db.execute(
                        'SELECT sub FROM users WHERE user_id = ?',
                        (user_id,)
                    )
                    sub_date = (await user_cursor.fetchone())[0]
                    if sub_date:  # Проверяем, что sub_date не None
                        sub_date = datetime.strptime(sub_date, "%Y-%m-%d").date()
                        if today.day == sub_date.day:
                            tokens = 60

                if tokens > 0:
                    # Начисляем токены
                    await give_tokens(user_id, tokens)
                    #logging.info(f"Начислено {tokens} токенов пользователю {user_id}.")

    except Exception as e:
        #logging.error(f"Ошибка при проверке и начислении токенов: {e}")
        print(e)

async def renew_subscription():
    """
    Автоматически продлевает подписку для пользователей с включенным автопродлением.
    """
    try:
        load_dotenv('keys.env')
        price_s = int(os.getenv('PRICE_START'))
        price_m = int(os.getenv('PRICE_MASTER'))
        price_y = int(os.getenv('PRICE_YEAR'))
        async with aiosqlite.connect(DB_NAME) as db:
            # Получаем текущую дату
            today = datetime.now().date()

            # Выбираем пользователей с истекающей подпиской и включенным автопродлением
            cursor = await db.execute(
                'SELECT user_id, payment_id, plan FROM users WHERE sub <= ? AND auto = 1',
                (today,)
            )
            users = await cursor.fetchall()

            # Для каждого пользователя создаем новый платеж и обновляем подписку
            for user_id, payment_id, plan in users:
                # Определяем стоимость подписки в зависимости от плана
                price = 0
                if plan == "start":
                    price = price_s # Пример стоимости
                elif plan == "master":
                    price = price_m  # Пример стоимости
                elif plan == "year":
                    price = price_y  # Пример стоимости
                
                if price > 0:
                    # Создаем новый платеж с использованием сохраненного payment_id
                    confirmation_url, new_payment_id = await create_auto_payment(price, payment_id)
                    asyncio.sleep(10)
                    if confirmation_url and new_payment_id:
                        if plan != 'year':
                            # Обновляем дату подписки 
                            new_sub_date = (datetime.now() + timedelta(days=30)).date()
                            await db.execute(
                                'UPDATE users SET sub = ?, payment_id = ? WHERE user_id = ?',
                                (new_sub_date, new_payment_id, user_id)
                            )
                            await db.commit()
                            logger.info(f"Подписка пользователя {user_id} успешно продлена до {new_sub_date}.")
                        else:
                            # Обновляем дату подписки 
                            new_sub_date = (datetime.now() + timedelta(days=360)).date()
                            await db.execute(
                                'UPDATE users SET sub = ?, payment_id = ? WHERE user_id = ?',
                                (new_sub_date, new_payment_id, user_id)
                            )
                            await db.commit()
                            logger.info(f"Подписка пользователя {user_id} успешно продлена до {new_sub_date}.")
                    else:
                        logger.error(f"Не удалось создать платеж для пользователя {user_id}.")

    except Exception as e:
        logger.error(f"Ошибка при продлении подписки: {e}", exc_info=True)