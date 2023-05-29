# Telegram-bot для отслеживания статуса домашней работы.
Бот позволяет в заданном временном интервале проверять статус работы через API, и присылать различные сообщения (в зависемости от входного статуса)

## Используемый стек:
Python, Python-Telegram-bot

## Для запуска Вам понадобиться:
#### 1. Общие настройки:
- Клонировать репозиторий на ваш сервер:
```
git clone git@github.com:Pe4enka5/homework_bot.git
``` 
- Устанавливаем виртуальное окружение 
```
python3 -m venv venv
source venv/Scripts/activate
``` 
- Установить зависимости из файла requirements.txt
```
pip install -r requirements.txt
``` 
- Создать файл .env и добавить зависимости по образцу:
```
PRACTICUM_TOKEN = 
TELEGRAM_TOKEN = 
TELEGRAM_CHAT_ID = 
```
#### 2. Запуск Telegram bota:

```
python homework_bot.py
```


### Автор: 
[Андрей Pe4enka5 Печерица](https://github.com/Pe4enka5)
Всем добра и печенек!
