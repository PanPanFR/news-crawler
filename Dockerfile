# Use an official Python runtime as a parent image
FROM python:3.11-slim

# Set environment variables
ENV PYTHONDONTWRITEBYTECODE 1
ENV PYTHONUNBUFFERED 1

# Set work directory
WORKDIR /app

# Install system dependencies
RUN apt-get update \\
    && apt-get install -y --no-install-recommends \\
        postgresql-client \\
    && rm -rf /var/lib/apt/lists/*

# Copy project requirements
COPY backend/requirements.txt .

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy project
COPY backend/ .

# Expose port
EXPOSE $PORT

# Run the application
CMD [\"sh\", \"-c\", \"uvicorn app.main:app --host 0.0.0.0 --port $PORT\"]