import logging
from openai import AsyncOpenAI
from catalog import CatalogLoader, Product
from config import config

logger = logging.getLogger(__name__)

SYSTEM_PROMPT_TEMPLATE = """Ты — консультант интернет-магазина одежды. Твоя задача: помогать клиентам выбирать товары, отвечать на вопросы об ассортименте, ценах, наличии.

ПРАВИЛА:
1. Отвечай ТОЛЬКО на основе каталога ниже. Не выдумывай товары, цен, размеров.
2. Если клиент спрашивает о товаре, которого нет — честно скажи, что его нет.
3. Цены называй в тенге (₸).
4. Наличие: если 0 — пиши "нет в наличии", если мало (1-3) — "осталось мало", если много — "в наличии".
5. Будь дружелюбным, кратким, по делу.
6. Если клиент хочет купить — предложи уточнить детали (размер) и скажи, как оформить заказ (написать менеджеру).
7. ИСПОЛЬЗУЙ Markdown: названия товаров выделяй **жирным**, цены — *курсивом*. Используй эмодзи (🔥, 👕, 👖, 🧥, 💰).
8. ВАЖНО: Если клиент просит показать товары (или спрашивает "что есть"), в самом конце своего ответа добавь специальный тег с ID товаров, которые ты упомянул. Формат: [IMAGES: 1, 2, 3] (где 1, 2, 3 — это id из каталога).

{catalog_context}

---
ПРИМЕР ОТВЕТА:

Клиент: "Что есть в наличии?"
Ты: "Сейчас в ассортименте 3 позиции:
• **Худи** 👕 — *14990 ₸*, осталось мало (1 шт.)
• **Куртка** 🧥 — *24990 ₸*, осталось мало (1 шт.)
• **Штаны** 👖 — *12990 ₸*, осталось мало (1 шт.)
Что интересует? 🔥
[IMAGES: 1, 2, 3]"
"""

class ShopAssistant:
    def __init__(self, catalog: CatalogLoader):
        self.catalog = catalog
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
        messages = [{"role": "system", "content": self._build_system_prompt()}]

        if conversation_history:
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
            return "Извини, технические неполадки. Попробуй ещё раз через минуту."

    def refresh_catalog(self):
        self.catalog.load()
        self._system_prompt = None
        logger.info("Каталог обновлён, промпт сброшен")