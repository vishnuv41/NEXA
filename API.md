# NEXA WAF - API Reference

Base URL: `http://localhost:8000/api`

## Authentication
Currently no authentication required for local development.

## WAF Endpoints

### Inspect Request
```http
POST /waf/inspect
Content-Type: application/json

{
  "method": "GET",
  "path": "/search",
  "query": "q=test",
  "headers": {"user-agent": "test"},
  "body": "",
  "source_ip": "127.0.0.1",
  "session_id": "optional-session-id",
  "user_id": "optional-user-id"
}
```

Response:
```json
{
  "request_id": "abc123",
  "decision": "allow",
  "risk_score": 0.15,
  "attack_type": null,
  "transformer_score": 0.1,
  "anomaly_score": 0.05,
  "session_score": 0.0,
  "application_score": 0.0,
  "rule_score": 0.0,
  "reasons": [],
  "signals": {"transformer": 0.1, "anomaly": 0.05, "session": 0.0, "application": 0.0, "rules": 0.0},
  "latency_ms": 12
}
```

### Inspect and Proxy
```http
POST /waf/inspect-and-proxy
```
Same request body as `/inspect`. If decision allows, proxies to demo app and returns upstream response.

### Get/Set Mode
```http
GET /waf/mode
POST /waf/mode {"mode": "enforce"}  // or "shadow"
```

### Policy Management
```http
GET /waf/policy
PUT /waf/policy {
  "thresholds": {"allow": 0.2, "monitor": 0.45, "rate_limit": 0.65, "challenge": 0.85, "block": 1.0},
  "weights": {"transformer": 0.35, "anomaly": 0.15, "session": 0.2, "application": 0.2, "rules": 0.1}
}
```

### Submit Feedback
```http
POST /waf/feedback {
  "request_id": "abc123",
  "analyst_label": "sql_injection",
  "reason": "Confirmed SQLi attempt"
}
```

### Get Events
```http
GET /waf/events?limit=100&decision=block&attack_type=sql_injection
GET /waf/events/{request_id}
GET /waf/events/{request_id}/explanation
GET /waf/stats
```

## Events Endpoints (Real-time)

### SSE Stream
```http
GET /events/stream
```
Server-Sent Events stream for live updates. Events have types: `request`, `stats`, `heartbeat`.

### Recent Events
```http
GET /events/recent?limit=50
GET /events/threats?limit=50
GET /events/stats/summary
```

### Sessions
```http
GET /events/sessions?limit=50&min_risk=0.5
GET /events/sessions/{session_id}
GET /events/sessions/{session_id}/events?limit=100
```

### Campaigns
```http
GET /events/campaigns?limit=50
```

## Application Context

### Import OpenAPI
```http
POST /context/openapi/import {
  "spec": {...},
  "source": "json",
  "base_url": "http://localhost:8001"
}

POST /context/openapi/import/file (multipart/form-data)
```

### Endpoints
```http
GET /context/endpoints
GET /context/endpoints/summary
GET /context/endpoints/{id}
POST /context/endpoints/{id}/sensitivity {"sensitivity": "high"}
```

## Attack Lab

### Run Test
```http
POST /attack-lab/run {
  "attack_family": "sql_injection",
  "base_payloads": ["' OR 1=1--"],
  "variant_count": 25,
  "target_endpoint": "/search"
}
```

### Get Results
```http
GET /attack-lab/runs/{run_id}
GET /attack-lab/runs
GET /attack-lab/payloads/families
```

## Batch Analysis

### Analyze File
```http
POST /batch/analyze (multipart/form-data)
- file: CSV or JSON
- has_labels: boolean
```

### Get Results
```http
GET /batch/runs/{run_id}
GET /batch/runs
POST /batch/runs/{run_id}/export?format=json|csv
```

## Models

### Model Management
```http
GET /models
GET /models/active
GET /models/{id}
POST /models/{id}/activate
GET /models/info/current
```

### Evaluation
```http
POST /models/evaluate {"dataset_name": "test", "run_name": "eval_1"}
GET /models/evaluation/runs
GET /models/evaluation/runs/{id}
```

## Health Check
```http
GET /health
GET /api/waf/health
```

Response:
```json
{
  "api": "healthy",
  "database": "healthy",
  "redis": "healthy",
  "model": "ready",
  "version": "0.1.0"
}
```

## Data Models

### DecisionEnum
`allow` | `monitor` | `rate_limit` | `challenge` | `block` | `would_block`

### ThreatTypeEnum
`benign` | `sql_injection` | `xss` | `path_traversal` | `command_injection` | `other_malicious`

### WAFModeEnum
`enforce` | `shadow`

### SensitivityEnum
`low` | `medium` | `high` | `critical`

## Error Responses
```json
{
  "detail": "Error message"
}
```
HTTP status codes: 400, 404, 500