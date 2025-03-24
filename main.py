from aiogram import F
from aiogram import Bot, Dispatcher, types
from aiogram.types import URLInputFile, FSInputFile
from aiogram.filters.command import Command
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton,WebAppInfo,LabeledPrice
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import Update, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.exceptions import TelegramRetryAfter
from contextlib import asynccontextmanager
from fastapi import FastAPI, Request, BackgroundTasks,HTTPException
from fastapi.responses import JSONResponse
import uvicorn
import os
from datetime import datetime, timedelta
import datetime
import time
import requests
import asyncio
import logging
import random
from dotenv import load_dotenv
from function import is_user_subscribed, generate_referral_code, generate_referral_link
import db 
import aimu
from db import add_referal,get_referal,get_ref_url,get_balance,deduct_tokens,check_status,ban,unban, check_all,check_ref,give_tokens,get_subsc,check_subsc, add_auto, un_auto,check_and_issue_tokens,renew_subscription,check_plan
from aiogram.enums.parse_mode import ParseMode
from payments import create_payment




# Настройка логирования
logging.basicConfig(
    level=logging.INFO,  # Уровень логирования (INFO, DEBUG, WARNING, ERROR, CRITICAL)
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',  # Формат логов
    handlers=[
        logging.FileHandler('logs/bot.log',encoding='utf-8'),  # Логи записываются в файл bot.log
        logging.StreamHandler()  # Логи также выводятся в консоль (опционально)
    ]
)
logger = logging.getLogger(__name__) 

load_dotenv('keys.env')
bot_token = os.getenv('BOT_TOKEN')
ADMIN_CHANNEL_ID = -1002337007587
img_face = FSInputFile('face_image.jpg')
img_gen = FSInputFile('gen_mus.webp')
img_promo = FSInputFile('img_promo.webp')
img_startgen = FSInputFile('img_startgen.webp')
exemple_music = FSInputFile('exemple.mp4',filename='Пример песни')

WEBHOOK_URL = os.getenv('WEBHOOK_URL')

bot = Bot(token=bot_token)
storage = MemoryStorage()
dp = Dispatcher()


# Определение состояний
class MusicGeneration(StatesGroup):
    waiting_for_genre = State()
    waiting_for_lyrics_full = State()
    waiting_for_lyrics = State()
    waiting_for_generate = State() 
    waiting_for_confirmation = State()  
    buying = State()
    simple = State()


async def set_commands(bot: Bot):
    commands = [
        types.BotCommand(command="/start", description="Главное меню"),
        types.BotCommand(command="/pay", description="Активировать подписку")
    ]
    await bot.set_my_commands(commands)

@dp.channel_post()
async def handle_admin_commands(message: types.Message):
    """Обработчик сообщений в админ-канале"""
    
    # Проверяем, что сообщение пришло из админ-канала
    if message.chat.id != ADMIN_CHANNEL_ID:
        return

    # Разбираем команду
    command_parts = message.text.split()
    if not command_parts:
        return

    command = command_parts[0].lower()  # Первая часть сообщения - команда

    if command == "/ban" and len(command_parts) > 1:
        try:
            user_id = int(command_parts[1])
            await ban(user_id)
            # Здесь можно добавить код блокировки пользователя в БД
            await message.answer(f"✅ Пользователь {user_id} забанен.")
        except ValueError:
            await message.answer("❌ Ошибка: неверный ID пользователя.")

    elif command == "/unban" and len(command_parts) > 1:
        try:
            user_id = int(command_parts[1])
            await unban(user_id)
            # Здесь можно добавить код разблокировки пользователя в БД
            await message.answer(f"✅ Пользователь {user_id} разбанен.")
        except ValueError:
            await message.answer("❌ Ошибка: неверный ID пользователя.")

    elif command == "/givetoken":
        # Проверяем количество аргументов
        if len(command_parts) < 3:
            await message.answer("❌ Ошибка: недостаточно аргументов. Используйте /givetoken <user_id> <tokens>.")
            return

        try:
            # Извлекаем user_id и tokens
            user_id = int(command_parts[1])
            tokens = int(command_parts[2])
        except ValueError:
            await message.answer("❌ Ошибка: неверный формат аргументов. <user_id> и <tokens> должны быть числами.")
            return

        # # Проверяем существование пользователя
        # user_exists = await db.user_exists(user_id)
        # if not user_exists:
        #     await message.answer(f"❌ Ошибка: пользователь с ID {user_id} не найден.")
        #     return

        try:
            
            await give_tokens(user_id, tokens)
            await message.answer(f"✅ Пользователю {user_id} успешно начислено {tokens} токенов.")

           
            
        except Exception as e:
           
            await message.answer("❌ Ошибка при начислении токенов. Пожалуйста, попробуйте позже.")

    elif command == "/untoken":
        # Проверяем количество аргументов
        if len(command_parts) < 3:
            await message.answer("❌ Ошибка: недостаточно аргументов. Используйте /untoken <user_id> <tokens>.")
            return

        try:
            # Извлекаем user_id и tokens
            user_id = int(command_parts[1])
            tokens = int(command_parts[2])
        except ValueError:
            await message.answer("❌ Ошибка: неверный формат аргументов. <user_id> и <tokens> должны быть числами.")
            return

        # # Проверяем существование пользователя
        # user_exists = await db.user_exists(user_id)
        # if not user_exists:
        #     await message.answer(f"❌ Ошибка: пользователь с ID {user_id} не найден.")
        #     return

        try:
            
            await deduct_tokens(user_id, tokens)
            await message.answer(f"✅ У пользователя {user_id} успешно списано {tokens} токенов.")

           
            
        except Exception as e:
           
            await message.answer("❌ Ошибка при начислении токенов. Пожалуйста, попробуйте позже.")
    elif command == '/automoney':
        try:
            # Проверяем, что команда содержит достаточно аргументов
            if len(command_parts) < 2:
                await message.answer("❌ Ошибка: не указан ID пользователя.\nИспользуйте: /automoney <user_id>")
                return

            # Пытаемся преобразовать user_id в число
            user_id = int(command_parts[1])
            
            # Проверяем, что user_id положительный
            if user_id <= 0:
                await message.answer("❌ Ошибка: ID пользователя должен быть положительным числом.")
                return

            # Отключаем автоподписку
            await un_auto(user_id)
            
            # Уведомляем об успешном выполнении
            await message.answer(f"✅ У пользователя {user_id} успешно отключена автоподписка.")

        except ValueError:
            await message.answer("❌ Ошибка: неверный ID пользователя. Укажите числовой ID.")
        except IndexError:
            await message.answer("❌ Ошибка: не указан ID пользователя.\nИспользуйте: /automoney <user_id>")
        except Exception as e:
            # Логируем другие ошибки
            logger.error(f"Произошла ошибка: {e}")
            await message.answer("❌ Произошла ошибка при отключении автоподписки.")
        
    elif command == "/giveprime":
        if len(command_parts) < 4:
            await message.answer("❌ Ошибка: недостаточно аргументов. Используйте /giveprime <user_id> <sub_type> <duration_days>.")
            return

        try:
            user_id = int(command_parts[1])
            sub_type = command_parts[2]
            duration_days = int(command_parts[3])
            await db.grant_subscription(user_id, sub_type, duration_days)
            await message.answer(f"✅ Пользователю {user_id} выдана подписка {sub_type} на {duration_days} дней.")

            # Отправляем благодарственное сообщение пользователю
            thank_you_message = (
            "❤️ Аврора благодарна за поддержку!\n"
            "Уверены, функционал премиум-версии принесет пользу и создаст ваш шедевр.\n"
            "Ваш тариф активирован."
        )
            await bot.send_message(chat_id=user_id, text=thank_you_message)
            # Выполняем команду /start для пользователя
        
            if user_id:

                # Создаем объект Message, имитирующий команду /start
                message = types.Message(
                    message_id=1,  # Уникальный ID сообщения (можно использовать временное значение)
                    date=datetime.datetime.now(),  # Текущая дата и время
                    chat=types.Chat(
                        id=int(user_id),  # ID чата пользователя
                        type="private"  # Тип чата (личный)
                    ),
                    from_user=types.User(
                        id=int(user_id),  # ID пользователя
                        is_bot=False,  # Пользователь не является ботом
                        first_name="User"  # Имя пользователя (можно оставить пустым)
                    ),
                    text="/start"  # Текст команды
                )
                # Создаем объект Update
                update = types.Update(
                    update_id=1,  # Уникальный ID обновления (можно использовать временное значение)
                    message=message  # Передаем созданное сообщение
                )
                # Вызываем обработчик команды /start
                await dp.feed_update(bot, update)
                # Отправляем сообщение с благодарностью и информацией об активации тарифа

        except ValueError:
            await message.answer("❌ Ошибка: неверный формат аргументов. <user_id> и <duration_days> должны быть числами.")
        except Exception as e:
            logger.error(f"Ошибка при выдаче подписки: {e}")
            await message.answer("❌ Ошибка при выдаче подписки. Пожалуйста, попробуйте позже.")

    elif command == "/unprime":
        if len(command_parts) < 2:
            await message.answer("❌ Ошибка: недостаточно аргументов. Используйте /unprime <user_id>.")
            return

        try:
            user_id = int(command_parts[1])
            await db.revoke_subscription(user_id)
            await message.answer(f"✅ Подписка пользователя {user_id} отозвана.")
        except ValueError:
            await message.answer("❌ Ошибка: неверный ID пользователя. Укажите числовой ID.")
        except Exception as e:
            logger.error(f"Ошибка при отзыве подписки: {e}")
            await message.answer("❌ Ошибка при отзыве подписки. Пожалуйста, попробуйте позже.")
    elif command == "/boss123":
        if len(command_parts) < 2:
            await message.answer("❌ Ошибка: недостаточно аргументов. Используйте /clearqueue <user_id>.")
            return

        try:
            user_id = int(command_parts[1])
            await db.clear_queue_for_user(user_id)  # Предполагаем, что такая функция существует
            await message.answer(f"✅ Очередь для пользователя {user_id} обнулена.")
        except ValueError:
            await message.answer("❌ Ошибка: неверный ID пользователя. Укажите числовой ID.")
        except Exception as e:
            logger.error(f"Ошибка при обнулении очереди: {e}")
            await message.answer("❌ Ошибка при обнулении очереди. Пожалуйста, попробуйте позже.")
    elif command == "/help":
        help_text = """
📜 *Список доступных команд:*

*/ban <user_id>* — Забанить пользователя.
*/unban <user_id>* — Разбанить пользователя.
*/givetoken <user_id> <tokens>* — Выдать токены пользователю.
*/untoken <user_id> <tokens>* — Забрать токены у пользователя.
*/automoney <user_id>* — Отключить автоподписку у пользователя.
*/giveprime <user_id> <sub_type> <duration_days>* — Выдать подписку пользователю.
*/unprime <user_id>* — Отозвать подписку у пользователя.
*/help* — Показать это сообщение.
*/boss123 <user_id>* - Обнуляет очеред ожидания на генерацию 
        """
        await message.answer(help_text, parse_mode="Markdown")
        return




