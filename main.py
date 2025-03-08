from aiogram import F
from aiogram import Bot, Dispatcher, types
from aiogram.types import URLInputFile, FSInputFile
from aiogram.filters.command import Command
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton,WebAppInfo,LabeledPrice
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.filters import StateFilter
import os
from datetime import datetime
import datetime
import time
import asyncio
import logging
import random
from dotenv import load_dotenv
from function import is_user_subscribed, generate_referral_code, generate_referral_link
import db 
import aimu
from db import add_referal,get_referal,get_ref_url,get_balance,deduct_tokens,check_status,ban,unban, check_all,check_ref,give_tokens,get_subsc,check_subsc, add_auto, un_auto,check_and_issue_tokens,renew_subscription
from aiogram.enums.parse_mode import ParseMode
from payments import create_payment,get_payment




logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

load_dotenv('keys.env')
bot_token = os.getenv('BOT_TOKEN')
ADMIN_CHANNEL_ID = -1002337007587
img_face = FSInputFile('face_image.jpg')
exemple_music = FSInputFile('exemple.mp3',filename='Пример песни')


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




@dp.message(Command('start'))
async def start(message: types.Message, state:FSMContext):
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="Создать песню", callback_data="generate_music"),InlineKeyboardButton(text="Получить токены", callback_data="my_refs")],
        [InlineKeyboardButton(text="Другие нейросети", url='https://t.me/hassanmaxim/84'),InlineKeyboardButton(text="Инструкция и поддержка", web_app=WebAppInfo(url='https://teletype.in/@infopovod/avrora'))],
        
    ])
    is_sub = await is_user_subscribed(bot, message.from_user.id, '@hassanmaxim')
    referrer_id = None
    current_state = await state.get_state()
    if current_state is not None:
            await state.clear()  # чтобы свободно перейти сюда из любого другого состояния
    
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

                await db.insert_table(user, referral_code, referrer_id, 2,1)
                
                

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
                    f"👤 Мой профиль\n\n"
                    f"🆔 Telegram ID: <code>{message.from_user.id}</code>\n"
                    f"🎬 Баланс: {round(await get_balance(message.from_user.id))} token🧾\n"
                    f"⭐️ Пригласил: {len(await get_referal(message.from_user.id))}\n\n"
                    "Если нужна помощь - посмотрите справку или свяжитесь с администратором."
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
                    "По правилам телеграм для активации нейросети подпишитесь на сообщество автора и получите бесплатные токены."
                )
                
                # Отправляем сообщение с изображением и клавиатурой
                await message.answer_photo(img_face, caption=face_message, reply_markup=sub_keyboard)
    

        
