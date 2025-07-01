import os
import shutil
import uuid
from contextlib import asynccontextmanager
from datetime import datetime
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from fastapi import Depends, FastAPI, HTTPException, UploadFile, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from dependencies import parse_dashboard_form
from models import Base, DashboardItem
from schemas import DashboardItemCreate, DashboardItemResponse, SearchResults
from search_service import SearchService
from settings import Settings

# 설정 불러오기
settings = Settings()
DATABASE_URL = settings.database_url

engine = create_engine(DATABASE_URL, pool_pre_ping=True)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Startup and shutdown events using FastAPI lifespan"""
    app.state.search = SearchService(settings.es_host, settings.es_port)
    Base.metadata.create_all(bind=engine)

    yield
    app.state.search.close()


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
    try:
        result = request.app.state.search.search_items(q)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

    hits = []
    for hit in result:
        src = hit.get("_source", {})
        hits.append(DashboardItemResponse(**src, id=int(hit.get("_id", 0))))

    return SearchResults(results=hits)
