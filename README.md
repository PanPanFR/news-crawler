# News Crawler with AI Summarization

A scalable news crawler system with AI-powered summarization and Redis-backed priority queues and background processing. Deployable on Hugging Face Spaces, Docker, Railway, Render, or any platform that runs FastAPI + Python.

## 🚀 Features

- **Multi-source News Crawling**: Supports RSS feeds and HTML fallback scraping
- **AI-Powered Summarization**: Uses Groq API with gemma2-9b-it model for news summarization
- **Priority Queue System**: Implements Redis sorted sets for prioritized summarization
- **Concurrent Processing**: Configurable concurrency for efficient crawling
- **Database Integration**: Uses Supabase (PostgreSQL) for data storage
- **RESTful API**: FastAPI-powered endpoints for news retrieval and management
- **Automated Scheduling**: CLI tools for scheduled crawling and prioritization
- **Duplicate Detection**: Content hash-based deduplication
- **Rate Limiting**: Built-in rate limiting to comply with API quotas (2s delay)
- **Portable Deployment**: Works on Hugging Face Spaces, Docker, Railway, Render, or any FastAPI-capable platform
- **Error Handling**: Robust error handling and logging
- **Retry Mechanism**: Failed summarizations are retried with exponential backoff

## 📋 Table of Contents

