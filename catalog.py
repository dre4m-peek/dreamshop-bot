import gspread
from google.oauth2.service_account import Credentials
from dataclasses import dataclass
from typing import Optional
import logging

logger = logging.getLogger(__name__)

@dataclass
class Product:
    id: str
    name: str
    description: str
    price: float
    stock: int
    category: str
    image_url: Optional[str] = None

    def to_context_string(self) -> str:
        return (
            f"ID: {self.id}\n"
            f"Название: {self.name}\n"
            f"Описание: {self.description}\n"
            f"Цена: {self.price:.2f} руб.\n"
            f"В наличии: {self.stock} шт.\n"
            f"Категория: {self.category}\n"
            f"{'Фото: ' + self.image_url if self.image_url else ''}"
        )

class CatalogLoader:
    SCOPES = [
        "https://www.googleapis.com/auth/spreadsheets.readonly",
        "https://www.googleapis.com/auth/drive.readonly"
    ]

    # Ожидаемые колонки в Google Sheets
    COLUMNS = ["id", "name", "description", "price", "stock", "category", "image_url"]

    def __init__(self, credentials_path: str, spreadsheet_id: str, sheet_name: str = "Sheet1"):
        self.credentials_path = credentials_path
        self.spreadsheet_id = spreadsheet_id
        self.sheet_name = sheet_name
        self._client = None
        self._products: list[Product] = []
        self._products_by_id: dict[str, Product] = {}

    def _get_client(self) -> gspread.Client:
        if self._client is None:
            creds = Credentials.from_service_account_file(
                self.credentials_path, scopes=self.SCOPES
            )
            self._client = gspread.authorize(creds)
        return self._client

    def load(self) -> list[Product]:
        """Загружает каталог из Google Sheets"""
        client = self._get_client()
        spreadsheet = client.open_by_key(self.spreadsheet_id)
        worksheet = spreadsheet.worksheet(self.sheet_name)

        # Получаем все значения
        rows = worksheet.get_all_values()
        if not rows:
            logger.warning("Google Sheets пуст")
            return []

        # Первая строка - заголовки
        headers = [h.strip().lower() for h in rows[0]]
        data_rows = rows[1:]

        # Маппинг колонок
        col_map = {}
        for i, header in enumerate(headers):
            if header in self.COLUMNS:
                col_map[header] = i

        products = []
        for row_idx, row in enumerate(data_rows, start=2):
            if not any(cell.strip() for cell in row):
                continue  # Пропускаем пустые строки

            try:
                product = Product(
                    id=str(row[col_map.get("id", 0)]).strip() if col_map.get("id", 0) < len(row) else f"row_{row_idx}",
                    name=str(row[col_map.get("name", 1)]).strip() if col_map.get("name", 1) < len(row) else "",
                    description=str(row[col_map.get("description", 2)]).strip() if col_map.get("description", 2) < len(row) else "",
                    price=float(str(row[col_map.get("price", 3)]).replace(",", ".").strip()) if col_map.get("price", 3) < len(row) and row[col_map.get("price", 3)].strip() else 0.0,
                    stock=int(str(row[col_map.get("stock", 4)]).strip()) if col_map.get("stock", 4) < len(row) and row[col_map.get("stock", 4)].strip() else 0,
                    category=str(row[col_map.get("category", 5)]).strip() if col_map.get("category", 5) < len(row) else "Общее",
                    image_url=str(row[col_map.get("image_url", 6)]).strip() if col_map.get("image_url", 6) < len(row) and row[col_map.get("image_url", 6)].strip() else None,
                )
                if product.name:
                    products.append(product)
            except (ValueError, IndexError) as e:
                logger.warning(f"Строка {row_idx}: ошибка парсинга - {e}, строка: {row}")
                continue

        self._products = products
        self._products_by_id = {p.id: p for p in products}
        logger.info(f"Загружено товаров: {len(products)}")
        return products

    def get_all(self) -> list[Product]:
        if not self._products:
            self.load()
        return self._products

    def get_by_id(self, product_id: str) -> Optional[Product]:
        if not self._products_by_id:
            self.load()
        return self._products_by_id.get(product_id)

    def search(self, query: str) -> list[Product]:
        """Простой поиск по названию, описанию, категории"""
        if not self._products:
            self.load()

        query_lower = query.lower()
        results = []
        for p in self._products:
            if (query_lower in p.name.lower() or
                query_lower in p.description.lower() or
                query_lower in p.category.lower()):
                results.append(p)
        return results

    def get_context_for_llm(self) -> str:
        """Формирует контекст каталога для системного промпта LLM"""
        products = self.get_all()
        if not products:
            return "Каталог пуст."

        parts = ["КАТАЛОГ ТОВАРОВ (полный список):", "=" * 40]
        for p in products:
            parts.append(p.to_context_string())
            parts.append("-" * 40)

        return "\n".join(parts)