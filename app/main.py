"""Main application entry point"""
import gc
import atexit
from contextlib import asynccontextmanager
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
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


class QueryRequest(BaseModel):
    question: str


class IngredientItem(BaseModel):
    name: str
    found: bool
    product_description: str | None = None
    price: str | None = None
    store: str | None = None
    link: str | None = None


class QueryResponse(BaseModel):
    success: bool
    dish_name: str | None = None
    portions: int | None = None
    ingredients: list[IngredientItem] = []
    total_price: float
    markdown_text: str
    elapsed_seconds: float
    stats: dict | None = None


class StatusResponse(BaseModel):
    status: str
    stats: dict


def cleanup_resources():
    global cache_agent, app_graph

    print("\n🧹 Cleaning up resources...")

    if cache_agent:
        cache_agent.products_cache.clear()
        cache_agent.categories_cache.clear()
        cache_agent.message_history_cache.clear()
        cache_agent.history.clear()
        print("   ✅ Cache cleared")

    app_graph = None
    gc.collect()
    print("   ✅ Garbage collected")
    print("👋 Cleanup complete")


atexit.register(cleanup_resources)


@asynccontextmanager
async def lifespan(app: FastAPI):
    global cache_agent, app_graph

    print("\n" + "=" * 60)
    print("🚀 CHEF'S ASSISTANT STARTING...")
    print("=" * 60)

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

    print("=" * 60)
    print("🎯 SYSTEM READY")
    print("=" * 60 + "\n")

    yield

    print("\n" + "=" * 60)
    print("🛑 SHUTTING DOWN...")
    print("=" * 60)
    cleanup_resources()
    print("✅ Shutdown complete")


app = FastAPI(
    title="Chef's Assistant",
    description="Multi-agent system for recipe-based shopping lists",
    version="1.0.0",
    lifespan=lifespan
)

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000",
        "http://127.0.0.1:3000",
        "http://frontend:3000",
        "*"
    ],
    allow_credentials=True,
    allow_methods=["GET", "POST", "OPTIONS"],
    allow_headers=["*"],
)


@app.get("/health")
async def health_check():
    return {"status": "ok", "graph_ready": app_graph is not None}


@app.get("/status")
async def get_status() -> StatusResponse:
    global cache_agent

    if not cache_agent:
        raise HTTPException(status_code=503, detail="System not initialized")

    return StatusResponse(
        status="ready",
        stats=cache_agent.get_stats()
    )


@app.options("/query")
async def options_query():
    return {"message": "OK"}


