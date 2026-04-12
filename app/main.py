"""Main application entry point - API only"""
import uuid
import atexit
from contextlib import asynccontextmanager
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
import redis
import json
import os

from app.config import MISTRAL_API_KEY
from app.cache import CacheAgent


cache_agent = None

# Redis клиент
redis_client = redis.Redis.from_url(
    os.getenv("REDIS_URL", "redis://localhost:6379"),
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
        return response


def cleanup_resources():
    global cache_agent
    if cache_agent:
        cache_agent.products_cache.clear()


atexit.register(cleanup_resources)


@asynccontextmanager
async def lifespan(app: FastAPI):
    global cache_agent
    print("🚀 Starting API...")
    cache_agent = CacheAgent(6)
    print("✅ API Ready")
    yield
    cleanup_resources()


app = FastAPI(lifespan=lifespan)

# CORS middleware
app.add_middleware(ForceCORSHeaderMiddleware)


@app.get("/health")
async def health_check():
    return {"status": "ok"}


@app.get("/status")
async def get_status():
    if not cache_agent:
        return {"status": "initializing"}
    return {"status": "ready", "stats": cache_agent.get_stats()}


@app.options("/{path:path}")
async def options_handler():
    return JSONResponse(content={"message": "OK"})


@app.post("/query")
async def create_task(request: QueryRequest):
    task_id = str(uuid.uuid4())
    print(f"📝 Creating task {task_id}")  # 👈 Лог

    try:
        redis_client.setex(
            f"task:{task_id}",
            3600,
            json.dumps({"status": "pending", "question": request.question})
        )
        print(f"✅ Task {task_id} saved to Redis")  # 👈 Лог
    except Exception as e:
        print(f"❌ Failed to save task: {e}")  # 👈 Лог
        raise

    return {"task_id": task_id, "status": "pending"}

@app.get("/task/{task_id}", response_model=TaskResultResponse)
async def get_task(task_id: str):
    """Проверить статус задачи в Redis"""
    task_data = redis_client.get(f"task:{task_id}")

    if not task_data:
        raise HTTPException(status_code=404, detail="Task not found")

    data = json.loads(task_data)

    return TaskResultResponse(
        task_id=task_id,
        status=data.get("status", "unknown"),
        result=data.get("result"),
        error=data.get("error")
    )


@app.delete("/task/{task_id}")
async def delete_task(task_id: str):
    redis_client.delete(f"task:{task_id}")
    return {"status": "deleted"}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("app.main:app", host="0.0.0.0", port=8000)