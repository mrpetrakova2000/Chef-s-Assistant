"""LLM-based tools for agents"""
import re
import json
from typing import Dict, Any, Optional, List
from langchain_core.tools import tool
from langchain_core.messages import HumanMessage

from app.models.schemas import (
    Product, StoreOffer, GeneratePlanInput, RouteIngredientInput,
    SelectProductInput, CompareOffersInput, GenerateReportInput
)
from app.stores import STORE_REGISTRY
from app.utils.llm_utils import call_llm_with_retry
from app.cache import CacheAgent

_cache_agent: CacheAgent = None


def set_cache_agent(cache: CacheAgent):
    """Set global cache agent"""
    global _cache_agent
    _cache_agent = cache


@tool("generate_plan_tool", args_schema=GeneratePlanInput)
def generate_plan_tool(question: str) -> Dict[str, Any]:
    """
    Генерирует план (список ингредиентов) на основе вопроса пользователя.

    Args:
        question (str): Вопрос пользователя, например "Сделай борщ на 2 порции".

    Returns:
        Dict[str, Any]: Словарь с ключами 'dish_name', 'portions', 'plan'.
    """
    # Extract dish name and portions
    parts = question.split(' на ')
    if len(parts) > 1:
        dish_name = parts[0].split(' ', 1)[1] if ' ' in parts[0] else parts[0]
        portions_match = re.search(r'(\d+)', parts[1])
        portions = int(portions_match.group(1)) if portions_match else 1
    else:
        dish_name = question
        portions = 1

    prompt = f"""
    Ты - эксперт по составлению списков покупок для рецептов.
    Сгенерируй список ингредиентов для "{dish_name}" на {portions} порций.

    ПРАВИЛА:

    1. ВКЛЮЧАЙ ТОЛЬКО ТО, ЧТО НУЖНО КУПИТЬ В МАГАЗИНЕ.
       НЕ включай воду (она из-под крана).

    2. Используй простые русские названия продуктов, как в магазине.

    3. НЕ указывай количество или вес в названии.

    4. НЕ используй бренды и специальные символы.

    Верни ТОЛЬКО JSON:
    {{
        "dish": "название",
        "portions": {portions},
        "ingredients": [
           {{
              "name": "название"
           }}
        ]
    }}
    """

    print(f"    [LLM Запрос] Planner: генерация рецепта для '{dish_name}' на {portions} порций")
    messages = [HumanMessage(content=prompt)]

    # Check cache
    response_text = None
    if _cache_agent:
        response_text = _cache_agent.get_cached_llm_response(messages)
        if response_text:
            print(f"    [LLM Ответ] Planner: (из кэша)")

    if not response_text:
        try:
            response_text = call_llm_with_retry(messages, max_retries=2, agent_name="Planner")
            print(f"    [LLM Ответ] Planner: {response_text[:200]}...")
            if _cache_agent:
                _cache_agent.save_llm_response(messages, response_text)
        except Exception as e:
            print(f"    Planner: LLM недоступен, использую фолбэк.")
            return {"dish_name": dish_name, "portions": portions, "plan": [{"name": "основной ингредиент"}]}

    try:
        json_match = re.search(r'\{.*\}', response_text, re.DOTALL)
        if json_match:
            recipe_json = json_match.group()
            plan_data = json.loads(recipe_json)
            plan = plan_data.get("ingredients", [])
            print(f"    Planner: успешно извлечено {len(plan)} ингредиентов")
        else:
            print("    Planner: Не удалось найти JSON в ответе. Использую фолбэк.")
            plan = [{"name": "ингредиент 1"}, {"name": "ингредиент 2"}]
    except json.JSONDecodeError:
        print("    Planner: Ошибка парсинга JSON. Использую фолбэк.")
        plan = [{"name": "ингредиент 1"}, {"name": "ингредиент 2"}]

    return {"dish_name": dish_name, "portions": portions, "plan": plan}


