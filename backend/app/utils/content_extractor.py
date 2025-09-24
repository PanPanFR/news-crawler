from __future__ import annotations

import logging
import asyncio
import os
from typing import Optional
import httpx
from bs4 import BeautifulSoup

from app.crawler.utils import fetch_html

logger = logging.getLogger(__name__)


async def extract_article_content(url: str) -> Optional[str]:
    """
    Extract article content from the given URL.
    """
    try:
        soup = await fetch_html(httpx.AsyncClient(), url)
        if not soup:
            return None

        # Try to find article content using various selectors
        selectors = [
            "article",           # Standard article tag
            ".article-body",     # Common class names
            ".post-content",     # Common class names 
            ".entry-content",    # Common class names
            ".content",          # Common class names
            "main",              # Main content area
            ".main-content",     # Common class names
            "p"                  # Paragraphs as fallback
        ]

        for selector in selectors:
            content = soup.select_one(selector)
            if content:
                # Extract text from the selected element
                paragraphs = content.find_all("p") if selector != "p" else content.find_all("p", recursive=False)
                if paragraphs:
                    # Return the first few paragraphs (first 1000 characters)
                    content_text = " ".join([p.get_text().strip() for p in paragraphs[:10]])
                    return content_text[:2000]  # Limit content length

        # If no specific content found, extract all paragraphs
        paragraphs = soup.find_all("p")
        if paragraphs:
            content_text = " ".join([p.get_text().strip() for p in paragraphs[:10]])
            return content_text[:2000]  # Limit content length

        return None

    except Exception as e:
        logger.error(f"Error extracting content from {url}: {e}")
        return None


async def summarize_with_llm(content: str, title: str) -> Optional[str]:
    """
    Call an LLM API to summarize the content.
    This is a template that needs to be configured with the actual LLM service.
    """
    # Get API configuration from environment
    llm_service = os.environ.get("LLM_SERVICE", "openai")
    api_key = os.environ.get("LLM_API_KEY")
    
    if not api_key:
        logger.error("LLM_API_KEY environment variable not set")
        return None

    try:
        if llm_service == "openai":
            # Example implementation for OpenAI
            import json
            
            headers = {
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json"
            }
            
            # Prepare the prompt
            prompt = f"Ringkas artikel berikut dalam 2-3 kalimat. Judul: {title}. Isi: {content}"

            payload = {
                "model": "gpt-3.5-turbo",  # or gpt-4 if preferred
                "messages": [
                    {"role": "user", "content": prompt}
                ],
                "max_tokens": 200,
                "temperature": 0.5
            }

            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.post(
                    "https://api.openai.com/v1/chat/completions",
                    headers=headers,
                    json=payload
                )
                
                if response.status_code == 200:
                    result = response.json()
                    summary = result["choices"][0]["message"]["content"].strip()
                    return summary
                else:
                    logger.error(f"LLM API error: {response.status_code} - {response.text}")
                    return None

        elif llm_service == "anthropic":
            # Example implementation for Anthropic Claude
            import json
            
            headers = {
                "x-api-key": api_key,
                "Content-Type": "application/json",
                "anthropic-version": "2023-06-01"
            }
            
            # Prepare the prompt
            prompt = f"Human: Ringkas artikel berikut dalam 2-3 kalimat. Judul: {title}. Isi: {content}\n\nAssistant:"

            payload = {
                "model": "claude-3-haiku-20240307",  # or another model
                "prompt": prompt,
                "max_tokens_to_sample": 200,
                "temperature": 0.5
            }

            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.post(
                    "https://api.anthropic.com/v1/complete",
                    headers=headers,
                    json=payload
                )
                
                if response.status_code == 200:
                    result = response.json()
                    summary = result["completion"].strip()
                    return summary
                else:
                    logger.error(f"LLM API error: {response.status_code} - {response.text}")
                    return None

        else:
            logger.error(f"Unsupported LLM service: {llm_service}")
            return None

    except Exception as e:
        logger.error(f"Error calling LLM API: {e}")
        return None