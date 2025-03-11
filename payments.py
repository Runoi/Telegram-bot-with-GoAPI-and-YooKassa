import json
from dotenv import load_dotenv
import os
import uuid
import asyncio
import yookassa
import logging


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
load_dotenv('keys.env')
shop_id = os.getenv('SHOP_ID')
secret_key = os.getenv('SECRET_KEY')

async def create_payment(price: str, expires_at: str, user_id: int, sub_type: str, tokens: int):
    """
    Создает платеж через ЮKassa.

    :param price: Цена подписки.
    :param expires_at: Время истечения срока действия платежа (в формате ISO 8601).
    :param user_id: ID пользователя.
    :param sub_type: Тип подписки.
    :param tokens: Количество токенов.
    :return: Ссылка на оплату и ID платежа.
    """
    try:
        inn = int(os.getenv('INN'))
        shop_id = os.getenv('SHOP_ID')
        secret_key = os.getenv('SECRET_KEY')
        yookassa.Configuration.configure(shop_id, secret_key)

        idempotence_key = str(uuid.uuid4())

        invoice = yookassa.Invoice.create({
            "payment_data": {
                "amount": {
                    "value": f"{price}.00",
                    "currency": "RUB"
                },
                "capture": True,
                "save_payment_method": True,
                "description": f"Подписка на AVRORA AI ({sub_type})",
                "metadata": {
                    "user_id": user_id,
                    "sub_type": sub_type,
                    "tokens": tokens
                }
            },
            "cart": [
                {
                    "description": f"Подписка на AVRORA AI ({sub_type})",
                    "price": {
                        "value": f"{price}.00",
                        "currency": "RUB"
                    },
                    "quantity": 1.000
                }
            ],
            "delivery_method_data": {
                "type": "self"
            },
            "locale": "ru_RU",
            "expires_at": expires_at,
            "description": f"Счет на оплату подписки {sub_type}",
            "metadata": {
                "user_id": user_id,
                "sub_type": sub_type,
                "tokens": tokens
            }
        }, idempotence_key)

        # Получаем ссылку на оплату и ID платежа
        link_to_invoice = invoice.delivery_method.url
        payment_id = invoice.id

        logger.info(f"Платеж создан: ID={payment_id}, ссылка={link_to_invoice}")
        return link_to_invoice, payment_id

    except Exception as e:
        logger.error(f"Ошибка при создании платежа: {e}")
        return None, None
# async def create_payment(price):
#     inn = int(os.getenv('INN'))
#     try:
#       idempotence_key = str(uuid.uuid4())
#       yookassa.Configuration.account_id = shop_id
#       yookassa.Configuration.secret_key = secret_key

#       payment = yookassa.Payment.create({
#       "amount": {
#         "value": f"{price}.00",
#         "currency": "RUB"
#       },
#       # "payment_method_data": {
#       #   "type": "bank_card"
#       # },
#       "confirmation": {
#         "type": "redirect",
#         "return_url": "https://t.me/avroraai_bot?start"
#       },
#       "receipt": {
#                   "customer":{
#                       "inn":inn,
#                       "email":'catkonfis@gmail.com'
#                   },
#                   "items": [
#                       {
#                           "description": "Подписка",
#                           "quantity": "1.00",
#                           "amount": {
#                               "value": f"{price}",  # Сумма в рублях
#                               "currency": "RUB"
#                           },
#                           "vat_code": 1
#                       }
#                   ]
#               },
#       "description": "Покупка подписки",
#       "capture": True
#   }, idempotence_key)
      
#       url = payment.confirmation.confirmation_url

#       return url, payment.id
    
#     except Exception as e:
#         # Логируем ошибку и возвращаем None
#         print(f"Произошла ошибка при создании платежа: {e}")
#         return None, None

async def create_auto_payment(price: str, expires_at: str, user_id: int, sub_type: str, tokens: int, payment_method_id: str):
    """
    Создает автоматический платеж через ЮKassa с использованием сохраненного способа оплаты.

    :param price: Цена подписки.
    :param expires_at: Время истечения срока действия платежа (в формате ISO 8601).
    :param user_id: ID пользователя.
    :param sub_type: Тип подписки.
    :param tokens: Количество токенов.
    :param payment_method_id: Идентификатор сохраненного способа оплаты.
    :return: ID платежа или None в случае ошибки.
    """
    try:
        # Настройка ЮKassa
        shop_id = os.getenv('SHOP_ID')
        secret_key = os.getenv('SECRET_KEY')
        yookassa.Configuration.configure(shop_id, secret_key)

        # Генерация уникального ключа идемпотентности
        idempotence_key = str(uuid.uuid4())

        # Создание платежа
        payment = yookassa.Payment.create({
            "amount": {
                "value": f"{price}.00",  # Форматируем цену
                "currency": "RUB"
            },
            "capture": True,  # Автоматическое подтверждение платежа
            "payment_method_id": payment_method_id,  # Используем сохраненный способ оплаты
            "description": f"Автоплатеж за подписку на AVRORA AI ({sub_type})",  # Описание платежа
            "metadata": {
                "user_id": user_id,  # ID пользователя
                "sub_type": sub_type,  # Тип подписки
                "tokens": tokens,  # Количество токенов
                "auto": True  # Указываем, что это автоплатеж
            },
            # "confirmation": {
            #     "type": "redirect",  # Тип подтверждения (например, редирект на страницу оплаты)
            #     "return_url": "https://yourdomain.com/return_url"  # URL для возврата после оплаты
            # },
            "expires_at": expires_at  # Время истечения срока действия платежа
        }, idempotence_key)

        # Проверяем статус платежа
        if payment.status == "succeeded":
            logger.info(f"Автоплатеж успешно создан. ID: {payment.id}")
            return payment.id
        else:
            logger.error(f"Автоплатеж не был успешным. Статус: {payment.status}")
            return None

    except Exception as e:
        # Логируем ошибку
        logger.error(f"Произошла ошибка при создании автоплатежа: {e}", exc_info=True)
        return None

async def get_payment(id):
    try:
        payment = yookassa.Invoice.find_one(id)

        # Проверяем статус платежа
        if payment.status == 'succeeded':
            # Проверяем, сохранён ли метод оплаты
            if hasattr(payment.payment_method, 'saved') and payment.payment_method.saved:
                return payment.status, payment.payment_method.id
            else:
                return payment.status
        else:
            return False
    except Exception as e:
        # Логируем ошибку и возвращаем False
        print(f"Произошла ошибка: {e}")
        return False