@dp.message(Command('start'))
async def start(message: types.Message, state:FSMContext):
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🎵Аврора нейросеть", callback_data="generate_music"),InlineKeyboardButton(text="💳Получить генерации", callback_data="my_refs")],
        [InlineKeyboardButton(text="🌟Продвижение песен артиста", callback_data="promo")],
        [InlineKeyboardButton(text="Инструкция и поддержка", web_app=WebAppInfo(url='https://teletype.in/@infopovod/avrora')),InlineKeyboardButton(text="Другие нейросети", url='https://t.me/hassanmaxim/84')],
        
    ])
    is_sub = await is_user_subscribed(bot, message.from_user.id, '@hassanmaxim')
    referrer_id = None
    current_state = await state.get_state()
    if current_state is not None:
            await state.clear()  # чтобы свободно перейти сюда из любого другого состояния
    
    plan = await check_plan(message.from_user.id)
    plan_nadp = 'Нет подписки'
    if plan:
        
        if plan[0] == 'start':
            plan_nadp = 'Старт'
        elif plan[0] == 'master':
            print(plan[0])
            plan_nadp = 'Мастер'
        elif plan[0] == 'year':
            plan_nadp = 'Годовая'
        else:
            plan_nadp = 'Нет подписки'
    else:
        plan_nadp = 'Нет подписки'
    # Проверяем, есть ли реферальная ссылка
    args = message.text.split()
    if len(args) > 1:
            try:
                referrer_id = args[1]  # Извлекаем идентификатор реферера
                
            except ValueError:
                referrer_id = None  # Если ссылка повреждена, игнорируем
        
    if is_sub:
            user = message.from_user
            user_data = await db.user_check(user)  # Проверяем, есть ли пользователь в БД
            
            if not user_data:  # Если пользователя нет в базе
                referral_code = await generate_referral_code() + str(user.id)
                
                if referrer_id:
                    await add_referal(referrer_id, user.id)  # Добавляем реферала
                    import re
                    # Разделяем на группы букв и цифр
                    groups = re.findall(r'[a-zA-Z]+|\d+', referrer_id)
                    await bot.send_message(chat_id=groups[1], text= f'Вам начислено 0,5 генераций. Спасибо что рекомендуете нас друзьям!') 

                await db.insert_table(user, referral_code, referrer_id, 1,1)
                
                

                await message.answer('Вы зарегистрированы!')
                all_users = await check_all()
                ref_name = None
                if referrer_id is not None:
                    ref_name = await check_ref(referrer_id)
                await bot.send_message(ADMIN_CHANNEL_ID,f'✅Новая регистрация:\n Имя: {user.first_name}\n ID: {user.id} \n Username: @{user.username}\n Пригласил: {ref_name} \n Пользователей: {all_users}\n ')
           
            status = await check_status(message.from_user.id)
            if status:
                # Если пользователь не забанен, отправляем информацию о профиле
                profile_message = (
                    f"📱 Управляйте мной кнопками меню👇🏻искусственный интеллект. \n\n"
                    f"🔎 ID: <code>{message.from_user.id}</code>\n"
                    f"1️⃣ Подписка: {plan_nadp}\n"
                    f"2️⃣ Баланс: {round(await get_balance(message.from_user.id))} генераций🧾\n"
                    f"3️⃣ Перешло по вашей ссылке: {len(await get_referal(message.from_user.id))}\n\n"
                    
                    "Используйте генерации для создания песен. Одна генерация = две песни."
                )
                await message.answer(profile_message, reply_markup=keyboard,parse_mode=ParseMode.HTML)
            else:
                # Если пользователь забанен
                await message.answer('Вы забанены!')
    else:
                # Если пользователь не подписан, показываем кнопки для подписки и активации
                sub_keyboard = InlineKeyboardMarkup(inline_keyboard=[
                    [InlineKeyboardButton(text="Подписаться", url="https://t.me/hassanmaxim")],
                    [InlineKeyboardButton(text="Активировать", callback_data="activate")]
                ])

                face_message = (
                    f"{message.from_user.first_name}, создавайте авторские песни и клипы с помощью искусственного интеллекта AVRORA 🌟\n\n"
                    "По правилам телеграм для активации нейросети подпишитесь на сообщество автора и получите бесплатные генерации."
                )
                
                # Отправляем сообщение с изображением и клавиатурой
                await message.answer_photo(img_face, caption=face_message, reply_markup=sub_keyboard)
    

        
