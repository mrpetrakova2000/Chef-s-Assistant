"""Comparator agent - compares offers from different stores"""
from app.models.schemas import State, StateUpdate, IngredientResult
from app.tools.llm_tools import compare_offers_tool


def comparator_node(state: State):
    """Comparator agent - compares offers and selects the best one"""
    print(f"\n--- Comparator: {state.current_ingredient} ---")

    successful_offers = [o for o in state.current_ingredient_offers if o.success]
    print(f"    Успешных предложений: {len(successful_offers)}/{len(state.current_ingredient_offers)}")

    for offer in state.current_ingredient_offers:
        if offer.success and offer.product:
            print(f"      - {offer.store}: {offer.product.price}")
        else:
            print(f"      - {offer.store}: не найдено")

    # Compare offers
    selected = compare_offers_tool.invoke({
        "ingredient": state.current_ingredient,
        "offers": state.current_ingredient_offers,
        "dish_name": state.dish_name
    })

    if selected:
        print(f"    ✅ Выбрано: {selected.store} - {selected.product.price}")
    else:
        print(f"    ❌ Предложение не выбрано")

    # Create result
    result = IngredientResult(
        ingredient=state.current_ingredient,
        success=selected is not None,
        offers=state.current_ingredient_offers,
        selected_offer=selected,
        category=selected.category if selected else "",
        found_count=len(successful_offers)
    )

    return StateUpdate(
        search_results=state.search_results + [result],
        current_ingredient_index=state.current_ingredient_index + 1,
        current_store_index=0,
        current_ingredient_offers=[]
    )