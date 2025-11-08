# Geopard - AI-Powered Geodata Assistant
# Multi-stage Docker build for Windows compatibility

FROM python:3.11-slim as base

# Set environment variables
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Create app directory
WORKDIR /app

# Copy requirements first for better caching
COPY requirements.txt requirements-dev.txt ./

# Install Python dependencies
RUN pip install --upgrade pip && \
    pip install -r requirements.txt && \
    pip install fastapi uvicorn[standard] mcp

# Copy application code
COPY backend/ ./backend/
COPY frontend/ ./frontend/
COPY location-tools/ ./location-tools/
COPY data/ ./data/
COPY mcp_server.py ./
COPY mcp_config.json ./

# Create non-root user for security
RUN useradd -m -u 1000 geopard && \
    chown -R geopard:geopard /app

USER geopard

# Expose port
EXPOSE 8000

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=40s --retries=3 \
    CMD curl -f http://localhost:8000/health || exit 1

# Default command - run web server
CMD ["python", "-m", "uvicorn", "frontend.chat_server_mcp:app", "--host", "0.0.0.0", "--port", "8000"]
