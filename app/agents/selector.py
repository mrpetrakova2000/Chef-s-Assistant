"""Selector agent - chooses best product from list"""
from app.models.schemas import State, StateUpdate, StoreOffer
from app.tools.llm_tools import select_product_tool
from app.cache import CacheAgent

_cache_agent: CacheAgent = None


def set_cache_agent(cache: CacheAgent):
    """Set global cache agent"""
    global _cache_agent
    _cache_agent = cache


def selector_node(state: State):
    """Selector agent - chooses the most suitable product"""
    print(f"\n--- Selector: {state.current_ingredient} @ {state.current_store} ---")

    products = state.current_products
    target_product = state.current_ingredient
    dish_name = state.dish_name
    current_store = state.current_store

    # Select best product
    selected_product = select_product_tool.invoke({
        "products": products,
        "target_product": target_product,
        "dish_name": dish_name
    })

    if selected_product:
        print(f"    Выбран товар в {current_store}: {selected_product.description[:50]}...")
        success = True
    else:
        print(f"    Не удалось выбрать подходящий товар в {current_store}.")
        success = False

    # Log search
    if _cache_agent:
        _cache_agent.log_search(
            target_product,
            current_store,
            state.current_category_name,
            success
        )

    # Create store offer
    store_offer = StoreOffer(
        store=current_store,
        product=selected_product,
        success=success,
        category=state.current_category_name,
        found_count=len(products),
        error=None if success else "No matching product found"
    )

    # Add to current offers
    current_offers = state.current_ingredient_offers + [store_offer]

    return StateUpdate(
        current_selected_product=selected_product,
        current_ingredient_offers=current_offers
    )