@tool("route_ingredient_tool", args_schema=RouteIngredientInput)
def route_ingredient_tool(product_name: str, dish_name: str, store: str, all_categories: Dict[str, str]) -> Dict[
    str, str]:
    """
    Определяет, в какой категории искать ингредиент в конкретном магазине.

    Args:
        product_name (str): Название ингредиента.
        dish_name (str): Название блюда.
        store (str): Название магазина.
        all_categories (Dict[str, str]): Словарь всех доступных категорий.

    Returns:
        Dict[str, str]: Словарь с ключами 'category_name', 'category_url'.
    """
    # Выводим полученные категории
    print(f"    Получено категорий: {len(all_categories)}")
    print(f"    Категории: {', '.join(list(all_categories.keys())[:10])}...")

    # Fallback-маппинг на случай недоступности LLM
    fallback_map = {
        'курин': 'Мясо, птица', 'филе': 'Мясо, птица', 'говядин': 'Мясо, птица',
        'свинин': 'Мясо, птица', 'мяс': 'Мясо, птица', 'фарш': 'Мясо, птица',
        'колбас': 'Колбасы и деликатесы', 'сосиск': 'Колбасы и деликатесы',
        'молок': 'Молочные продукты', 'сметан': 'Молочные продукты',
        'творог': 'Молочные продукты', 'кефир': 'Молочные продукты',
        'йогурт': 'Молочные продукты', 'яйц': 'Молочные продукты',
        'масл': 'Молочные продукты', 'сыр': 'Сыры', 'пармезан': 'Сыры',
        'моцарелл': 'Сыры', 'овощ': 'Овощи, фрукты', 'фрукт': 'Овощи, фрукты',
        'картоф': 'Овощи, фрукты', 'морков': 'Овощи, фрукты', 'лук': 'Овощи, фрукты',
        'чеснок': 'Овощи, фрукты', 'помидор': 'Овощи, фрукты', 'томат': 'Овощи, фрукты',
        'огурец': 'Овощи, фрукты', 'капуст': 'Овощи, фрукты', 'свекл': 'Овощи, фрукты',
        'перец': 'Овощи, фрукты', 'зелень': 'Овощи, фрукты', 'укроп': 'Овощи, фрукты',
        'петрушк': 'Овощи, фрукты', 'салат': 'Овощи, фрукты', 'лимон': 'Овощи, фрукты',
        'хлеб': 'Хлеб и выпечка', 'булк': 'Хлеб и выпечка', 'батон': 'Хлеб и выпечка',
        'сухар': 'Хлеб и выпечка', 'крутон': 'Хлеб и выпечка', 'гренк': 'Хлеб и выпечка',
        'сухарик': 'Хлеб и выпечка', 'мук': 'Бакалея', 'сахар': 'Бакалея',
        'сол': 'Бакалея', 'круп': 'Бакалея', 'рис': 'Бакалея', 'греч': 'Бакалея',
        'макарон': 'Бакалея', 'спагетти': 'Бакалея', 'масл растительн': 'Бакалея',
        'оливков': 'Бакалея', 'уксус': 'Бакалея', 'соус': 'Бакалея',
        'кетчуп': 'Бакалея', 'майонез': 'Бакалея', 'горчиц': 'Бакалея',
        'приправ': 'Бакалея', 'консерв': 'Консервация', 'замороз': 'Замороженные продукты',
    }

    prompt = f"""
        Ты помощник для выбора продуктовой категории в магазине {store}.

        Продукт: "{product_name}"
        {f'Для блюда: "{dish_name}"' if dish_name else ''}

        Доступные категории в магазине {store}:
        {'; '.join(all_categories.keys())}

        Выбери ОДНУ наиболее подходящую категорию.
        Верни ТОЛЬКО ОДНО точное название категории из списка.
    """

    print(f"    [LLM Запрос] Router: определение категории для '{product_name}' в магазине {store}")
    messages = [HumanMessage(content=prompt)]

    selected_category_name = ""
    selected_category_url = ""

    try:
        response = call_llm_with_retry(messages, max_retries=3, agent_name="Router")
        if response:
            response = response.strip()
            print(f"    [LLM Ответ] Router: '{response}'")

            # Ищем точное совпадение
            for cat_name, cat_url in all_categories.items():
                if cat_name.lower() == response.lower():
                    selected_category_name = cat_name
                    selected_category_url = cat_url
                    break

            # Если точного нет - ищем частичное
            if not selected_category_name:
                for cat_name, cat_url in all_categories.items():
                    if response.lower() in cat_name.lower() or cat_name.lower() in response.lower():
                        selected_category_name = cat_name
                        selected_category_url = cat_url
                        break
    except Exception as e:
        print(f"    Router: LLM недоступен, использую fallback-маппинг.")

    # Fallback если LLM не дал результат
    if not selected_category_name:
        product_lower = product_name.lower()
        for keyword, fallback_cat in fallback_map.items():
            if keyword in product_lower:
                for cat_name, cat_url in all_categories.items():
                    if fallback_cat in cat_name:
                        selected_category_name = cat_name
                        selected_category_url = cat_url
                        print(f"    Router (fallback): '{product_name}' -> '{selected_category_name}'")
                        break
                if selected_category_name:
                    break

        # Если и fallback не сработал - берем первую категорию
        if not selected_category_name:
            print(f"    Router: не удалось определить категорию для '{product_name}', беру первую доступную.")
            selected_category_name = list(all_categories.keys())[0]
            selected_category_url = list(all_categories.values())[0]

    print(f"    Выбрана категория: {selected_category_name} -> {selected_category_url}")
    return {"category_name": selected_category_name, "category_url": selected_category_url}


