# Araya Engine API Documentation

## Overview

The Araya Engine provides a RESTful API for submitting research tasks and retrieving results. The API is built with FastAPI and provides automatic interactive documentation.

## Base URL

```
http://localhost:8000
```

When the engine is running, interactive API documentation is available at:
- Swagger UI: `http://localhost:8000/docs`
- ReDoc: `http://localhost:8000/redoc`

## Authentication

Currently, the API does not require authentication for basic usage. However, it is designed to support API key authentication in the future through the `X-API-Key` header.

## Rate Limiting

To prevent abuse, the API implements rate limiting:
- **Limit**: 10 requests per minute per IP address
- **Response**: HTTP 429 (Too Many Requests) when limit is exceeded
- **Headers**: Rate limit information may be included in response headers

## Endpoints

### Root Endpoint

```http
GET /
```

Returns basic information about the API.

**Response:**
```json
{
  "message": "Welcome to Araya Engine API",
  "version": "0.1.0"
}
```

### Health Check

```http
GET /health
```

Returns the health status of the service and performs periodic cleanup of old jobs.

**Response:**
```json
{
  "status": "healthy"
}
```

### Metrics Endpoint

```http
GET /metrics
```

Returns system metrics for monitoring purposes.

**Response:**
```json
{
  "total_started": 125,
  "total_completed": 118,
  "total_failed": 7,
  "total_cleaned_up": 5,
  "current_active": 3,
  "timestamp": "2026-05-09T10:30:00.123456",
  "uptime_seconds": 3600.5
}
```

### Start Research Task

```http
POST /research/start
```

Starts a new research task. This endpoint accepts a JSON body with the research objective and optional parameters.

**Request Body:**
```json
{
  "objective": "Analyze the impact of renewable energy adoption on global oil markets through 2030",
  "context": {
    "focus_regions": ["North America", "Europe", "Asia"],
    "time_horizon": "2025-2030"
  },
  "files": [
    "/path/to/document1.pdf",
    "/path/to/spreadsheet.xlsx"
  ]
}
```

**Parameters:**
- `objective` (string, required): The main research objective or question (max 500 characters)
- `context` (object, optional): Additional context or constraints for the research
- `files` (array of strings, optional): List of file paths to analyze

**Response:**
```json
{
  "research_id": "a1b2c3d4-e5f6-7890-g1h2-i3j4k5l6m7n8"
}
```

**Error Responses:**
- `400 Bad Request`: Invalid input (empty objective, too long, etc.)
- `429 Too Many Requests`: Rate limit exceeded
- `503 Service Unavailable`: Server at maximum capacity

### Get Research Status

```http
GET /research/{research_id}/status
```

Returns the current status of a research task.

**Path Parameters:**
- `research_id` (string, required): The ID of the research task

**Response:**
```json
{
  "research_id": "a1b2c3d4-e5f6-7890-g1h2-i3j4k5l6m7n8",
  "status": "in-progress",
  "created_at": "2026-05-09T10:00:00.123456",
  "updated_at": "2026-05-09T10:15:30.789012",
  "error": null
}
```

**Possible Status Values:**
- `in-progress`: Research is currently being processed
- `complete`: Research has finished successfully
- `failed`: Research encountered an error

**Error Responses:**
- `404 Not Found`: Research job not found
- `400 Bad Request`: Invalid research ID format

### Get Research Report

```http
GET /research/{research_id}/report
```

Returns the final research report if the task is complete.

**Path Parameters:**
- `research_id` (string, required): The ID of the research task

**Response:**
```json
{
  "research_id": "a1b2c3d4-e5f6-7890-g1h2-i3j4k5l6m7n8",
  "objective": "Analyze the impact of renewable energy adoption on global oil markets through 2030",
  "report": "# Research Report\n\n## Executive Summary\n\n[Report content...]",
  "metadata": {}
}
```

**Error Responses:**
- `404 Not Found`: Research job not found
- `400 Bad Request`: Research is still in progress or failed

### Get Research Findings

```http
GET /research/{research_id}/findings
```

Returns the extracted findings from the research process.