@dp.callback_query(lambda query: query.data == "activate")
async def activate(callback_query: types.CallbackQuery, state: FSMContext):
    user = callback_query.from_user
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🎵Аврора нейросеть", callback_data="generate_music"),InlineKeyboardButton(text="💳Получить генерации", callback_data="my_refs")],
        [InlineKeyboardButton(text="🌟Продвижение песен артиста", callback_data="promo")],
        [InlineKeyboardButton(text="Инструкция и поддержка", web_app=WebAppInfo(url='https://teletype.in/@infopovod/avrora')),InlineKeyboardButton(text="Другие нейросети", url='https://t.me/hassanmaxim/84')],
       
    ])
    keyboard1 = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🎵Аврора нейросеть", callback_data="generate_music")],
    ])
    keyboard2 = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="Посмотреть пример", callback_data="sample")],
    ])
    current_state = await state.get_state()
    if current_state is not None:
            await state.clear()  # чтобы свободно перейти сюда из любого другого состояния
    plan = await check_plan(callback_query.from_user.id)
    plan_nadp = 'Нет подписки'
    if plan:
        
        if plan[0] == 'start':
            plan_nadp = 'Старт'
        elif plan[0] == 'master':
            print(plan[0])
            plan_nadp = 'Мастер'
        elif plan[0] == 'year':
            plan_nadp = 'Годовая'
        else:
            plan_nadp = 'Нет подписки'
    else:
        plan_nadp = 'Нет подписки'
    
    # Проверяем подписку
    is_sub = await is_user_subscribed(bot, user.id, '@hassanmaxim')
    
    if is_sub:
            user_data = await db.user_check(user)  # Проверяем, есть ли пользователь в БД

            if not user_data:  # Если пользователя нет в базе
                referral_code = await generate_referral_code() + str(user.id)
                referrer_id = None  # В callback нет реферальных данных, убираем

                if referrer_id:
                    await add_referal(referrer_id, user.id)  

                await db.insert_table(user, referral_code, referrer_id, 1,1)

                

                await callback_query.message.answer('Вы зарегистрированы!')
                all_users = await check_all()
                ref_name = None
                if referrer_id is not None:
                    ref_name = await check_ref(referrer_id)
                await bot.send_message(ADMIN_CHANNEL_ID,f'✅Новая регистрация:\n Имя: {user.first_name}\n ID: {user.id} \n Username: @{user.username}\n Пригласил: {ref_name} \n Пользователей: {all_users}\n ')

            balance = await get_balance(user.id)
            status = await check_status(callback_query.from_user.id)
            if status:
                # Проверяем, содержит ли сообщение фото и подпись
                if callback_query.message.photo:
                    # Проверяем, что подпись не равна 'Выберите один из доступных жанров'
                    if callback_query.message.caption and 'создавайте авторские песни и клипы' in callback_query.message.caption:
                        try:
                            # Удаляем предыдущее сообщение
                            await bot.delete_message(
                                chat_id=callback_query.message.chat.id,
                                message_id=callback_query.message.message_id
                            )
                        except Exception as e:
                            print(f"Ошибка при удалении сообщения: {e}")
                        
                        # Отправляем первое сообщение с описанием и балансом
                        await callback_query.message.answer(
                            f'✅ Доступ открыт. Добро пожаловать!\n'
                            f'Имя: {user.first_name}\n'
                            f'▶️ Ваш баланс: {round(balance)} генерация (вы можете создать две песни) \n'
                            '''Я могу создать уникальную песню по вашему запросу, с вашим текстом, голосом и в любом жанре, чтобы далее опубликовать ее на стриминговых площадках и приносить доход.\n

Не нужно платить сотни тысяч продюсерам!\n
В 2 клика создавай инструментал, вокал и многое другое!\n\n

Посмотри пример и создай свой шедевр 👇''',
                            
                            parse_mode=ParseMode.HTML, reply_markup= keyboard2
                        )

                    else:
                        try:
                            # Удаляем предыдущее сообщение
                            current_state = await state.get_state()
                            if current_state is not None:
                                await state.clear()
                            await bot.delete_message(
                                chat_id=callback_query.message.chat.id,
                                message_id=callback_query.message.message_id
                            )
                            profile_message = (
                        f"📱 Управляйте мной кнопками меню👇🏻искусственный интеллект. \n\n"
                        f"🔎 ID: <code>{callback_query.from_user.id}</code>\n"
                        f"1️⃣ Подписка: {plan_nadp}\n"
                        f"2️⃣ Баланс: {round(await get_balance(callback_query.from_user.id))} генераций🧾\n"
                        f"3️⃣ Перешло по вашей ссылке: {len(await get_referal(callback_query.from_user.id))}\n\n"
                        "Используйте генерации для создания песен. Одна генерация = две песни."
                    )
                            await callback_query.message.answer(
                            profile_message,
                            reply_markup=keyboard,
                            parse_mode=ParseMode.HTML
                        )
                        except Exception as e:
                            print(f"Ошибка при удалении сообщения: {e}")

                # Если сообщение содержит текст
                elif callback_query.message.text:
                    profile_message = (
                        f"📱 Управляйте мной кнопками меню👇🏻искусственный интеллект. \n\n"
                        f"🔎 ID: <code>{callback_query.from_user.id}</code>\n"
                        f"1️⃣ Подписка: {plan_nadp}\n"
                        f"2️⃣ Баланс: {round(await get_balance(callback_query.from_user.id))} генераций🧾\n"
                        f"3️⃣ Перешло по вашей ссылке: {len(await get_referal(callback_query.from_user.id))}\n\n"
                        "Используйте генерации для создания песен. Одна генерация = две песни."
                    )

                    # Редактируем текстовое сообщение
                    try:
                        await callback_query.message.edit_text(
                            profile_message,
                            reply_markup=keyboard,
                            parse_mode=ParseMode.HTML
                        )
                    except Exception as e:
                        print(f"Ошибка при редактировании сообщения: {e}")
                
            else:
                            # Если статус False (пользователь забанен)
                    await callback_query.message.answer('Вы забанены!')
                        

    else:
            # Если пользователь не подписан, просим подписаться
            sub_keyboard = InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="Подписаться", url="https://t.me/hassanmaxim")],
                [InlineKeyboardButton(text="Активировать", callback_data="activate")]
            ])
            face_message = f'''{callback_query.message.from_user.first_name}, создавайте авторские песни и клипы с помощью искусственного интеллекта AVRORA 🌟\n

    По правилам телеграм для активации нейросети подпишитесь на сообщество автора и получите бесплатные генерации.'''
            await callback_query.message.answer_photo(img_face, caption= face_message, reply_markup= sub_keyboard)
    

    # Убираем "часики" на кнопке
    await callback_query.answer()

@dp.callback_query(lambda query: query.data == "sample")
async def sample(callback_query: types.CallbackQuery, state: FSMContext):
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="Создать песню", callback_data="generate_music")],
    ])

    # Отправляем аудио с примером песни
    await callback_query.message.answer_video(exemple_music,reply_markup=keyboard,)

# Список всех музыкальных жанров
genres = [
    "Поп", "Рэп", "Рок", "Эстрадное", "Частушки", "Считалочки", "Детские песни", "Колыбельные", "Шансон", "Хип-хоп",
    "Электронная", "Джаз", "Блюз", "Классика", "Регги", "Поп-рок", "Фолк", "Метал", "Панк", "Инди", "Клубная музыка",
    "Диско", "Соул", "Музыка для праздников", "Латино", "Техно", "Хоровая музыка", "Ретро", "Грустная музыка", "Мюзиклы",
    "Афро-бит", "Даунтемпо", "Транс", "Лоу-фай", "Кантри", "Рэггетон", "Романсы", "Акустическая", "Дети поют", "Музыка для медитации",
    "Фанк", "Светская музыка", "Инструментальная", "Спектакли", "Передачи с музыкой", "Хипстерская", "Уличная музыка", "Песни о любви",
    "Сказки для детей", "Электро"
]

# Количество жанров на одной странице
ITEMS_PER_PAGE = 15

# Уровни подписки
SUBSCRIPTION_LEVELS = {
    False: ["Поп", "Рэп", "Рок",],  # Без подписки — нет доступных жанров
    "start": genres[:15],  # Стартовая подписка
    "master": genres[:30],  # Мастер-подписка — первые 20 жанров
    "year": genres  # Годовая подписка — все жанры
    }

async def create_keyboard(user_id: int, page: int = 0, selected_genre: str = None):
    # Создаем клавиатуру с пустым списком кнопок
    keyboard = InlineKeyboardMarkup(inline_keyboard=[])

    # Определяем доступные жанры для уровня подписки
    plan = await check_plan(user_id)
    print(f'KEY{plan}')
    if plan != False:
        available_genres = SUBSCRIPTION_LEVELS.get(plan[0], [])
    else:
        available_genres = SUBSCRIPTION_LEVELS.get(plan, [])
    print(available_genres)

    # Добавляем кнопки с жанрами по 4 в ряд
    start = page * ITEMS_PER_PAGE
    end = start + ITEMS_PER_PAGE
    genres_to_display = genres[start:end]

    # Группируем кнопки по 4 в ряд
    row = []
    for genre in genres_to_display:
        if genre in available_genres:
            # Если жанр доступен, добавляем активную кнопку
            button_text = f"✅{genre} " if genre == selected_genre else genre
            
            row.append(InlineKeyboardButton(text=button_text, callback_data=f"genre_{genre}"))
        else:
            # Если жанр недоступен, добавляем отключенную кнопку
            row.append(InlineKeyboardButton(text=f'🔒{genre}', callback_data=f"genre_{genre}", disabled=True))

        # Если в ряду 4 кнопки, добавляем его в клавиатуру и начинаем новый ряд
        if len(row) == 3:
            keyboard.inline_keyboard.append(row)
            row = []

    # Если остались кнопки, которые не вошли в последний ряд, добавляем их
    if row:
        keyboard.inline_keyboard.append(row)

    # Кнопки пагинации
    pagination_buttons = []
    if page > 0:
        pagination_buttons.append(InlineKeyboardButton(text="⬅️ Назад", callback_data=f"page_{page - 1}"))
    if end < len(genres):
        pagination_buttons.append(InlineKeyboardButton(text="Вперед ➡️", callback_data=f"page_{page + 1}"))

    # Добавляем кнопки пагинации как один ряд
    if pagination_buttons:
        keyboard.inline_keyboard.append(pagination_buttons)

    # Кнопка "Назад"
    keyboard.inline_keyboard.append([InlineKeyboardButton(text="🔙Главное меню", callback_data="activate")])

    return keyboard

