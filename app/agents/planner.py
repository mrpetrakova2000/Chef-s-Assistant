"""Planner agent - generates ingredient list"""
from app.models.schemas import State, StateUpdate, PlanItem
from app.tools.llm_tools import generate_plan_tool


def planner_node(state: State):
    """Planner agent - generates ingredient list from recipe"""
    print("\n" + "=" * 50)
    print("--- Planner Agent ---")
    print("=" * 50)

    result = generate_plan_tool.invoke({"question": state.question})

    dish_name = result["dish_name"]
    portions = result["portions"]
    plan = [PlanItem(**item) for item in result["plan"]]

    print(f"    Блюдо: {dish_name}")
    print(f"    Порций: {portions}")
    print(f"    Ингредиентов: {len(plan)}")
    print(f"    План: {[ing.name for ing in plan[:5]]}...")

    return StateUpdate(
        dish_name=dish_name,
        portions=portions,
        plan=plan,
        current_ingredient_index=0,
        current_store_index=0,
        search_results=[],
        finished=False
    )