@dp.callback_query(lambda query: query.data == "activate")
async def activate(callback_query: types.CallbackQuery, state: FSMContext):
    user = callback_query.from_user
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="Создать песню", callback_data="generate_music"),InlineKeyboardButton(text="Получить токены", callback_data="my_refs")],
        [InlineKeyboardButton(text="Другие нейросети", url='https://t.me/hassanmaxim/84'),InlineKeyboardButton(text="Инструкция и поддержка", web_app=WebAppInfo(url='https://teletype.in/@infopovod/avrora'))],
       
    ])
    keyboard1 = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="Создать песню", callback_data="gen_mus")],
    ])
    current_state = await state.get_state()
    if current_state is not None:
            await state.clear()  # чтобы свободно перейти сюда из любого другого состояния

    
    # Проверяем подписку
    is_sub = await is_user_subscribed(bot, user.id, '@hassanmaxim')
    
    if is_sub:
            user_data = await db.user_check(user)  # Проверяем, есть ли пользователь в БД

            if not user_data:  # Если пользователя нет в базе
                referral_code = await generate_referral_code() + str(user.id)
                referrer_id = None  # В callback нет реферальных данных, убираем

                if referrer_id:
                    await add_referal(referrer_id, user.id)  

                await db.insert_table(user, referral_code, referrer_id, 2,1)

                

                await callback_query.message.answer('Вы зарегистрированы!')
                all_users = await check_all()
                ref_name = None
                if referrer_id is not None:
                    ref_name = await check_ref(referrer_id)
                await bot.send_message(ADMIN_CHANNEL_ID,f'✅Новая регистрация:\n Имя: {user.first_name}\n ID: {user.id} \n Username: @{user.username}\n Пригласил: {ref_name} \n Пользователей: {all_users}\n ')
            balance = await get_balance(user.id)
            status = await check_status(callback_query.from_user.id)
            if status:
                if callback_query.message.photo and callback_query.message.caption:
                    # Удаляем предыдущее сообщение
                    await bot.delete_message(chat_id=callback_query.message.chat.id, message_id=callback_query.message.message_id)

                    # Отправляем первое сообщение с описанием и балансом
                    await callback_query.message.answer(
                        f'✅ Доступ открыт. Добро пожаловать!\n'
                        f'Имя: {user.first_name}\n'
                        f'▶️ Ваш баланс: {round(balance)} токена\n'
                        f'🧾 А это значит = генерация {round(balance) * 2} песен.\n'
                        'Я могу создать уникальную песню по вашему запросу, с вашим текстом и в любом жанре.\n'
                        'Теперь больше не нужно платить тысячи и обращаться к специалистам. В 2 клика создавай инструментал, вокал и многое другое! В высоком качестве и по лучшей цене.\n\n'
                        '<b>Вот коротенький пример моей песни👇</b>',
                        reply_markup=keyboard1
                    ,parse_mode= ParseMode.HTML)
                    await callback_query.message.answer_audio(exemple_music)

                    # # Отправляем второе сообщение с профилем пользователя
                    # await callback_query.message.answer(
                    #     f'👤 Мой профиль\n\n'
                    #     f'🆔 Telegram ID: {callback_query.from_user.id}\n'
                    #     f'🎬 Баланс: {await get_balance(callback_query.from_user.id)} token🧾\n'
                    #     f'⭐️ Пригласил: {len(await get_referal(callback_query.from_user.id))}',
                    #     reply_markup=keyboard
                    # )
                else:
                    # Если нет изображения с описанием, отправляем только профиль
                    await callback_query.message.edit_text(
                        f'👤 Мой профиль\n\n'
                        f'🆔 Telegram ID: <code>{callback_query.from_user.id}</code>\n'
                        f'🎬 Баланс: {await get_balance(callback_query.from_user.id)} token🧾\n'
                        f'⭐️ Пригласил: {len(await get_referal(callback_query.from_user.id))}\n\n'
                        'Если нужна помощь - посмотрите справку или свяжитесь с администратором.',
                        reply_markup=keyboard, parse_mode= ParseMode.HTML
                    )
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

    По правилам телеграм для активации нейросети подпишитесь на сообщество автора и получите бесплатные токены.'''
            await callback_query.message.answer_photo(img_face, caption= face_message, reply_markup= sub_keyboard)
    

    # Убираем "часики" на кнопке
    await callback_query.answer()

@dp.callback_query(lambda query: query.data == "generate_music")
async def generate_music(callback_query: types.CallbackQuery, state: FSMContext):
    status = await check_status(callback_query.from_user.id)
    if status:
        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="1️⃣Простой режим❤️", callback_data="simple"), InlineKeyboardButton(text="2️⃣ Режим мастера⭐️", callback_data="hard")],
            [InlineKeyboardButton(text="📚Инструкция", web_app=WebAppInfo(url="https://teletype.in/@infopovod/avrora"))],
            [InlineKeyboardButton(text="🔙Назад", callback_data="activate")]
        ])
        await callback_query.answer("Выберите режим")  # Подтверждаем получение callback
        # Устанавливаем состояние "waiting_for_genre"
        await state.set_state(MusicGeneration.waiting_for_genre)
        await callback_query.message.edit_text(
            '''<b>Выберите необходимый раздел:</b>\n

1️⃣Простой режим❤️ (бесплатный)\n
2️⃣ Режим мастера⭐️ (доступно с подпиской)\n

