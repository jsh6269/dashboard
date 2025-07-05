from fastapi.testclient import TestClient
from tests.helpers import prepare_test_app

app = prepare_test_app()
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
