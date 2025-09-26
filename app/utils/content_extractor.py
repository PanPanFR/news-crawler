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
                paragraphs = content.find_all("p") if selector != "p" else content.find_all("p", recursive=False)
                if paragraphs:
                    content_text = " ".join([p.get_text().strip() for p in paragraphs[:10]])
                    return content_text[:2000]  # Limit content length

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
    Configured for Groq with gemma2-9b-it model by default.
    """
    llm_service = os.environ.get("LLM_SERVICE", "groq")
    api_key = os.environ.get("LLM_API_KEY")
    rate_delay_s = float(os.environ.get("LLM_RATE_LIMIT_DELAY", "2.0"))

    if not api_key:
        logger.error("LLM_API_KEY environment variable not set")
        return None

    try:

        if llm_service == "groq":
            headers = {
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json",
            }

            prompt = (
                "Ringkas artikel berikut dalam 2-3 kalimat dengan bahasa Indonesia yang baku.\n"
                f"Judul: {title}\n"
                f"Isi: {content}"
            )

            payload = {
                "model": "gemma2-9b-it",
                "messages": [{"role": "user", "content": prompt}],
                "max_tokens": 200,
                "temperature": 0.5,
                "top_p": 0.9,
            }

            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.post(
                    "https://api.groq.com/openai/v1/chat/completions",
                    headers=headers,
                    json=payload,
                )

            if response.status_code == 200:
                data = response.json()
                try:
                    return data["choices"][0]["message"]["content"].strip()
                except Exception:
                    logger.error("Unexpected Groq response format: %s", data)
                    return None
            else:
                logger.error("Groq API error: %s - %s", response.status_code, response.text)
                return None

        elif llm_service == "openai":
            headers = {
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json",
            }
            prompt = (
                "Ringkas artikel berikut dalam 2-3 kalimat.\n"
                f"Judul: {title}\n"
                f"Isi: {content}"
            )
            payload = {
                "model": "gpt-3.5-turbo",
                "messages": [{"role": "user", "content": prompt}],
                "max_tokens": 200,
                "temperature": 0.5,
            }
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.post(
                    "https://api.openai.com/v1/chat/completions",
                    headers=headers,
                    json=payload,
                )
            if response.status_code == 200:
                data = response.json()
                try:
                    return data["choices"][0]["message"]["content"].strip()
                except Exception:
                    logger.error("Unexpected OpenAI response format: %s", data)
                    return None
            else:
                logger.error("OpenAI API error: %s - %s", response.status_code, response.text)
                return None

        elif llm_service == "anthropic":
            headers = {
                "x-api-key": api_key,
                "Content-Type": "application/json",
                "anthropic-version": "2023-06-01",
            }
            prompt = (
                "Human: Ringkas artikel berikut dalam 2-3 kalimat.\n"
                f"Judul: {title}\n"
                f"Isi: {content}\n\n"
                "Assistant:"
            )
            payload = {
                "model": "claude-3-haiku-20240307",
                "prompt": prompt,
                "max_tokens_to_sample": 200,
                "temperature": 0.5,
            }
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.post(
                    "https://api.anthropic.com/v1/complete",
                    headers=headers,
                    json=payload,
                )
            if response.status_code == 200:
                data = response.json()
                try:
                    return data["completion"].strip()
                except Exception:
                    logger.error("Unexpected Anthropic response format: %s", data)
                    return None
            else:
                logger.error("Anthropic API error: %s - %s", response.status_code, response.text)
                return None

        else:
            logger.error(f"Unsupported LLM service: {llm_service}")
            return None

    except Exception as e:
        logger.error(f"Error calling LLM API: {e}")
        return None