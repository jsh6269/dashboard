import os
import shutil
import uuid
from contextlib import asynccontextmanager
from datetime import datetime
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

import orjson
import redis.asyncio as redis
from dependencies import parse_dashboard_form
from fastapi import Depends, FastAPI, HTTPException, Request, UploadFile
from fastapi.concurrency import run_in_threadpool
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from models import Base, DashboardItem
from schemas import DashboardItemCreate, DashboardItemResponse, SearchResults
from search_service import SearchService
from settings import Settings
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker

# 설정 불러오기
settings = Settings()
DATABASE_URL = settings.async_database_url

engine = create_async_engine(DATABASE_URL, pool_pre_ping=True)
AsyncSessionLocal = sessionmaker(engine, expire_on_commit=False, class_=AsyncSession)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Startup and shutdown events using FastAPI lifespan"""
    # Initialize Elasticsearch service
    app.state.search = SearchService(settings.es_host, settings.es_port)

    # Initialize Redis (optional in tests)
    try:
        app.state.redis = redis.Redis(
            host=settings.redis_host,
            port=settings.redis_port,
            decode_responses=False,
            socket_connect_timeout=0.1,
            socket_timeout=0.1,
        )
        # optional ping to verify connection quickly (non-blocking async)
        try:
            await app.state.redis.ping()
        except Exception:
            app.state.redis = None
    except Exception:
        # If Redis is not available, proceed without caching
        app.state.redis = None

    # Create tables (run sync via async engine)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    yield
    # Cleanup resources
    app.state.search.close()
    if getattr(app.state, "redis", None):
        try:
            await app.state.redis.close()
        except Exception:
            pass


app = FastAPI(lifespan=lifespan)

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Serving uploaded images
os.makedirs("uploads", exist_ok=True)
app.mount("/uploads", StaticFiles(directory="uploads"), name="uploads")


@app.post("/items", response_model=DashboardItemResponse)
async def create_item(
    request: Request,
    payload_and_image: tuple[DashboardItemCreate, UploadFile | None] = Depends(
        parse_dashboard_form
    ),
):
    payload, image = payload_and_image
    try:
        tz = ZoneInfo("Asia/Seoul")
    except ZoneInfoNotFoundError:
        from datetime import timedelta, timezone

        tz = timezone(timedelta(hours=9))
    now_seoul = datetime.now(tz)
    saved_path = None

    # Handle image saving
    if image is not None and getattr(image, "filename", None):
        os.makedirs("uploads", exist_ok=True)
        ext = os.path.splitext(image.filename)[1]
        unique_name = f"{uuid.uuid4().hex}{ext}"
        saved_path = f"uploads/{unique_name}"
        with open(saved_path, "wb") as buffer:
            shutil.copyfileobj(image.file, buffer)
        image.file.close()

    async with AsyncSessionLocal() as session:
        db_item = DashboardItem(
            title=payload.title,
            description=payload.description,
            image_path=saved_path,
            created_at=now_seoul,
        )
        session.add(db_item)
        await session.commit()
        await session.refresh(db_item)

        es_doc = {
            "title": payload.title,
            "description": payload.description,
            "created_at": now_seoul.isoformat(),
        }
        if saved_path:
            es_doc["image_path"] = saved_path
        # Elasticsearch 색인
        request.app.state.search.index_item(db_item.id, es_doc)

        return DashboardItemResponse(
            id=db_item.id,
            image_path=saved_path,
            **payload.model_dump(),
            created_at=db_item.created_at,
        )


@app.get("/search", response_model=SearchResults)
async def search_items(q: str, request: Request):
    """Elasticsearch에서 아이템 검색"""
    cache_key = f"search:{q}"
    redis_client = getattr(request.app.state, "redis", None)

    # Attempt to fetch from cache first
    if redis_client is not None:
        try:
            cached = await redis_client.get(cache_key)
        except Exception:
            cached = None
        if cached:
            try:
                cached_data = orjson.loads(cached)
                hits = [DashboardItemResponse(**item) for item in cached_data]
                return SearchResults(results=hits)
            except Exception:
                # Corrupted cache; ignore and proceed to fresh search
                pass

    # Cache miss -> query Elasticsearch
    try:
        result = await run_in_threadpool(request.app.state.search.search_items, q)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

    hits = []
    for hit in result:
        src = hit.get("_source", {})
        hits.append(DashboardItemResponse(**src, id=int(hit.get("_id", 0))))

    # Store in Redis cache for 15 seconds
    if redis_client is not None:
        try:
            await redis_client.set(
                cache_key,
                orjson.dumps([h.model_dump(mode="python") for h in hits]),
                ex=15,  # seconds
            )
        except Exception:
            pass

    return SearchResults(results=hits)
