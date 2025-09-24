# News Crawler Backend

A FastAPI-based news aggregator backend that crawls news from multiple Indonesian and international sources, stores them in Supabase, and provides RESTful APIs for frontend consumption.

## 🚀 Features

- **Multi-source News Crawling**: Supports RSS feeds and HTML fallback scraping
- **Concurrent Processing**: Configurable concurrency for efficient crawling
- **Database Integration**: Uses Supabase (PostgreSQL) for data storage
- **RESTful API**: FastAPI-powered endpoints for news retrieval and management
- **Automated Scheduling**: CLI tools for scheduled crawling and cleanup
- **Duplicate Detection**: Content hash-based deduplication
- **Rate Limiting**: Built-in rate limiting to respect source websites
- **Error Handling**: Robust error handling and logging

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
| `POST` | `/api/news/cleanup` | Trigger data cleanup |

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

### Data Cleanup

```bash
# Delete data older than 30 days (by crawl_date)
python -m app.scheduler cleanup --days 30

# Delete data older than 30 days (by publish_date)
python -m app.scheduler cleanup --days 30 --by-publish
```

## 🌐 Deployment

### Render Web Service

1. **Service Configuration**:
   - Service type: Web Service
   - Runtime: Python
   - Build command: `pip install -r requirements.txt`
   - Start command: `uvicorn app.main:app --host 0.0.0.0 --port $PORT`

2. **Environment Variables**:
   - `SUPABASE_URL`: Your Supabase project URL
   - `SUPABASE_KEY`: Your Supabase anon key

### Render Scheduler Jobs

Create two scheduled jobs:

#### 1. Crawl Job
- **Name**: `crawl-news`
- **Schedule**: Every 15-30 minutes
- **Command**: `python -m app.scheduler crawl --concurrency 3`

#### 2. Cleanup Job
- **Name**: `cleanup-news`
- **Schedule**: Daily at 01:00
- **Command**: `python -m app.scheduler cleanup --days 30`

## 📁 Project Structure

```
backend/
├── app/
│   ├── __init__.py
│   ├── main.py              # FastAPI application entry point
│   ├── scheduler.py         # CLI scheduler for crawling and cleanup
│   ├── api/
│   │   └── routes.py        # API endpoints and request/response models
│   ├── crawler/
│   │   ├── spider.py        # Main crawling logic and RSS parsing
│   │   └── utils.py         # Utility functions for crawling
│   └── db/
│       ├── database.py      # Database connection and client
│       ├── models.py        # Pydantic models for data validation
│       └── crud.py          # Database operations (CRUD)
├── .env                     # Environment variables (create this)
├── requirements.txt         # Python dependencies
├── konfigurasi.md          # Detailed configuration guide
├── skema.md                # Database schema and SQL commands
├── konteks.md              # Backend design documentation
├── konteks 2 be.md         # Advanced architecture notes
└── README.md               # This file
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

### Logging

The application uses Python's built-in logging. To see detailed logs:

```bash
# Set log level for more verbose output
export PYTHONPATH=.
python -c "import logging; logging.basicConfig(level=logging.INFO)"
python -m app.scheduler crawl
```

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

## 🔗 Related Documentation

- [`konfigurasi.md`](konfigurasi.md) - Detailed configuration and deployment guide
- [`skema.md`](skema.md) - Database schema and SQL commands
- [`konteks.md`](konteks.md) - Backend design and architecture
- [`konteks 2 be.md`](konteks%202%20be.md) - Advanced architecture with Redis integration

---

For more detailed configuration and deployment instructions, see [`konfigurasi.md`](konfigurasi.md).