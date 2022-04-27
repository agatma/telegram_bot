import requests
import time
import os
import telegram
import logging
from telegram import Bot
from dotenv import load_dotenv
from http import HTTPStatus
from typing import Union

load_dotenv()

PRACTICUM_TOKEN = os.getenv('PRAKTIKUM_TOKEN')
TELEGRAM_TOKEN = os.getenv('TELEGRAM_TOKEN')
TELEGRAM_CHAT_ID = os.getenv('CHAT_ID')

RETRY_TIME = 600
ENDPOINT = 'https://practicum.yandex.ru/api/user_api/homework_statuses/'
HEADERS = {'Authorization': f'OAuth {PRACTICUM_TOKEN}'}
REVIEWING = 'reviewing'
HOMEWORK_STATUSES = {
    'approved': 'Работа проверена: ревьюеру всё понравилось. Ура!',
    REVIEWING: 'Работа взята на проверку ревьюером.',
    'rejected': 'Работа проверена: у ревьюера есть замечания.'
}

TOKENS = {
    'PRACTICUM_TOKEN': PRACTICUM_TOKEN,
    'TELEGRAM_TOKEN': TELEGRAM_TOKEN,
    'TELEGRAM_CHAT_ID': TELEGRAM_CHAT_ID,
}


def init_logger():
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
    return logger


logger = init_logger()


def send_message(bot: Bot, message: str) -> None:
    """Sending message from bot (instance of Bot class).
    to chat (TELEGRAM_CHAT_ID)

    Args:
        bot: class Bot(TelegramObject) instance
        message (str): message to telegram chat

    Returns:
        None

    Raises:
        Exception: An error occurred during sending message to telegram chat

    """
    try:
        bot.send_message(TELEGRAM_CHAT_ID, message)
    except Exception as error:
        message = f'Ошибка при отправке сообщения: {error}'
        logger.error(message)
        raise Exception(message)


def get_api_answer(current_timestamp: int) -> dict[str, Union[list, int]]:
    """Requesting answer from api (ENDPOINT url).

    Args:
        current_timestamp: (int): Unix timestamp

    Returns:
        dict: Result of api request to ENDPOINT

    Raises:
        Exception: An error occurred during api request

    """
    timestamp = current_timestamp or int(time.time())
    params = {'from_date': timestamp}
    try:
        homework_status = requests.get(
            ENDPOINT, headers=HEADERS, params=params
        )
    except Exception as error:
        message = (f'Ошибка при запросе к основному API. '
                   f'Описание ошибки {error}')
        logger.error(message)
        raise Exception(message)
    if homework_status.status_code != HTTPStatus.OK:
        message = (f'Ошибка при запросе к основному API. Эндпоинт {ENDPOINT}'
                   f'вернул код {homework_status.status_code}, '
                   f'а должен был {HTTPStatus.OK}')
        logger.error(message)
        raise Exception(message)
    try:
        return homework_status.json()
    except ValueError as error:
        message = (f'Ошибка при запросе к основному API. Эндпоинт {ENDPOINT}'
                   f'Не удалось привести API ответ к типу данных python.'
                   f'Описание ошибки {error}')
        logger.error(message)
        raise ValueError(message)


def check_response(response: dict[str, Union[list, int]]) -> list[dict]:
    """Check response from get_api_answer function.

    Args:
        response (dict): response from api request (function get_api_answer)

    Returns:
        list: list of available homeworks (possible to empty list)

    Raises:
        Exception: An error occurred during api response check

    """
    if not isinstance(response['homeworks'], list):
        message = 'Ответ с домашними заданиями пришел не в виде списка'
        logger.error(message)
        raise TypeError(message)
    try:
        return response['homeworks']
    except KeyError as error:
        message = f'Ключ {error} не присутствует в словаре'
        logger.error(message)
        raise KeyError(message)


def parse_status(homework: dict[str, Union[str, int]]) -> str:
    """Parse status from homework.

    Args:
        homework (dict): information about homework (name, status and so on)

    Returns:
        str: Message for user
    Raises:
        KeyError: An error occurred during getting value
        from the key in HOMEWORK_STATUSES dict
        Exception: Another error occurred during parsing status

    """
    homework_name = homework.get('homework_name')
    homework_status = homework.get('status')
    try:
        verdict = HOMEWORK_STATUSES[homework_status]
        return f'Изменился статус проверки работы "{homework_name}". {verdict}'
    except KeyError:
        message = (f'Ключ {homework_status} не присутствует '
                   f'в словаре HOMEWORK_STATUSES')
        logger.error(message)
        raise KeyError(message)


def check_tokens() -> bool:
    """Check if tokens are available.

    Returns:
        bool: True if all tokens available, False if something is missing.

    """
    return all([TELEGRAM_TOKEN, TELEGRAM_CHAT_ID, PRACTICUM_TOKEN])


def main():
    """Main function of bot.
    1. Requesting api answer - get_api_answer function
    2. Check answer - check_response function
    3. Parse status of homework - parse_status
    4. Sending message to user if status was updated

    Returns:
        None

    Raises:
        Exception: An error occurred during main function
    """
    if not check_tokens():
        result = [k for k, v in TOKENS.items() if v is None]
        message = (f'Отсутствует обязательная переменная окружения: {result}.'
                   f'Программа остановлена')
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
                logger.debug('В ответе нет новых работ')
                logger.info(f'Бот отправил сообщение: "{message}"')
                continue
            elif not response.get('status') == REVIEWING:
                message = parse_status(check_response_result[0])
                send_message(bot, message)
                logger.info(f'Бот отправил сообщение: "{message}"')
                continue
            current_timestamp = response.get('current_date')
        except Exception as error:
            if last_error['error'] == error.args:
                message = (f'Ошибка {error} по-прежнему не решена. '
                           f'Программу останавливаем')
                logger.error(message)
                send_message(bot, message)
            else:
                last_error['error'] = error.args
                message = f'Сбой в работе программы: {error}'
                send_message(bot, message)
                logger.info(f'Бот отправил сообщение: "{message}"')
        finally:
            time.sleep(RETRY_TIME)


if __name__ == '__main__':

    main()
