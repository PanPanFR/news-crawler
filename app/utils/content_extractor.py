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
    \"\"\"\n    Call an LLM API to summarize the content.\n    This is configured for Groq with gemma2-9b-it model as specified in konteks.\n    \"\"\"\n    # Get API configuration from environment\n    llm_service = os.environ.get(\"LLM_SERVICE\", \"groq\")\n    api_key = os.environ.get(\"LLM_API_KEY\")\n    \n    if not api_key:\n        logger.error(\"LLM_API_KEY environment variable not set\")\n        return None

    try:\n        if llm_service == \"groq\":\n            # Implementation for Groq API with gemma2-9b-it model\n            import json\n            \n            headers = {\n                \"Authorization\": f\"Bearer {api_key}\",\n                \"Content-Type\": \"application/json\"\n            }\n            \n            # Prepare the prompt for Indonesian news summarization\n            prompt = f\"Ringkas artikel berikut dalam 2-3 kalimat dengan bahasa Indonesia yang baku. Judul: {title}. Isi: {content}\"

            payload = {\n                \"model\": \"gemma2-9b-it\",  # Using the model specified in konteks\n                \"messages\": [\n                    {\"role\": \"user\", \"content\": prompt}\n                ],\n                \"max_tokens\": 200,\n                \"temperature\": 0.5,\n                \"top_p\": 0.9\n            }

            async with httpx.AsyncClient(timeout=30.0) as client:\n                response = await client.post(\n                    \"https://api.groq.com/openai/v1/chat/completions\",\n                    headers=headers,\n                    json=payload\n                )\n                \n                if response.status_code == 200:\n                    result = response.json()\n                    summary = result[\"choices\"][0][\"message\"][\"content\"].strip()\n                    return summary\n                else:\n                    logger.error(f\"Groq API error: {response.status_code} - {response.text}\")\n                    return None

        elif llm_service == \"openai\":\n            # Fallback implementation for OpenAI\n            import json\n            \n            headers = {\n                \"Authorization\": f\"Bearer {api_key}\",\n                \"Content-Type\": \"application/json\"\n            }\n            \n            # Prepare the prompt\n            prompt = f\"Ringkas artikel berikut dalam 2-3 kalimat. Judul: {title}. Isi: {content}\"

            payload = {\n                \"model\": \"gpt-3.5-turbo\",  # or gpt-4 if preferred\n                \"messages\": [\n                    {\"role\": \"user\", \"content\": prompt}\n                ],\n                \"max_tokens\": 200,\n                \"temperature\": 0.5\n            }

            async with httpx.AsyncClient(timeout=30.0) as client:\n                response = await client.post(\n                    \"https://api.openai.com/v1/chat/completions\",\n                    headers=headers,\n                    json=payload\n                )\n                \n                if response.status_code == 200:\n                    result = response.json()\n                    summary = result[\"choices\"][0][\"message\"][\"content\"].strip()\n                    return summary\n                else:\n                    logger.error(f\"LLM API error: {response.status_code} - {response.text}\")\n                    return None

        elif llm_service == \"anthropic\":\n            # Fallback implementation for Anthropic Claude\n            import json\n            \n            headers = {\n                \"x-api-key\": api_key,\n                \"Content-Type\": \"application/json\",\n                \"anthropic-version\": \"2023-06-01\"\n            }\n            \n            # Prepare the prompt\n            prompt = f\"Human: Ringkas artikel berikut dalam 2-3 kalimat. Judul: {title}. Isi: {content}\\n\\nAssistant:\"

            payload = {\n                \"model\": \"claude-3-haiku-20240307\",  # or another model\n                \"prompt\": prompt,\n                \"max_tokens_to_sample\": 200,\n                \"temperature\": 0.5\n            }

            async with httpx.AsyncClient(timeout=30.0) as client:\n                response = await client.post(\n                    \"https://api.anthropic.com/v1/complete\",\n                    headers=headers,\n                    json=payload\n                )\n                \n                if response.status_code == 200:\n                    result = response.json()\n                    summary = result[\"completion\"].strip()\n                    return summary\n                else:\n                    logger.error(f\"LLM API error: {response.status_code} - {response.text}\")\n                    return None

        else:\n            logger.error(f\"Unsupported LLM service: {llm_service}\")\n            return None

    except Exception as e:\n        logger.error(f\"Error calling LLM API: {e}\")\n        return None