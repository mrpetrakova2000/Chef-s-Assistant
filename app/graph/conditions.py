"""Graph transition conditions"""
from app.models.schemas import State
from app.config import SUPPORTED_STORES


def should_start_planning(state: State) -> str:
    """Determine whether to start planning or go directly to reporter"""
    if state.skip_execution:
        print("    Условие: skip_execution = True, идём к reporter")
        return "reporter"
    else:
        print("    Условие: skip_execution = False, идём к planner")
        return "planner"


def should_continue_search(state: State) -> str:
    """Determine next step after search coordinator"""
    if state.finished:
        print("    Условие: finished = True, идём к reporter")
        return "reporter"

    if state.current_ingredient_index >= len(state.plan):
        print("    Условие: все ингредиенты обработаны, идём к reporter")
        return "reporter"

    if state.current_store_index >= len(SUPPORTED_STORES):
        print(f"    Условие: все магазины обработаны для '{state.current_ingredient}', идём к comparator")
        return "comparator"

    print(f"    Условие: продолжаем обработку магазина {state.current_store_index + 1}/{len(SUPPORTED_STORES)}")
    return "router"