# Обработчик для пагинации
@dp.callback_query(lambda query: query.data.startswith("page_"))
async def handle_pagination(callback_query: types.CallbackQuery):
    page = int(callback_query.data.split("_")[1])

    await callback_query.message.edit_caption(
        caption="Выберите один из доступных жанров",
        reply_markup=await create_keyboard(callback_query.from_user.id, page=page)
    )

    await callback_query.answer()

@dp.callback_query(lambda query: query.data == "generate_music")
async def generate_music_start(callback_query: types.CallbackQuery, state: FSMContext):
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🎸СОЗДАТЬ ПЕСНЮ", callback_data="gen_music")],
        [InlineKeyboardButton(text="Главное меню", callback_data='activate')],
       
    ])
    keyboard1 = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="Получить генерации", callback_data="my_refs")],
        [InlineKeyboardButton(text="Бесплатные генерации", callback_data='free')],
        [InlineKeyboardButton(text="Главное меню", callback_data='activate')],
       
    ])
    balance = await get_balance(callback_query.from_user.id)
    if balance < 1:
            await callback_query.message.answer(
                f'У вас закончились генерации. Пожалуйста пополните подписку, либо используйте бесплатные генерации что мы даем всем хорошим людям.',
            reply_markup=keyboard1)
    else:

            await bot.delete_message(
                chat_id=callback_query.message.chat.id,
                message_id=callback_query.message.message_id
            )

            await callback_query.message.answer_photo(
                img_startgen,
                caption=''' ✅Активировано нейросеть AVRORA – всего в 2 клика: музыка, ритм, голос, исполнение, публикация, продвижение.\n\n

        Можешь представить свою песню? Значит теперь можешь ее создать легко!\n
        01/ Выбери жанр.\n
        02/ Выбери режим.\n
        03/ Выбери текст, голос, уникализируй\n
        04/ УРА! ТВОЙ ШЕДЕВР ГОТОВ!\n
        05/ Публикуй и зарабатывай на своем творчестве.\n\n

        Ознакомьтесь с инструкцией. Результат зависит от качества ваших запросов и подписки.️\n
        https://teletype.in/@infopovod/avrora''',
                reply_markup=keyboard,
                parse_mode=ParseMode.HTML,
                disable_web_page_preview=True
            )

@dp.callback_query(lambda query: query.data == "gen_music")
async def generate_music(callback_query: types.CallbackQuery, state: FSMContext):
    user_id = callback_query.from_user.id
    await callback_query.answer('')

    # Проверяем статус пользователя (забанен или нет)
    status = await check_status(user_id)
    if not status:
        await callback_query.message.edit_text('Вы забанены!')
        return

    # Проверяем, когда пользователь последний раз отправлял запрос
    last_request_time = await db.get_last_request_time(user_id)
    if last_request_time:
        from datetime import datetime, timedelta
        current_time = datetime.now()
        time_difference = current_time - last_request_time

        # Если с последнего запроса прошло менее 10 минут
        if time_difference < timedelta(minutes=10):
            # Вычисляем оставшееся время
            remaining_time = timedelta(minutes=10) - time_difference
            minutes, seconds = divmod(remaining_time.seconds, 60)

            # Формируем сообщение
            message = (
                f"⏳ Вы можете отправлять новый запрос только раз в 10 минут.\n"
                f"Попробуйте через {minutes} минут {seconds} секунд."
            )
            await callback_query.message.answer(message)
            return

    # Удаляем предыдущее сообщение
    await bot.delete_message(
        chat_id=callback_query.message.chat.id,
        message_id=callback_query.message.message_id
    )

    # Устанавливаем состояние "waiting_for_genre"
    await state.set_state(MusicGeneration.waiting_for_genre)
    await callback_query.message.answer_photo(
        img_gen,
        caption='Выберите один из доступных жанров',
        reply_markup=await create_keyboard(user_id),
        parse_mode=ParseMode.HTML,
        disable_web_page_preview=True
    )

    # Обновляем время последнего запроса пользователя
    await db.update_last_request_time(user_id)

    # Очищаем старые записи (опционально)
    await db.clear_old_requests()

# Обработчик callback-запроса для выбора жанра
@dp.callback_query(lambda query: query.data.startswith('genre_'))
async def choice_genre(callback_query: types.CallbackQuery, state: FSMContext):
    user_id = callback_query.from_user.id
    user_subscription = await check_plan(user_id)
    
    # Получаем выбранный жанр
    selected_genre = callback_query.data.split('_', 1)[1]

    # Проверяем, доступен ли жанр для текущей подписки
    available_genres = SUBSCRIPTION_LEVELS.get(user_subscription[0], [])
    if selected_genre not in available_genres:
        await callback_query.answer("❌ Этот жанр недоступен для вашей подписки.", show_alert=True)
        return

    # Показываем зелёную галочку
    await callback_query.answer()

    # Сохраняем выбранный жанр в состояние
    await state.update_data(genre=selected_genre)
    print(f"Выбран жанр: {selected_genre}")

    # Обновляем клавиатуру с учётом выбранного жанра
    updated_keyboard = await create_keyboard(user_id, selected_genre=selected_genre)

    # Редактируем сообщение с обновлённой клавиатурой
    await callback_query.message.edit_caption(
       caption= '''✅Простой режим активирован. (1 токен = 2 песни).\n\n
<b>Выберите один из доступных жанров.👇</b>''',
        reply_markup=updated_keyboard,
        parse_mode=ParseMode.HTML
    )

    # Устанавливаем следующее состояние
    await state.set_state(MusicGeneration.waiting_for_lyrics_full)
    print(f"Установлено состояние: {await state.get_state()}")

    # Отправляем сообщение с инструкцией
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🔙Назад", callback_data="generate_music")]
    ])
    await callback_query.message.answer(
        '''Песня почти готова, теперь просто отправьте текст (не более 3000 символов).
А нейросеть сама его положит в такт музыки.\n\n
<b>👇отправьте слова песни👇</b>''', parse_mode=ParseMode.HTML, reply_markup=keyboard)
    print(f"Установлено состояние: {await state.get_state()}")


# Обработчик текстового сообщения (текст песни)
@dp.message(MusicGeneration.waiting_for_lyrics_full)
async def full_lyric(message: types.Message, state: FSMContext):
    print("Обработчик full_lyric вызван.")
    try:
        # Получаем текст песни
        text = message.text
        print(f"Получен текст: {text}")

        # Проверяем длину текста
        if len(text) > 3000:
            await message.answer("Текст слишком длинный. Максимум 3000 символов.")
            return

        # Сохраняем текст в состояние
        await state.update_data(text=text)
        print("Текст сохранен в состояние.")

        # Получаем данные из состояния
        user_data = await state.get_data()
        genre = user_data.get('genre')
        print(f"Получен жанр: {genre}")

        # Проверяем наличие жанра
        if not genre:
            await message.answer("Ошибка: жанр не найден. Пожалуйста, начните заново.")
            await state.clear()
            return

        # Создаем клавиатуру для подтверждения
        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="✅ Начать генерацию", callback_data="confirm")],
            #[InlineKeyboardButton(text="✏️ Изменить текст", callback_data="change_text")],
            [InlineKeyboardButton(text="🔙 Назад", callback_data="generate_music")]
        ])

        # Отправляем сообщение с подтверждением
        await message.answer(
            f'''Проверьте информацию 
<b>Ваш жанр</b>: {genre}\n\n
<b>Ваш текст</b>: {text[:500]}...'''  # Обрезаем текст для удобства
        ,parse_mode=ParseMode.HTML)
        await message.answer("Подтвердите данные или измените текст:", reply_markup=keyboard)

        # Устанавливаем состояние "waiting_for_confirmation"
        await state.set_state(MusicGeneration.waiting_for_confirmation)
        print("Состояние установлено: waiting_for_confirmation")

    except Exception as e:
        print(f"Ошибка в обработчике full_lyric: {e}")
        await message.answer("Произошла ошибка. Пожалуйста, попробуйте позже.")

