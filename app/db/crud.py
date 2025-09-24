from __future__ import annotations

from datetime import date, datetime
from typing import Any, Dict, List, Optional
from uuid import UUID

from .database import fetch_all, fetch_one, upsert, delete


COLUMNS = "id, title, url, summary, source, category, publish_date, crawl_date, content_hash"


async def fetch_news(
    q: Optional[str] = None,
    category: Optional[str] = None,
    source: Optional[str] = None,
    from_date: Optional[date] = None,
    to_date: Optional[date] = None,
    limit: int = 20,
    offset: int = 0,
) -> List[Dict[str, Any]]:
    """
    Return a list of news rows as dicts with optional filters, ordered by publish_date then crawl_date.
    """
    from .database import get_supabase_client
    
    client = await get_supabase_client()
    query = client.table("news").select(COLUMNS)
    
    # Apply filters using method chaining
    if category:
        query = query.eq("category", category)
    if source:
        query = query.eq("source", source)
    if from_date:
        query = query.gte("publish_date", from_date.isoformat())
    if to_date:
        query = query.lte("publish_date", to_date.isoformat())
    
    # Apply ordering
    query = query.order("publish_date", desc=True).order("crawl_date", desc=True)
    
    # Apply pagination
    if offset:
        query = query.range(offset, offset + limit - 1)
    else:
        query = query.limit(limit)
    
    response = query.execute()
    items = response.data
    
    # Apply text search filter locally if needed
    if q:
        filtered_items = []
        q_lower = q.lower()
        for item in items:
            if (q_lower in (item.get("title", "") or "").lower() or 
                q_lower in (item.get("summary", "") or "").lower()):
                filtered_items.append(item)
        items = filtered_items
    
    return items


async def count_news(
    q: Optional[str] = None,
    category: Optional[str] = None,
    source: Optional[str] = None,
    from_date: Optional[date] = None,
    to_date: Optional[date] = None,
) -> int:
    """
    Return the total count for the given filters.
    """
    from .database import get_supabase_client
    
    client = await get_supabase_client()
    query = client.table("news").select("id", count="exact")
    
    # Apply filters using method chaining
    if category:
        query = query.eq("category", category)
    if source:
        query = query.eq("source", source)
    if from_date:
        query = query.gte("publish_date", from_date.isoformat())
    if to_date:
        query = query.lte("publish_date", to_date.isoformat())

    response = query.execute()
    
    # Get count from response
    if hasattr(response, 'count') and response.count is not None:
        total_count = response.count
    else:
        # Fallback if count not available
        items = response.data
        total_count = len(items)
    
    # Apply text search filter locally if needed
    if q and items:
        filtered_items = []
        q_lower = q.lower()
        for item in items:
            # Need to fetch full data for text search
            full_item = await fetch_one(
                table="news",
                filters={"id": item["id"]},
                select=COLUMNS
            )
            if full_item and (q_lower in (full_item.get("title", "") or "").lower() or
                q_lower in (full_item.get("summary", "") or "").lower()):
                filtered_items.append(item)
        return len(filtered_items)
    
    


async def fetch_news_by_id(news_id: UUID) -> Optional[Dict[str, Any]]:
    """
    Return a single news row by id as dict, or None if not found.
    """
    return await fetch_one(
        table="news",
        filters={"id": str(news_id)},
        select=COLUMNS
    )


async def upsert_news(item: Dict[str, Any]) -> str:
    """
    Insert or update a news row by unique URL constraint.
    Expects keys: url (str), title (str), summary (str|None), source (str),
                  category (str|None), publish_date (datetime|None),
                  crawl_date (datetime), content_hash (str|None)
    Returns the ID of the inserted/updated row.
    """
    # Ensure datetime objects are properly formatted for Supabase
    for key in ['publish_date', 'crawl_date']:
        if key in item and item[key] is not None and not isinstance(item[key], str):
            item[key] = item[key].isoformat()
    
    # Supabase handles upsert automatically with the upsert method
    result = await upsert(
        table="news",
        data=item
    )
    return result.get("id", "")


async def upsert_news_batch(items: List[Dict[str, Any]]) -> List[str]:
    """
    Batch insert or update multiple news rows by unique URL constraint.
    This is more efficient for processing many items at once.
    Returns the list of IDs of the inserted/updated rows.
    """
    # Ensure datetime objects are properly formatted for Supabase
    for item in items:
        for key in ['publish_date', 'crawl_date']:
            if key in item and item[key] is not None and not isinstance(item[key], str):
                item[key] = item[key].isoformat()
    
    # Supabase handles batch upsert automatically
    results = await upsert(
        table="news",
        data=items
    )
    
    # Extract IDs from results
    ids = [item.get("id", "") for item in results]
    return ids


async def delete_older_than(days: int = 30, by_publish_date: bool = False) -> int:
    """
    Delete old rows older than given days.
    - If by_publish_date is True, compare publish_date
    - Else compare crawl_date
    Returns deleted rows count.
    """
    # For simplicity, we'll fetch and delete items one by one
    # In production, you might want to use Supabase's RPC functions or bulk operations
    
    if by_publish_date:
        filters = {"publish_date.lt": f"now()-{days}days"}
    else:
        filters = {"crawl_date.lt": f"now()-{days}days"}
    
    deleted_items = await delete(
        table="news",
        filters=filters
    )
    
    return len(deleted_items)