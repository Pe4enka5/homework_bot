import logging
import os
import time
import sys

import requests
import telegram

from dotenv import load_dotenv
from http import HTTPStatus
from logging import StreamHandler

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

logging.basicConfig(
    level=logging.DEBUG,
    filename='api.log',
    filemode='w',
    encoding='UTF-8',
    format='%(asctime)s, %(levelname)s, %(message)s'
)
logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)
handler = StreamHandler(stream=sys.stdout)
logger.addHandler(handler)
formatter = logging.Formatter(
    '%(asctime)s - %(levelname)s - %(message)s'
)
handler.setFormatter(formatter)


def check_tokens():
    """Проверка доступности переменных, без которых работа бота не возможна."""
    try:
        if all([PRACTICUM_TOKEN, TELEGRAM_TOKEN, TELEGRAM_CHAT_ID]):
            return True
    except Exception:
        logger.critical('Отсутствует обязательная переменная окружения!')


def send_message(bot, message):
    """Отправка сообщений в чат."""
    try:
        bot.send_message(TELEGRAM_CHAT_ID, message)
        logger.debug('Удачная отправка сообщения в Telegram')
    except Exception:
        logger.error('Сбой при отправке сообщения в Telegram')


def get_api_answer(timestamp):
    """Запрос к единственному эндпоинту API-сервиса."""
    try:
        timestamp = START_OF_TRAINING or int(time.time())
        payload = {'from_date': timestamp}
        responce = requests.get(ENDPOINT,
                                headers=HEADERS,
                                params=payload)
    except Exception:
        logger.error('Ошибка при запросе к API-сервису')
    if responce.status_code != HTTPStatus.OK:
        logger.error('Ошибка доступа к сайту(Код 200)')
        raise Exception('Ошибка доступа к сайту(Код 200)')
    return responce.json()


def check_response(response):
    """Проверка полученого ответа от API на соответствие."""
    try:
        homeworks = response['homeworks']
    except KeyError:
        logger.error('Отсутствие ожидаемых ключей в ответе API')
    if type(response) != dict:
        logger.error('Запрос пришел не в виде словаря')
        raise TypeError('Запрос пришел не в виде словаря')
    if type(homeworks) != list:
        logger.error('Данные представлены не в виде списка')
        raise TypeError('Запрос пришел не в виде словаря')
    try:
        homework = homeworks[0]
    except IndexError:
        logger.error('Список домашних работ пуст')
    return homework


def parse_status(homework):
    """Проверка статуса домашней работы."""
    homework_name = homework.get('homework_name')
    homework_status = homework.get('status')
    if 'homework_name' not in homework:
        logger.error('Отсутствие ключа имени домашней работы')
        raise KeyError('Отсутствие ключа имени домашней работы')
    if 'status' not in homework:
        logger.error('Отсутствие ключа статуса домашней работы')
        raise KeyError('Отсутствие ключа статуса домашней работы')
    verdict = HOMEWORK_VERDICTS.get(homework_status)
    if homework_status not in HOMEWORK_VERDICTS:
        logger.error('Неожиданный статус домашней работы')
        raise Exception('Неожиданный статус домашней работы')
    return f'Изменился статус проверки работы "{homework_name}". {verdict}'


def main():
    """Основная логика работы бота."""
    if not check_tokens():
        logger.critical('Отсутствуют одна или несколько переменных окружения')
        raise Exception('Отсутствуют одна или несколько переменных окружения')
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
            message = parse_status(homework)
            if message != old_messages:
                send_message(bot, message)
                old_messages = message
                time.sleep(RETRY_PERIOD)
        except Exception as error:
            message = f'Сбой в работе программы: {error}'
            logger.error('Сбой в работе программы')
            if message != old_messages:
                send_message(bot, message)
                old_messages = message
        time.sleep(RETRY_PERIOD)


if __name__ == '__main__':
    main()
