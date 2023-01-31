import logging
import os
import sys
import time
from http import HTTPStatus
from logging import StreamHandler

import requests
import telegram
from dotenv import load_dotenv

load_dotenv()
PRACTICUM_TOKEN = os.getenv('PRACTICUM_TOKEN')
TELEGRAM_TOKEN = os.getenv('TELEGRAM_TOKEN')
TELEGRAM_CHAT_ID = os.getenv('TELEGRAM_CHAT_ID')

START_OF_TRAINING = 1666094400
RETRY_PERIOD = 600
ENDPOINT = 'https://practicum.yandex.ru/api/user_api/homework_statuses/'
HEADERS = {'Authorization': f'OAuth {PRACTICUM_TOKEN}'}


HOMEWORK_VERDICTS = {
    'approved': 'Работа проверена: ревьюеру всё понравилось. Ура!',
    'reviewing': 'Работа взята на проверку ревьюером.',
    'rejected': 'Работа проверена: у ревьюера есть замечания.'
}

logger = logging.getLogger(__name__)
handler = StreamHandler()
logger.addHandler(handler)


def check_tokens():
    """Проверка доступности переменных, без которых работа бота не возможна."""
    return all([PRACTICUM_TOKEN, TELEGRAM_TOKEN, TELEGRAM_CHAT_ID])


def send_message(bot, message):
    """Отправка сообщений в чат."""
    logger.debug('Отправка сообщения в Telegram')
    try:
        bot.send_message(TELEGRAM_CHAT_ID, message)
    except telegram.TelegramError:
        logger.error('Сбой при отправке сообщения в Telegram')


def get_api_answer(timestamp):
    """Запрос к единственному эндпоинту API-сервиса."""
    logger.debug('Начало запроса к API')
    timestamp = START_OF_TRAINING or int(time.time())
    params = {'from_date': timestamp}
    logger.debug(f'Начался запрос к {ENDPOINT}')
    try:
        response = requests.get(ENDPOINT,
                                headers=HEADERS,
                                params=params)
        logger.debug(f'Получили ответ сервера {response}')
    except Exception:
        logger.error('Ошибка при запросе к API-сервису')
    if response.status_code != HTTPStatus.OK:
        raise ValueError(f'Ошибка доступа к сайту(Код {response.status_code})')
    return response.json()


def check_response(response):
    """Проверка полученого ответа от API на соответствие."""
    if not isinstance(response, dict):
        raise TypeError('Запрос пришел не в виде словаря')
    if 'homeworks' not in response:
        raise KeyError('Отсутствует ключ homeworks')
    if not isinstance(response['homeworks'], list):
        raise TypeError('Запрос пришел не в виде списка')
    if 'current_date' not in response:
        raise KeyError('Отсутствует ключ current_date')
    homework = response['homeworks'][0]
    return homework


def parse_status(homework):
    """Проверка статуса домашней работы."""
    if 'homework_name' not in homework:
        raise KeyError('Отсутствие ключа имени домашней работы')
    if 'status' not in homework:
        raise KeyError('Отсутствие ключа статуса домашней работы')
    homework_name = homework.get('homework_name')
    homework_status = homework.get('status')
    verdict = HOMEWORK_VERDICTS.get(homework_status)
    if homework_status not in HOMEWORK_VERDICTS:
        raise ValueError('Неожиданный статус домашней работы')
    return f'Изменился статус проверки работы "{homework_name}". {verdict}'


def main():
    """Основная логика работы бота."""
    if not check_tokens():
        error_text = 'Отсутствуют одна или несколько переменных окружения'
        logger.critical(error_text)
        sys.exit(error_text)
    bot = telegram.Bot(token=TELEGRAM_TOKEN)
    timestamp = int(time.time())
    start_message = "Проверка ДЗ"
    send_message(bot, start_message)
    logging.info(start_message)
    old_messages = ''

    while True:
        try:
            response = get_api_answer(timestamp)
            timestamp = response.get('current_date')
            homework = check_response(response)
            if homework == response['homeworks'][0]:
                message = parse_status(homework)
                if message != old_messages:
                    send_message(bot, message)
                    old_messages = message
            else:
                logger.debug('Статус не изменился')
        except Exception as error:
            message = f'Сбой в работе программы: {error}'
            logging.exception('Сбой в работе программы')
            send_message(bot, message)
            if message != old_messages:
                send_message(bot, message)
                old_messages = message
        time.sleep(RETRY_PERIOD)


if __name__ == '__main__':
    logging.basicConfig(
        level=logging.DEBUG,
        filename='api.log',
        filemode='w',
        encoding='UTF-8',
        format='%(asctime)s, %(levelname)s, %(message)s')
    main()
