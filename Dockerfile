# Use lightweight Python image
FROM python:3.11-slim

# Set environment variables for Python optimization
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

# Create a non-root user for security
RUN groupadd --gid 1000 appuser && \
    useradd --uid 1000 --gid appuser --shell /bin/bash --create-home appuser

# Set working directory
WORKDIR /app

# Install system dependencies for Pillow (PIL), curl for health checks, and clean up in same layer
RUN apt-get update && apt-get install -y \
    libjpeg-dev zlib1g-dev libpng-dev libfreetype6-dev \
    curl \
    && rm -rf /var/lib/apt/lists/* \
    && apt-get clean

# Copy dependency list first for better Docker layer caching
COPY requirements.txt .

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy application files
COPY --chown=appuser:appuser . .

# Create temp directory with proper permissions
RUN mkdir -p /tmp/ocr_temp && chown -R appuser:appuser /tmp/ocr_temp

# Switch to non-root user
USER appuser

# Expose port 8050 as requested
EXPOSE 8050

# Set environment variable for the port
ENV PORT=8050

# Health check for Cloud Run
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:8050/health || exit 1

# Run FastAPI app with Uvicorn with optimized settings for Cloud Run
CMD ["uvicorn", "fastapi_app:app", "--host", "0.0.0.0", "--port", "8050", "--workers", "1", "--access-log", "--log-level", "info"]
