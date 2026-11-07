# Shop Bot — Telegram-консультант для демо-магазина

Бот читает каталог из Google Sheets, отвечает на вопросы про товары, цены, наличие через GPT-4o-mini.

## Быстрый старт

### 1. Установи зависимости
```bash
cd C:\Users\Laptop_Kz\арман\shop_bot
pip install -r requirements.txt
```

### 2. Настрой Google Sheets

**Структура таблицы (заголовки в строке 1):**
| id | name | description | price | stock | category | image_url |
|---|---|---|---|---|---|---|
| 1 | Худи | Тёплое худи из хлопка, воротник-стойка | 3500 | 15 | Худи | https://... |
| 2 | Куртка | Зимняя куртка, мембрана, пух | 8500 | 7 | Куртки | https://... |
| 3 | Штаны | Джинсовые штаны, прямой крой | 4200 | 12 | Штаны | https://... |

**Важно:** 
- `id` — уникальный идентификатор (любой)
- `price` — число (можно с точкой или запятой)
- `stock` — целое число
- `image_url` — опционально, ссылка на фото

### 3. Создай Service Account для Google Sheets API

1. Открой [Google Cloud Console](https://console.cloud.google.com/)
2. Создай проект или выбери существующий
3. Включи **Google Sheets API** и **Google Drive API**
4. Создай **Service Account** (IAM → Service Accounts)
5. Скачай JSON-ключ → положи в папку бота как `credentials.json`
6. Открой свою Google Таблицу → кнопка **Доступ** → добавь email сервисного аккаунта (из JSON: `client_email`) с правом **Читатель**
7. Скопируй **Spreadsheet ID** из URL таблицы:
   `https://docs.google.com/spreadsheets/d/SPREADSHEET_ID/edit`

### 4. Создай Telegram-бота

1. Напиши @BotFather → `/newbot`
2. Скопируй токен

### 5. Настрой `.env`

```bash
copy .env.example .env
```
Открой `.env` и заполни:
```env
BOT_TOKEN=123456:ABC-DEF1234ghIkl-zyx57W2v1u123ew11
OPENAI_API_KEY=sk-proj-...
OPENAI_MODEL=gpt-4o-mini
GOOGLE_SHEETS_CREDENTIALS=credentials.json
SPREADSHEET_ID=1AbCdEfGhIjKlMnOpQrStUvWxYz...
SHEET_NAME=Sheet1
ADMIN_IDS=твой_telegram_id
```

Узнать свой Telegram ID: напиши @userinfobot

### 6. Запусти
```bash
python bot.py
```

## Команды бота

| Команда | Описание |
|---|---|
| `/start` | Главное меню |
| `/catalog` | Полный каталог |
| `/search` | Поиск по названию/категории |
| `/help` | Помощь |
| `/admin` | Админ-панель (только для админов) |

## Админ-панель

- 🔄 **Обновить каталог** — перезагрузить из Google Sheets
- 📋 **Показать каталог** — список с ID и остатками
- ⚙️ **Настройки Sheets** — сменить Spreadsheet ID / имя листа без перезапуска
- 📊 **Статус бота** — проверка конфигурации

## Как это работает

1. При старте бот загружает каталог из Google Sheets в память
2. Каталог полностью встраивается в системный промпт GPT-4o-mini
3. Пользователь спрашивает → бот шлёт вопрос + контекст каталога в OpenAI
4. LLM отвечает, опираясь ТОЛЬКО на данные из каталога
4. Админ может обновить каталог одной кнопкой — изменения вступают сразу

## Стоимость

GPT-4o-mini: ~$0.15 за 1M токенов ввода, $0.60 за 1M токенов вывода.
При каталоге из 3 товаров — промпт ~300 токенов. 1000 диалогов = ~$0.05.

## Структура проекта

```
shop_bot/
├── bot.py           # Основной файл бота (aiogram 3)
├── config.py        # Конфигурация из .env
├── catalog.py       # Загрузка каталога из Google Sheets
├── assistant.py     # LLM-ассистент (OpenAI)
├── requirements.txt # Зависимости
├── .env.example     # Пример конфига
└── credentials.json # Ключ Google Service Account (не в гит!)
```

## Траблшутинг

**"Каталог пуст"** — проверь: 
- Spreadsheet ID верный?
- Сервисный аккаунт добавлен в доступ к таблице?
- Заголовки в строке 1 точно совпадают (id, name, description, price, stock, category, image_url)?

**"Ошибка OpenAI"** — проверь баланс и валидность API ключа.

**Бот не отвечает** — смотри логи в консоли, проверь BOT_TOKEN.