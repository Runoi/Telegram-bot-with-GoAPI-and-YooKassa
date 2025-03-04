#For use ai and other
import aiohttp
from dotenv import load_dotenv
import os
import time
import asyncio
import aiofiles

load_dotenv('keys.env')
ai_token = os.getenv('AI_TOKEN')

headers = {'X-API-KEY': ai_token,'Content-Type': 'application/json' }
url = "https://api.goapi.ai/api/v1/task"


            
async def post_music(regime = 0,prompt="",tags = '', title = "Untitled"):
    async with aiohttp.ClientSession() as session:
        if regime == 0:
            data = {
                "model": "music-s",
                "task_type": "generate_music_custom",
                "input": {
                    "prompt": prompt,
                    "lyrics_type": "generate",
                    "tags": tags,
                    
                },
                "config": {
                        "service_mode": "public",
                        "webhook_config": {
                            "endpoint": "",
                            "secret": ""
                        }
                        }
                }
        elif regime == 1:
            data = {
                "model": "music-s",
                "task_type": "generate_music_custom",
                "input": {
                    "prompt": prompt,
                    "lyrics_type": "user",
                    "tags": tags,
                    "seed": -1
                },
                "config": {
                        "service_mode": "public",
                        "webhook_config": {
                            "endpoint": "",
                            "secret": ""
                        }
                        }
            }
        
        async with session.post(url, json=data, headers=headers) as response:
            if response.status == 200:
                result = await response.json()
                print('1')
                return result
            else:
                print(f"Failed to post music: {response.status}")
                return None

async def get_music(result, max_attempts=25):
    url_to_get = f"https://api.goapi.ai/api/v1/task/{result['data']['task_id']}"
    attempts = 0
    status = None
    
    async with aiohttp.ClientSession() as session:
        print(url_to_get)
        while attempts < max_attempts:
            await asyncio.sleep(60)  # Ждем 60 секунд перед следующей проверкой
            attempts += 1

            async with session.get(url_to_get, headers=headers) as response:
                if response.status == 200:
                    result = await response.json()
                    # Проверяем статус задачи
                    if 'data' in result and 'status' in result['data']:
                        status = result['data']['status']
                    elif 'status' in result:
                        status = result['status']
                    else:
                        print("Status not found in response.")
                        return None

                    print(f"Attempt {attempts}: Status is {status}")

                    if status == 'completed':
                        return result  # Задача завершена, возвращаем результат
                    if status == 'failed':
                        print(f"Attempt {attempts}: Status is {status}")
                else:
                    print(f"Failed to get task status: {response.status}")
                    return None  # Запрос не удался, возвращаем None

        print("Max attempts reached. Task is not completed.")
        return None  # Достигнуто максимальное количество попыток
        


