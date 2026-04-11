"""Magnit store implementation (stub)"""
from typing import Dict, List
from .base import BaseStore


class MagnitStore(BaseStore):
    """Magnit store (stub - returns empty, parsing not implemented)"""

    def __init__(self):
        super().__init__("magnit.ru", "https://magnit.ru")

    def get_categories(self, driver) -> Dict[str, str]:
        """Return predefined categories (stub)"""
        return {
            "Овощи, фрукты": "/catalog/ovoshchi-frukty",
            "Молочные продукты, яйцо": "/catalog/molochnye-produkty",
            "Мясо, птица": "/catalog/myaso-ptitsa",
            "Сыры": "/catalog/syry",
            "Хлеб и выпечка": "/catalog/khleb-vypechka",
            "Бакалея": "/catalog/bakaleya",
        }

    def parse_category(self, driver, category_url: str) -> List[Dict]:
        """Return empty list (stub - parsing not implemented)"""
        print(f"    [ЗАГЛУШКА] Магазин magnit.ru требует отдельного парсера")
        return []

    def get_category_prompt_hints(self) -> str:
        return """
        Категории Магнита:
        - Масло растительное → "Бакалея"
        - Масло сливочное → "Молочные продукты, яйцо"
        """