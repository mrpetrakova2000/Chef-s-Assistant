"""Router agent - determines category for ingredient"""
from app.models.schemas import State, StateUpdate
from app.tools.parse_tools import get_categories_tool
from app.tools.llm_tools import route_ingredient_tool


def router_node(state: State):
    """Router agent - determines which category to search in"""
    print(f"\n--- Router: {state.current_ingredient} @ {state.current_store} ---")

    # Get categories for the store
    categories = get_categories_tool.invoke({"store": state.current_store})
    print(f"    Получено категорий: {len(categories)}")

    # Route ingredient to category
    result = route_ingredient_tool.invoke({
        "product_name": state.current_ingredient,
        "dish_name": state.dish_name,
        "store": state.current_store,
        "all_categories": categories
    })

    print(f"    → Категория: {result['category_name']}")

    return StateUpdate(
        current_category_name=result["category_name"],
        current_category_url=result["category_url"]
    )