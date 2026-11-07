import logging
from openai import AsyncOpenAI
from catalog import CatalogLoader, Product
from config import config

logger = logging.getLogger(__name__)

SYSTEM_PROMPT_TEMPLATE = """Ты — консультант интернет-магазина одежды. Твоя задача: помогать клиентам выбирать товары, отвечать на вопросы об ассортименте, ценах, наличии.

ПРАВИЛА:
1. Отвечай ТОЛЬКО на основе каталога ниже. Не выдумывай товары, цен, размеров.
2. Если клиент спрашивает о товаре, которого нет — честно скажи, что его нет в ассортименте.
3. Цены называй в тенге (₸).
4. Наличие: если 0 — пиши "нет в наличии", если мало (1-3) — "осталось мало", если много — "в наличии".
5. Будь дружелюбным, кратким, по делу. Не льей воду.
6. Если клиент хочет купить — предложи уточнить детали и скажи, как оформить заказ (написать администратору).
7. Не обещай скидки, доставку, гарантии — только то, что точно знаешь.

{catalog_context}

---
ПРИМЕРЫ ОТВЕТОВ:

Клиент: "Что есть в наличии?"
Ты: "Сейчас в ассортименте 3 позиции:
• Худи — 14990 ₸, осталось мало (1 шт.)
• Куртка — 24990 ₸, осталось мало (1 шт.)
• Штаны — 12990 ₸, осталось мало (1 шт.)
Что интересует? Могу рассказать подробнее про каждую позицию."

Клиент: "Сколько стоит куртка?"
Ты: "Куртка — 24990 ₸, осталось мало (1 шт.). Хочешь уточнить детали или оформить заказ?"

Клиент: "Есть ли шапки?"
Ты: "Шапок в ассортименте пока нет — только худи, куртка и штаны. Могу прислать фото того, что есть."
"""

class ShopAssistant:
    def __init__(self, catalog: CatalogLoader):
        self.catalog = catalog
        # Настройка клиента Gemini через OpenAI-совместимый эндпоинт
        self.client = AsyncOpenAI(
            api_key=config.GEMINI_API_KEY,
            base_url="https://generativelanguage.googleapis.com/v1beta/openai/"
        )
        self.model = config.GEMINI_MODEL
        self._system_prompt = None

    def _build_system_prompt(self) -> str:
        if self._system_prompt is None:
            catalog_context = self.catalog.get_context_for_llm()
            self._system_prompt = SYSTEM_PROMPT_TEMPLATE.format(catalog_context=catalog_context)
        return self._system_prompt

    async def get_response(self, user_message: str, conversation_history: list[dict] = None) -> str:
        """Получает ответ от LLM с контекстом каталога"""
        messages = [{"role": "system", "content": self._build_system_prompt()}]

        if conversation_history:
            # Берём последние 10 сообщений для контекста
            messages.extend(conversation_history[-10:])

        messages.append({"role": "user", "content": user_message})

        try:
            response = await self.client.chat.completions.create(
                model=self.model,
                messages=messages,
                temperature=0.3,
                max_tokens=500,
            )
            return response.choices[0].message.content.strip()
        except Exception as e:
            logger.error(f"Gemini error: {e}")
            return "Извини, технические неполадки. Попробуй ещё раз через минуту или напиши администратору."

    def refresh_catalog(self):
        """Обновить кэш каталога и сбросить системный промпт"""
        self.catalog.load()
        self._system_prompt = None
        logger.info("Каталог обновлён, промпт сброшен")