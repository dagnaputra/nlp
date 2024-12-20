from pydantic import BaseModel
from typing import List, Dict, Any

class SearchResult(BaseModel):
    id: str
    event_original: str
class SearchResponse(BaseModel):
    request_id: str
    results: List[SearchResult]
    aggregations: Dict[str,Any]

class EnrichResponse(BaseModel):
    request_id: str
    enriched_response: str

