# API Guide

## Base URL
```
http://localhost:8000
```

Production: `https://arprofm.com`

## OpenAPI Documentation
- Swagger UI: `http://localhost:8000/docs`
- ReDoc: `http://localhost:8000/redoc`

---

## Authentication

The API supports both authenticated and unauthenticated access:

- **Authenticated (Google OAuth)**: Uses Gemini API (user's quota, zero cost)
- **Unauthenticated**: Falls back to Ollama (server-side, if configured)

Pass the Google OAuth access token in the `Authorization` header:
```
Authorization: Bearer <access_token>
```

---

## Endpoints

### Health Check
```http
GET /health
```

**Response:**
```json
{
  "status": "healthy",
  "service": "liftlogic"
}
```

---

### API Info
```http
GET /api
```

**Response:**
```json
{
  "name": "LiftLogic API",
  "version": "2.0.0",
  "description": "AI-native elevator/lift documentation intelligence",
  "docs": "/docs"
}
```

---

### Search Documents

```http
POST /api/search
Content-Type: application/json

{
  "query": "KONE fault code 505",
  "limit": 20,
  "manufacturer": "KONE",
  "use_rag": true
}
```

**Response:**
```json
{
  "query": "KONE fault code 505",
  "results": [
    {
      "doc_id": 1,
      "filename": "kone_ecospace_manual.pdf",
      "content": "Fault 505 indicates a door zone sensor...",
      "manufacturer": "KONE",
      "score": 0.92
    }
  ],
  "total": 15,
  "answer": "Fault code 505 in KONE elevators indicates...",
  "llm_provider": "gemini"
}
```

**Fields:**
- `query` (required): Search text (min 1 character)
- `limit` (optional): Max results (1-100, default 20)
- `manufacturer` (optional): Filter by manufacturer
- `use_rag` (optional): Generate AI answer (default false)

**Response Fields:**
- `llm_provider`: "gemini" (authenticated) or "ollama" (unauthenticated)
- `answer`: AI-generated answer (only if `use_rag: true`)

---

### Fault Code Lookup

```http
GET /api/search/fault/{code}?manufacturer=KONE
```

**Response:**
```json
{
  "code": "505",
  "manufacturer": "KONE",
  "explanation": "Fault 505 is a door zone sensor malfunction...",
  "llm_provider": "gemini",
  "db_results": [...],
  "graph_data": {
    "name": "Door Zone Fault",
    "description": "Door zone sensor malfunction",
    "resolution_procedures": ["Clean sensor", "Check alignment"],
    "test_procedures": ["Run door cycle test"]
  }
}
```

---

### Extract PDF

```http
POST /api/extraction/extract
Content-Type: multipart/form-data

file: <binary PDF data>
```

**Response:**
```json
{
  "filename": "manual.pdf",
  "components_count": 45,
  "connections_count": 120,
  "fault_codes_count": 23,
  "quality_score": 0.87
}
```

---

### Get Extraction Status

```http
GET /api/extraction/status/{job_id}
```

**Response:**
```json
{
  "job_id": "abc123",
  "status": "completed",
  "progress": 100,
  "result": {...}
}
```

---

### Diagnose Fault

```http
POST /api/diagnosis/diagnose
Content-Type: application/json

{
  "fault_code": "F505",
  "manufacturer": "KONE",
  "symptoms": ["door won't close", "intermittent alarm"],
  "mode": "detailed"
}
```

**Response:**
```json
{
  "fault_code": "F505",
  "description": "Door zone sensor malfunction",
  "severity": "medium",
  "causes": ["Dirty or misaligned door sensor"],
  "remedies": ["Clean sensor", "Check alignment"],
  "related_components": ["K1 Relay", "Door Controller"],
  "confidence": 0.9
}
```

**Modes:**
- `quick`: Fast basic diagnosis (2-3 sentences)
- `detailed`: Comprehensive analysis (default)
- `safety`: Safety-focused analysis
- `maintenance`: Maintenance-focused analysis
- `strategic`: Strategic planning analysis

**Severity Levels:**
- `critical`: Immediate action required (elevator locks out)
- `high`: Prevents certain operations
- `medium`: Standard fault
- `low`: Warning/alarm only

---

### Safety Analysis

```http
POST /api/diagnosis/analyze/safety?document_id=1
```

**Response:**
```json
{
  "document_id": 1,
  "filename": "kone_manual.pdf",
  "manufacturer": "KONE",
  "analysis": "Safety analysis text from AI...",
  "llm_provider": "gemini",
  "critical_risks": [],
  "recommendations": []
}
```

---

### Maintenance Analysis

```http
POST /api/diagnosis/analyze/maintenance?document_id=1
```

**Response:**
```json
{
  "document_id": 1,
  "filename": "kone_manual.pdf",
  "manufacturer": "KONE",
  "analysis": "Maintenance schedule text from AI...",
  "llm_provider": "gemini",
  "schedule": {
    "monthly": [],
    "quarterly": [],
    "annually": []
  }
}
```

---

## Error Responses

All errors return:
```json
{
  "detail": "Error message here"
}
```

**Status Codes:**
- `400` - Bad request (invalid input)
- `404` - Resource not found
- `422` - Validation error
- `500` - Internal server error
- `503` - Service unavailable (e.g., Gemini API down)

---

## Rate Limiting

The API includes rate limiting middleware:
- **Default:** 60 requests per minute per IP
- **Headers returned:**
  - `X-RateLimit-Limit`: Maximum requests per window
  - `X-RateLimit-Remaining`: Requests remaining
  - `X-RateLimit-Reset`: Window reset time

Gemini API has additional rate limits:
- Automatic retry with exponential backoff
- OAuth/ADC mode: Uses user's quota (zero cost)

---

## Request Tracking

All requests include tracking headers:
- `X-Request-ID`: Unique request identifier (auto-generated or pass your own)
- `X-Response-Time-Ms`: Request processing time in milliseconds

---

## CORS

CORS is enabled for all origins in development. Configure `allow_origins` in production.
