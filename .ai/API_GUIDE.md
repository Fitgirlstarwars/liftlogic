# API Guide

## Base URL
```
http://localhost:8000
```

## OpenAPI Documentation
- Swagger UI: `http://localhost:8000/docs`
- ReDoc: `http://localhost:8000/redoc`

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
  "version": "2.0.0",
  "timestamp": "2024-01-15T10:30:00Z"
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
  "answer": "Fault code 505 in KONE elevators indicates..."
}
```

**Fields:**
- `query` (required): Search text
- `limit` (optional): Max results (1-100, default 20)
- `manufacturer` (optional): Filter by manufacturer
- `use_rag` (optional): Generate AI answer (default false)

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
  "results": [...]
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
  "causes": [
    "Dirty or misaligned door sensor",
    "Wiring fault in door circuit",
    "Faulty door controller board"
  ],
  "root_cause": "Dirty or misaligned door sensor",
  "remedies": [
    "Clean door sensors with dry cloth",
    "Check sensor alignment",
    "Inspect wiring for damage"
  ],
  "related_components": ["K1 Relay", "Door Controller", "Safety Circuit"],
  "safety_implications": ["Do not bypass door safety circuit"],
  "parts_needed": ["Door sensor (P/N 123456)"],
  "estimated_time": "30-60 minutes",
  "confidence": 0.85
}
```

**Modes:**
- `quick`: Fast basic diagnosis
- `detailed`: Comprehensive analysis (default)
- `safety`: Safety-focused analysis

---

### Safety Analysis

```http
POST /api/diagnosis/analyze/safety?document_id=1
```

**Response:**
```json
{
  "document_id": 1,
  "critical_risks": [
    {
      "title": "Exposed high voltage",
      "severity": "critical",
      "mitigation": "Install protective covers"
    }
  ],
  "recommendations": [...]
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
  "schedule": {
    "monthly": ["Lubricate door tracks", "Check safety sensors"],
    "quarterly": ["Inspect wire ropes", "Test emergency brake"],
    "annually": ["Full safety audit", "Load test"]
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

The API uses the Gemini API internally which has rate limits:
- 15 requests per minute (RPM) for standard tier
- Automatic retry with exponential backoff

For high-volume usage, consider:
- Batching extraction requests
- Using `use_rag: false` for simple searches
- Caching frequent queries (handled automatically)

---

## CORS

CORS is enabled for all origins in development. Configure `allow_origins` in production.
