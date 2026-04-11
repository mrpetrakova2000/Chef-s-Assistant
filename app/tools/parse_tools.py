"""Parsing tools - synchronous, parse on demand"""
from typing import List
from langchain_core.tools import tool

from app.models.schemas import Product, ParseCategoryInput
from app.stores import STORE_REGISTRY
from app.utils.driver_utils import get_driver
from app.cache import CacheAgent

_cache_agent: CacheAgent = None


def set_cache_agent(cache: CacheAgent):
    """Set global cache agent"""
    global _cache_agent
    _cache_agent = cache


# Глобальный драйвер
_global_driver = None


def get_global_driver():
    global _global_driver
    if _global_driver is None:
        _global_driver = get_driver()
    return _global_driver

@tool("parse_category_tool", args_schema=ParseCategoryInput)
def parse_category_tool(category_url: str, store: str) -> List[Product]:
    """
    Парсит страницы категории на сайте магазина с пагинацией и возвращает список объектов Product.

    Args:
        category_url (str): URL категории для парсинга.
        store (str): Название магазина.

    Returns:
        List[Product]: Список объектов Product.
    """
    # Заглушки для magnit.ru и vkusvill.ru
    if store in ["magnit.ru", "vkusvill.ru"]:
        print(f"    [ЗАГЛУШКА] Магазин {store} требует отдельного парсера. Возвращаю пустой список.")
        return []

    store_obj = STORE_REGISTRY.get(store)
    if not store_obj:
        return []

    driver = get_global_driver()
    if not driver:
        print('    WebDriver не инициализирован.')
        return []

    try:
        items = store_obj.parse_category(driver, category_url)
        return [Product(**item) for item in items]
    finally:
        driver.quit()


@tool("get_categories_tool")
def get_categories_tool(store: str = "dixy.ru") -> dict:
    """
    Получает список всех основных категорий с главной страницы магазина.

    Args:
        store (str): Название магазина.

    Returns:
        Dict[str, str]: Словарь {название_категории: URL_категории}.
    """
    global _cache_agent

    # Заглушки для magnit.ru и vkusvill.ru
    if store == "magnit.ru":
        print(f"    [ЗАГЛУШКА] Категории для {store}: возвращаю базовый набор.")
        return {
            "Овощи, фрукты": "/catalog/ovoshchi-frukty",
            "Молочные продукты, яйцо": "/catalog/molochnye-produkty",
            "Мясо, птица": "/catalog/myaso-ptitsa",
            "Сыры": "/catalog/syry",
            "Хлеб и выпечка": "/catalog/khleb-vypechka",
            "Бакалея": "/catalog/bakaleya",
            "Колбасы и деликатесы": "/catalog/kolbasy-delikatesy",
            "Консервация": "/catalog/konservatsiya",
        }

    if store == "vkusvill.ru":
        print(f"    [ЗАГЛУШКА] Категории для {store}: возвращаю базовый набор.")
        return {
            "Овощи, фрукты": "/catalog/fresh",
            "Молочные продукты": "/catalog/milk",
            "Мясо, птица": "/catalog/meat",
            "Сыры": "/catalog/cheese",
            "Хлеб и выпечка": "/catalog/bread",
            "Бакалея": "/catalog/grocery",
        }

    # Проверяем кэш
    if _cache_agent:
        cached = _cache_agent.get_cached_categories(store)
        if cached:
            print(f"    Категории для {store} взяты из кэша.")
            return cached

    store_obj = STORE_REGISTRY.get(store)
    if not store_obj:
        return {}

    print(f"    Парсим категории с сайта {store}...")
    driver = get_global_driver()
    if driver:
        try:
            categories = store_obj.get_categories(driver)
            if _cache_agent:
                _cache_agent.save_categories(store, categories)
            print(f"    Найдено {len(categories)} категорий на сайте")
            return categories
        finally:
            driver.quit()
    return {}