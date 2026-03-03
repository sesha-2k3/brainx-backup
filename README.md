# Personal CRM

Web-based personal relationship manager with AI-powered contact extraction.

## Quick Start

### 1. Prerequisites

- Python 3.11+
- Node.js 18+ (for frontend)
- PostgreSQL 15+
- Tesseract OCR (for business cards): `brew install tesseract`

### 2. Setup

```bash
cd personal-crm

# Python setup
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt

# Copy environment config
cp .env.example .env
# Edit .env with your GROQ_API_KEY

# Frontend setup
cd frontend
npm install
cd ..
```

### 3. Database

```bash
# Start Postgres with Docker
docker compose -f docker/docker-compose.yml up -d

# Run migrations
alembic upgrade head
```

### 4. Run (Development)

```bash
# Terminal 1: Backend API
uvicorn src.main:app --reload --port 8000

# Terminal 2: Frontend dev server
cd frontend
npm run dev
```

Open http://localhost:3000

### 5. Run 

```bash
# Build frontend
cd frontend
npm run build
cd ..

# Start server (serves both API and frontend)
uvicorn src.main:app --host 0.0.0.0 --port 8000
```

Open http://localhost:8000

## Configuration

Key environment variables in `.env`:

| Variable | Description |
|----------|-------------|
| `DATABASE_URL` | Postgres connection string |
| `GROQ_API_KEY` | Groq API key for transcription and LLM |

## Features

- **Text input**: Paste meeting notes, extract contacts automatically
- **Voice upload**: Upload voice memos, transcribed and parsed
- **Business cards**: Upload photos, OCR extracts contact info
- **Smart extraction**: LLM identifies name, email, phone, company, role
- **Deduplication**: Detects existing contacts by email/phone
- **Follow-ups**: Create tasks linked to contacts
- **Natural search**: "Who is Eddie?", "Investors I met last month"

