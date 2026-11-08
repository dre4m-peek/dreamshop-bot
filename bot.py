import asyncio
import logging
import os
import re
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

# Загрузка каталога и ассистента
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

# Вспомогательная функция для отправки ответа (с картинками или без)
async def send_response(message: Message, text: str):
    # Ищем тег [IMAGES: 1, 2, 3]
    match = re.search(r'\[IMAGES:\s*([\d,\s]+)\]', text)
    if match:
        # Вырезаем тег из текста
        clean_text = re.sub(r'\[IMAGES:\s*[\d,\s]+\]', '', text).strip()
        await message.answer(clean_text, parse_mode="Markdown")
        
        # Получаем список ID
        ids = [int(x.strip()) for x in match.group(1).split(',')]
        
        # Отправляем картинки (если они есть в таблице)
        for product_id in ids:
            product = next((p for p in catalog.get_all() if p.id == product_id), None)
            if product and product.image_url:
                try:
                    await message.answer_photo(photo=product.image_url, caption=f"**{product.name}** — {product.price} ₸", parse_mode="Markdown")
                except Exception as e:
                    logger.error(f"Ошибка отправки фото: {e}")
    else:
        # Если тегов нет, просто отправляем текст
        await message.answer(text, parse_mode="Markdown")

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
        await message.answer("✅ Каталог успешно обновлен!")
    except Exception as e:
        await message.answer(f"❌ Ошибка: {e}")

@dp.message(F.text == "Что в наличии?")
async def btn_stock(message: Message):
    await message.answer("Секунду, посмотрю в каталоге...")
    response = await assistant.get_response("Что есть в наличии?")
    await send_response(message, response)

@dp.message(F.text == "Цены")
async def btn_prices(message: Message):
    await message.answer("Секунду, проверяю цены...")
    response = await assistant.get_response("Сколько стоят все товары?")
    await send_response(message, response)

@dp.message(F.text == "Помощь")
async def btn_help(message: Message):
    await message.answer(
        "Я умею:\n"
        "• Показывать наличие и фото\n"
        "• Называть цены\n"
        "• Советовать, что выбрать\n\n"
        "Просто напиши мне свой вопрос!"
    )

@dp.message(F.text)
async def handle_text(message: Message):
    await bot.send_chat_action(chat_id=message.chat.id, action="typing")
    try:
        response = await assistant.get_response(message.text)
        await send_response(message, response)
    except Exception as e:
        logger.error(f"Ошибка при ответе: {e}")
        await message.answer("Ой, что-то пошло не так.")

async def main():
    logger.info("Запуск бота...")
    await bot.set_my_commands([
        BotCommand(command="start", description="Запустить бота"),
        BotCommand(command="admin", description="Админка")
    ])
    try:
        catalog.load()
        logger.info("Каталог загружен.")
    except Exception as e:
        logger.error(f"Ошибка: {e}")

    port = int(os.getenv("PORT", 10000))
    health_runner = await start_health_server(port)

    try:
        await dp.start_polling(bot)
    finally:
        await health_runner.cleanup()
        await bot.session.close()

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except (KeyboardInterrupt, SystemExit):
        logger.info("Бот остановлен.")