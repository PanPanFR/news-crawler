# News Crawler - Hugging Face Spaces Deployment Guide

This guide will help you deploy the News Crawler application to Hugging Face Spaces.

## Prerequisites

1. A Hugging Face account (free tier is sufficient)
2. A Supabase project for database
3. A Redis instance (Redis Cloud free tier recommended)
4. API keys for LLM services (Groq, OpenAI, or Anthropic)

## Deployment Steps

### 1. Create a Hugging Face Space

1. Go to [huggingface.co](https://huggingface.co) and sign in
2. Click on "Spaces" in the top navigation
3. Click "Create new Space"
4. Fill in the details:
   - **Space name**: `news-crawler` (or your preferred name)
   - **SDK**: Docker
   - **Hardware**: CPU basic (free tier)
   - **Make it public**: Yes (recommended for free tier)
5. Click "Create Space"

### 2. Upload Your Code

#### Option A: Using Git (Recommended)

1. Clone your Space repository:
   ```bash
   git clone https://huggingface.co/spaces/your-username/news-crawler
   cd news-crawler
   ```

2. Copy all project files to the Space directory:
   ```bash
   # Copy all files from your project to the Space directory
   cp -r /path/to/your/project/* .
   ```

3. Commit and push the changes:
   ```bash
   git add .
   git commit -m "Initial deployment of news crawler"
   git push
   ```

#### Option B: Using Web Interface

1. Go to your Space page
2. Click on "Files" tab
3. Upload or create the following files:
   - `app.py` (main entry point)
   - `requirements.txt`
   - `.env` (with your actual configuration)
   - All files in the `app/` directory

### 3. Configure Environment Variables

1. Go to your Space page
2. Click on "Settings" tab
3. Scroll down to "Variables" section
4. Add the following environment variables:

   ```bash
   # Platform Configuration
   PLATFORM=HUGGINGFACE_SPACES
   HUGGINGFACE_SPACES=true

   # Supabase Configuration
   SUPABASE_URL=https://your-project-id.supabase.co
   SUPABASE_KEY=your-anon-key-here

   # Redis Configuration
   REDIS_HOST=your-upstash-redis-host-12345.upstash.io
   REDIS_PORT=6379
   REDIS_PASSWORD=your-upstash-redis-password

   # LLM API Configuration
   LLM_API_KEY=your-groq-api-key-here
   LLM_SERVICE=groq

   # Rate Limiting Configuration
   LLM_RATE_LIMIT_DELAY=2.0
   MAX_RETRY_ATTEMPTS=3
   FAILED_QUEUE_TTL=3600
   ```

### 4. Build and Deploy

1. After pushing your code or uploading files, Hugging Face will automatically build the Docker image
2. You can monitor the build progress in the "Build" tab
3. Once the build is complete, your app will be available at:
   ```
   https://huggingface.co/spaces/your-username/news-crawler
   ```

## Architecture Overview

### Components

1. **FastAPI Web Service** - Main API endpoint
2. **Background Scheduler** - Runs crawl jobs every 40 minutes
3. **Background Worker** - Processes summarization tasks
4. **External Services**:
   - Supabase (Database)
   - Redis (Queue management)
   - LLM API (Content summarization)

### How It Works

1. The main `app.py` starts the FastAPI application
2. On startup, it launches background threads for:
   - Scheduler (checks every minute if crawl job should run)
   - Worker (checks every minute if summarization tasks should run)
3. The scheduler runs crawl jobs every 40 minutes
4. The worker processes summarization tasks every 5 minutes
5. All data is stored in Supabase and Redis

## Monitoring and Maintenance

### Health Check

You can check if your application is running by visiting:
```
https://huggingface.co/spaces/your-username/news-crawler/health
```

### Logs

1. Go to your Space page
2. Click on "Logs" tab to view application logs
3. You can filter logs by component (app, scheduler, worker)

### Manual Triggers

You can manually trigger crawl jobs:
```bash
curl -X POST https://huggingface.co/spaces/your-username/news-crawler/trigger-crawl
```

## Troubleshooting

### Common Issues

1. **Build Failures**
   - Check that all files are uploaded correctly
   - Verify `requirements.txt` has all dependencies
   - Check build logs for specific errors

2. **Application Crashes**
   - Check environment variables are set correctly
   - Verify external service connections (Supabase, Redis)
   - Review application logs for error messages

3. **Scheduler Not Running**
   - Check that background threads are starting correctly
   - Verify scheduler logs in the application logs
   - Ensure no exceptions are preventing thread execution

### Debug Mode

To enable debug logging, add this to your environment variables:
```bash
LOG_LEVEL=DEBUG
```

## Scaling and Optimization

### Free Tier Limitations

- CPU: 2 vCPUs (shared)
- RAM: 16GB (shared)
- Storage: 20GB
- No GPU access (unless upgraded)

### Optimization Tips

1. **Reduce Crawl Frequency**: Increase the crawl interval if resources are limited
2. **Limit Concurrent Tasks**: Reduce `MAX_CONCURRENT_CRAWL` and `MAX_CONCURRENT_WORKER`
3. **Optimize LLM Usage**: Adjust `LLM_RATE_LIMIT_DELAY` to manage API quotas
4. **Monitor Resource Usage**: Keep an eye on CPU and memory usage

### Upgrading to Paid Tier

If you need more resources:
1. Go to your Space settings
2. Click on "Upgrade" in the Hardware section
3. Choose a paid plan with GPU if needed for LLM processing

## Security Considerations

1. **Environment Variables**: Never commit API keys to your repository
2. **CORS Configuration**: Update CORS origins in `app.py` for production
3. **Rate Limiting**: Implement additional rate limiting if needed
4. **Authentication**: Consider adding API key authentication for production use

## Support

If you encounter issues:
1. Check Hugging Face Spaces documentation
2. Review application logs
3. Check external service status (Supabase, Redis, LLM API)
4. Create an issue in the project repository

## Alternative Deployment Options

If Hugging Face Spaces doesn't meet your needs, consider:
- **PythonAnywhere**: Good for scheduled tasks but limited background processes
- **Replit**: Good for background tasks with generous free tier
- **Heroku**: More mature but requires credit card for free tier
- **Railway**: Good for microservices but requires credit card