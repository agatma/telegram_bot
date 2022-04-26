import requests
import logging
import time
import os
import telegram
import json
from pprint import pprint

from dotenv import load_dotenv
from telegram.ext import Updater, CommandHandler
from telegram import ReplyKeyboardMarkup


load_dotenv()


PRACTICUM_TOKEN = os.getenv('PRAKTIKUM_TOKEN')
TELEGRAM_TOKEN = os.getenv('TELEGRAM_TOKEN')
TELEGRAM_CHAT_ID = os.getenv('CHAT_ID')

RETRY_TIME = 600
ENDPOINT = 'https://practicum.yandex.ru/api/user_api/homework_fstatuses/'
HEADERS = {'Authorization': f'OAuth {PRACTICUM_TOKEN}'}

HOMEWORK_STATUSES = {
    'approved': 'Работа проверена: ревьюеру всё понравилось. Ура!',
    'reviewing': 'Работа взята на проверку ревьюером.',
    'rejected': 'Работа проверена: у ревьюера есть замечания.'
}

def check_tokens():
    CHECK_ENV_VARS = {
        'PRACTICUM_TOKEN': PRACTICUM_TOKEN,
        'TELEGRAM_TOKEN': TELEGRAM_TOKEN,
        'TELEGRAM_CHAT_ID': TELEGRAM_CHAT_ID,
    }
    if all(CHECK_ENV_VARS.values()):
        return True
    else:
        result = [k for k, v in CHECK_ENV_VARS.items() if v is None]
        message = f'Отсутствует обязательная переменная окружения: {result}. Программа остановлена'
        raise Exception(message)

def get_api_answer(current_timestamp):
    timestamp = current_timestamp or int(time.time())
    params = {'from_date': timestamp}
    homework_status = requests.get(ENDPOINT, headers=HEADERS, params=params)

    return homework_status.json()


    # if homework_status.status_code == 200:
    #     return homework_status.json()
    # else:
    #     message = (f'Ошибка при запросе к основному API. Эндпоинт {ENDPOINT}'
    #                f'вернул код {homework_status.status_code}')
    #     raise Exception(message)

print(get_api_answer(1587719772))

print(check_tokens())
#
# def check_response(response):
#     try:
#         return response['homeworks']
#     except KeyError as error:
#         logging.error(f'Ключ homeworks не присутствует в словаре. Ошибка: {error}')
#
#
#
#
# def parse_status(homework):
#     homework_name = homework.get('homework_name')
#     homework_status = homework.get('status')
#     verdict = HOMEWORK_STATUSES.get(homework_status)
#     return f'Изменился статус проверки работы "{homework_name}". {verdict}'
#
#
#
#
# result = get_api_answer(1587719772)
# result = check_response(result)[0]
# result = parse_status(result)
#
#
# bot = telegram.Bot(token=TELEGRAM_TOKEN)
# current_timestamp = int(time.time())
#
# def send_message(bot, message):
#     bot.send_message(TELEGRAM_CHAT_ID, message)
#
#
# print(send_message(bot, result))
#
#
#
#
