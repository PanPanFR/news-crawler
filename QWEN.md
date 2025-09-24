# News Crawler Project - Qwen Code Context

This document provides context about the News Crawler project for Qwen Code, an AI coding assistant. It covers the project structure, technologies, and key implementation details to help the assistant understand and work with the codebase effectively.

## Project Overview

This is a FastAPI-based news aggregator backend that crawls news from multiple Indonesian and international sources, stores them in Supabase, and provides RESTful APIs for frontend consumption. The system features concurrent processing, duplicate detection, rate limiting, and automated scheduling.

### Key Features
- Multi-source News Crawling (RSS feeds and HTML fallback)
- Concurrent Processing with configurable concurrency
- Supabase (PostgreSQL) Database Integration
- RESTful API with FastAPI
- Automated Scheduling via CLI tools
- Content Hash-based Deduplication
- Built-in Rate Limiting
- Robust Error Handling and Logging

## Project Structure

```
news-crawler/
├── backend/
│   ├── app/
│   │   ├── __init__.py
│   │   ├── main.py              # FastAPI application entry point
│   │   ├── scheduler.py         # CLI scheduler for crawling and cleanup
│   │   ├── api/
│   │   │   └── routes.py        # API endpoints and request/response models
│   │   ├── crawler/
│   │   │   ├── spider.py        # Main crawling logic and RSS parsing
│   │   │   └── utils.py         # Utility functions for crawling
│   │   └── db/
│   │       ├── database.py      # Database connection and client
│   │       ├── models.py        # Pydantic models for data validation
│   │       └── crud.py          # Database operations (CRUD)
│   ├── .env                     # Environment variables (contains Supabase credentials)
│   ├── requirements.txt         # Python dependencies
│   ├── konfigurasi.md           # Detailed configuration guide
│   ├── skema.md                 # Database schema and SQL commands
│   ├── konteks.md               # Backend design documentation
│   ├── konteks 2 be.md          # Advanced architecture with Redis integration
│   └── README.md                # Project overview and documentation
└── konteks2.md                  # Frontend design documentation
```

## Technologies Used

### Backend
- **Python 3.11+**: Primary programming language
- **FastAPI**: Web framework for building APIs
- **Uvicorn**: ASGI server for running FastAPI
- **Supabase**: Database (PostgreSQL) for data storage
- **BeautifulSoup4**: HTML parsing for web scraping
- **lxml**: XML/HTML parser for feed parsing
- **feedparser**: RSS/Atom feed parsing
- **httpx**: HTTP client library
- **Redis**: For advanced queue-based processing (planned)

### Key Python Libraries
- `fastapi==0.115.0`: Web framework
- `uvicorn[standard]==0.30.6`: ASGI server
- `httpx==0.27.0`: HTTP client
- `beautifulsoup4==4.12.3`: HTML parsing
- `lxml==5.3.0`: XML/HTML parser
- `feedparser==6.0.11`: Feed parsing
- `python-dotenv==1.0.1`: Environment variable loading
- `pydantic==2.8.2`: Data validation
- `orjson==3.10.0`: Fast JSON serialization
- `tenacity==8.5.0`: Retry utilities
- `supabase==2.4.5`: Supabase client
- `redis==5.0.4`: Redis client (for future implementation)

## Core Components

### 1. Main Application (`app/main.py`)
- FastAPI application entry point
- Health check endpoints
- CORS middleware configuration
- Supabase client initialization

### 2. Database Layer (`app/db/`)
- **database.py**: Supabase client management and basic database operations
- **crud.py**: News-specific CRUD operations with filtering and pagination
- **models.py**: Pydantic models for data validation

### 3. Crawler System (`app/crawler/`)
- **spider.py**: Main crawling logic with RSS parsing and HTML fallback
- **utils.py**: Helper functions for URL normalization, text cleaning, date parsing, etc.

### 4. API Layer (`app/api/routes.py`)
- RESTful endpoints for news listing, retrieval, manual crawling, and cleanup
- Request/response models using Pydantic
- Query parameter validation and pagination

### 5. Scheduler (`app/scheduler.py`)
- CLI interface for scheduled crawling and cleanup operations
- Concurrency management
- Error handling for batch operations

## Database Schema

The application uses a single `news` table in Supabase with the following structure:

```sql
CREATE TABLE IF NOT EXISTS public.news (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  title TEXT NOT NULL,
  url TEXT NOT NULL,
  summary TEXT NULL,
  source TEXT NOT NULL,
  category TEXT NULL,
  publish_date TIMESTAMPTZ NULL,
  crawl_date TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  content_hash TEXT NULL
);

-- URL must be unique to prevent duplicates
ALTER TABLE public.news
  ADD CONSTRAINT news_url_unique UNIQUE (url);
```

## API Endpoints

### Core Endpoints
- `GET /`: Service status and version
- `GET /health`: Health check
- `GET /api/news`: List news with filters and pagination
- `GET /api/news/{id}`: Get specific news item
- `POST /api/news/crawl`: Trigger manual crawling
- `POST /api/news/cleanup`: Trigger data cleanup

### Query Parameters
- `/api/news` supports filtering by query, category, source, date range
- Pagination with limit and offset
- `/api/news/crawl` accepts concurrency and domain list parameters
- `/api/news/cleanup` accepts days and date field parameters

## Running the Application

### Local Development
1. Create and activate virtual environment:
   ```bash
   python -m venv .venv
   .venv\Scripts\activate  # Windows
   source .venv/bin/activate  # macOS/Linux
   ```

2. Install dependencies:
   ```bash
   pip install --upgrade pip
   pip install -r requirements.txt
   ```

3. Set up environment variables in `.env`:
   ```env
   SUPABASE_URL=https://your-project-ref.supabase.co
   SUPABASE_KEY=your-anon-key-here
   ```

4. Run the application:
   ```bash
   uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
   ```

### CLI Commands
- Crawl all default sources: `python -m app.scheduler crawl --concurrency 3`
- Crawl specific domains: `python -m app.scheduler crawl --domains kompas.com,detik.com --concurrency 2`
- Cleanup old data: `python -m app.scheduler cleanup --days 30`

## Deployment

The application is designed for deployment on Render with:
1. Web Service for the FastAPI application
2. Scheduled jobs for crawling and cleanup
3. Supabase for database storage

Environment variables must be configured in Render:
- `SUPABASE_URL`: Your Supabase project URL
- `SUPABASE_KEY`: Your Supabase anon key

## Development Guidelines

### Code Style
- Follow Python best practices and PEP 8 guidelines
- Use type hints for all function parameters and return values
- Write async code where appropriate for I/O operations
- Use logging instead of print statements

### Testing
- Add unit tests for new functionality
- Test database operations with real Supabase instance
- Verify API endpoints with curl or similar tools

### Error Handling
- Handle exceptions gracefully with appropriate HTTP status codes
- Log errors for debugging purposes
- Implement retry logic for network operations

## Future Enhancements

The project includes plans for advanced features using Redis:
1. Priority-based news summarization queue
2. Separate worker processes for AI summarization
3. Better load handling during peak crawling times
4. Improved retry mechanisms for failed operations

These enhancements would create a more resilient and scalable system by decoupling the crawling, prioritization, and summarization processes.