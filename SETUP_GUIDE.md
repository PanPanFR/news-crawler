# Complete Setup Guide: News Crawler with AI Summarization

This guide covers complete setup from local development to deployment on Render.

## Table of Contents
1. [Prerequisites](#prerequisites)
2. [Local Development Setup](#local-development-setup)
3. [Supabase Configuration](#supabase-configuration)
4. [Redis Setup](#redis-setup)
5. [LLM API Configuration](#llm-api-configuration)
6. [Deployment Options](#deployment-options)
7. [Render Deployment Configuration](#render-deployment-configuration)
8. [Environment Variables Guide](#environment-variables-guide)

## Prerequisites

- Python 3.11+ (recommended)
- Git
- Supabase account
- Redis server (for local development)
- LLM API key (Groq, OpenAI, or Anthropic)

## Local Development Setup

### 1. Clone the Repository
```bash
git clone https://github.com/your-username/news-crawler.git
cd news-crawler
```

### 2. Create Virtual Environment
```bash
python -m venv venv

# On Windows
venv\Scripts\activate

# On macOS/Linux
source venv/bin/activate
```

### 3. Install Dependencies
```bash
pip install --upgrade pip
pip install -r requirements.txt
```

### 4. Create Environment File
Copy the example environment file:
```bash
cp .env.example .env
```

Then edit `.env` with your specific configuration values (see Environment Variables Guide below).

### 5. Install Redis (for local development)
For Windows, you can use Windows Subsystem for Linux (WSL) or Docker:
```bash
# Option 1: Docker
docker run --name redis-local -p 6379:6379 -d redis:alpine

# Option 2: On Windows with WSL
sudo apt-get install redis-server
```

## Supabase Configuration

### 1. Create Supabase Project
1. Go to [supabase.com](https://supabase.com)
2. Sign in and create a new project
3. Note down your Project URL and Project API key (anon key)

### 2. Database Schema Setup
Execute the SQL commands from `skema.md` in your Supabase SQL Editor:
1. Go to your project dashboard
2. Navigate to "SQL Editor"
3. Create a new query
4. Copy and paste the content from `skema.md`

### 3. Database Configuration in .env
```env
SUPABASE_URL=https://your-project-id.supabase.co
SUPABASE_KEY=your-anon-key-here
```

### 4. Required Extensions
Execute these SQL commands in your Supabase SQL Editor:
```sql
CREATE EXTENSION IF NOT EXISTS pgcrypto;
CREATE EXTENSION IF NOT EXISTS pg_trgm;
```

## Redis Setup

### For Local Development
- Option 1: Use Redis Docker container (recommended)
  ```bash
  docker run --name redis-local -p 6379:6379 -d redis:alpine
  ```
- Option 2: Install Redis locally
- Option 3: Use a Redis cloud service

### For Render Deployment with Redis Cloud
Since you're using Redis Cloud instead of Render's Redis add-on, configure as follows:

1. **Get Redis Cloud Connection Details**:
   - Host: `redis-12045.crce185.ap-seast-1-1.ec2.redns.redis-cloud.com`
   - Port: `12045`
   - You'll need your Redis Cloud password

2. **Update Environment Variables on Render Dashboard**:
   - In Web Service settings, add:
     - `REDIS_HOST`: `redis-12045.crce185.ap-seast-1-1.ec2.redns.redis-cloud.com`
     - `REDIS_PORT`: `12045`
     - `REDIS_PASSWORD`: Your Redis Cloud password
   - In Worker Service settings, add the same variables

3. **Update render.yaml**:
   - The `render.yaml` no longer includes the Redis add-on service
   - Instead, it uses connection parameters via environment variables
   - The Redis client will connect to your Redis Cloud instance

4. **Security Considerations**:
   - Store the Redis password securely in Render's environment variables
   - Do not commit Redis credentials to the repository
   - The Redis client uses SSL by default for secure connections

## LLM API Configuration

### 1. Choose an LLM Service
The system supports multiple providers:

#### Groq (Recommended for Rate Limits)
1. Go to [console.groq.com](https://console.groq.com)
2. Sign up and navigate to "API Keys" section
3. Create a new API key
4. Set in `.env`:
   ```env
   LLM_SERVICE=groq
   LLM_API_KEY=your-groq-api-key
   ```

#### OpenAI
1. Go to [platform.openai.com](https://platform.openai.com)
2. Navigate to "API Keys" section
3. Create a new secret key
4. Set in `.env`:
   ```env
   LLM_SERVICE=openai
   LLM_API_KEY=your-openai-api-key
   ```

#### Anthropic (Claude)
1. Go to [anthropic.com](https://anthropic.com)
2. Get access to Claude API and generate API key
3. Set in `.env`:
   ```env
   LLM_SERVICE=anthropic
   LLM_API_KEY=your-anthropic-api-key
   ```

### 2. Rate Limiting Configuration
For API quota compliance, set the rate limit delay:
```env
LLM_RATE_LIMIT_DELAY=2.0  # 2 seconds between requests for 30 RPM
```

## Deployment Options

### Docker vs GitHub Deployment on Render

#### Docker Deployment Advantages:
- More control over the environment
- Consistent behavior across development and production
- Can specify exact versions of dependencies
- Better for complex setups with multiple services
- More predictable deployments

#### GitHub Deployment Advantages:
- Simpler setup process
- No need to manage Dockerfiles
- Render handles the containerization
- Faster deployment process
- Less maintenance overhead

**Recommendation**: For this application, I recommend **GitHub deployment via repository** because:
1. The application is Python-based with relatively simple dependencies
2. Render has good Python support
3. The `render.yaml` configuration handles all services properly
4. It's easier to manage and update

### Local Testing Before Deployment

Run the service locally to test all components:
```bash
# Terminal 1: Start the web service
uvicorn app.main:app --host 0.0.0.0 --port 8000

# Terminal 2: Start the worker (in another terminal)
python -m app.workers.summarizer_worker

# Terminal 3: Trigger a test crawl
python -m app.scheduler crawl --concurrency 1
```

## Render Deployment Configuration

### 1. Preparing for Deployment
1. Ensure all environment variables are set in Render dashboard (not in the repository)
2. Verify `render.yaml` is properly configured (it should be already in your repo)
3. Make sure your Git repository is up to date

### 2. Deploy to Render
1. Go to [dashboard.render.com](https://dashboard.render.com)
2. Click "New +" and select "Web Service"
3. Connect your GitHub/GitLab repository
4. Choose the repository containing this code
5. Select the branch (usually `main` or `master`)
6. Configure environment variables (see section below)
7. Review the settings and click "Create Web Service"

### 3. Render Services Configuration
The `render.yaml` creates three services:

#### Web Service:
- **Runtime**: Python
- **Build Command**: 
  ```bash
  python -m venv venv
  source venv/bin/activate
  pip install -r requirements.txt
  ```
- **Start Command**:
  ```bash
  source venv/bin/activate
  uvicorn app.main:app --host 0.0.0.0 --port $PORT
  ```

#### Redis Add-on:
- Automatically configured as a separate service
- Connected to web service and worker

#### Worker Service:
- **Runtime**: Python
- **Build Command**: Same as Web Service
- **Start Command**:
  ```bash
  source venv/bin/activate
  python -m app.workers.summarizer_worker
  ```

#### Cron Job:
- **Schedule**: `*/40 * * * *` (every 40 minutes)
- **Command**: `curl -X POST https://your-service-name.onrender.com/trigger-crawl`

### 4. Environment Variables on Render Dashboard
In the Render dashboard, add these environment variables:

#### Web Service Variables:
- `SUPABASE_URL`: Your Supabase project URL
- `SUPABASE_KEY`: Your Supabase anon key
- `LLM_API_KEY`: Your LLM API key
- `LLM_SERVICE`: groq (or openai/anthropic)
- `LLM_RATE_LIMIT_DELAY`: 2.0
- `MAX_RETRY_ATTEMPTS`: 3
- `FAILED_QUEUE_TTL`: 3600
- `RENDER`: true

#### Worker Service Variables:
Same as Web Service (Render automatically syncs service connections)

The `REDIS_URL` will be automatically configured through service connections in Render.

## Environment Variables Guide

### Required Variables:

| Variable | Description | Example | Required |
|----------|-------------|---------|----------|
| `SUPABASE_URL` | Supabase project URL | `https://your-project.supabase.co` | Yes |
| `SUPABASE_KEY` | Supabase anon key | `eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...` | Yes |
| `LLM_API_KEY` | API key for chosen LLM service | `gsk-xxx` (for Groq) | Yes |
| `LLM_SERVICE` | LLM service to use | `groq`, `openai`, `anthropic` | Yes |

### Optional Variables:

| Variable | Description | Default | Notes |
|----------|-------------|---------|-------|
| `REDIS_URL` | Redis connection URL | `redis://localhost:6379` | Auto-configured in Render |
| `LLM_RATE_LIMIT_DELAY` | Delay between API calls in seconds | `2.0` | Controls rate limiting |
| `MAX_RETRY_ATTEMPTS` | Max attempts for failed summaries | `3` | Retry logic |
| `FAILED_QUEUE_TTL` | TTL for failed queue items in seconds | `3600` | Expire failed items |
| `RENDER` | Is running on Render | `false` | Deployment detection |

### Rate Limiting Configuration
For Groq API with gemma2-9b-it model:
- Set `LLM_RATE_LIMIT_DELAY=2.0` to stay within 30 requests/minute limit
- This allows ~300 requests per 10 minutes window
- Adjust based on your API provider's rate limits

## Troubleshooting

### Common Issues:

1. **Connection Errors to Supabase**: 
   - Verify URLs and keys are correct
   - Check that Supabase project is active

2. **Redis Connection Issues**:
   - In Render, ensure services are connected properly
   - In local development, make sure Redis server is running

3. **API Rate Limiting**:
   - Ensure `LLM_RATE_LIMIT_DELAY` matches your provider's limits
   - For Groq: 2 seconds delay = 30 requests/minute

4. **Worker Not Processing Queue**:
   - Verify that Redis is configured correctly
   - Check that worker has proper environment access

### Monitoring & Logs
- Check Render dashboard for service logs
- Monitor database for unsummarized news (`summary IS NULL`)
- Verify cron job execution in logs

## Performance Optimization

The system is designed to handle:
- ~300 news items per crawl cycle
- Process items within 10 minutes (with 2s delay per item)
- Stay within API quota limits of 14,400 requests/day
- Cron runs every 40 minutes (36 times/day) = 10,800 max requests/day

This configuration ensures compliance with most API rate limits while maintaining good performance.