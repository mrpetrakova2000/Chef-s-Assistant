"""Main application entry point - API with Redis queue"""
import gc
import atexit
import uuid
import json
import time
from contextlib import asynccontextmanager
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
import redis
import os

from app.config import MISTRAL_API_KEY
from app.cache import CacheAgent


# Global instances
cache_agent = None

# Redis клиент с decode_responses=True для строк
redis_client = redis.Redis.from_url(
    os.getenv("REDIS_URL", "redis://redis:6379"),
    decode_responses=True
)


class QueryRequest(BaseModel):
    question: str


class TaskResponse(BaseModel):
    task_id: str
    status: str


class TaskResultResponse(BaseModel):
    task_id: str
    status: str
    result: dict | None = None
    error: str | None = None


class ForceCORSHeaderMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        if request.method == "OPTIONS":
            response = JSONResponse(content={"message": "OK"})
            response.headers["Access-Control-Allow-Origin"] = "*"
            response.headers["Access-Control-Allow-Methods"] = "*"
            response.headers["Access-Control-Allow-Headers"] = "*"
            return response

        response = await call_next(request)
        response.headers["Access-Control-Allow-Origin"] = "*"
        response.headers["Access-Control-Allow-Methods"] = "*"
        response.headers["Access-Control-Allow-Headers"] = "*"
        return response


def cleanup_resources():
    global cache_agent
    print("\n🧹 Cleaning up resources...", flush=True)
    if cache_agent:
        cache_agent.products_cache.clear()
        cache_agent.categories_cache.clear()
        cache_agent.message_history_cache.clear()
        cache_agent.history.clear()
        print("   ✅ Cache cleared", flush=True)
    gc.collect()
    print("👋 Cleanup complete", flush=True)


atexit.register(cleanup_resources)


@asynccontextmanager
async def lifespan(app: FastAPI):
    global cache_agent

    print("\n" + "="*60, flush=True)
    print("🚀 CHEF'S ASSISTANT API STARTING...", flush=True)
    print("="*60, flush=True)

    if not MISTRAL_API_KEY:
        raise ValueError("MISTRAL_API_KEY is not set")
    print("✅ Mistral API key loaded", flush=True)

    cache_agent = CacheAgent(6)
    print("✅ Cache agent initialized", flush=True)

    # Проверяем Redis
    try:
        redis_client.ping()
        print("✅ Redis connected", flush=True)
    except Exception as e:
        print(f"⚠️ Redis connection failed: {e}", flush=True)

    print("="*60, flush=True)
    print("🎯 API READY", flush=True)
    print("="*60 + "\n", flush=True)

    yield

    print("\n🛑 SHUTTING DOWN...", flush=True)
    cleanup_resources()
    print("✅ Shutdown complete", flush=True)


app = FastAPI(
    title="Chef's Assistant",
    description="Multi-agent system for recipe-based shopping lists",
    version="1.0.0",
    lifespan=lifespan
)

# CORS middleware
app.add_middleware(ForceCORSHeaderMiddleware)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {"status": "ok", "redis": redis_client.ping()}


@app.get("/status")
async def get_status():
    """Get system status"""
    global cache_agent

    if not cache_agent:
        return {"status": "initializing", "stats": {}}

    return {
        "status": "ready",
        "stats": cache_agent.get_stats()
    }


@app.options("/{path:path}")
async def options_handler(path: str):
    """Handle OPTIONS requests"""
    return JSONResponse(content={"message": "OK"})


@app.post("/query", response_model=TaskResponse)
async def create_task(request: QueryRequest):
    """Создаёт задачу в Redis и сразу возвращает task_id"""

    task_id = str(uuid.uuid4())
    key = f"task:{task_id}"

    print(f"\n📝 Task {task_id}: {request.question}", flush=True)

    try:
        redis_client.setex(
            key,
            3600,  # TTL 1 час
            json.dumps({"status": "pending", "question": request.question})
        )
        print(f"✅ Task {task_id} saved to Redis", flush=True)
    except Exception as e:
        print(f"❌ Failed to save task {task_id}: {e}", flush=True)
        raise HTTPException(status_code=500, detail="Failed to create task")

    return TaskResponse(task_id=task_id, status="pending")


@app.get("/task/{task_id}", response_model=TaskResultResponse)
async def get_task(task_id: str):
    """Проверить статус задачи"""

    key = f"task:{task_id}"

    try:
        task_data = redis_client.get(key)
    except Exception as e:
        print(f"❌ Redis error: {e}", flush=True)
        raise HTTPException(status_code=500, detail="Redis unavailable")

    if not task_data:
        raise HTTPException(status_code=404, detail="Task not found")

    try:
        data = json.loads(task_data)
    except json.JSONDecodeError:
        raise HTTPException(status_code=500, detail="Invalid task data")

    return TaskResultResponse(
        task_id=task_id,
        status=data.get("status", "unknown"),
        result=data.get("result"),
        error=data.get("error")
    )


@app.delete("/task/{task_id}")
async def delete_task(task_id: str):
    """Удалить задачу"""

    key = f"task:{task_id}"

    try:
        redis_client.delete(key)
        print(f"🗑️ Task {task_id} deleted", flush=True)
    except Exception as e:
        print(f"⚠️ Failed to delete task {task_id}: {e}", flush=True)

    return {"status": "deleted"}


@app.post("/clear-cache")
async def clear_cache():
    """Clear all caches (admin endpoint)"""
    global cache_agent

    if not cache_agent:
        raise HTTPException(status_code=503, detail="System not initialized")

    cache_agent.products_cache.clear()
    cache_agent.categories_cache.clear()
    cache_agent.message_history_cache.clear()
    cache_agent.history.clear()

    print("🧹 Cache cleared via API", flush=True)

    return {"status": "ok", "message": "Cache cleared"}


@app.get("/tasks")
async def list_tasks():
    """List all pending/processing tasks (admin endpoint)"""

    try:
        keys = redis_client.keys("task:*")
        tasks = []

        for key in keys:
            task_id = key.split(":")[1]
            task_data = redis_client.get(key)
            if task_data:
                data = json.loads(task_data)
                tasks.append({
                    "task_id": task_id,
                    "status": data.get("status"),
                    "question": data.get("question", "")[:50]
                })

        return {"count": len(tasks), "tasks": tasks}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "app.main:app",
        host="0.0.0.0",
        port=8000,
        reload=False,
        log_level="info",
        timeout_keep_alive=30000
    )