- [Prerequisites](#prerequisites)
- [Installation](#installation)
- [Configuration](#configuration)
- [Database Setup](#database-setup)
- [Running the Application](#running-the-application)
- [API Endpoints](#api-endpoints)
- [CLI Commands](#cli-commands)
- [Deployment](#deployment)
- [Project Structure](#project-structure)
- [Supported News Sources](#supported-news-sources)
- [Contributing](#contributing)

## Code Cleanup Policy

- Configuration and usage are documented here instead of inline comments. Refer to files such as [app/main.py](app/main.py), [app/api/routes.py](app/api/routes.py), and [app/db/database.py](app/db/database.py) for current implementations without comments.

## 🔧 Prerequisites

- Python 3.11+ (recommended)
- Supabase account and project
- Git (optional, for deployment)

## 📦 Installation

1. **Clone the repository** (if applicable):
   ```bash
   git clone <repository-url>
   cd news-crawler/backend
   ```

2. **Create and activate virtual environment**:
   ```bash
   python -m venv .venv
   
   # Windows
   .venv\Scripts\activate
   
   # macOS/Linux
   source .venv/bin/activate
   ```

3. **Install dependencies**:
   ```bash
   pip install --upgrade pip
   pip install -r requirements.txt
   ```

## ⚙️ Configuration

### Environment Variables

Create a `.env` file in the backend directory with the following variables:

```env
SUPABASE_URL=https://your-project-ref.supabase.co
SUPABASE_KEY=your-anon-key-here
```

### Getting Supabase Credentials

1. Go to your Supabase project dashboard
2. Navigate to **Settings** → **API**
3. Copy the **Project URL** to `SUPABASE_URL`
4. Copy the **anon** key from **Project API keys** to `SUPABASE_KEY`

## 🗄️ Database Setup

1. **Create the database schema** by running the SQL commands in [`skema.md`](skema.md)
2. **Enable required extensions**:
   ```sql
   CREATE EXTENSION IF NOT EXISTS pgcrypto;
   CREATE EXTENSION IF NOT EXISTS pg_trgm;
   ```
3. **Create the news table** and indexes as specified in the schema file

## 🚀 Running the Application

### Local Development

Start the FastAPI server:

```bash
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```

The API will be available at:
- **Base URL**: http://localhost:8000
- **API Documentation**: http://localhost:8000/docs
- **Health Check**: http://localhost:8000/health

## 📡 API Endpoints

### Core Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| `GET` | `/` | Service status and version |
| `GET` | `/health` | Health check |
| `GET` | `/api/news` | List news with filters and pagination |
| `GET` | `/api/news/{id}` | Get specific news item |
| `POST` | `/api/news/crawl` | Trigger manual crawling |
| `POST` | `/api/news/prioritize` | Trigger prioritization of unsummarized news |
| `POST` | `/api/news/summarize` | Trigger summarization batch |
| `POST` | `/api/news/cleanup` | Trigger data cleanup |
| `POST` | `/api/news/cleanup-placeholders` | Delete rows with placeholder summaries |
| `POST` | `/trigger-crawl` | Cron job endpoint to start crawling and prioritization |

### Query Parameters

#### `/api/news` (List News)
- `q`: Full-text search on title/summary
- `category`: Filter by category
- `source`: Filter by source domain
- `from_date`: Start date filter (YYYY-MM-DD)
- `to_date`: End date filter (YYYY-MM-DD)
- `limit`: Items per page (1-50, default: 20)
- `offset`: Pagination offset (default: 0)

#### `/api/news/crawl` (Manual Crawl)
- `concurrency`: Max concurrent domains (1-10, default: 3)
- `domains`: Comma-separated domain list (optional)

#### `/api/news/prioritize` (Trigger Prioritization)
- No parameters required

#### `/api/news/summarize` (Trigger Summarization)
- `concurrency`: Max concurrent summarization tasks (1-5, default: 1)
- `batch`: Run in batch mode (true) or continuous mode (false, default: true)

#### `/api/news/cleanup` (Data Cleanup)
- `days`: Delete items older than N days (1-365, default: 30)
- `by_publish`: Use publish_date instead of crawl_date (default: false)

### Example API Calls

```bash
# Get latest news
curl "http://localhost:8000/api/news?limit=10"

# Search for specific topics
curl "http://localhost:8000/api/news?q=ekonomi&category=bisnis"

# Trigger crawl for specific domains
curl -X POST "http://localhost:8000/api/news/crawl?domains=kompas.com,detik.com&concurrency=2"

# Cleanup old data
curl -X POST "http://localhost:8000/api/news/cleanup?days=30&by_publish=true"
```

## 🖥️ CLI Commands

The application provides CLI tools for scheduled operations:

### Crawling

```bash
# Crawl all default sources
python -m app.scheduler crawl --concurrency 3

# Crawl specific domains
python -m app.scheduler crawl --domains kompas.com,detik.com --concurrency 2
```

### News Prioritization

```bash
# Run prioritizer to score and queue unsummarized news
python -m app.scheduler prioritize
```

### News Summarization

```bash
# Process summarization queue in batch mode (processes available items then exits)
python -m app.scheduler summarize --concurrency 1 --batch

# Run summarization worker continuously (should be used as a background process)
python -m app.scheduler summarize --concurrency 1 --continuous
```

### Data Cleanup

```bash
# Delete data older than 30 days (by crawl_date)
python -m app.scheduler cleanup --days 30

# Delete data older than 30 days (by publish_date)
python -m app.scheduler cleanup --days 30 --by-publish
```

## 🌐 Deployment

This project is platform-agnostic and can run anywhere FastAPI + Python is supported.

Supported environments:
- Hugging Face Spaces (recommended for this repository). See [README_HUGGINGFACE.md](README_HUGGINGFACE.md) for step-by-step deployment.
- Docker on any VM or cloud provider.
- PaaS platforms such as Railway or Render.
- Bare metal or on-prem servers.

Quick start (generic):
```bash
pip install -r requirements.txt
uvicorn app.main:app --host 0.0.0.0 --port 8000
```

Background worker (optional, for summarization queue):
```bash
python -m app.workers.summarizer_worker
```

Environment variables (common across platforms):
- `SUPABASE_URL`: Supabase project URL
- `SUPABASE_KEY`: Supabase anon key
- `REDIS_HOST`: Redis host
- `REDIS_PORT`: Redis port
- `REDIS_PASSWORD`: Redis password
- `LLM_API_KEY`: Groq/OpenAI/Anthropic API key
- `LLM_SERVICE`: 'groq' (default), or 'openai' / 'anthropic'
- `LLM_RATE_LIMIT_DELAY`: Delay between API requests (default: 2.0 seconds)
- `MAX_RETRY_ATTEMPTS`: Max attempts to summarize news (default: 3)
- `FAILED_QUEUE_TTL`: Time to live for failed queue items (default: 3600 seconds)

Scheduling (optional):
- Use any cron/scheduler available on your platform to trigger crawling:
  ```bash
  curl -X POST https://your-service-host/trigger-crawl
  ```

## 📁 Project Structure

```
/
├── app/
│   ├── __init__.py
│   ├── main.py
│   ├── startup.py
│   ├── scheduler.py
│   ├── api/
│   │   └── routes.py
│   ├── crawler/
│   │   ├── spider.py
│   │   └── utils.py
│   ├── db/
│   │   ├── database.py
│   │   ├── models.py
│   │   ├── crud.py
│   │   └── redis_client.py
│   ├── utils/
│   │   └── content_extractor.py
│   └── workers/
│       └── summarizer_worker.py
├── app.py
├── Dockerfile
├── requirements.txt
├── README.md
├── README_HUGGINGFACE.md
├── tools/
│   └── remove_comments.py
└── .env
```

## 📰 Supported News Sources

The crawler supports the following news sources with RSS feeds:

### Indonesian Sources
- **kompas.com** - Leading Indonesian news portal
- **detik.com** - Popular Indonesian news website
- **tempo.co** - Indonesian news magazine
- **antaranews.com** - Indonesian national news agency
- **cnbcindonesia.com** - Indonesian business news
- **republika.co.id** - Indonesian news portal
- **katadata.co.id** - Indonesian data journalism

### International Sources
- **bbc.com** - BBC World News
- **theguardian.com** - The Guardian International
- **nytimes.com** - New York Times World News

## 🔧 Technical Details

### Crawling Strategy
1. **RSS First**: Attempts to fetch RSS feeds for structured data
2. **HTML Fallback**: Falls back to HTML scraping if RSS unavailable
3. **Rate Limiting**: Respects source websites with configurable delays
4. **Deduplication**: Uses content hashing to prevent duplicates
5. **Concurrent Processing**: Processes multiple sources simultaneously

### Data Processing
- **Content Cleaning**: Removes HTML tags and normalizes text
- **Date Parsing**: Handles various date formats from different sources
- **Category Extraction**: Extracts categories from RSS tags when available
- **URL Normalization**: Standardizes URLs for consistency

### Performance Optimizations
- **Connection Pooling**: Reuses HTTP connections for efficiency
- **Async Processing**: Non-blocking I/O for better performance
- **Batch Operations**: Groups database operations for efficiency
- **Selective Indexing**: Database indexes for common query patterns

## 🐛 Troubleshooting

### Common Issues

1. **Database Connection Error**:
   ```
   SUPABASE_URL and SUPABASE_KEY must be configured
   ```
   - Ensure `.env` file exists with correct Supabase credentials

2. **No Data After Crawling**:
   - Check crawler logs for errors
   - Verify database schema is created
   - Test with specific domains: `python -m app.scheduler crawl --domains kompas.com`

3. **Slow Query Performance**:
   - Ensure database indexes are created (see `skema.md`)
   - Consider using full-text search features in Supabase

4. **Rate Limiting Issues**:
   - Reduce concurrency: `--concurrency 1`
   - Increase delays in rate limiter configuration

### Architecture

The system follows a microservices architecture with the following components:

```
[Crawler] -> [Database PostgreSQL] -> [Skrip Prioritas] -> [Antrian Prioritas REDIS] -> [Worker Summarizer] -> [Database PostgreSQL (Update)]
```

- **Crawler**: Extracts news data and stores with NULL summary field
- **Database**: Stores news articles with summaries
- **Prioritizer**: Scores and queues unsummarized news items by priority
- **Redis Queue**: Manages prioritized news for summarization
- **Summarizer Worker**: Processes queue with rate-limited LLM API calls
- **Cron Job**: Triggers crawling every 40 minutes

### Configuration Options

- `LLM_RATE_LIMIT_DELAY`: Delay in seconds between API requests (default: 2.0)
- `MAX_RETRY_ATTEMPTS`: Max attempts to summarize news (default: 3)
- `FAILED_QUEUE_TTL`: Time to live for failed queue items in seconds (default: 3600)
- `LLM_SERVICE`: LLM service to use (groq, openai, or anthropic)
- `RATE_LIMIT_DELAY`: Internal delay between processing tasks

### Logging

The application uses Python's built-in logging. To see detailed logs:

```bash
# Set log level for more verbose output
export PYTHONPATH=.
python -c "import logging; logging.basicConfig(level=logging.INFO)"
python -m app.scheduler crawl
```

### Performance & Rate Limiting

- Rate Limit: 2 seconds between API requests (30 requests/minute)
- Daily Limit: Max 14,400 requests (well below API quota)
- Batch Processing: Up to 300 news items processed in ~10 minutes
- Cron Schedule: Every 40 minutes (36 times per day)

## 📈 Monitoring

### Health Checks
- **API Health**: `GET /health`
- **Database Connectivity**: Automatic on startup
- **Crawl Success**: Monitor CLI command exit codes

### Metrics to Monitor
- Number of articles crawled per run
- Database storage usage
- API response times
- Error rates in logs

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Add tests if applicable
5. Submit a pull request

## 📄 License

This project is licensed under the MIT License - see the LICENSE file for details.

## 🚀 Quick Start

1. Clone or fork this repository.
2. Create a `.env` file with required variables (Supabase, Redis, LLM).
3. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```
4. Start the API:
   ```bash
   uvicorn app.main:app --host 0.0.0.0 --port 8000
   ```
5. Optionally start the summarization worker:
   ```bash
   python -m app.workers.summarizer_worker
   ```
6. For Hugging Face Spaces deployment, follow [README_HUGGINGFACE.md](README_HUGGINGFACE.md).

## 🔗 Related Documentation

- [`README_HUGGINGFACE.md`](README_HUGGINGFACE.md) - Hugging Face Spaces deployment guide

---

For detailed deployment instructions specific to Hugging Face Spaces, see [README_HUGGINGFACE.md](README_HUGGINGFACE.md).