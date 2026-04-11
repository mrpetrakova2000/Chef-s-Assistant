"""Reporter agent - generates final report"""
from app.models.schemas import State, StateUpdate
from app.tools.llm_tools import generate_report_tool


def reporter_node(state: State):
    """Reporter agent - generates final shopping list report"""
    print("\n" + "=" * 50)
    print("--- Reporter Agent ---")
    print("=" * 50)

    if state.skip_execution:
        print("    Генерация ответа для пропущенного вопроса")
        final_response = "Извините, я могу помочь только с составлением списка покупок на основе рецептов. Ваш вопрос не подходит под эту задачу."
        total_price = 0.0
    else:
        print("    Генерация итогового отчета")

        found = sum(1 for item in state.search_results if item.success)
        total = len(state.search_results)
        print(f"    Найдено ингредиентов: {found}/{total}")

        result = generate_report_tool.invoke({
            "dish_name": state.dish_name,
            "portions": state.portions,
            "search_results": state.search_results
        })
        final_response = result["final_response"]
        total_price = result["total_price"]

        print(f"    Итоговая стоимость: {total_price} руб.")

    return StateUpdate(
        final_response=final_response,
        total_price=total_price
    )