# Обработчик callback-запросов (подтверждение или изменение текста)
@dp.callback_query(lambda query: query.data in ["confirm", "change_text", "generate_music"])
async def handle_confirmation(callback_query: types.CallbackQuery, state: FSMContext):
    await callback_query.answer()  # Подтверждаем получение callback

    if callback_query.data == "confirm":
        # Логика подтверждения данных
        #await callback_query.message.answer("Данные подтверждены. Начинаем генерацию...")
        
        # Здесь можно добавить логику для начала генерации
        await state.set_state(MusicGeneration.waiting_for_generate)
        print(f"Установлено состояние: {await state.get_state()}")
        # Вызываем обработчик генерации напрямую
        await handle_music_generation(callback_query, state)

    elif callback_query.data == "change_text":
        # Логика изменения текста
        await callback_query.message.answer("Введите новый текст:")
        await state.set_state(MusicGeneration.waiting_for_lyrics_full)

    elif callback_query.data == "generate_music":
        # Логика возврата к генерации музыки
        await callback_query.message.answer("Возвращаемся к выбору жанра...")
        await state.set_state(MusicGeneration.waiting_for_genre)

from aiogram import types
import datetime
async def return_to_start(user_id: int):
    """
    Имитирует команду /start для пользователя.
    """
    try:
        # Создаем объект Message, имитирующий команду /start
        message = types.Message(
            message_id=1,  # Уникальный ID сообщения (можно использовать временное значение)
            date=datetime.datetime.now(),  # Текущая дата и время
            chat=types.Chat(
                id=int(user_id),  # ID чата пользователя
                type="private"  # Тип чата (личный)
            ),
            from_user=types.User(
                id=int(user_id),  # ID пользователя
                is_bot=False,  # Пользователь не является ботом
                first_name="User"  # Имя пользователя (можно оставить пустым)
            ),
            text="/start"  # Текст команды
        )

        # Создаем объект Update
        update = types.Update(
            update_id=1,  # Уникальный ID обновления (можно использовать временное значение)
            message=message  # Передаем созданное сообщение
        )

        # Вызываем обработчик команды /start
        await dp.feed_update(bot, update)

        logger.info(f"Пользователь {user_id} возвращён на /start.")

    except Exception as e:
        logger.error(f"Ошибка при возврате пользователя {user_id} на /start: {e}")
            
# Обработчик callback-запроса для генерации музыки
@dp.callback_query(MusicGeneration.waiting_for_generate)
async def handle_music_generation(callback_query: types.CallbackQuery, state: FSMContext):
    try:
        balance = await get_balance(callback_query.from_user.id)
        if balance < 1:
            await callback_query.message.answer(
                f'У вас закончились генерации. Пожалуйста пополните подписку, либо используйте бесплатные генерации что мы даем всем хорошим людям.',
            )
            # Имитируем команду /start
            user_id = callback_query.from_user.id
            await return_to_start(user_id)
        else:
            await callback_query.answer()  # Подтверждаем получение callback
            await deduct_tokens(callback_query.from_user.id, 1)  # Списываем токен

            await callback_query.message.answer('Генерация может занять до 800 сек. ⏳ Создаю мелодию, рифму, бит, голос, обложку.')

            # Получаем данные из состояния
            user_data = await state.get_data()
            genre = user_data['genre']
            lyrics = user_data['text']

           

            
            await aimu.post_music(user_id= callback_query.from_user.id, regime= 0, prompt= lyrics,tags= genre)
            
            await state.clear()
    except Exception as e:
        await bot.send_message(
            ADMIN_CHANNEL_ID,
            f"Произошла ошибка: {e}\n У пользователя @{callback_query.from_user.username} ({callback_query.from_user.id})"
        )



async def process_music_task(task_id: str, status: str, output: dict, user_id: int,lyrics,input):
    """
    Обрабатывает задачу генерации музыки в фоновом режиме.
    """
    try:
        if status == 'completed':
            logger.info(f"Задача {task_id} завершена.")
            await handle_completed_music_task(output, user_id,lyrics)
        elif status == 'failed':
            logger.error(f"Задача {task_id} завершена с ошибкой.")
            await handle_failed_music_task(task_id, user_id,input)
        else:
            logger.info(f"Задача {task_id} имеет статус: {status}")
    except Exception as e:
        logger.error(f"Ошибка при обработке задачи {task_id}: {e}")

async def handle_completed_music_task(output: dict, user_id: int, lyrics: str):
    """
    Обрабатывает завершённую задачу генерации музыки.
    """
    try:
        # Проверяем, что lyrics является строкой
        if not isinstance(lyrics, str):
            lyrics = str(lyrics)  # Преобразуем в строку, если это не строка

        # Отправляем результат пользователю
        for _, clip_data in output.get('clips', {}).items():
            out_img = types.URLInputFile(clip_data['image_url'])
            out_music = types.URLInputFile(clip_data['audio_url'])

            # Разбиваем текст на строки, удаляем пустые
            lines = [line.strip() for line in lyrics.split('\n') if line.strip()]

            # Если есть строки, выбираем случайную
            if lines:
                first_string = random.choice(lines)
            else:
                first_string = "Без названия"  # Если текст пуст, подставляем заглушку

            title = '@avroraai_bot - ' + first_string

            await bot.send_photo(user_id, out_img)
            await bot.send_audio(user_id, out_music, title=title)
            await bot.send_message(user_id,'''ВАШ ШЕДЕВР ГОТОВ!🌟
Публикуйте на всех площадках и зарабатывайте.\n
АВРОРА ИИ - является партнёром крупнейших муз.площадок.Мы способны оказать всестороннюю поддержку в размещении вашего творчества в редакторских плейлистах, баннерах и витринах Яндекс. Музыки, VK Музыки, Apple Music, Звук, МТС Музыки, Spotify и других сервисах.\n\nЕсли результат не точный - обязательно посмотри инструкции, 99% это решит запрос, я умею всё, просто правильно используй!''')

        # Логируем успешное завершение
        logger.info(f"Результат задачи отправлен пользователю {user_id}.")

        # Возвращаем пользователя на /start
        await return_to_start(user_id)

    except Exception as e:
        logger.error(f"Ошибка при отправке результата пользователю {user_id}: {e}")
        await bot.send_message(
            chat_id=user_id,
            text="🚨 Произошла ошибка при отправке результата. Пожалуйста, попробуйте ещё раз."
        )

        

async def handle_failed_music_task(task_id: str, user_id: int,input):
    """
    Обрабатывает задачу, завершённую с ошибкой.
    """
    try:
    
        await bot.send_message(chat_id=user_id,text='''🚨 Упс. Сейчас у нас много запросов. Произошла ошибка при генерации музыки.
Измените ваш текст и попробуйте еще раз.  А так же, можете активировать подписку для приоритетной очереди.''')
        await give_tokens(user_id,1)
        await return_to_start(user_id)
        #aimu.post_music(user_id=user_id,regime=0, prompt = input.get('prompt'),tags= input.get('tags') )
        logger.error(f"Задача {task_id} завершена с ошибкой для пользователя {user_id}.")

    except Exception as e:
        logger.error(f"Ошибка при отправке уведомления об ошибке пользователю {user_id}: {e}")
    
