from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker


def prepare_test_app():
    """Create FastAPI test app with in-memory DB and DummySearch service."""
    import main
    from models import Base

    # In-memory SQLite async engine
    engine = create_async_engine("sqlite+aiosqlite:///./test.db")
    TestingSession = sessionmaker(engine, expire_on_commit=False, class_=AsyncSession)

    # Create tables
    import asyncio

    async def _create_schema():
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)

    asyncio.get_event_loop().run_until_complete(_create_schema())

    # Dummy search service replacing Elasticsearch
    class DummySearch:
        def __init__(self):
            self.store = {}

        def index_item(self, item_id: int, doc: dict):
            self.store[item_id] = doc

        def search_items(self, query: str):
            q = query.lower()
            return [
                {"_id": _id, "_source": doc}
                for _id, doc in self.store.items()
                if q in doc["title"].lower()
                or q in (doc.get("description") or "").lower()
            ]

    # Monkeypatch DB and search
    main.engine = engine
    main.AsyncSessionLocal = TestingSession

    app = main.app
    app.state.search = DummySearch()

    return app