@tool("select_product_tool", args_schema=SelectProductInput)
def select_product_tool(products: List[Product], target_product: str, dish_name: str) -> Optional[Product]:
    """
    Выбирает наиболее подходящий товар из списка.

    Args:
        products (List[Product]): Список доступных товаров.
        target_product (str): Название целевого ингредиента.
        dish_name (str): Название блюда.

    Returns:
        Optional[Product]: Выбранный товар или None.
    """
    if not products:
        print("    Selector: Нет товаров для выбора.")
        return None

    # Limit products for prompt
    display_products = products[:30]
    products_text = "\n".join([
        f"{i + 1}. {p.description} - {p.price} [{p.store}]"
        for i, p in enumerate(display_products)
    ])

    prompt = f"""
    Выбери наиболее подходящий товар для "{target_product}"
    {f'для приготовления блюда "{dish_name}"' if dish_name else ''}.

    Критерии выбора:
    1. Соответствие названию продукта "{target_product}"
    2. Подходящий объем/вес для приготовления
    3. Лучшее соотношение цена/качество

    Доступные товары:
    {products_text}

    Верни ТОЛЬКО номер выбранного товара (от 1 до {len(display_products)}).
    Пример ответа: 3
    """

    print(f"    [LLM Запрос] Selector: выбор товара для '{target_product}' из {len(products)} вариантов")
    messages = [HumanMessage(content=prompt)]

    # Check cache
    response_text = None
    if _cache_agent:
        response_text = _cache_agent.get_cached_llm_response(messages)
        if response_text:
            print(f"    [LLM Ответ] Selector: (из кэша)")

    if not response_text:
        try:
            response_text = call_llm_with_retry(messages, max_retries=2, agent_name="Selector")
            print(f"    [LLM Ответ] Selector: '{response_text}'")
            if _cache_agent:
                _cache_agent.save_llm_response(messages, response_text)
        except Exception as e:
            print(f"    Selector: LLM недоступен, беру первый товар.")
            return products[0] if products else None

    try:
        numbers = re.findall(r'\b\d+\b', response_text)
        if numbers:
            selected_num = int(numbers[0])
            if 1 <= selected_num <= len(display_products):
                selected_product = display_products[selected_num - 1]
                print(f"    Выбран товар #{selected_num}: {selected_product.description[:50]}...")
                return selected_product
    except (ValueError, IndexError):
        pass

    print("    Selector: Ошибка при обработке ответа LLM, использую фолбэк (первый товар).")
    return products[0] if products else None


@tool("compare_offers_tool", args_schema=CompareOffersInput)
def compare_offers_tool(ingredient: str, offers: List[StoreOffer], dish_name: str) -> Optional[StoreOffer]:
    """
    Сравнивает предложения из разных магазинов и выбирает оптимальное.

    Args:
        ingredient (str): Название ингредиента.
        offers (List[StoreOffer]): Список предложений из магазинов.
        dish_name (str): Название блюда.

    Returns:
        Optional[StoreOffer]: Выбранное предложение или None.
    """
    successful_offers = [o for o in offers if o.success and o.product is not None]

    if not successful_offers:
        print("    Comparator: Нет успешных предложений для сравнения.")
        return None

    if len(successful_offers) == 1:
        print(f"    Comparator: Только одно предложение, выбираю его.")
        return successful_offers[0]

    offers_text = "\n".join([
        f"{i + 1}. Магазин: {o.store}, Товар: {o.product.description[:50]}..., Цена: {o.product.price}"
        for i, o in enumerate(successful_offers)
    ])

    prompt = f"""
    Сравни предложения для ингредиента "{ingredient}"
    {f'для приготовления блюда "{dish_name}"' if dish_name else ''}.

    Предложения из разных магазинов:
    {offers_text}

    Выбери оптимальное предложение, учитывая:
    1. Соответствие товара ингредиенту
    2. Цену (чем дешевле, тем лучше)

    Верни ТОЛЬКО номер выбранного предложения (от 1 до {len(successful_offers)}).
    """

    print(f"    [LLM Запрос] Comparator: сравнение {len(successful_offers)} предложений для '{ingredient}'")
    messages = [HumanMessage(content=prompt)]

    # Check cache
    response_text = None
    if _cache_agent:
        response_text = _cache_agent.get_cached_llm_response(messages)

    if not response_text:
        try:
            response_text = call_llm_with_retry(messages, max_retries=2, agent_name="Comparator")
            print(f"    [LLM Ответ] Comparator: '{response_text}'")
            if _cache_agent:
                _cache_agent.save_llm_response(messages, response_text)
        except Exception as e:
            print(f"    Comparator: LLM недоступен, выбираю самое дешевое.")
            return min(successful_offers, key=lambda o: _extract_price(o))

    try:
        numbers = re.findall(r'\b\d+\b', response_text)
        if numbers:
            selected_num = int(numbers[0])
            if 1 <= selected_num <= len(successful_offers):
                selected_offer = successful_offers[selected_num - 1]
                print(f"    Выбрано предложение #{selected_num}: {selected_offer.store}")
                return selected_offer
    except (ValueError, IndexError):
        pass

    print("    Comparator: Ошибка при обработке ответа LLM, выбираю самое дешевое.")
    return min(successful_offers, key=lambda o: _extract_price(o))