🎸 AVRORA – лучшая нейросеть для создания красивых трендовых песен.
Всего в 2 клика: музыка, ритм, голос, исполнение.
''', reply_markup=keyboard, parse_mode=ParseMode.HTML, disable_web_page_preview= True
        )
    else:
        await callback_query.message.edit_text('Вы забанены!')

@dp.callback_query(lambda query: query.data in ["simple", "hard"])
async def process_genre(callback_query: types.CallbackQuery, state: FSMContext):
    current_state = await state.get_state()
    if current_state is not None:
        await state.clear()  # Сбрасываем состояние

    # Подтверждаем обработку callback-запроса
    await callback_query.answer()

    # Проверяем подписку заранее
    subsc = await check_subsc(callback_query.from_user.id)

    # Клавиатура "Назад"
    back_keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🔙Назад", callback_data="generate_music")]
    ])

    # Обрабатываем "Простой режим"
    if callback_query.data == "simple":
        genre_keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="Рок📀", callback_data="rock"),
             InlineKeyboardButton(text="Рэп💿", callback_data="rap")], 
            [InlineKeyboardButton(text="🔙Назад", callback_data="generate_music")]
        ])

        await state.update_data(mode="simple")
        await state.set_state(MusicGeneration.waiting_for_lyrics)
        await callback_query.message.edit_text(
            '''✅Простой режим активирован. (1 токен = 2 песни).\n\n
<b>Выберите один из двух доступных жанров.👇</b>''',
            reply_markup=genre_keyboard,
            parse_mode=ParseMode.HTML
        )

    # Обрабатываем "Мастер режим"
    elif callback_query.data == "hard":
        if subsc:
            await state.update_data(mode="hard")
            await state.set_state(MusicGeneration.waiting_for_lyrics)
            await callback_query.message.edit_text(
                '''✅Мастер режим активирован. (1 токен = 2 песни).\n\n
<b>👇Прямо в чат напишите 1 из 250 жанров (пример: рок, считалочка, русские частушки..)</b>''',
                parse_mode=ParseMode.HTML,
                reply_markup=back_keyboard
            )
        else:
            await callback_query.message.edit_text(
                '❌ У вас нет подписки для этого режима',
                reply_markup=back_keyboard
            )


@dp.message(MusicGeneration.waiting_for_lyrics)
async def harde_mode(message: types.Message, state: FSMContext):    
    await state.update_data(genre= message.text)
    await state.set_state(MusicGeneration.waiting_for_lyrics_full)
    # Создаем клавиатуру с кнопкой "Назад"
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🔙Назад", callback_data="generate_music")]
    ])
    
    await message.answer(
        '''Песня почти готова, теперь просто отправьте текст (не более 3000 символов).
А нейросеть сама его положит в такт музыки.\n\n
<b>👇отправьте слова песни👇</b>''', parse_mode= ParseMode.HTML, reply_markup= keyboard
    )

# Обработчик callback-запроса для выбора жанра
@dp.callback_query(lambda query: query.data in ['rock', 'rap', 'pop'])
async def choice_lyric(callback_query: types.CallbackQuery, state: FSMContext):
    await callback_query.answer()  # Подтверждаем получение callback
    # Создаем клавиатуру с кнопкой "Назад"
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🔙Назад", callback_data="generate_music")]
    ])
    # Сохраняем выбранный жанр в состояние
    await state.update_data(genre=callback_query.data)
    print(f"Установлено состояние: {await state.get_state()}")
    # Устанавливаем следующее состояние
    await state.set_state(MusicGeneration.waiting_for_lyrics_full)

    # Отправляем сообщение с инструкцией
    await callback_query.message.answer(
        '''Песня почти готова, теперь просто отправьте текст (не более 3000 символов).
