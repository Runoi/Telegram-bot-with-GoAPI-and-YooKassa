# AVRORA Telegram Bot

Этот проект представляет собой Telegram-бота, который позволяет пользователям создавать уникальные музыкальные композиции с помощью искусственного интеллекта.

## Возможности
- 🎵 Генерация музыки на основе заданного текста
- 🎤 Поддержка различных жанров (рок, рэп, поп и др.)
- 💰 Работа с реферальной системой и начислением токенов
- 🔒 Управление подписками и автоплатежами
- 📩 Поддержка платежных систем для покупки подписки
- 🛠 Административные команды (бан, разбан, начисление токенов)

## Установка
1. Склонируйте репозиторий:
   ```sh
   git clone https://github.com/your-repo/avrorabot.git
   cd avrorabot
   ```
2. Установите зависимости:
   ```sh
   pip install -r requirements.txt
   ```
3. Создайте `.env` файл и укажите переменные окружения:
   ```sh
   BOT_TOKEN=your_telegram_bot_token
   ADMIN_CHANNEL_ID=-100XXXXXXXXXX
   TEST_PROVIDER_TOKEN=your_provider_token
   PRICE_START=35000  # Цена в копейках
   PRICE_MASTER=75000
   PRICE_YEAR=350000
   ```
4. Запустите бота:
   ```sh
   python main.py
   ```

## Основные команды
- `/start` – Запуск бота и регистрация пользователя
- `/pay` – Покупка подписки и управление балансом
- `/music` – Создание музыки с выбором режима

## Используемые технологии
- `aiogram` – Фреймворк для создания Telegram-ботов
- `asyncio` – Асинхронное программирование
- `sqlite` – База данных для хранения информации о пользователях
- `dotenv` – Управление переменными окружения

Бот - @avroraai_bot
