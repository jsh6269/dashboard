from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker


def prepare_test_app():
    """Create FastAPI test app with in-memory DB and DummySearch service."""
    import main
    from models import Base

    # In-memory SQLite engine
    engine = create_engine("sqlite:///./test.db", connect_args={"check_same_thread": False})
    TestingSession = sessionmaker(bind=engine, autocommit=False, autoflush=False)
    Base.metadata.create_all(engine)

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
                if q in doc["title"].lower() or q in (doc.get("description") or "").lower()
            ]

    # Monkeypatch DB and search
    main.engine = engine
    main.SessionLocal = TestingSession

    app = main.app
    app.state.search = DummySearch()

    return app 