А нейросеть сама его положит в такт музыки.\n\n
<b>👇отправьте слова песни👇</b>''', parse_mode= ParseMode.HTML,reply_markup= keyboard)
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

# Обработчик callback-запроса для генерации музыки
@dp.callback_query(MusicGeneration.waiting_for_generate )
async def handle_music_generation(callback_query: types.CallbackQuery, state: FSMContext):
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="Вернуться на главную", callback_data="activate")],
        [InlineKeyboardButton(text="Сгенерировать заново", callback_data="generate_music")]
    ])
    try:
        balance = await get_balance(callback_query.from_user.id)
        if balance < 1:
            await callback_query.message.answer(
                f'Не хватает токенов. Ваш баланс - {balance}. Возвращение в главное меню',
            )
            await activate(callback_query)
        else:
            await callback_query.answer()  # Подтверждаем получение callback
            await deduct_tokens(callback_query.from_user.id, 1)  # Списываем токен
            print('gener')
            await callback_query.message.answer('Генерация может занять до 800 сек. ⏳ Создаю мелодию, рифму, бит, голос, обложку.')
            # Получаем данные из состояния
            user_data = await state.get_data()
            genre = user_data['genre']
            lyrics = user_data['text']
            #regime = user_data['regime']
            max_retries=3
            retry_delay=5
            # Завершаем состояние
            #await state.clear()

            ret = 0
            while ret < max_retries:
                await asyncio.sleep(retry_delay)  # Задержка перед повтором
                #Генерация музыки
                #post = await aimu.post_music(0, lyrics, genre)
                post = None
                if post is not None:
                    get = await aimu.get_music(post)
                    await callback_query.message.answer("🎵 Генерация завершена!")
                    for _,clip_data in get['data']['output']['clips'].items():
                        # retries = 0
                        
                        # while retries < max_retries:
                            try:
                                out_img = URLInputFile(clip_data['image_url'])
                                out_music = URLInputFile(clip_data['audio_url'])
                                # Разбиваем текст на строки, удаляем пустые
                                lines = [line.strip() for line in lyrics.split('\n') if line.strip()]

                                # Если есть строки, выбираем случайную
                                if lines:
                                    first_string = random.choice(lines)
                                else:
                                    first_string = "Без названия"  # Если текст пуст, подставляем заглушку

                                title = 'AuroraAI - ' + first_string
                                await callback_query.message.answer_photo(out_img)
                                await callback_query.message.answer_audio(out_music, title=title)

                                break  # Если отправка успешна — выходим из цикла

                            except Exception as e:
                                retries += 1
                                if retries < max_retries:
                                    await asyncio.sleep(retry_delay)  # Ждем перед повторной попыткой
                                    #await callback_query.message.answer(f"⚠ Ошибка при загрузке песни, пробую снова... ({retries}/{max_retries})")
                                    await bot.send_message(ADMIN_CHANNEL_ID,f"🚨 Ошибка при отправке файла: {e}\nПесня  не может быть загружена Телеграмом.\n У пользователя @{callback_query.from_user.username}")
                                else:
                                    #await callback_query.message.answer(f"🚨 Ошибка при отправке файла: {e}\nПесня {clip_data['title']} не может быть загружена.")
                                    await bot.send_message(ADMIN_CHANNEL_ID,f"🚨 Ошибка при отправке файла: {e}\nПесня  не может быть загружена Телеграмом.\n У пользователя @{callback_query.from_user.username}")
                    #break
                else:
                    #ret += 1
                    await callback_query.message.answer('💜 Сейчас у нас очень много запросов.  Произошла ошибка, повторите ваш запрос позже, либо активируйте подписку для приоритетной очереди.')
                    
                    await bot.send_message(ADMIN_CHANNEL_ID, f"🚨 Общая ошибка генерации музыки: API вернул ошибку")
                    activate(callback_query)
                    break
            # Обновляем баланс
            # balance = await get_balance(callback_query.from_user.id)
            # await callback_query.message.answer(f'Ваш баланс - {balance}. Желаете вернуться на главную или сгенерировать ещё раз?', reply_markup=keyboard)
            await activate(callback_query)


    except Exception as e:
        #await callback_query.message.answer(f"Произошла ошибка")
        await bot.send_message(ADMIN_CHANNEL_ID,f"Произошла ошибка: {e}\n У пользователя @{callback_query.from_user.username}")
    
@dp.message(Command('pay'))
async def pay(message:types.Message):
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🌘Старт", callback_data="sub_start"),
         InlineKeyboardButton(text="🌗Мастер", callback_data="sub_master"),
        ],
        [InlineKeyboardButton(text="🌕Годовая", callback_data="sub_year"),
         InlineKeyboardButton(text="Бесплатные токены", callback_data="free")],
        [InlineKeyboardButton(text="Отменить продление", url="https://t.me/dropsupport")],
        [InlineKeyboardButton(text="🔙 Назад", callback_data="activate")]
    ])
    mess = (
            f'''Создавайте легко свои песни и публикуйте их на всех площадках, зарабатывая за прослушивания!\n
