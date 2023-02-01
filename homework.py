import logging
import os
import sys
import time
from http import HTTPStatus

import requests
import telegram
from dotenv import load_dotenv

from exceptions import ApiAnswerError

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


def check_tokens():
    """Проверка доступности переменных, без которых работа бота не возможна."""
    return all([PRACTICUM_TOKEN, TELEGRAM_TOKEN, TELEGRAM_CHAT_ID])


def send_message(bot, message):
    """Отправка сообщений в чат."""
    logging.debug('Отправка сообщения в Telegram')
    try:
        bot.send_message(TELEGRAM_CHAT_ID, message)
        logging.debug(f'Отправляется следующие сообщение: {message}')
    except telegram.TelegramError as error:
        logging.error(f'Сбой при отправке сообщения в Telegram. {error}',
                      exc_info=True)
    logging.debug('Сообщение отправлено успешно!')


def get_api_answer(timestamp):
    """Запрос к единственному эндпоинту API-сервиса."""
    logging.debug('Начало запроса к API')
    timestamp = START_OF_TRAINING or int(time.time())
    params = {'from_date': timestamp}
    logging.debug(f'Начался запрос к {ENDPOINT}')
    try:
        response = requests.get(ENDPOINT,
                                headers=HEADERS,
                                params=params)
    except Exception as error:
        raise Exception(f'Ошибка при запросе к API-сервису, {error}'
                        'при следующих параметрах запроса'
                        f'url = {ENDPOINT}, headers = {HEADERS}'
                        f'params = {params}')
    if response.status_code != HTTPStatus.OK:
        raise ApiAnswerError(f'Ошибка доступа к API.'
                             f'request params = {params};'
                             f'http_code = {response.status_code};'
                             f'reason = {response.reason};'
                             f'content = {response.text}')
    logging.debug(f'Получили ответ сервера {response}')
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
    homework = response.get('homeworks')[0]
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
        logging.critical(error_text)
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
            if homework == []:
                message = (f'За период от {timestamp} до настоящего'
                           'момента домашних работ нет.')
                logging.debug('Новых статусов нет')
            else:
                message = parse_status(homework)
            if message != old_messages:
                send_message(bot, message)
                old_messages = message
        except Exception as error:
            message = f'Сбой в работе программы: {error}'
            logging.exception(message)
            if message != old_messages:
                send_message(bot, message)
                old_messages = message
        time.sleep(RETRY_PERIOD)


if __name__ == '__main__':
    logging.basicConfig(
        level=logging.DEBUG,
        format='%(asctime)s, %(levelname)s, %(message)s')
    main()
