"""Main application entry point"""
import gc
import atexit
import uuid
import asyncio
from contextlib import asynccontextmanager
from fastapi import FastAPI, HTTPException, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from typing import Dict
import time

from app.config import MISTRAL_API_KEY
from app.models.schemas import State
from app.cache import CacheAgent
from app.graph.builder import create_graph
from app.tools.parse_tools import set_cache_agent as set_parse_cache
from app.tools.llm_tools import set_cache_agent as set_llm_cache
from app.agents.parser import set_cache_agent as set_parser_cache
from app.agents.selector import set_cache_agent as set_selector_cache
from app.agents.classifier import set_cache_agent as set_classifier_cache


# Global instances
cache_agent = None
app_graph = None

# Хранилище результатов задач
task_results: Dict[str, dict] = {}


class QueryRequest(BaseModel):
    question: str


class TaskResponse(BaseModel):
    task_id: str
    status: str
    message: str


class TaskResultResponse(BaseModel):
    task_id: str
    status: str  # "pending", "processing", "completed", "failed"
    result: dict | None = None
    error: str | None = None


class ForceCORSHeaderMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        if request.method == "OPTIONS":
            response = JSONResponse(content={"message": "OK"})
            response.headers["Access-Control-Allow-Origin"] = "*"
            response.headers["Access-Control-Allow-Methods"] = "GET, POST, PUT, DELETE, OPTIONS"
            response.headers["Access-Control-Allow-Headers"] = "*"
            return response

        response = await call_next(request)
        response.headers["Access-Control-Allow-Origin"] = "*"
        response.headers["Access-Control-Allow-Methods"] = "GET, POST, PUT, DELETE, OPTIONS"
        response.headers["Access-Control-Allow-Headers"] = "*"
        return response


def cleanup_resources():
    global cache_agent, app_graph
    print("\n🧹 Cleaning up resources...")
    if cache_agent:
        cache_agent.products_cache.clear()
        cache_agent.categories_cache.clear()
        cache_agent.message_history_cache.clear()
        cache_agent.history.clear()
    app_graph = None
    gc.collect()
    print("👋 Cleanup complete")


atexit.register(cleanup_resources)


@asynccontextmanager
async def lifespan(app: FastAPI):
    global cache_agent, app_graph

    print("\n" + "="*60)
    print("🚀 CHEF'S ASSISTANT STARTING...")
    print("="*60)

    if not MISTRAL_API_KEY:
        raise ValueError("MISTRAL_API_KEY is not set")
    print("✅ Mistral API key loaded")

    cache_agent = CacheAgent(6)
    print("✅ Cache agent initialized")

    set_parse_cache(cache_agent)
    set_llm_cache(cache_agent)
    set_parser_cache(cache_agent)
    set_selector_cache(cache_agent)
    set_classifier_cache(cache_agent)
    print("✅ Cache agent injected into all modules")

    app_graph = create_graph()
    print("✅ Agent graph created")

    print("="*60)
    print("🎯 SYSTEM READY")
    print("="*60 + "\n")

    yield

    print("\n🛑 SHUTTING DOWN...")
    cleanup_resources()


app = FastAPI(
    title="Chef's Assistant",
    description="Multi-agent system for recipe-based shopping lists",
    version="1.0.0",
    lifespan=lifespan
)

app.add_middleware(ForceCORSHeaderMiddleware)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)


async def process_recipe_task(task_id: str, question: str):
    """Фоновая задача обработки рецепта"""
    global app_graph, cache_agent, task_results

    task_results[task_id] = {"status": "processing", "result": None, "error": None}

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

    try:
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

        markdown_text = _generate_markdown(skip_execution, dish_name, portions, ingredients, total_price)

        task_results[task_id] = {
            "status": "completed",
            "result": {
                "success": not skip_execution,
                "dish_name": dish_name if not skip_execution else None,
                "portions": portions if not skip_execution else None,
                "ingredients": ingredients,
                "total_price": total_price,
                "markdown_text": markdown_text,
                "elapsed_seconds": round(elapsed, 2),
                "stats": cache_agent.get_stats() if cache_agent else None
            },
            "error": None
        }

    except Exception as e:
        elapsed = time.time() - start_time
        print(f"❌ Task {task_id} failed after {elapsed:.1f}s: {e}")
        import traceback
        traceback.print_exc()

        markdown_text = _get_error_message()

        task_results[task_id] = {
            "status": "failed",
            "result": {
                "success": False,
                "dish_name": None,
                "portions": None,
                "ingredients": [],
                "total_price": 0.0,
                "markdown_text": markdown_text,
                "elapsed_seconds": round(elapsed, 2),
                "stats": None
            },
            "error": str(e)
        }

    finally:
        gc.collect()


