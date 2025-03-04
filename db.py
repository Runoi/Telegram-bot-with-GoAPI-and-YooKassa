#For work with DB
#import asyncpg
import asyncio
import aiosqlite
import datetime

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
        
async def get_subsc(date: str, user_id: int) -> bool:
    """
    Обновляет дату подписки для пользователя.
    Возвращает True в случае успеха, иначе False.
    """
    try:
        async with aiosqlite.connect(DB_NAME) as db:
            await db.execute(
                'UPDATE users SET sub = ? WHERE user_id = ?',
                (date, user_id)
            )
            await db.commit()
            
            return True

    except Exception as e:
        
        return False

async def chec_subsc(id):
    async with aiosqlite.connect(DB_NAME) as db:
      async with  db.execute('SELECT sub FROM users WHERE user_id = ?', (id,)) as cursor:
        user_data = await cursor.fetchone()
        if user_data[0] is not None:
            end_date = datetime.datetime.strptime(user_data[0], '%Y-%m-%d')
            return datetime.datetime.today() <= end_date
        return False
    