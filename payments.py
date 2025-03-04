import json
from dotenv import load_dotenv
import os
import uuid
import yookassa

load_dotenv('keys.env')
shop_id = os.getenv('SHOP_ID')
secret_key = os.getenv('SECRET_KEY')

async def create_payment(price):
    
    try:
      idempotence_key = str(uuid.uuid4())
      yookassa.Configuration.account_id = shop_id
      yookassa.Configuration.secret_key = secret_key

      payment = yookassa.Payment.create({
      "amount": {
        "value": f"{price}.00",
        "currency": "RUB"
      },
      # "payment_method_data": {
      #   "type": "bank_card"
      # },
      "confirmation": {
        "type": "redirect",
        "return_url": "https://t.me/avroraai_bot?start"
      },
      # "receipt": {
      #             "items": [
      #                 {
      #                     "description": "Подписка",
      #                     "quantity": "1.00",
      #                     "amount": {
      #                         "value": f"{price}",  # Сумма в рублях
      #                         "currency": "RUB"
      #                     },
      #                     "vat_code": 1
      #                 }
      #             ]
      #         },
      "description": "Покупка подписки",
      "capture": True
  }, idempotence_key)
      
      url = payment.confirmation.confirmation_url

      return url, payment.id
    except Exception as e:
        # Логируем ошибку и возвращаем None
        print(f"Произошла ошибка при создании платежа: {e}")
        return None, None

async def get_payment(id):
    try:
        # Вызываем асинхронный метод с await
        payment = yookassa.Payment.find_one(id)

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