@dp.message(Command('pay'))
async def pay(message:types.Message,state: FSMContext):
    current_state = await state.get_state()
    if current_state is not None:
            await state.clear()
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🌘Старт", callback_data="sub_start"),
         InlineKeyboardButton(text="🌗Творец", callback_data="sub_master"),
        ],
        [InlineKeyboardButton(text="⭐Звезда", callback_data="sub_year"),
         InlineKeyboardButton(text="❤️Бесплатные генерации", callback_data="free")],
        [InlineKeyboardButton(text="Отменить продление", url="https://t.me/dropsupport")],
        [InlineKeyboardButton(text="🔙 Назад", callback_data="activate")]
    ])
    mess = (
            f'''Выберите тариф ниже👇🏽\n
<b>Пойте как ваш любимый исполнитель за считанные минуты, публикуйте на всех площадках и зарабатывайте.</b>\n
<b>ТАРИФЫ:</b>\n
🌘 Старт - 10 генераций (2 жанра) - 350₽/мес \n

🌗 Творец- 30 генераций (35 жанров) - 990₽/мес \n

⭐ Звезда - 30 генераций (250 жанров) - 5900₽/мес \n

✅Оплачивайте через официальные платежные с-мы безопасно. Нам доверяю: Paypal, Sber, Yandex money, СБП, Vk pay и другие.\n

{message.from_user.first_name}, вы можете поддержать наш социальный проект который мы развиваем полностью на свои средства, либо использовать бесплатные генерации что мы дарим каждый день всем хорошим людям.\n

<b>Выберите тариф ниже👇🏽</b>'''
        )
    await message.answer(mess, reply_markup=keyboard,parse_mode=ParseMode.HTML)
    

@dp.callback_query(lambda query: query.data == "my_refs")
async def get_sub(callback_query: types.CallbackQuery,state: FSMContext):
    current_state = await state.get_state()
    if current_state is not None:
            await state.clear() 
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🌘Старт", callback_data="sub_start"),
         InlineKeyboardButton(text="🌗Творец", callback_data="sub_master"),
        ],
        [InlineKeyboardButton(text="⭐Звезда", callback_data="sub_year"),
         InlineKeyboardButton(text="❤️Бесплатные генерации", callback_data="free")],
        [InlineKeyboardButton(text="Отменить продление", url="https://t.me/dropsupport")],
        [InlineKeyboardButton(text="🔙 Назад", callback_data="activate")]
    ])
    mess = (
            f'''Выберите тариф ниже👇🏽\n
<b>Пойте как ваш любимый исполнитель за считанные минуты, публикуйте на всех площадках и зарабатывайте.</b>\n
<b>ТАРИФЫ:</b>\n
🌘 Старт - 10 генераций (2 жанра) - 350₽/мес \n

🌗 Творец- 30 генераций (35 жанров) - 990₽/мес \n

⭐ Звезда - 30 генераций (250 жанров) - 5900₽/мес \n

✅Оплачивайте через официальные платежные с-мы безопасно. Нам доверяю: Paypal, Sber, Yandex money, СБП, Vk pay и другие.\n

{callback_query.from_user.first_name}, вы можете поддержать наш социальный проект который мы развиваем полностью на свои средства, либо использовать бесплатные генерации что мы дарим каждый день всем хорошим людям.\n

<b>Выберите тариф ниже👇🏽</b>'''
        )
    await callback_query.message.edit_text(mess, reply_markup=keyboard,parse_mode=ParseMode.HTML)

from aiogram.utils.keyboard import InlineKeyboardBuilder
import pytz
async def process_subscription(callback_query: types.CallbackQuery, state: FSMContext, sub_type: str, price_env: str, tokens: int):
    """
    Обрабатывает запрос на подписку: создает платеж и отправляет пользователю ссылку для оплаты.

    :param callback_query: CallbackQuery от пользователя.
    :param state: Состояние FSM.
    :param sub_type: Тип подписки (например, "start", "master", "year").
    :param price_env: Название переменной окружения с ценой подписки.
    :param tokens: Количество токенов, которые пользователь получит после оплаты.
    """
    try:
        user_id = callback_query.from_user.id
        current_state = await state.get_state()
        if current_state is not None:
            await state.clear()
        from datetime import datetime
        # Получаем текущее время в UTC
        now_datetime = datetime.now(pytz.utc)
        expires_at = (now_datetime + timedelta(minutes=15)).strftime("%Y-%m-%dT%H:%M:%S.%f")[:-3] + "Z"
        sub_price = os.getenv(price_env)

        if not sub_price:
            logger.error(f"Не удалось получить цену подписки из переменной окружения: {price_env}")
            await callback_query.message.edit_text("Произошла ошибка. Попробуйте позже.")
            return
        
        # Создаем платеж
        url, payment_id = await create_payment(sub_price, expires_at, user_id, sub_type, tokens)
        if not url or not payment_id:
            logger.error(f"Не удалось создать платеж для пользователя {user_id}")
            await callback_query.message.edit_text("Не удалось создать платёж. Попробуйте ещё раз.")
            return

        # Сохраняем платеж в базу данных
        await save_payment(payment_id, user_id, sub_type, tokens)

        # Создаем клавиатуру с кнопкой для оплаты
        keyboard = InlineKeyboardBuilder()
        keyboard.row(types.InlineKeyboardButton(text=f"Оплатить {sub_price} руб.", url=url))
        keyboard.row(types.InlineKeyboardButton(text="⬅ Назад", callback_data='my_refs'))

        # Отправляем сообщение с инструкцией
        await callback_query.message.edit_text(
            '✅Оплачивайте через официальные платежные с-мы безопасно. Нам доверяют: Paypal, Sber, Yandex money, СБП, Vk pay и другие.\n',
            reply_markup=keyboard.as_markup()
        )
        await callback_query.answer('', cache_time=60)

    except Exception as e:
        logger.error(f"Ошибка в process_subscription: {e}")
        await callback_query.answer("Произошла ошибка. Попробуйте позже.")
        await state.clear()

from db import save_payment,select_payment,update_payment
async def handle_payment_webhook(data: dict, bot: Bot):
    """
    Обрабатывает вебхук с событием 'payment.succeeded'.

    :param data: Данные вебхука.
    :param bot: Экземпляр бота для отправки уведомлений.
    :return: JSONResponse с результатом обработки.
    """
    try:
        if data.get('event') == 'payment.succeeded':
            payment_id = data.get('object', {}).get('invoice_details', {}).get('id')
            user_id = data.get('object', {}).get('metadata', {}).get('user_id')
            sub_type = data.get('object', {}).get('metadata', {}).get('sub_type')
            tokens = int(data.get('object', {}).get('metadata', {}).get('tokens', 0))
            payment_method_id = data.get('object', {}).get('payment_method', {}).get('id')
            payment_method_saved = data.get('object', {}).get('payment_method', {}).get('saved', False)

            # Проверяем, что платеж существует в базе данных
            payment = await select_payment(payment_id)
            if not payment:
                logger.error(f"Платеж {payment_id} не найден в базе данных")
                return JSONResponse(
                    content={"status": "error", "message": f"Платеж {payment_id} не найден"},
                    status_code=404
                )

            # Обращение к данным по индексам (если payment - кортеж)
            payment_status = payment[4]  # Пример: статус находится на 4-й позиции
            if payment_status == "succeeded":
                logger.warning(f"Платеж {payment_id} уже был обработан")
                return JSONResponse(
                    content={"status": "ignored", "message": "Payment already processed"}
                )

            # Обновляем статус платежа
            await update_payment(payment_id)
            from datetime import datetime
            # Начисляем токены и активируем подписку
            await give_tokens(user_id, tokens)
            expiry_date = (datetime.now() + timedelta(days=30)).strftime('%Y-%m-%d')
            await get_subsc(expiry_date, sub_type, user_id)

            # Если способ оплаты сохранен, сохраняем payment_method.id
            if payment_method_saved and payment_method_id:
                await add_auto(user_id, payment_method_id)
                logger.info(f"Способ оплаты сохранен для пользователя {user_id}: {payment_method_id}")
            # Исправленный код
            user_info = await db.get_user(user_id)  # Добавляем await
            username = user_info[0] if user_info else "Unknown"  # Проверяем, что результат не None
            # Уведомляем администратора
            await bot.send_message(
                ADMIN_CHANNEL_ID,
                f'Пользователь {user_id}(@{username}) оплатил подписку {sub_type}. Генераций начислено: {tokens}'
            )

            return JSONResponse(content={"status": "ok"})

        else:
            logger.info(f"Игнорируем событие: {data.get('event')}")
            return JSONResponse(
                content={"status": "ignored", "message": "Event is not payment.succeeded"}
            )

    except Exception as e:
        logger.error(f"Ошибка при обработке вебхука: {e}")
        return JSONResponse(
            content={"status": "error", "message": str(e)},
            status_code=500
        )


@dp.callback_query(lambda query: query.data == "sub_start")
async def sub_start(callback_query: types.CallbackQuery, state: FSMContext):
    await callback_query.answer("", cache_time=1)
    await process_subscription(callback_query, state, "start", 'PRICE_START', 20)

