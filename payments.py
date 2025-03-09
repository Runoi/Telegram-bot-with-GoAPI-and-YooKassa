import json
from dotenv import load_dotenv
import os
import uuid
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

async def create_payment(price,expires_at):
    inn = int(os.getenv('INN'))
    try:
      idempotence_key = str(uuid.uuid4())
      # yookassa.Configuration.account_id = shop_id
      # yookassa.Configuration.secret_key = secret_key
      yookassa.Configuration.configure(shop_id, secret_key)

      invoice = yookassa.Invoice.create({
      "payment_data":{
        "amount": {
        "value": f"{price}.00",
        "currency": "RUB"
      },
      # "payment_method_data": {
      #   "type": "bank_card"
      # },
      # "confirmation": {
      #   "type": "redirect",
      #   "return_url": "https://t.me/avroraai_bot?start"
      # },
      "receipt": {
                  "customer":{
                      "inn":inn,
                      "email":'catkonfis@gmail.com'
                  },
                  "items": [
                      {
                          "description": "Подписка",
                          "quantity": "1.00",
                          "amount": {
                              "value": f"{price}",  # Сумма в рублях
                              "currency": "RUB"
                          },
                          "vat_code": 1
                      }
                  ]
              },
              "save_payment_method": True,
              "capture": True,
              "description": "Покупка подписки"
              },
     "cart": [
        {
            "description": "Подписка на AVRORA AI",
            "price": {
                "value": f"{price}.00",
                "currency": "RUB"
            },
            "quantity": 1.000
        }],
      "delivery_method_data": {
        "type": "self"},
      "expires_at": expires_at,   
      "locale": "ru_RU",
      
  }, idempotence_key)
      
      # url = payment.confirmation.confirmation_url
      if invoice.delivery_method is not None:
        linkToInvoice = invoice.delivery_method.url
      if invoice.payment_details is not None:
        paymentId = invoice.payment_details.id

      return linkToInvoice, paymentId
    
    except Exception as e:
        # Логируем ошибку и возвращаем None
        print(f"Произошла ошибка при создании платежа(1): {e}")
        return None, None

async def create_auto_payment(price: float, payment_method_id: str):
    """
    Создает автоматический платеж через ЮKassa.

    :param price: Сумма платежа (в рублях).
    :param payment_method_id: Идентификатор метода оплаты.
    :return: Кортеж (confirmation_url, payment_id) или (None, None) в случае ошибки.
    """
    try:
        # Генерация уникального ключа идемпотентности
        idempotence_key = str(uuid.uuid4())
        yookassa.Configuration.account_id = shop_id
        yookassa.Configuration.secret_key = secret_key

        # Создание платежа
        payment = yookassa.Payment.create({
            "amount": {
                "value": f"{price:.2f}",  # Форматируем сумму с двумя знаками после запятой
                "currency": "RUB"
            },
            "receipt": {
                "customer": {
                    "inn": "583509348538",  # ИНН клиента
                    "email": "catkonfis@gmail.com"  # Email клиента
                },
                "items": [
                    {
                        "description": "Подписка",
                        "quantity": "1.00",
                        "amount": {
                            "value": f"{price:.2f}",  # Сумма в рублях
                            "currency": "RUB"
                        },
                        "vat_code": 1  # Код НДС
                    }
                ]
            },
            "description": "Продление подписки",
            "capture": True,  # Автоматическое подтверждение платежа
            "payment_method_id": payment_method_id  # Идентификатор метода оплаты
        }, idempotence_key)

        # Получаем URL для подтверждения платежа
        confirmation_url = payment.status
        payment_id = payment.id

        logger.info(f"Платеж создан. ID: {payment_id}, URL: {confirmation_url}")
        return confirmation_url, payment_id

    except Exception as e:
        # Логируем ошибку
        logger.error(f"Произошла ошибка при создании платежа: {e}", exc_info=True)
        return None, None

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

