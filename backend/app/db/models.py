from __future__ import annotations

from datetime import datetime
from typing import Optional
from pydantic import BaseModel, HttpUrl


class NewsItem(BaseModel):
    id: str
    title: str
    url: HttpUrl
    summary: Optional[str] = None
    source: str
    category: Optional[str] = None
    publish_date: Optional[datetime] = None
    crawl_date: datetime
    content_hash: Optional[str] = None


class NewsUpsert(BaseModel):
    title: str
    url: HttpUrl
    summary: Optional[str] = None
    source: str
    category: Optional[str] = None
    publish_date: Optional[datetime] = None
    crawl_date: datetime
    content_hash: Optional[str] = None