@dp.callback_query(lambda query: query.data == "sub_master")
async def sub_master(callback_query: types.CallbackQuery, state: FSMContext):
    await callback_query.answer("", cache_time=1)
    await process_subscription(callback_query, state, "master", 'PRICE_MASTER', 60)

@dp.callback_query(lambda query: query.data == "sub_year")
async def sub_year(callback_query: types.CallbackQuery, state: FSMContext):
    await callback_query.answer("", cache_time=1)
    await process_subscription(callback_query, state, "year", 'PRICE_YEAR', 60)

@dp.callback_query(lambda query: query.data == 'free')
async def get_free(callback_query: types.CallbackQuery):
    user_id = callback_query.from_user.id
    refs = await get_referal(user_id)
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🔙 Назад", callback_data="my_refs")]
    ])
    bot_username = await bot.get_me()  # Получаем username бота
    username = bot_username.username
    ref = await get_ref_url(callback_query.from_user.id)  # Ожидаем результат функции

    if not ref:
        await callback_query.message.edit_text("У вас пока нет реферального кода.")
        return

    ref_url = await generate_referral_link(username, ref)
    mess = f'''{callback_query.from_user.first_name}, расскажите о нас своим коллегам.\n
📍За каждого приглашенного - 0.5 генераций (2 песни).\n

Ваша ссылка для приглашения (скопируйте и отправьте её коллегам или в чаты):\n
{ref_url}

▶️ Вы пригласили: {len(refs)} чел.

'''
    await callback_query.message.edit_text(mess, reply_markup= keyboard)


@dp.callback_query(lambda query: query.data == "help")
async def help(callback_query: types.CallbackQuery):
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🔙 Назад", callback_data="activate")]
    ])
    await callback_query.message.edit_text("Другие нейросети по ссылке - https://t.me/hassanmaxim/84", reply_markup=keyboard)

@dp.callback_query(lambda query: query.data == "support")
async def support(callback_query: types.CallbackQuery):
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🔙 Назад", callback_data="activate")]
    ])
    await callback_query.message.edit_text("Поддержка - https://teletype.in/@infopovod/avrora", reply_markup=keyboard)

@dp.callback_query(lambda query: query.data == "promo")
async def promo(callback_query: types.CallbackQuery):
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🔙 Назад", callback_data="activate")]
    ])
    # Удаляем предыдущее сообщение
    await bot.delete_message(
        chat_id=callback_query.message.chat.id,
        message_id=callback_query.message.message_id
    )
    await callback_query.message.answer_photo(img_promo, caption= 'Поможем с монетизацией вашего творчества и отгрузкой треков на Яндекс. Музыку, VK Музыку, Apple Music, Звук, МТС Музыка, Spotify и другие музыкальные площадки\n\n Доступна на тарифе Звезда', reply_markup= keyboard)

@dp.message()
async def any_message_handler(message: types.Message, state: FSMContext):
    # Проверяем текущее состояние пользователя
    current_state = await state.get_state()
    # Если состояние пользователя не равно None, завершаем выполнение хэндлера
    if current_state is not None:
        return
    
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🎵Аврора нейросеть", callback_data="generate_music"),InlineKeyboardButton(text="💳Получить генерации", callback_data="my_refs")],
        [InlineKeyboardButton(text="🌟Продвижение песен артиста", callback_data="promo")],
        [InlineKeyboardButton(text="Другие нейросети", url='https://t.me/hassanmaxim/84'),InlineKeyboardButton(text="Инструкция и поддержка", web_app=WebAppInfo(url='https://teletype.in/@infopovod/avrora'))],
        
    ])

    # Проверяем текущее состояние пользователя
    current_state = await state.get_state()
    plan = await check_plan(message.from_user.id)
    plan_nadp = 'Нет подписки'
    if plan:
        
        if plan[0] == 'start':
            plan_nadp = 'Старт'
        elif plan[0] == 'master':
            print(plan[0])
            plan_nadp = 'Мастер'
        elif plan[0] == 'year':
            plan_nadp = 'Годовая'
        else:
            plan_nadp = 'Нет подписки'
    else:
        plan_nadp = 'Нет подписки'
    # Если у пользователя есть активное состояние, пропускаем обработку этого хэндлера
    if current_state is not None:
        return

    is_sub = await is_user_subscribed(bot, message.from_user.id, '@hassanmaxim')
        
        
    if is_sub:
            user = message.from_user
            user_data = await db.user_check(user)  # Проверяем, есть ли пользователь в БД
            
            if not user_data:  # Если пользователя нет в базе
                await message.answer('Вы не зарегестрированы! Введите /start')
           
            status = await check_status(message.from_user.id)
            if status:
                # Если пользователь не забанен, отправляем информацию о профиле
                profile_message = (
                    f"📱 Управляйте мной кнопками меню👇🏻искусственный интеллект. \n\n"
                    f"🔎 ID: <code>{message.from_user.id}</code>\n"
                    f"1️⃣ Подписка: {plan_nadp}\n"
                    f"2️⃣ Баланс: {round(await get_balance(message.from_user.id))} генераций🧾\n"
                    f"3️⃣ Перешло по вашей ссылке: {len(await get_referal(message.from_user.id))}\n\n"
                    
                    "Используйте генерации для создания песен. Одна генерация = две песни."
                )
                await message.answer(profile_message, reply_markup=keyboard,parse_mode=ParseMode.HTML)
            else:
                # Если пользователь забанен
                await message.answer('Вы забанены!')
    else:
                # Если пользователь не подписан, показываем кнопки для подписки и активации
                sub_keyboard = InlineKeyboardMarkup(inline_keyboard=[
                    [InlineKeyboardButton(text="Подписаться", url="https://t.me/hassanmaxim")],
                    [InlineKeyboardButton(text="Активировать", callback_data="activate")]
                ])

                face_message = (
                    f"{message.from_user.first_name}, создавайте авторские песни и клипы с помощью искусственного интеллекта AVRORA 🌟\n\n"
                    "По правилам телеграм для активации нейросети подпишитесь на сообщество автора и получите бесплатные генерации."
                )
                
                # Отправляем сообщение с изображением и клавиатурой
                await message.answer_photo(img_face, caption=face_message, reply_markup=sub_keyboard)   
async def bot_monitoring(bot = bot, admin_channel_id = ADMIN_CHANNEL_ID, interval: int = 7200):
    """
    Функция для мониторинга бота. Каждый час отправляет сообщение в админ-канал.
    
    :param bot: Экземпляр бота.
    :param admin_channel_id: ID админ-канала.
    :param interval: Интервал отправки сообщений в секундах (по умолчанию 3600 секунд = 1 час).
    """
    while True:
        try:
            from datetime import datetime
            # Получаем текущее время
            current_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            
            # Формируем сообщение для админ-канала
            message = f"🔄 Бот работает исправно. Время: {current_time}"
            
            # Отправляем сообщение в админ-канал
            await bot.send_message(admin_channel_id, message)
            
            # Логируем отправку сообщения
            logging.info(f"Сообщение мониторинга отправлено в админ-канал: {message}")
            
            # Ждем указанный интервал перед следующей отправкой
            await asyncio.sleep(interval)
        
        except Exception as e:
            # Логируем ошибку, если что-то пошло не так
            logging.error(f"Ошибка в функции мониторинга: {e}")
            await asyncio.sleep(60)  # Ждем 1 минуту перед повторной попыткой

async def daily_check():
    """Фоновая задача для ежедневной проверки."""
    while True:
        logging.info("Запуск ежедневной проверки подписок для токенов...")
        await check_and_issue_tokens()
        logging.info("Ежедневная проверка завершена.")
        await asyncio.sleep(86400)  # 86400 секунд = 1 день

async def renw_check():
    """Фоновая задача для ежедневной проверки продления."""
    while True:
        logging.info("Запуск ежедневной проверки подписок для продления...")
        await renew_subscription()
        logging.info("Ежедневная проверка завершена.")
        await asyncio.sleep(86401)  # 86400 секунд = 1 день

