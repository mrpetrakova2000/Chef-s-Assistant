"""Background worker for processing tasks"""
import time
import json
import redis
import os
from app.graph.builder import create_graph
from app.cache import CacheAgent
from app.tools.parse_tools import set_cache_agent as set_parse_cache
from app.tools.llm_tools import set_cache_agent as set_llm_cache
from app.agents.parser import set_cache_agent as set_parser_cache
from app.agents.selector import set_cache_agent as set_selector_cache
from app.agents.classifier import set_cache_agent as set_classifier_cache

# Инициализация — С decode_responses=True для строк
redis_client = redis.Redis.from_url(
    os.getenv("REDIS_URL", "redis://localhost:6379"),
    decode_responses=True  # 👈 Включаем строки
)

cache_agent = CacheAgent(6)
set_parse_cache(cache_agent)
set_llm_cache(cache_agent)
set_parser_cache(cache_agent)
set_selector_cache(cache_agent)
set_classifier_cache(cache_agent)

app_graph = create_graph()

print("👷 Worker started, waiting for tasks...", flush=True)


def process_question(question: str) -> dict:
    """Обрабатывает вопрос и возвращает результат"""
    start_time = time.time()

    initial_state = {
        "question": question,
        "skip_execution": False,
        "dish_name": "",
        "portions": 0,
        "plan": [],
        "current_ingredient_index": 0,
        "current_store_index": 0,
        "current_ingredient": "",
        "current_store": "",
        "current_category_name": "",
        "current_category_url": "",
        "current_products": [],
        "current_selected_product": None,
        "current_ingredient_offers": [],
        "search_results": [],
        "total_price": 0.0,
        "final_response": "",
        "finished": False
    }

    result = app_graph.invoke(initial_state)
    elapsed = time.time() - start_time

    skip_execution = result.get("skip_execution", False)
    dish_name = result.get("dish_name", "")
    portions = result.get("portions", 0)
    search_results = result.get("search_results", [])
    total_price = result.get("total_price", 0.0)

    ingredients = []
    for res in search_results:
        if hasattr(res, 'ingredient'):
            ingredients.append({
                "name": res.ingredient,
                "found": res.success,
                "product_description": res.selected_offer.product.description if res.success and res.selected_offer else None,
                "price": res.selected_offer.product.price if res.success and res.selected_offer else None,
                "store": res.selected_offer.store if res.success and res.selected_offer else None,
                "link": res.selected_offer.product.link if res.success and res.selected_offer else None
            })

    return {
        "success": not skip_execution,
        "dish_name": dish_name,
        "portions": portions,
        "ingredients": ingredients,
        "total_price": total_price,
        "elapsed_seconds": round(elapsed, 2)
    }


# Главный цикл — слушаем Redis
while True:
    try:
        # keys возвращает список строк (благодаря decode_responses=True)
        keys = redis_client.keys("task:*")
        print(f"📋 Found {len(keys)} keys", flush=True)

        for key in keys:
            # key уже строка
            task_id = key.split(":")[1]

            # get возвращает строку
            task_data = redis_client.get(key)

            if task_data:
                # task_data уже строка, парсим JSON
                data = json.loads(task_data)

                if data.get("status") == "pending":
                    question = data.get("question")

                    print(f"🔄 Processing task {task_id}: {question}", flush=True)

                    # Обновляем статус
                    redis_client.setex(
                        key, 3600,
                        json.dumps({"status": "processing", "question": question})
                    )

                    try:
                        result = process_question(question)

                        # Сохраняем результат
                        redis_client.setex(
                            key, 3600,
                            json.dumps({"status": "completed", "result": result})
                        )

                        print(f"✅ Task {task_id} completed in {result['elapsed_seconds']}s", flush=True)

                    except Exception as e:
                        print(f"❌ Task {task_id} failed: {e}", flush=True)
                        redis_client.setex(
                            key, 3600,
                            json.dumps({"status": "failed", "error": str(e)})
                        )

        time.sleep(2)

    except Exception as e:
        print(f"Worker error: {e}", flush=True)
        time.sleep(5)