<b>ТАРИФЫ:</b>\n
🌘 Старт - 20 токенов (40 песен) в месяц\n
🌗 Мастер - 60 токенов (120 песен) в месяц\n
🌕 Годовой - всё из тарифа «Мастер» на целый год с выгодой 50%.\n

✅Оплачивайте через официальные платежные с-мы безопасно. Нам доверяю: Paypal, Sber, Yandex money, СБП, Vk pay и другие.\n

{message.from_user.first_name}, вы можете поддержать наш социальный проект который мы развиваем полностью на свои средства, либо использовать бесплатные токены что мы дарим каждый день всем хорошим людям.\n

<b>Выберите тариф ниже👇🏽</b>'''
        )
    await message.answer(mess, reply_markup=keyboard,parse_mode=ParseMode.HTML)
    

@dp.callback_query(lambda query: query.data == "my_refs")
async def get_sub(callback_query: types.CallbackQuery):
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🌘Старт", callback_data="sub_start"),
         InlineKeyboardButton(text="🌗Мастер", callback_data="sub_master"),
        ],
        [InlineKeyboardButton(text="🌕Годовая", callback_data="sub_year"),
         InlineKeyboardButton(text="Бесплатные токены", callback_data="free")],
        [InlineKeyboardButton(text="Отменить продление", url="https://t.me/dropsupport")],
        [InlineKeyboardButton(text="🔙 Назад", callback_data="activate")]
    ])
    mess = (
            f'''Создавайте легко свои песни и публикуйте их на всех площадках, зарабатывая за прослушивания!\n
<b>ТАРИФЫ:</b>\n
🌘 Старт - 20 токенов (40 песен) в месяц\n
🌗 Мастер - 60 токенов (120 песен) в месяц\n
🌕 Годовой - всё из тарифа «Мастер» на целый год с выгодой 50%.\n

✅Оплачивайте через официальные платежные с-мы безопасно. Нам доверяю: Paypal, Sber, Yandex money, СБП, Vk pay и другие.\n

{callback_query.from_user.first_name}, вы можете поддержать наш социальный проект который мы развиваем полностью на свои средства, либо использовать бесплатные токены что мы дарим каждый день всем хорошим людям.\n

