# Backend Design Documentation for News Crawler with AI Summarizer

## Overview
This document describes the architecture and implementation of the news crawler backend with AI-powered summarization. The system is optimized for deployment on Render with proper rate limiting to comply with both Render's infrastructure limits and external API quotas.

## Architecture & Optimized Workflow
The following is the new workflow that cleanly separates each task, making it more resilient, efficient, and scalable.

Visual Flow:
```
[Crawler] -> [Database PostgreSQL] -> [Prioritization Script] -> [Priority Queue REDIS] -> [Summarizer Worker] -> [Database PostgreSQL (Update)]
```

### Phase 1: Ingestion - Crawler/Scraper 🏃‍♂️
Single Task: The crawler's job every 40 minutes is to fetch ~300 news articles (title, URL, raw content, source, etc.).

Save to Database: After obtaining data, immediately INSERT into the public.news table in Supabase. Leave the summary column as NULL.

Complete: The crawler process is done here. It doesn't need to know anything about summarization. This makes the scraping process very fast and isolated.

### Phase 2: Priority & Queue - The System's Brain with Redis 🧠
This is the smartest part of the new system. We won't summarize all news, only what's important.

Priority Script: Create a separate script (e.g., prioritizer.py) that runs after the crawler completes.

Fetch New News: The script queries Supabase: `SELECT id, title, source, publish_date FROM public.news WHERE summary IS NULL;`.

Score (Scoring): For each news article, assign a priority score. Example simple scoring:

- Source Score: If source is a major media (e.g., Kompas, Detik, CNN Indonesia), give +20 points.
- Title Score: If title contains trending keywords (e.g., "government", "stocks", "technology", "election"), give +10 points per keyword.
- Time Score: Newer news can be given a slight bonus.

Add to Priority Queue Redis: Instead of summarizing immediately, the script adds news IDs to a Redis Sorted Set.

Command: `ZADD news_summarization_queue <PRIORITY_SCORE> <NEWS_ID>`

Example: `ZADD news_summarization_queue 30 "uuid-news-A"` (News A has score 30)

`ZADD news_summarization_queue 10 "uuid-news-B"` (News B has score 10)

### Phase 3: Execution - Summarizer Worker 🤖
This is a script running continuously in the background. Its task is to execute summaries based on the Redis queue.

Fetch Task from Queue: The worker gets the highest-score news from Redis.

Command: `ZPOPMAX news_summarization_queue` (Take and remove 1 member with highest score).

Fetch Complete Content: With the NEWS_ID from Redis, the worker queries Supabase to retrieve the complete article content.

Call LLM API: The worker calls the LLM API to summarize content. Rate limiting is implemented with 2-second delays between requests. The worker is the only component that "talks" to the LLM API.

Update Database: After obtaining the summary, the worker UPDATEs the row in Supabase, filling the summary column.

Failure Management (Retry): If the API fails, the worker can add the NEWS_ID back to the Redis queue, perhaps with a slightly lower score or to a special "failed" queue to try later.

Repeat: The worker returns to Step 1 to get the next task.

### Phase 4: Management - Cache & Cleanup 🧹
Caching: The Supabase database acts as a cache. Since the worker only takes news with summary IS NULL, already-summarized news will never be processed again. This meets requirement number 3.

Clean Up: Create a cron job that runs weekly or monthly to clean up old summaries if needed.

Example SQL: `UPDATE public.news SET summary = NULL WHERE publish_date < NOW() - INTERVAL '6 months';`

This will clear the summary column for news older than 6 months, saving space and allowing those news to be re-summarized in the future if newer LLM models become available.

## Configuration and Constraints for Render Deployment
- Cron Job: */40 * * * * (Every 40 minutes)
- API Model: gemma2-9b-it on Groq
- API Limits: 14,400 requests per day (RPD), 30 requests per minute (RPM)
- Request Delay: 2-second delay (time.sleep(2)) to maintain rate at 30 requests per minute
- Processing Speed: Capable of completing 1 batch (300 news) in 10 minutes

## Why Redis is Very Useful Here?
Burst Handling: The crawler "throws" 300 news articles at once. Redis easily absorbs all of them into the queue, while the worker continues working calmly and steadily according to the API rate limit.

Priority Queue: With Sorted Set, you ensure the worker always works on the most important news first. Regular news will be summarized only if there are no more important news in the queue.

Process Decoupling: Crawler, prioritizer, and worker are three separate processes running independently. If the worker dies, the queue in Redis stays safe and the crawler can still run. The system becomes much more stable.

## API Endpoints
- `GET /api/news`: List news with filters and pagination
- `GET /api/news/{id}`: Get specific news item
- `POST /api/news/crawl`: Trigger manual crawling
- `POST /api/news/prioritize`: Trigger prioritization of unsummarized news
- `POST /api/news/summarize`: Trigger summarization batch
- `POST /api/news/cleanup`: Trigger data cleanup
- `POST /trigger-crawl`: Cron job endpoint to start crawling and prioritization

## Deployment on Render
The system is designed with three main services on Render:
- Web Service: Serves the API and handles the cron job trigger
- Redis Service: Manages the priority queue
- Worker Service: Processes the summarization queue in the background