**Path Parameters:**
- `research_id` (string, required): The ID of the research task

**Response:**
```json
{
  "research_id": "a1b2c3d4-e5f6-7890-g1h2-i3j4k5l6m7n8",
  "findings": [
    {
      "id": "finding_abc123",
      "claim": "Renewable energy adoption is projected to reduce global oil demand by 25% by 2030",
      "source_doc_id": "doc123.pdf",
      "source_page": 15,
      "source_url": null,
      "source_excerpt": "According to recent studies, aggressive renewable energy policies could cut oil demand...",
      "confidence": "high",
      "verified": false,
      "verified_against": [],
      "metadata": {
        "credibility_score": 0.9
      }
    }
  ],
  "iteration_count": 2
}
```

## Data Models

### ResearchRequest
- `objective` (string): The research objective
- `context` (object, optional): Additional context
- `files` (array of strings, optional): File paths to analyze

### ResearchStatusResponse
- `research_id` (string): Unique identifier for the research task
- `status` (string): Current status (in-progress, complete, failed)
- `created_at` (string): ISO timestamp when the task was created
- `updated_at` (string, optional): ISO timestamp when the task was last updated
- `error` (string, optional): Error message if the task failed

### ResearchReportResponse
- `research_id` (string): Unique identifier for the research task
- `objective` (string): The research objective
- `report` (string, optional): The final research report in Markdown format
- `metadata` (object): Additional metadata about the research

## Error Handling

The API uses standard HTTP status codes to indicate success or failure:

- `200 OK`: Request succeeded
- `400 Bad Request`: Invalid request data
- `404 Not Found`: Resource not found
- `429 Too Many Requests`: Rate limit exceeded
- `500 Internal Server Error`: Unexpected server error
- `503 Service Unavailable`: Server at maximum capacity

Error responses include a JSON body with error details:
```json
{
  "detail": "Error description"
}
```

## Usage Examples

### Starting a Research Task

```bash
curl -X POST "http://localhost:8000/research/start" \
  -H "Content-Type: application/json" \
  -d '{
    "objective": "What are the economic implications of AI adoption in healthcare?",
    "context": {
      "geographic_scope": "United States",
      "timeframe": "2024-2029"
    }
  }'
```

### Checking Research Status

```bash
curl -X GET "http://localhost:8000/research/a1b2c3d4-e5f6-7890-g1h2-i3j4k5l6m7n8/status"
```

### Getting the Final Report

```bash
curl -X GET "http://localhost:8000/research/a1b2c3d4-e5f6-7890-g1h2-i3j4k5l6m7n8/report"
```

## Security Considerations

1. **Input Validation**: All inputs are validated and sanitized to prevent injection attacks
2. **Rate Limiting**: Protects against abuse and denial-of-service attacks
3. **Research Objectives**: Limited to 500 characters and stripped of HTML/script tags
4. **File Paths**: Should be validated on the client side to prevent directory traversal

## Scalability Features

1. **Job Cleanup**: Old research jobs are automatically cleaned up after 24 hours
2. **Concurrency Limits**: Maximum of 100 concurrent jobs to prevent resource exhaustion
3. **Job Timeouts**: Individual jobs are limited to 6 hours to prevent runaway processes
4. **Metrics Collection**: Built-in metrics for monitoring system performance

## Production Deployment

For production deployment, consider:

1. **Reverse Proxy**: Use NGINX or similar for SSL termination and additional security
2. **Process Management**: Use systemd, Docker, or Kubernetes for process management
3. **Monitoring**: Integrate with Prometheus/Grafana using the `/metrics` endpoint
4. **Logging**: Configure structured logging for centralized log management
5. **Database**: Replace in-memory job storage with a persistent database (Redis, PostgreSQL)
6. **Caching**: Implement Redis caching for frequently accessed data
7. **Load Balancing**: Use a load balancer for horizontal scaling

## Version Information

- **Current Version**: 0.1.0
- **API Version**: /api/v1 (prefix configurable via API_V1_STR environment variable)
- **Release Date**: 2026-05-09

## Support

For questions or issues regarding the API, please refer to the project documentation or contact the development team.