from typing import Any, Dict, List, Optional

from pydantic import BaseModel


class SearchResponse(BaseModel):
    status: str
    message: str
    search_id: Optional[str] = None
    result: Optional[Dict[str, Any]] = None
    error: Optional[str] = None


class SearchStatusResponse(BaseModel):
    search_id: str
    status: str
    message: str
    result: Optional[Dict[str, Any]] = None