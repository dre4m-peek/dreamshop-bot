import asyncio
import logging
import os
from aiogram import Bot, Dispatcher, F
from aiogram.filters import Command, CommandStart
from aiogram.types import Message, ReplyKeyboardMarkup, KeyboardButton, BotCommand
from aiogram.fsm.storage.memory import MemoryStorage

from config import config
from catalog import CatalogLoader
from assistant import ShopAssistant
from render_health import start_health_server

# Настройка логирования
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)

# Инициализация бота и диспетчера
bot = Bot(token=config.BOT_TOKEN)
dp = Dispatcher(storage=MemoryStorage())

# Загрузка каталога и ассистента (с указанием правильного имени листа!)
catalog = CatalogLoader(
    credentials_path=config.GOOGLE_SHEETS_CREDENTIALS,
    spreadsheet_id=config.SPREADSHEET_ID,
    sheet_name="Лист1"
)
assistant = ShopAssistant(catalog)

# Клавиатура с кнопками
main_kb = ReplyKeyboardMarkup(
    keyboard=[
        [KeyboardButton(text="Что в наличии?"), KeyboardButton(text="Цены")],
        [KeyboardButton(text="Помощь")]
    ],
    resize_keyboard=True
)

@dp.message(CommandStart())
async def cmd_start(message: Message):
    await message.answer(
        "Привет! Я ИИ-консультант магазина DreamShop 👋\n"
        "Могу рассказать о наличии, ценах и помочь с выбором.\n"
        "Спрашивай что угодно или жми на кнопки ниже!",
        reply_markup=main_kb
    )

@dp.message(Command("admin"))
async def cmd_admin(message: Message):
    if message.from_user.id not in config.ADMIN_IDS:
        await message.answer("⛔ У вас нет доступа к админке.")
        return
    
    try:
        catalog.load()
        assistant.refresh_catalog()
        await message.answer("✅ Каталог успешно обновлен! Бот видит новые данные.")
    except Exception as e:
        await message.answer(f"❌ Ошибка обновления: {e}")

@dp.message(F.text == "Что в наличии?")
async def btn_stock(message: Message):
    await message.answer("Секунду, посмотрю в каталоге...")
    response = await assistant.get_response("Что есть в наличии?")
    await message.answer(response)

@dp.message(F.text == "Цены")
async def btn_prices(message: Message):
    await message.answer("Секунду, проверяю цены...")
    response = await assistant.get_response("Сколько стоят все товары?")
    await message.answer(response)

@dp.message(F.text == "Помощь")
async def btn_help(message: Message):
    await message.answer(
        "Я умею:\n"
        "• Показывать наличие\n"
        "• Называть цены\n"
        "• Советовать, что выбрать\n\n"
        "Просто напиши мне свой вопрос обычным текстом!"
    )

@dp.message(F.text)
async def handle_text(message: Message):
    # Ставим статус "печатает..."
    await bot.send_chat_action(chat_id=message.chat.id, action="typing")
    
    # Получаем ответ от ИИ
    try:
        response = await assistant.get_response(message.text)
        await message.answer(response)
    except Exception as e:
        logger.error(f"Ошибка при ответе: {e}")
        await message.answer("Ой, что-то пошло не так. Попробуй еще раз.")

async def main():
    logger.info("Запуск бота...")
    
    # Устанавливаем команды в меню
    await bot.set_my_commands([
        BotCommand(command="start", description="Запустить бота"),
        BotCommand(command="admin", description="Админка (для владельца)")
    ])
    
    # Проверяем каталог при старте
    try:
        catalog.load()
        logger.info("Каталог успешно загружен.")
    except Exception as e:
        logger.error(f"Ошибка загрузки каталога: {e}")

    # Запуск health endpoint для Render (порт 10000 по умолчанию)
    port = int(os.getenv("PORT", 10000))
    health_runner = await start_health_server(port)

    try:
        # Запускаем polling
        await dp.start_polling(bot)
    finally:
        await health_runner.cleanup()
        await bot.session.close()

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except (KeyboardInterrupt, SystemExit):
        logger.info("Бот остановлен.")