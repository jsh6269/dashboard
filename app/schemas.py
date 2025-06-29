from typing import List, Optional

from pydantic import BaseModel


class DashboardItemCreate(BaseModel):
    title: str
    description: Optional[str] = None


class DashboardItemResponse(DashboardItemCreate):
    id: int
    created_at: str
    image_path: Optional[str] = None

    model_config = dict(from_attributes=True)


class SearchResults(BaseModel):
    results: List[DashboardItemResponse]