@app.post("/query", response_model=QueryResponse)
async def process_query(request: QueryRequest):
    global app_graph, cache_agent

    if not app_graph:
        raise HTTPException(status_code=503, detail="System not ready")

    print(f"\n📝 Query: {request.question}")
    start_time = time.time()

    initial_state = {
        "question": request.question,
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

        print(f"⏱️ Completed in {elapsed:.1f}s")

        skip_execution = result.get("skip_execution", False)
        dish_name = result.get("dish_name", "")
        portions = result.get("portions", 0)
        search_results = result.get("search_results", [])
        total_price = result.get("total_price", 0.0)

        ingredients = []
        for res in search_results:
            if hasattr(res, 'ingredient'):
                ingredient_item = IngredientItem(
                    name=res.ingredient,
                    found=res.success,
                    product_description=res.selected_offer.product.description if res.success and res.selected_offer else None,
                    price=res.selected_offer.product.price if res.success and res.selected_offer else None,
                    store=res.selected_offer.store if res.success and res.selected_offer else None,
                    link=res.selected_offer.product.link if res.success and res.selected_offer else None
                )
                ingredients.append(ingredient_item)

        # Проверяем, пустой ли ответ (нет ингредиентов или skip_execution)
        if skip_execution or len(ingredients) == 0:
            markdown_text = _get_not_recipe_message()
            return QueryResponse(
                success=False,
                dish_name=None,
                portions=None,
                ingredients=[],
                total_price=0.0,
                markdown_text=markdown_text,
                elapsed_seconds=round(elapsed, 2),
                stats=cache_agent.get_stats() if cache_agent else None
            )

        markdown_text = _generate_markdown(
            skip_execution=skip_execution,
            dish_name=dish_name,
            portions=portions,
            ingredients=ingredients,
            total_price=total_price
        )

        gc.collect()

        return QueryResponse(
            success=not skip_execution,
            dish_name=dish_name if not skip_execution else None,
            portions=portions if not skip_execution else None,
            ingredients=ingredients,
            total_price=total_price,
            markdown_text=markdown_text,
            elapsed_seconds=round(elapsed, 2),
            stats=cache_agent.get_stats() if cache_agent else None
        )

    except Exception as e:
        elapsed = time.time() - start_time
        print(f"❌ Error after {elapsed:.1f}s: {e}")
        import traceback
        traceback.print_exc()

        gc.collect()

        # При ошибке тоже возвращаем понятное сообщение
        markdown_text = _get_error_message()
        return QueryResponse(
            success=False,
            dish_name=None,
            portions=None,
            ingredients=[],
            total_price=0.0,
            markdown_text=markdown_text,
            elapsed_seconds=round(elapsed, 2),
            stats=cache_agent.get_stats() if cache_agent else None
        )


def _get_not_recipe_message() -> str:
    """Сообщение когда запрос не является рецептом"""
    return """### ❌ Запрос не распознан

Извините, я могу помочь только с составлением списка покупок на основе рецептов.

**Попробуйте спросить:**
- 🥗 "Салат Цезарь на 4 порции"
- 🍲 "Борщ с говядиной на 2 порции"
- 🥔 "Оливье на 6 персон"
- 🍝 "Паста карбонара на 3 порции"

Я помогу найти все ингредиенты и сравню цены в разных магазинах!
"""


def _get_error_message() -> str:
    """Сообщение при ошибке обработки"""
    return """### ⚠️ Ошибка обработки

К сожалению, произошла ошибка при обработке вашего запроса.

**Возможные причины:**
- Сервер временно перегружен
- Проблемы с подключением к магазинам
- Слишком сложный рецепт

**Попробуйте:**
- 🔄 Повторить запрос через минуту
- 📝 Упростить название блюда
- 🛒 Указать меньшее количество порций

Приносим извинения за неудобства!
"""


def _generate_markdown(
        skip_execution: bool,
        dish_name: str,
        portions: int,
        ingredients: list,
        total_price: float
) -> str:
    """Генерирует Markdown текст для отображения на фронтенде"""

    if skip_execution:
        return _get_not_recipe_message()

    md = f"""### 🛒 Список покупок для **{dish_name}** ({portions} порций)

"""

    found_items = [i for i in ingredients if i.found]
    if found_items:
        md += "#### ✅ Найденные товары\n\n"
        for item in found_items:
            md += f"**{item.name}**\n"
            md += f"- {item.product_description}\n"
            md += f"- 💰 {item.price}\n"
            md += f"- 🏪 {item.store}\n"
            if item.link:
                md += f"- 🔗 [Ссылка на товар]({item.link})\n"
            md += "\n"

    not_found_items = [i for i in ingredients if not i.found]
    if not_found_items:
        md += "#### ❌ Не найденные товары\n\n"
        for item in not_found_items:
            md += f"- {item.name}\n"
        md += "\n"

    md += f"---\n\n"
    md += f"### 💰 Итоговая стоимость: **{total_price} руб.**\n\n"

    if found_items:
        md += f"*Найдено {len(found_items)} из {len(ingredients)} ингредиентов*"
    else:
        md += f"*К сожалению, ничего не найдено*"

    return md


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


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "app.main:app",
        host="0.0.0.0",
        port=8000,
        reload=False,
        log_level="info",
        timeout_keep_alive=300
    )