"""Classifier agent - determines if question is recipe-related"""
from langchain_core.messages import HumanMessage

from app.models.schemas import State, StateUpdate
from app.utils.llm_utils import call_llm_with_retry
from app.cache import CacheAgent

_cache_agent: CacheAgent = None


def set_cache_agent(cache: CacheAgent):
    """Set global cache agent"""
    global _cache_agent
    _cache_agent = cache


def classifier_node(state: State):
    """
    Classifier agent - analyzes user query to determine if it's related to recipe shopping lists.

    Args:
        state: Current graph state

    Returns:
        StateUpdate with skip_execution flag
    """
    print("\n" + "=" * 50)
    print("--- Classifier Agent ---")
    print("=" * 50)

    question = state.question

    classification_prompt = f"""
    Ты помощник, который помогает составлять списки покупок на основе рецептов.
    Определи, относится ли следующий вопрос к этой задаче.
    Вопрос: "{question}"

    Ответь ТОЛЬКО "ДА", если вопрос:
    - запрашивает список ингредиентов для приготовления блюда (например, "Сделай борщ", "Салат Оливье на 4 порции").
    - запрашивает информацию о продуктах для конкретного блюда.
    - запрашивает список покупок для приготовления чего-либо.

    Ответь ТОЛЬКО "НЕТ", если вопрос:
    - не связан с едой, готовкой или покупкой продуктов.
    - слишком общий или неясный для нашей задачи.

    Примеры:
    - "Салат Цезарь на 6 порций" -> ДА
    - "Сделай борщ с говядиной на 2 порции" -> ДА
    - "Что такое мультиагентная система?" -> НЕТ
    - "Как спроектировать систему агентов?" -> НЕТ
    - "Погода сегодня хорошая" -> НЕТ

    Ответ (ДА / НЕТ):
    """

    print(f"    [LLM Запрос] Classifier: классификация запроса '{question[:50]}...'")
    messages = [HumanMessage(content=classification_prompt)]

    response_text = None
    if _cache_agent:
        response_text = _cache_agent.get_cached_llm_response(messages)
        if response_text:
            print(f"    [LLM Ответ] Classifier: (из кэша) '{response_text.strip().upper()}'")

    if not response_text:
        try:
            response_text = call_llm_with_retry(messages, max_retries=2, agent_name="Classifier")
            print(f"    [LLM Ответ] Classifier: '{response_text.strip().upper()}'")
            if _cache_agent:
                _cache_agent.save_llm_response(messages, response_text)
        except Exception as e:
            print(f"    Classifier: LLM недоступен, по умолчанию считаю запрос подходящим.")
            response_text = "ДА"

    response_upper = response_text.strip().upper()

    if response_upper == "ДА":
        print("    ✅ Вопрос подходит. Продолжаем выполнение.")
        skip_flag = False
    elif response_upper == "НЕТ":
        print("    ❌ Вопрос не подходит. Пропускаем выполнение основного цикла.")
        skip_flag = True
    else:
        # Fallback for unexpected response
        print(f"    ⚠️ Неожиданный ответ: '{response_text}'. По умолчанию обрабатываем.")
        skip_flag = False

    return StateUpdate(skip_execution=skip_flag)