def _extract_price(offer: StoreOffer) -> float:
    """Extract numeric price from offer"""
    if offer.product:
        match = re.search(r'(\d+[.,]?\d*)', offer.product.price)
        if match:
            return float(match.group(1).replace(',', '.'))
    return float('inf')


@tool("generate_report_tool", args_schema=GenerateReportInput)
def generate_report_tool(dish_name: str, portions: int, search_results: List) -> Dict[str, Any]:
    """
    Генерирует итоговый отчет.

    Args:
        dish_name (str): Название блюда.
        portions (int): Количество порций.
        search_results (List[IngredientResult]): Результаты поиска.

    Returns:
        Dict[str, Any]: Словарь с ключами 'final_response', 'total_price'.
    """
    found = sum(1 for item in search_results if item.success)
    total = len(search_results)

    total_price = 0
    for item in search_results:
        if item.selected_offer and item.selected_offer.product:
            price_str = item.selected_offer.product.price
            match = re.search(r'(\d+[.,]?\d*)', price_str)
            if match:
                try:
                    price_val = float(match.group(1).replace(',', '.'))
                    total_price += price_val
                except ValueError:
                    pass

    total_price = round(total_price, 2)

    results_for_prompt = []
    for res in search_results:
        res_dict = {
            'ingredient': res.ingredient,
            'success': res.success,
            'selected_store': res.selected_offer.store if res.selected_offer else None,
            'selected_product': res.selected_offer.product.description if res.selected_offer and res.selected_offer.product else None,
            'price': res.selected_offer.product.price if res.selected_offer and res.selected_offer.product else None,
            'link': res.selected_offer.product.link if res.selected_offer and res.selected_offer.product else None,
            'offers_count': len([o for o in res.offers if o.success])
        }
        results_for_prompt.append(res_dict)

    prompt = f"""
    Сформируй итоговый отчет для пользователя.
    Блюдо: {dish_name}
    Порции: {portions}
    Найдено ингредиентов: {found}/{total}
    Примерная стоимость: {total_price} руб.

    Результаты поиска (с ссылками на товары):
    {json.dumps(results_for_prompt, ensure_ascii=False, indent=2)}

    Сформируй красивый ответ в формате Markdown:

    🛒 **Список покупок для {dish_name}** ({portions} порций)

    **Найденные товары:**
    ✅ Ингредиент: описание товара - цена - [ссылка](url) - магазин

    **Не найденные товары:**
    ❌ Ингредиент: не найдено в магазинах

    💰 **Итоговая стоимость: {total_price} руб.**

    ВАЖНО: Обязательно включи ссылки на товары в формате Markdown: [товар](ссылка)
    """

    print(f"    [LLM Запрос] Reporter: генерация итогового отчета")
    messages = [HumanMessage(content=prompt)]

    # Check cache
    response_text = None
    if _cache_agent:
        response_text = _cache_agent.get_cached_llm_response(messages)

    if not response_text:
        try:
            response_text = call_llm_with_retry(messages, max_retries=2, agent_name="Reporter")
            print(f"    [LLM Ответ] Reporter: отчет сгенерирован")
            if _cache_agent:
                _cache_agent.save_llm_response(messages, response_text)
        except Exception as e:
            print(f"    Reporter: LLM недоступен, генерирую простой отчет.")
            response_text = _generate_fallback_report(dish_name, portions, search_results, total_price)

    return {"final_response": response_text, "total_price": total_price}


def _generate_fallback_report(dish_name: str, portions: int, search_results: List, total_price: float) -> str:
    """Generate simple report when LLM is unavailable"""
    response = f"🛒 **Список покупок для {dish_name}** ({portions} порций)\n\n"
    response += "**Найденные товары:**\n"

    for res in search_results:
        if res.success and res.selected_offer:
            p = res.selected_offer.product
            response += f"✅ **{res.ingredient}**: {p.description} ({p.price}) - [Ссылка]({p.link}) - {res.selected_offer.store}\n"

    response += "\n**Не найденные товары:**\n"
    for res in search_results:
        if not res.success:
            response += f"❌ **{res.ingredient}**: не найдено в магазинах\n"

    response += f"\n💰 **Итоговая стоимость: {total_price} руб.**"
    return response