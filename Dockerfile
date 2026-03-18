# Dockerfile
FROM python:3.11-slim

WORKDIR /app

# Install system dependencies (for psycopg2, pytesseract)
RUN apt-get update && apt-get install -y \
    gcc \
    libpq-dev \
    tesseract-ocr \
    && rm -rf /var/lib/apt/lists/*

# Install Python dependencies
COPY pyproject.toml ./
RUN pip install --no-cache-dir -e ".[prod]"

# Copy application code
COPY src/ ./src/

# Create non-root user
RUN useradd -m appuser && chown -R appuser:appuser /app
USER appuser

EXPOSE 8000

CMD ["uvicorn", "src.main:app", "--host", "0.0.0.0", "--port", "8000"]