"""Parser agent - synchronous parsing"""
from app.models.schemas import State, StateUpdate, Product
from app.tools.parse_tools import parse_category_tool
from app.cache import CacheAgent

_cache_agent: CacheAgent = None


def set_cache_agent(cache: CacheAgent):
    global _cache_agent
    _cache_agent = cache


def parser_node(state: State):
    """Parser agent - fetches products from cache or parses on demand"""
    print(f"\n--- Parser: {state.current_category_name} ---")

    category_url = state.current_category_url
    current_store = state.current_store

    # Проверяем кэш
    cached_products = None
    if _cache_agent:
        cached_products = _cache_agent.get_cached_products(current_store, category_url)

    if cached_products is not None:
        print(f"    Результаты для {current_store} - {category_url} взяты из кэша.")
        parsed_products = [Product(**item) for item in cached_products]
    else:
        print(f"    Запрашиваю инструмент parse_category_tool для {current_store} - {category_url}...")
        parsed_products = parse_category_tool.invoke({
            "category_url": category_url,
            "store": current_store
        })

        if parsed_products and _cache_agent:
            _cache_agent.save_products(
                current_store,
                category_url,
                [p.model_dump() for p in parsed_products]
            )

    print(f"    Найдено {len(parsed_products)} товаров в {current_store}.")

    return StateUpdate(current_products=parsed_products)