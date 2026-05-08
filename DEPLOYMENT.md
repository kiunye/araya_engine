# Araya Engine Deployment Guide

This guide covers the deployment of the Araya Labs Multimodal Research Engine.

## 1. Prerequisites

### Infrastructure
- **PostgreSQL**: Used for job tracking and metadata storage.
- **Pinecone**: Vector database for multimodal RAG.
- **Python**: Version 3.10 or higher.

### External API Keys
You will need the following API keys:
- `GOOGLE_API_KEY`: For Gemini 1.5 Pro/Flash (Reasoning, Vision, Synthesis).
- `PINECONE_API_KEY`: For vector storage and retrieval.
- `DEEPGRAM_API_KEY`: For audio transcription and diarization.
- `SERPER_API_KEY`: For web search capabilities.
- `LANGCHAIN_API_KEY` (Optional): For LangSmith tracing and observability.

## 2. Environment Setup

### Local Setup
1. Clone the repository and navigate to the root directory.
2. Create and activate a virtual environment:
   ```bash
   python -m venv .venv
   source .venv/bin/activate
   ```
3. Install the engine and its dependencies:
   ```bash
   pip install -e .
   ```
4. Install Playwright browsers (required for web ingestion):
   ```bash
   playwright install --with-deps
   ```

### Configuration
Create a `.env` file in the root directory with the following variables:
```env
# Core API
PROJECT_NAME="Araya Engine"
API_V1_STR="/api/v1"

# Database
DATABASE_URL="postgresql://user:password@localhost:5432/araya"

# LLM & Vector DB
GOOGLE_API_KEY="your-gemini-key"
PINECONE_API_KEY="your-pinecone-key"
PINECONE_INDEX_NAME="araya-research"
PINECONE_ENVIRONMENT="your-pinecone-env"

# Specialized Tools
DEEPGRAM_API_KEY="your-deepgram-key"
SERPER_API_KEY="your-serper-key"

# Observability (Optional)
LANGCHAIN_TRACING_V2=true
LANGCHAIN_ENDPOINT="https://api.smith.langchain.com"
LANGCHAIN_API_KEY="your-langsmith-key"
LANGCHAIN_PROJECT="araya-engine"
```

## 3. Running the Application

Start the FastAPI server using Uvicorn:
```bash
uvicorn araya.api.main:app --host 0.0.0.0 --port 8000
```

The API documentation will be available at `http://localhost:8000/docs`.

## 4. Docker Deployment

A basic `Dockerfile` is provided for containerized environments.

### Build and Run with Docker Compose
1. Create a `docker-compose.yml` file:
```yaml
version: '3.8'
services:
  api:
    build: .
    ports:
      - "8000:8000"
    env_file:
      - .env
    depends_on:
      - db
  db:
    image: postgres:15
    environment:
      POSTGRES_USER: postgres
      POSTGRES_PASSWORD: password
      POSTGRES_DB: araya
    ports:
      - "5432:5432"
```

2. Build and start:
```bash
docker-compose up --build
```

## 5. Scaling Considerations

- **Ingestion Workers**: The ingestion layer (Docling, Playwright) is resource-intensive. For production, consider moving ingestion tasks to a distributed worker pool (e.g., Celery/RabbitMQ).
- **Concurrency**: LangGraph handles stateful orchestration, but ensure your vector database and PostgreSQL instances are configured for your expected request volume.
- **Monitoring**: Ensure LangSmith or OpenTelemetry is enabled to monitor agent costs and performance bottlenecks.
