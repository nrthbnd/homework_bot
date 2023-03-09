import logging
import os
import sys
import time
from http import HTTPStatus

import requests
import telegram
from dotenv import load_dotenv

from exceptions import NoHomeworkError

load_dotenv()

PRACTICUM_TOKEN = os.getenv('PRACTICUM_TOKEN')
TELEGRAM_TOKEN = os.getenv('TELEGRAM_TOKEN')
TELEGRAM_CHAT_ID = os.getenv('TELEGRAM_CHAT_ID')

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
    filename='main_log',
    filemode='w',
    format='%(asctime)s - %(levelname)s - %(message)s',
    encoding='utf-8',
)


def check_tokens() -> None:
    """Проверяет доступность переменных окружения."""
    logging.debug('Проверка доступности переменных окружения.')
    return all((PRACTICUM_TOKEN, TELEGRAM_TOKEN, TELEGRAM_CHAT_ID))


def send_message(bot, message):
    """Отправляет сообщение в Telegram чат."""
    try:
        bot.send_message(TELEGRAM_CHAT_ID, message)
        logging.debug('В чат отправлено сообщение.')
    except Exception as error:
        logging.error(f'Не получилось отправить сообщение: {error}')


def get_api_answer(timestamp):
    """Делает запрос к эндпоинту API-сервиса. Передает временную метку."""
    # GET-запрос к эндпоинту
    # Ответ возвращается в формате json и приводится к типу данных Python
    timestamp = int(time.time() - 2500000)
    try:
        response = requests.get(
            url=ENDPOINT,
            headers=HEADERS,
            params={'from_date': timestamp}
        )
        if response.status_code != HTTPStatus.OK:
            error_text = (
                'Ошибочный ответ от сервиса '
                f'Практикум.Домашка: {response.status_code}'
            )
            logging.error(error_text)
            raise ValueError(error_text)

        logging.error(
            f'Сервер возвращает ответ. Статус код: {response.status_code}.'
        )
        return response.json()

    except Exception as error:
        error_text = f'Ошибка при запросе к API: {error}.'
        logging.error(error_text)
        raise Exception(error_text)


def check_response(response):
    """Проверяет ответ API на соответствие документации."""
    if not isinstance(response, dict):
        error_text = 'На проверку поступил не dict.'
        logging.error(error_text)
        raise TypeError
    if isinstance(response, list):
        error_text = 'На проверку поступил list.'
        logging.error(error_text)
        raise TypeError
    if not isinstance(response.get('homeworks'), list):
        error_text = 'На проверку homeworks поступил не list.'
        logging.error(error_text)
        raise TypeError
    if 'homeworks' not in response:
        error_text = 'В ответе API нет сведений о домашней работе.'
        logging.error(error_text)
        raise NoHomeworkError(error_text)
    logging.debug('Ответ API проверен, все в порядке.')
    return response


def parse_status(homework):
    """Извлекает из информации о конкретной домашней работе её статус."""
    homework_name = homework.get('homework_name')
    status = homework.get('status')
    verdict = HOMEWORK_VERDICTS.get(status)
    if homework_name is None:
        error_text = 'В homework_name не передано название домашней работы.'
        logging.error(error_text)
        raise KeyError(error_text)
    if status is None:
        error_text = 'В status не передан статус домашней работы.'
        logging.error(error_text)
        raise KeyError(error_text)
    if verdict is None:
        error_text = 'В словаре HOMEWORK_VERDICTS нет переданного ключа.'
        logging.error(error_text)
        raise KeyError(error_text)
    return f'Изменился статус проверки работы "{homework_name}". {verdict}'


def main():
    """Основная логика работы бота."""
    if not check_tokens():
        error_text = 'Не передан токен для доступа к боту.'
        logging.critical(error_text)
        sys.exit(error_text)

    bot = telegram.Bot(token=TELEGRAM_TOKEN)
    timestamp = ''
    logging.info('Бот для проверки домашней работы запущен.')

    while True:
        try:
            response = get_api_answer(timestamp)
            timestamp = response.get('current_date')
            homework = check_response(response)
            message = parse_status(homework['homeworks'][0])
            send_message(bot, message)
        except Exception as error:
            error_text = f'Сбой в работе программы: {error}.'
            logging.error(error_text)
            send_message(bot, error_text)
        finally:
            time.sleep(RETRY_PERIOD)


if __name__ == '__main__':
    main()
