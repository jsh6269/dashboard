import types

from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker


def _prepare_test_app():
    """Create in-memory SQLite engine and monkeypatch app.* for isolated tests."""
    import app.main as main
    from app.models import Base  # relative import within package

    # 1. SQLite in-memory DB
    engine = create_engine(
        "sqlite:///./test.db", connect_args={"check_same_thread": False}
    )
    TestingSession = sessionmaker(bind=engine, autocommit=False, autoflush=False)
    Base.metadata.create_all(engine)

    # 2. Dummy Elasticsearch client
    class DummyES:
        def __init__(self):
            self.store = {}

        def index(self, index: str, id: int, document: dict):
            self.store.setdefault(index, {})[id] = document

        def search(self, index: str, query: dict):
            keyword = query["multi_match"]["query"].lower()
            hits = []
            for _id, doc in self.store.get(index, {}).items():
                if (
                    keyword in doc["title"].lower()
                    or (doc.get("description") or "").lower().find(keyword) != -1
                ):
                    hits.append({"_id": _id, "_source": doc})
            return {"hits": {"hits": hits}}

        def indices(self):  # dummy method for es.indices.exists
            return types.SimpleNamespace(exists=lambda index: True)

    # 3. Monkeypatch
    main.engine = engine
    main.SessionLocal = TestingSession
    main.es = DummyES()

    return main.app


app = _prepare_test_app()
client = TestClient(app)


def test_docs_available():
    resp = client.get("/openapi.json")
    assert resp.status_code == 200


def test_create_and_search_item():
    resp = client.post("/items", data={"title": "pytest", "description": "demo"})
    assert resp.status_code == 200
    created = resp.json()

    search = client.get("/search", params={"q": "pytest"})
    assert search.status_code == 200
    assert any(item["id"] == created["id"] for item in search.json()["results"])
