import requests
import logging
import time
import os
import telegram
from telegram.ext import Updater, CommandHandler
from dotenv import load_dotenv

load_dotenv()

PRACTICUM_TOKEN = os.getenv('PRAKTIKUM_TOKEN')
TELEGRAM_TOKEN = os.getenv('TELEGRAM_TOKEN')
TELEGRAM_CHAT_ID = os.getenv('CHAT_ID')

RETRY_TIME = 600
ENDPOINT = 'https://practicum.yandex.ru/api/user_api/homework_statuses/'
HEADERS = {'Authorization': f'OAuth {PRACTICUM_TOKEN}'}


HOMEWORK_STATUSES = {
    'approved': 'Работа проверена: ревьюеру всё понравилось. Ура!',
    'reviewing': 'Работа взята на проверку ревьюером.',
    'rejected': 'Работа проверена: у ревьюера есть замечания.'
}

TOKEN_DICT = {
        'PRACTICUM_TOKEN': PRACTICUM_TOKEN,
        'TELEGRAM_TOKEN': TELEGRAM_TOKEN,
        'TELEGRAM_CHAT_ID': TELEGRAM_CHAT_ID,
}

logging.basicConfig(
    level=logging.DEBUG,
    filename='api_bot.log',
    format='%(asctime)s, %(levelname)s, %(message)s, %(name)s'
)

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)
handler = logging.StreamHandler()
formatter = logging.Formatter(
    '%(asctime)s %(levelname)s %(message)s'
)
handler.setFormatter(formatter)
logger.addHandler(handler)


def send_message(bot, message):
    try:
        bot.send_message(TELEGRAM_CHAT_ID, message)
    except Exception as error:
        message = f'Ошибка при отправке сообщения: {error}'
        logger.error(message)
        raise Exception(message)


def get_api_answer(current_timestamp):
    timestamp = current_timestamp or int(time.time())
    params = {'from_date': timestamp}
    homework_status = requests.get(ENDPOINT, headers=HEADERS, params=params)
    try:
        return homework_status.json()
    except Exception as error:
        message = (f'Ошибка при запросе к основному API. Эндпоинт {ENDPOINT}'
                   f'вернул код {homework_status.status_code}.'
                   f'Описание ошибки {error}')
        logger.error(message)
        raise Exception(message)


def check_response(response):
    try:
        return response['homeworks']
    except KeyError as error:
        message = f'Ключ {error} не присутствует в словаре. Должен быть homeworks'
        logger.error(message)
        raise KeyError(message)
    except Exception as error:
        message = f'Ошибка в функции check_response. Описание {error}'
        logger.error(message)
        raise KeyError(message)


def parse_status(homework):
    homework = homework[0]
    homework_name = homework.get('homework_name')
    homework_status = homework.get('status')
    try:
        verdict = HOMEWORK_STATUSES[homework_status]
        return f'Изменился статус проверки работы "{homework_name}". {verdict}'
    except KeyError:
        message = f'Ключ {homework_status} не присутствует в словаре HOMEWORK_STATUSES'
        logger.error(message)
        raise KeyError(message)
    except Exception as error:
        message = f'Ошибка в функции parse_status. Описание {error}'
        logger.error(message)
        raise KeyError(message)


def check_tokens():
    return all(TOKEN_DICT.values())


def main():
    """Основная логика работы бота."""
    if not check_tokens():
        result = [k for k, v in TOKEN_DICT.items() if v is None]
        message = f'Отсутствует обязательная переменная окружения: {result}. Программа остановлена'
        logger.critical(message)
        raise Exception(message)
    bot = telegram.Bot(token=TELEGRAM_TOKEN)
    current_timestamp = int(time.time())
    last_error = {'error': None}
    while True:
        try:
            response = get_api_answer(current_timestamp)
            check_response_result = check_response(response)
            if not check_response_result:
                message = 'В данный момент работ на проверке нет. Отдыхай'
                send_message(bot, message)
                logger.debug(f'В ответе нет новых работ')
                logger.info(f'Бот отправил сообщение: "{message}"')
                break
            elif not response.get('status') == 'reviewing':
                message = parse_status(check_response_result)
                send_message(bot, message)
                logger.info(f'Бот отправил сообщение: "{message}"')
                break
            current_timestamp = response.get('current_date')
            time.sleep(RETRY_TIME)
        except Exception as error:
            if last_error['error'] == error.args:
                message = f'Ошибка {error} по-прежнему не решена. Программу останавливаем'
                logger.error(message)
                send_message(bot, message)
                raise Exception(message)
            else:
                last_error['error'] = error.args
                message = f'Сбой в работе программы: {error}'
                send_message(bot, message)
                logger.info(f'Бот отправил сообщение: "{message}"')
                time.sleep(RETRY_TIME)


if __name__ == '__main__':

    main()