<b>Выберите тариф ниже👇🏽</b>'''
        )
    await callback_query.message.edit_text(mess, reply_markup=keyboard,parse_mode=ParseMode.HTML)


async def process_subscription(callback_query: types.CallbackQuery, state: FSMContext, sub_type: str, price_env: str, tokens: int):
    try:
        user_id = callback_query.from_user.id
        current_state = await state.get_state()
        if current_state is not None:
            await state.clear()
        
        prov_token = os.getenv('TEST_PROVIDER_TOKEN')
        sub_price = os.getenv(price_env)
        
        if not prov_token or not sub_price:
            raise ValueError("Не удалось загрузить переменные окружения")
        
        await state.set_state(MusicGeneration.buying)
        url, payment_id = await create_payment(sub_price)
        if not url or not payment_id:
            await callback_query.message.edit_text("Не удалось создать платёж. Попробуйте ещё раз.")
            return
        
        now = datetime.date.today()
        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text=f"Оплатить {sub_price} руб.", web_app=WebAppInfo(url=url))],
            [InlineKeyboardButton(text=f"⬅ Назад", callback_data='my_refs')]
        ])
        
        await callback_query.message.edit_text(f'Купить подписку за {sub_price} рублей', reply_markup=keyboard)
        await callback_query.answer('', cache_time=60)
        expiry_date = (now + datetime.timedelta(days=30)).strftime('%Y-%m-%d')
        
        for _ in range(10):
            await asyncio.sleep(5)
            payment = await get_payment(payment_id)
            
            if payment is False:
                continue
            #print(type(payment))
            if payment or payment[0] == 'succeeded':
                
                if isinstance(payment, tuple):
                    await add_auto(user_id, payment[1])
                
                await get_subsc(expiry_date, sub_type, user_id)
                await give_tokens(user_id, tokens)
                await bot.send_message(ADMIN_CHANNEL_ID, f'Пользователь {user_id} оплатил подписку{sub_type} {"с автопродлением" if isinstance(payment, tuple) else "без автопродления"}')
                await state.clear()
                await activate(callback_query, state)
                break
        else:
            await callback_query.message.answer("Платёж не был завершён. Попробуйте ещё раз.")
    except Exception as e:
        print(f"Ошибка: {e}")
        await callback_query.answer("Произошла ошибка. Попробуйте позже.")
        await state.clear()

@dp.callback_query(lambda query: query.data == "sub_start")
async def sub_start(callback_query: types.CallbackQuery, state: FSMContext):
    await process_subscription(callback_query, state, "start", 'PRICE_START', 20)

@dp.callback_query(lambda query: query.data == "sub_master")
async def sub_master(callback_query: types.CallbackQuery, state: FSMContext):
    await process_subscription(callback_query, state, "master", 'PRICE_MASTER', 60)

@dp.callback_query(lambda query: query.data == "sub_year")
async def sub_year(callback_query: types.CallbackQuery, state: FSMContext):
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
📍За каждого приглашенного - 1 токен (2 песни).\n

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

@dp.message()
async def any_message_handler(message: types.Message, state: FSMContext):
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="Создать песню", callback_data="generate_music"),InlineKeyboardButton(text="Получить токены", callback_data="my_refs")],
        [InlineKeyboardButton(text="Другие нейросети", url='https://t.me/hassanmaxim/84'),InlineKeyboardButton(text="Инструкция и поддержка", web_app=WebAppInfo(url='https://teletype.in/@infopovod/avrora'))],
        
    ])

    # Проверяем текущее состояние пользователя
    current_state = await state.get_state()

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
                    f"👤 Мой профиль\n\n"
                    f"🆔 Telegram ID: <code>{message.from_user.id}</code>\n"
                    f"🎬 Баланс: {round(await get_balance(message.from_user.id))} token🧾\n"
                    f"⭐️ Пригласил: {len(await get_referal(message.from_user.id))}\n\n"
                    "Если нужна помощь - посмотрите справку или свяжитесь с администратором."
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
                    "По правилам телеграм для активации нейросети подпишитесь на сообщество автора и получите бесплатные токены."
                )
                
                # Отправляем сообщение с изображением и клавиатурой
                await message.answer_photo(img_face, caption=face_message, reply_markup=sub_keyboard)   

async def daily_check():
    while True:

        logging.info("Запуск ежедневной проверки подписок...")
        await check_and_issue_tokens()
        logging.info("Ежедневная проверка завершена.")
        
        # Ждем до следующего дня
        await asyncio.sleep(86400)  # 86400 секунд = 1 день

async def renw_check():
    while True:

        logging.info("Запуск ежедневной проверки подписок...")
        await renew_subscription()
        logging.info("Ежедневная проверка завершена.")
        
        # Ждем до следующего дня
        await asyncio.sleep(86401)  # 86400 секунд = 1 день

async def main():

    await db.create_table()
    await set_commands(bot)
    asyncio.create_task(daily_check())
    asyncio.create_task(renw_check())
    await dp.start_polling(bot)

# Запуск бота
if __name__ == '__main__':
    asyncio.run(main())