async def startup():
    """Код, который выполняется при запуске приложения."""
    # Настройка вебхука
    current_webhook = await bot.get_webhook_info()
    if current_webhook.url != WEBHOOK_URL:
        try:
            await bot.set_webhook(WEBHOOK_URL)
            logging.info("Вебхук успешно установлен.")
        except TelegramRetryAfter as e:
            logging.warning(f"Telegram просит подождать {e.retry_after} секунд перед установкой вебхука.")
            await asyncio.sleep(e.retry_after)
            await bot.set_webhook(WEBHOOK_URL)
            logging.info("Вебхук успешно установлен после ожидания.")

    # Создаем таблицы в базе данных
    await db.create_table()
    logging.info("Таблицы в базе данных созданы или уже существуют.")

    # Устанавливаем команды бота
    await set_commands(bot)
    logging.info("Команды бота установлены.")

    # Запускаем фоновые задачи
    asyncio.create_task(daily_check())
    asyncio.create_task(renw_check())
    asyncio.create_task(bot_monitoring())
    logging.info("Фоновые задачи запущены.")

    # Запускаем бота
    asyncio.create_task(dp.start_polling())
    logging.info("Бот запущен.")

async def shutdown():
    """Код, который выполняется при завершении приложения."""
    # Удаление вебхука
    await bot.delete_webhook()
    logging.info("Вебхук успешно удален.")

    # Останавливаем фоновые задачи
    logging.info("Фоновые задачи остановлены.")

    # Закрываем соединение с ботом
    await bot.session.close()
    logging.info("Соединение с ботом закрыто.")

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Контекстный менеджер для управления жизненным циклом приложения."""
    await startup()
    yield
    await shutdown()

# Создание приложения FastAPI
app = FastAPI(lifespan=lifespan)

@app.post("/webhook")
async def webhook(request: Request, background_tasks: BackgroundTasks):
    """Обработчик вебхуков в фоне"""
    update = Update.model_validate_json(await request.body())
    background_tasks.add_task(dp.feed_update, bot, update)  # Запускаем обработку в фоне
    return {"status": "ok"}  # Возвращаем ответ сразу, без ожидания обработки

@app.post("/payments")
async def webhook_payments(request: Request):
    """
    Обрабатывает входящие вебхуки от платежной системы.
    """
    try:
        
        # Получаем данные из вебхука
        data = await request.json()
        logger.info(f"Получен вебхук: {data}")

        # Проверяем, что данные содержат обязательные поля
        if not data.get('event') or not data.get('object'):
            logger.error("Вебхук не содержит обязательных полей: 'event' или 'object'")
            raise HTTPException(status_code=400, detail="Invalid webhook data")

        # Извлекаем ID платежа
        payment_id = data.get('object', {}).get('id')
        if not payment_id:
            logger.error("Вебхук не содержит ID платежа.")
            raise HTTPException(status_code=400, detail="Payment ID is missing")

        # Проверяем, был ли платеж уже обработан
        if await db.is_payment_processed(payment_id):
            logger.info(f"Платеж {payment_id} уже был обработан.")
            return JSONResponse(
                content={"status": "ignored", "message": "Payment already processed"},
                status_code=200
            )

        # Проверяем, является ли это автоплатежом
        metadata = data.get('object', {}).get('metadata', {})
        if metadata.get('auto') == 'true':
            logger.info("Пропускаем обработку автоплатежа.")
            # Выполняем команду /start для пользователя
            user_id = metadata.get('user_id')
            if user_id:

                # Создаем объект Message, имитирующий команду /start
                message = types.Message(
                    message_id=1,  # Уникальный ID сообщения (можно использовать временное значение)
                    date=datetime.datetime.now(),  # Текущая дата и время
                    chat=types.Chat(
                        id=int(user_id),  # ID чата пользователя
                        type="private"  # Тип чата (личный)
                    ),
                    from_user=types.User(
                        id=int(user_id),  # ID пользователя
                        is_bot=False,  # Пользователь не является ботом
                        first_name="User"  # Имя пользователя (можно оставить пустым)
                    ),
                    text="/start"  # Текст команды
                )
                # Создаем объект Update
                update = types.Update(
                    update_id=1,  # Уникальный ID обновления (можно использовать временное значение)
                    message=message  # Передаем созданное сообщение
                )
                # Вызываем обработчик команды /start
                await dp.feed_update(bot, update)
                # Отправляем сообщение с благодарностью и информацией об активации тарифа
                thank_you_message = "❤️ Аврора благодарна за поддержку!\nУверены, функционал премиум-версии принесет пользу и создаст ваш шедевр.\nВаш тариф активирован."
                await bot.send_message(chat_id=user_id, text=thank_you_message)
            return JSONResponse(
                content={"status": "ignored", "message": "Автоплатеж не требует обработки."},
                status_code=200
            )

        # Обрабатываем вебхук
        result = await handle_payment_webhook(data, bot)

        # Помечаем платеж как обработанный
        logger.info(f"Платеж {payment_id} помечен как обработанный.")

        # Выполняем команду /start для пользователя
        user_id = metadata.get('user_id')
        if user_id:

            # Создаем объект Message, имитирующий команду /start
            message = types.Message(
                message_id=1,  # Уникальный ID сообщения (можно использовать временное значение)
                date=datetime.datetime.now(),  # Текущая дата и время
                chat=types.Chat(
                    id=int(user_id),  # ID чата пользователя
                    type="private"  # Тип чата (личный)
                ),
                from_user=types.User(
                    id=int(user_id),  # ID пользователя
                    is_bot=False,  # Пользователь не является ботом
                    first_name="User"  # Имя пользователя (можно оставить пустым)
                ),
                text="/start"  # Текст команды
            )
            # Создаем объект Update
            update = types.Update(
                update_id=1,  # Уникальный ID обновления (можно использовать временное значение)
                message=message  # Передаем созданное сообщение
            )
            # Вызываем обработчик команды /start
            await dp.feed_update(bot, update)
            # Отправляем сообщение с благодарностью и информацией об активации тарифа
            thank_you_message = "❤️ Аврора благодарна за поддержку!\nУверены, функционал премиум-версии принесет пользу и создаст ваш шедевр.\nВаш тариф активирован."
            await bot.send_message(chat_id=user_id, text=thank_you_message)
            logger.info(f"Для пользователя {user_id} выполнена команда /start.")

        # Возвращаем результат обработки
        return result

    except HTTPException as e:
        # Обрабатываем ошибки FastAPI (например, неверные данные)
        logger.error(f"Ошибка в обработчике вебхуков: {e.detail}")
        return JSONResponse(
            content={"status": "error", "message": e.detail},
            status_code=e.status_code
        )

    except Exception as e:
        # Логируем другие ошибки
        logger.error(f"Ошибка в обработчике вебхуков: {e}")
        return JSONResponse(
            content={"status": "error", "message": str(e)},
            status_code=500
        )
    
@app.post("/webhook/music")
async def webhook_music(request: Request):
    """
    Обрабатывает входящие вебхуки от API генерации музыки.
    """
    try:
        # Получаем данные из вебхука
        data = await request.json()
        logger.info(f"Получен вебхук: {data}")

        # Проверяем, что данные содержат обязательные поля
        if not data.get('timestamp') or not data.get('data'):
            logger.error("Вебхук не содержит обязательных полей: 'timestamp' или 'data'")
            raise HTTPException(status_code=400, detail="Invalid webhook data")

        # Извлекаем данные задачи
        task_data = data.get('data', {})
        task_id = task_data.get('task_id')
        status = task_data.get('status')
        output = task_data.get('output', {})
        input = task_data.get('input', {})
        user_id = int(task_data.get('input', {}).get('title',{}))  # Извлекаем user_id из метаданных
        lyrics = task_data.get('input', {}).get('prompt',{}) 

        if not task_id:
            logger.error("Вебхук не содержит ID задачи.")
            raise HTTPException(status_code=400, detail="Task ID is missing")

        if not user_id:
            logger.error("Вебхук не содержит user_id.")
            raise HTTPException(status_code=400, detail="User ID is missing")

        # Быстро отвечаем успешным статусом
        response = JSONResponse(
            content={"status": "success", "message": "Webhook received"},
            status_code=200
        )

        # Обрабатываем задачу в фоновом режиме
        asyncio.create_task(process_music_task(task_id, status, output, user_id,lyrics, input))

        return response

    except HTTPException as e:
        logger.error(f"Ошибка в обработчике вебхуков: {e.detail}")
        return JSONResponse(
            content={"status": "error", "message": e.detail},
            status_code=e.status_code
        )

    except Exception as e:
        logger.error(f"Ошибка в обработчике вебхуков: {e}")
        return JSONResponse(
            content={"status": "error", "message": str(e)},
            status_code=500
        )    
    

# Запуск приложения
if __name__ == '__main__':
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8443, reload=True)
