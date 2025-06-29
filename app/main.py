import os
import shutil
import uuid
from contextlib import asynccontextmanager
from datetime import datetime
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from elasticsearch import Elasticsearch
from fastapi import Depends, FastAPI, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from .dependencies import parse_dashboard_form
from .models import Base, DashboardItem
from .schemas import DashboardItemCreate, DashboardItemResponse, SearchResults

# 환경 변수 읽기
DB_HOST = os.getenv("DB_HOST", "localhost")
DB_USER = os.getenv("DB_USER", "root")
DB_PASSWORD = os.getenv("DB_PASSWORD", "password")
DB_NAME = os.getenv("DB_NAME", "dashboard_db")
ES_HOST = os.getenv("ES_HOST", "localhost")
ES_PORT = os.getenv("ES_PORT", "9200")

DATABASE_URL = f"mysql+pymysql://{DB_USER}:{DB_PASSWORD}@{DB_HOST}/{DB_NAME}"

engine = create_engine(DATABASE_URL, pool_pre_ping=True)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Startup and shutdown events using FastAPI lifespan"""
    # Startup logic
    Base.metadata.create_all(bind=engine)
    if not es.indices.exists(index="dashboard_items"):
        es.indices.create(index="dashboard_items")
    yield
    # (Optional) Shutdown logic


app = FastAPI(lifespan=lifespan)

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Elasticsearch 클라이언트
es = Elasticsearch([f"http://{ES_HOST}:{ES_PORT}"])

# Serving uploaded images
os.makedirs("uploads", exist_ok=True)
app.mount("/uploads", StaticFiles(directory="uploads"), name="uploads")


@app.post("/items", response_model=DashboardItemResponse)
async def create_item(
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
    now_seoul = datetime.now(tz).isoformat()
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

    with SessionLocal() as session:
        db_item = DashboardItem(
            title=payload.title,
            description=payload.description,
            image_path=saved_path,
            created_at=now_seoul,
        )
        session.add(db_item)
        session.commit()
        session.refresh(db_item)

        es_doc = {
            "title": payload.title,
            "description": payload.description,
            "created_at": now_seoul,
        }
        if saved_path:
            es_doc["image_path"] = saved_path
        es.index(index="dashboard_items", id=db_item.id, document=es_doc)

        return DashboardItemResponse(
            id=db_item.id,
            image_path=saved_path,
            **payload.model_dump(),
            created_at=now_seoul,
        )


@app.get("/search", response_model=SearchResults)
async def search_items(q: str):
    """Elasticsearch에서 아이템 검색"""
    try:
        result = es.search(
            index="dashboard_items",
            query={
                "multi_match": {
                    "query": q,
                    "fields": ["title", "description"],
                }
            },
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

    hits = []
    for hit in result.get("hits", {}).get("hits", []):
        src = hit.get("_source", {})
        hits.append(DashboardItemResponse(**src, id=int(hit.get("_id", 0))))

    return SearchResults(results=hits)
