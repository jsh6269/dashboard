from typing import Any, Dict, List

from elasticsearch import Elasticsearch


class SearchService:
    """Elasticsearch 관련 기능을 캡슐화한 서비스 클래스"""

    INDEX_NAME = "dashboard_items"

    def __init__(self, host: str = "localhost", port: str = "9200") -> None:
        self.es = Elasticsearch([f"http://{host}:{port}"])
        self._ensure_index()

    # private method
    def _ensure_index(self) -> None:
        """인덱스가 없으면 생성 (한국어 Nori + 영어 분석기 적용)"""
        if self.es.indices.exists(index=self.INDEX_NAME):
            return

        self.es.indices.create(
            index=self.INDEX_NAME,
            body={
                "settings": {
                    "analysis": {
                        "analyzer": {
                            "korean": {
                                "type": "custom",
                                "tokenizer": "nori_tokenizer",
                                "filter": ["lowercase"],
                            }
                        }
                    }
                },
                "mappings": {
                    "properties": {
                        "title": {
                            "type": "text",
                            "analyzer": "korean",
                            "fields": {"en": {"type": "text", "analyzer": "english"}},
                        },
                        "description": {
                            "type": "text",
                            "analyzer": "korean",
                            "fields": {"en": {"type": "text", "analyzer": "english"}},
                        },
                        "image_path": {"type": "keyword"},
                        "created_at": {"type": "date"},
                    }
                },
            },
        )

    # public method
    def index_item(self, item_id: int, doc: Dict[str, Any]) -> None:
        """문서 색인"""
        self.es.index(index=self.INDEX_NAME, id=item_id, document=doc)

    def search_items(self, query: str) -> List[Dict[str, Any]]:
        """query 문자열로 검색 결과(hit)를 리스트 형태로 반환"""
        result = self.es.search(
            index=self.INDEX_NAME,
            query={
                "multi_match": {
                    "query": query,
                    "fields": [
                        "title",
                        "description",
                        "title.en",
                        "description.en",
                    ],
                }
            },
        )
        return result.get("hits", {}).get("hits", [])

    def close(self) -> None:
        self.es.close()
