"""Vkusvill store implementation (stub)"""
from typing import Dict, List
from .base import BaseStore


class VkusvillStore(BaseStore):
    """Vkusvill store (stub - returns empty, parsing not implemented)"""

    def __init__(self):
        super().__init__("vkusvill.ru", "https://vkusvill.ru")

    def get_categories(self, driver) -> Dict[str, str]:
        """Return predefined categories (stub)"""
        return {
            "Овощи, фрукты": "/catalog/fresh",
            "Молочные продукты": "/catalog/milk",
            "Мясо, птица": "/catalog/meat",
            "Сыры": "/catalog/cheese",
            "Хлеб и выпечка": "/catalog/bread",
            "Бакалея": "/catalog/grocery",
        }

    def parse_category(self, driver, category_url: str) -> List[Dict]:
        """Return empty list (stub - parsing not implemented)"""
        print(f"    [ЗАГЛУШКА] Магазин vkusvill.ru требует отдельного парсера")
        return []

    def get_category_prompt_hints(self) -> str:
        return """
        Категории ВкусВилл:
        - Масло растительное → "Бакалея"
        - Масло сливочное → "Молочные продукты"
        """