from pydantic import BaseModel
from typing import Optional, List

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