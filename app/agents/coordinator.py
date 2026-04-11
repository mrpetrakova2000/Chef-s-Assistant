"""Search coordinator agent - manages iteration over ingredients and stores"""
from app.models.schemas import State, StateUpdate
from app.config import SUPPORTED_STORES


def search_coordinator_node(state: State):
    """Search coordinator - manages ingredient/store iteration"""
    print("\n" + "=" * 50)
    print("--- Search Coordinator ---")
    print("=" * 50)

    # Check if all ingredients processed
    if state.current_ingredient_index >= len(state.plan):
        print("    Все ингредиенты обработаны")
        return StateUpdate(finished=True)

    # Check if all stores processed for current ingredient
    if state.current_store_index >= len(SUPPORTED_STORES):
        print(f"    Все магазины обработаны для '{state.current_ingredient}'")
        return StateUpdate()

    current_ingredient = state.plan[state.current_ingredient_index].name
    current_store = SUPPORTED_STORES[state.current_store_index]

    print(f"    Ингредиент [{state.current_ingredient_index + 1}/{len(state.plan)}]: {current_ingredient}")
    print(f"    Магазин [{state.current_store_index + 1}/{len(SUPPORTED_STORES)}]: {current_store}")

    return StateUpdate(
        current_ingredient=current_ingredient,
        current_store=current_store,
        current_store_index=state.current_store_index + 1
    )