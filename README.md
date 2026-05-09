# Araya Labs: Multimodal Research Engine

A production-grade multimodal agentic research engine designed to automate deep research workloads. It ingests heterogeneous documents (PDFs, audio, screenshots, web pages), orchestrates a team of specialist agents, and produces structured, cited reports with a full evaluation and observability loop.

## Features

- **Multimodal Ingestion**: Process PDFs (with layout analysis), audio/video transcription, image analysis, and dynamic web scraping
- **Multi-Agent Orchestration**: LangGraph-based workflow with specialized agents for document analysis, web search, cross-referencing, and citation
- **Quality Assurance**: LLM-as-a-Judge evaluation for grounding and completeness
- **Observability**: OpenTelemetry tracing and LangSmith integration for monitoring and debugging
- **Structured Reporting**: Generate professional Markdown/PDF reports with executive summary, detailed findings, and source citations
- **Extensible Design**: Modular agent architecture allows for easy addition of new capabilities

## System Architecture

### Core Components

1. **Ingestion Layer**
   - Docling/PyMuPDF: High-fidelity PDF extraction and layout analysis
   - Whisper: Audio/video transcription
   - Vision LLM: Screenshot and image analysis
   - Playwright: Dynamic web scraping
   - Output: Unified Markdown/JSON format stored in temporary vector store and raw text storage

2. **Orchestration Layer (The "Brain")**
   - Framework: LangGraph for stateful, cyclic multi-agent workflows
   - Lead Agent: Decomposes research objectives into plans, assigns tasks, and synthesizes final findings
   - State Management: Shared Pydantic state tracking objective, plan, findings, pending tasks, and evaluation scores

3. **Specialist Agents**
   - Document Analyst: Processes local files and extracts specific data points
   - Search Specialist: Performs iterative web searches and evaluates source credibility
   - Cross-Reference Agent: Identifies corroborations/contradictions across sources and detects research gaps
   - Citation Agent: Ensures every claim in the report maps back to a specific source ID

4. **Reporting Layer**
   - Engine: Jinja2 templates for Markdown/PDF generation
   - Structure: Executive Summary, Detailed Findings (per category), Contradictions & Nuances, Source Appendix (Citations)

5. **Evaluation & Observability Loop**
   - Evaluator Agent: Uses LLM-as-a-Judge to score the final report on grounding (data support) and completeness (objective coverage)
   - Observability: OpenTelemetry tracing of agent decisions and tool calls; LangSmith for debugging and dataset collection

## Technology Stack

- **Language**: Python 3.11+
- **Agent Framework**: LangChain / LangGraph
- **LLMs**: Gemini 1.5 Pro / Flash (Primary), GPT-4o (Evaluation)
- **Database**: PostgreSQL (Metadata), Pinecone (Vector)
- **API**: FastAPI
- **Tracing**: OpenTelemetry / LangSmith
- **Additional Tools**: Docling, Deepgram SDK, Playwright, Serper API

## Installation and Setup

### Prerequisites

- Python 3.10 or higher
- PostgreSQL database
- Pinecone account
- Required API keys:
  - `GOOGLE_API_KEY` (for Gemini)
  - `PINECONE_API_KEY` and `PINECONE_ENVIRONMENT`
  - `DEEPGRAM_API_KEY` (for audio transcription)
  - `SERPER_API_KEY` (for web search)
  - Optional: `LANGCHAIN_API_KEY` (for LangSmith tracing)

### Local Development Setup

1. **Clone the repository** (if not already done):
   ```bash
   git clone <https://github.com/kiunye/araya_engine.git>
   cd araya-engine
   ```

2. **Create and activate a virtual environment**:
   ```bash
   # Windows
   python -m venv .venv
   .venv\Scripts\activate
   
   # Linux/MacOS
   python -m venv .venv
   source .venv/bin/activate
   ```

3. **Install the engine and dependencies**:
   ```bash
   pip install -e .
   ```

4. **Install Playwright browsers** (required for web ingestion):
   ```bash
   playwright install --with-deps
   ```

5. **Configure environment variables**:
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

6. **Run the application**:
   ```bash
   uvicorn araya.api.main:app --host 0.0.0.0 --port 8000
   ```
   
   The API documentation will be available at `http://localhost:8000/docs`.

### Docker Deployment

1. **Create a `docker-compose.yml` file** (if not present):
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

2. **Build and start**:
   ```bash
   docker-compose up --build
   ```

## Usage

Once the engine is running, you can interact with it through the API endpoints documented at `/docs`. The primary workflow involves:

1. **Submitting a research objective** along with any relevant files or URLs
2. **Monitoring the progress** as the Lead Agent orchestrates the specialist agents
3. **Retrieving the final structured report** with citations and evaluation scores

Example API usage (see `/docs` for detailed specifications):
```bash
curl -X POST "http://localhost:8000/research/start" \
  -H "Content-Type: application/json" \
  -d '{
    "objective": "Analyze the impact of renewable energy adoption on global oil markets through 2030",
    "files": [],  # Optional: list of file paths or URLs
  }'
```

For detailed API documentation, see [API_DOCUMENTATION.md](API_DOCUMENTATION.md).
For security information, see [SECURITY.md](SECURITY.md).

## Environment Variables

| Variable | Description | Required |
|----------|-------------|----------|
| `PROJECT_NAME` | Name of the project | Yes |
| `API_V1_STR` | API version prefix | Yes |
| `DATABASE_URL` | PostgreSQL connection string | Yes |
| `GOOGLE_API_KEY` | Gemini API key | Yes |
| `PINECONE_API_KEY` | Pinecone API key | Yes |
| `PINECONE_ENVIRONMENT` | Pinecone environment | Yes |
| `PINECONE_INDEX_NAME` | Pinecone index name | Yes |
| `DEEPGRAM_API_KEY` | Deepgram API key for audio | Yes |
| `SERPER_API_KEY` | Serper API key for web search | Yes |
| `LANGCHAIN_TRACING_V2` | Enable LangSmith tracing | No |
| `LANGCHAIN_ENDPOINT` | LangSmith endpoint | No (if tracing enabled) |
| `LANGCHAIN_API_KEY` | LangSmith API key | No (if tracing enabled) |
| `LANGCHAIN_PROJECT` | LangSmith project name | No (if tracing enabled) |

## API Documentation

When the engine is running, interactive API documentation is available at:
- Swagger UI: `http://localhost:8000/docs`
- ReDoc: `http://localhost:8000/redoc`

Additional documentation:
- [API Documentation](API_DOCUMENTATION.md) - Detailed API reference and usage examples
- [Security Policy](SECURITY.md) - Security best practices and vulnerability reporting

## Contributing

We welcome contributions to improve the Araya Research Engine. Please follow these steps:

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add some amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

Please ensure your code follows the project's coding standards and includes appropriate tests.

### Development Guidelines

- Follow PEP 8 style guide for Python code
- Write meaningful commit messages
- Add unit tests for new functionality
- Update documentation when adding or modifying features
- Ensure all tests pass before submitting a pull request

### Code Review Process

All contributions will be reviewed through our code review process which includes:
1. Automated testing
2. Manual code review for quality and security
3. Documentation verification
4. Performance impact assessment

## Acknowledgments

- LangChain and LangGraph teams for the excellent agent framework
- The open-source community for tools like Docling, Deepgram, and Playwright
