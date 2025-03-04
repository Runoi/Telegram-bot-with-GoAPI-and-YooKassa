#For any usful functions
from aiogram import Bot
from aiogram.enums import ChatMemberStatus
import random
import string
import secrets


async def is_user_subscribed(bot: Bot, user_id: int, channel_id,) -> bool:
    '''
    bot - экземпляр бота
    user_id - айди пользователя
    channel_id - айди канала в формате @Канал или цифровом
    '''

    try:
        # Получаем информацию о пользователе в канале
        chat_member = await bot.get_chat_member(chat_id=channel_id, user_id=user_id)
        # Проверяем, что статус пользователя не "left" (не вышел из канала)
        return chat_member.status not in [ChatMemberStatus.LEFT, ChatMemberStatus.KICKED]
    except:
        # Если пользователь не найден в канале
        return False
    
# Функция для генерации реферального кода
async def generate_referral_code(length: int = 8) -> str:
    characters = string.ascii_letters + string.digits
    return ''.join(secrets.choice(characters) for _ in range(length))

async def generate_referral_link(bot_username: str, ref: int) -> str:
    return f"https://t.me/{bot_username}?start={ref}"

   


