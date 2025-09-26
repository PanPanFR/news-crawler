from __future__ import annotations

import os
from typing import Any, Dict, List, Optional
from dotenv import load_dotenv
from supabase import create_client, Client

load_dotenv()

_supabase: Optional[Client] = None


def _get_supabase_client() -> Client:
    """
    Create and return a Supabase client.
    Raises RuntimeError if required environment variables are missing.
    """
    global _supabase
    if _supabase is not None:
        return _supabase

    url: str = os.environ.get("SUPABASE_URL", "")
    key: str = os.environ.get("SUPABASE_KEY", "")

    if not url or not key:
        raise RuntimeError("SUPABASE_URL and SUPABASE_KEY must be configured")

    _supabase = create_client(url, key)
    return _supabase


async def get_supabase_client() -> Client:
    """
    Return the Supabase client.
    """
    return _get_supabase_client()


async def close_client() -> None:
    """
    Close the Supabase client connection.
    """
    global _supabase
    if _supabase is not None:
        _supabase = None


async def fetch_all(table: str, filters: Optional[Dict[str, Any]] = None, 
                   select: str = "*", order_by: Optional[str] = None, 
                   limit: Optional[int] = None, offset: Optional[int] = None) -> List[Dict[str, Any]]:
    """
    Fetch all records from a table with optional filters.
    """
    client = _get_supabase_client()
    query = client.table(table).select(select)
    
    if filters:
        for key, value in filters.items():
            query = query.eq(key, value)
    
    if order_by:
        query = query.order(order_by)
    
    if limit:
        query = query.limit(limit)
    
    if offset:
        query = query.range(offset, offset + limit - 1 if limit else offset)
    
    response = query.execute()
    return response.data


async def fetch_one(table: str, filters: Dict[str, Any], select: str = "*") -> Optional[Dict[str, Any]]:
    """
    Fetch a single record from a table with filters.
    """
    client = _get_supabase_client()
    query = client.table(table).select(select)
    
    for key, value in filters.items():
        query = query.eq(key, value)
    
    response = query.limit(1).execute()
    return response.data[0] if response.data else None


async def insert(table: str, data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Insert a record into a table.
    """
    client = _get_supabase_client()
    response = client.table(table).insert(data).execute()
    return response.data[0] if response.data else {}


async def upsert(table: str, data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Upsert a record into a table.
    """
    client = _get_supabase_client()
    response = client.table(table).upsert(data).execute()
    return response.data[0] if response.data else {}


async def update(table: str, filters: Dict[str, Any], data: Dict[str, Any]) -> List[Dict[str, Any]]:
    """
    Update records in a table with filters.
    """
    client = _get_supabase_client()
    builder = client.table(table).update(data)

    for key, value in filters.items():
        builder = builder.eq(key, value)

    response = builder.execute()
    return response.data


async def delete(table: str, filters: Dict[str, Any]) -> List[Dict[str, Any]]:
    """
    Delete records from a table with filters.
    """
    client = _get_supabase_client()
    builder = client.table(table).delete()

    for key, value in filters.items():
        builder = builder.eq(key, value)

    response = builder.execute()
    return response.data