@app.get("/health")
async def health_check():
    return {"status": "ok", "graph_ready": app_graph is not None}


@app.get("/status")
async def get_status():
    global cache_agent
    if not cache_agent:
        raise HTTPException(status_code=503, detail="System not initialized")
    return {"status": "ready", "stats": cache_agent.get_stats()}


@app.options("/{path:path}")
async def options_handler(path: str):
    return JSONResponse(content={"message": "OK"})


@app.post("/query", response_model=TaskResponse)
async def process_query(request: QueryRequest):
    """Создаёт задачу и возвращает task_id"""
    global app_graph

    if not app_graph:
        raise HTTPException(status_code=503, detail="System not ready")

    task_id = str(uuid.uuid4())
    print(f"\n📝 Task {task_id}: {request.question}")

    # Запускаем в фоне
    asyncio.create_task(process_recipe_task(task_id, request.question))

    return TaskResponse(
        task_id=task_id,
        status="processing",
        message="Запрос принят в обработку"
    )


@app.get("/task/{task_id}", response_model=TaskResultResponse)
async def get_task_result(task_id: str):
    """Получить результат задачи по ID"""
    global task_results

    if task_id not in task_results:
        raise HTTPException(status_code=404, detail="Task not found")

    task_data = task_results[task_id]

    return TaskResultResponse(
        task_id=task_id,
        status=task_data["status"],
        result=task_data["result"],
        error=task_data["error"]
    )


@app.delete("/task/{task_id}")
async def delete_task(task_id: str):
    """Удалить результат задачи"""
    global task_results

    if task_id in task_results:
        del task_results[task_id]
        return {"status": "deleted"}

    raise HTTPException(status_code=404, detail="Task not found")


@app.post("/clear-cache")
async def clear_cache():
    global cache_agent
    if not cache_agent:
        raise HTTPException(status_code=503, detail="System not initialized")
    cache_agent.products_cache.clear()
    cache_agent.categories_cache.clear()
    cache_agent.message_history_cache.clear()
    cache_agent.history.clear()
    print("🧹 Cache cleared via API")
    return {"status": "ok", "message": "Cache cleared"}


def _get_not_recipe_message() -> str:
    return """### ❌ Запрос не распознан

Извините, я могу помочь только с составлением списка покупок на основе рецептов.

**Попробуйте спросить:**
- 🥗 "Салат Цезарь на 4 порции"
- 🍲 "Борщ с говядиной на 2 порции"
- 🥔 "Оливье на 6 персон"
"""


def _get_error_message() -> str:
    return """### ⚠️ Ошибка обработки

К сожалению, произошла ошибка. Попробуйте повторить запрос позже.
"""


def _generate_markdown(skip_execution: bool, dish_name: str, portions: int, ingredients: list, total_price: float) -> str:
    if skip_execution:
        return _get_not_recipe_message()

    md = f"""### 🛒 Список покупок для **{dish_name}** ({portions} порций)\n\n"""

    found_items = [i for i in ingredients if i.get("found")]
    if found_items:
        md += "#### ✅ Найденные товары\n\n"
        for item in found_items:
            md += f"**{item['name']}**\n"
            md += f"- {item['product_description']}\n"
            md += f"- 💰 {item['price']}\n"
            md += f"- 🏪 {item['store']}\n"
            if item.get('link'):
                md += f"- 🔗 [Ссылка на товар]({item['link']})\n"
            md += "\n"

    not_found_items = [i for i in ingredients if not i.get("found")]
    if not_found_items:
        md += "#### ❌ Не найденные товары\n\n"
        for item in not_found_items:
            md += f"- {item['name']}\n"
        md += "\n"

    md += f"---\n\n### 💰 Итоговая стоимость: **{total_price} руб.**\n\n"

    if found_items:
        md += f"*Найдено {len(found_items)} из {len(ingredients)} ингредиентов*"
    else:
        md += "*К сожалению, ничего не найдено*"

    return md


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("app.main:app", host="0.0.0.0", port=8000, reload=False)