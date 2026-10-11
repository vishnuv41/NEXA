# NEXA Adaptive Transformer WAF - Architecture

## High-Level Architecture

```
┌─────────────┐     ┌──────────────┐     ┌─────────────────┐     ┌──────────────┐
│   Client    │────▶│  WAF Gateway │────▶│ Detection Pipeline│────▶│  Risk Engine │
└─────────────┘     └──────────────┘     └─────────────────┘     └──────┬───────┘
                                                                        │
                    ┌───────────────────────────────────────────────────┘
                    ▼
            ┌───────────────┐     ┌──────────────┐     ┌────────────────┐
            │  Enforcement  │────▶│ Demo App     │     │ Event Storage  │
            │  (Allow/Block/│     │  (Target)    │     │  (PostgreSQL)  │
            │  Rate/Challenge)     └──────────────┘     └───────┬────────┘
            └───────────────┘                                    │
                                                                 ▼
                                                        ┌────────────────┐
                                                        │  Redis Streams │
                                                        └───────┬────────┘
                                                                │
                                                                ▼
                                                        ┌────────────────┐
                                                        │  SSE Manager   │
                                                        └───────┬────────┘
                                                                │
                                                                ▼
                                                        ┌────────────────┐
                                                        │  Frontend      │
                                                        │  (Dashboard)   │
                                                        └────────────────┘
```

## Component Overview

### 1. WAF Gateway (`backend/app/waf/gateway.py`)
Main entry point that orchestrates the full detection pipeline:
- Request normalization
- ML inference
- Rule engine matching
- Application context validation
- Session behavior analysis
- Risk calculation
- Decision enforcement

### 2. Detection Pipeline Components

#### Request Normalizer (`backend/app/waf/normalizer.py`)
- Standardizes HTTP requests for consistent processing
- Redacts sensitive headers/parameters
- Creates structured summaries for storage
- Generates sequence strings for ML model

#### ML Inference Service (`backend/app/ml/inference.py`)
- Loads and manages Transformer model
- Tokenizes requests using byte-level tokenizer
- Runs batched inference for performance
- Returns malicious probability, attack class, anomaly score

#### Rule Engine (`backend/app/waf/rules.py`)
- Deterministic pattern matching for known attacks
- Categories: SQLi, XSS, Path Traversal, Command Injection
- Configurable rules with severity scoring
- Returns matched rules and aggregate score

#### Session Analyzer (`backend/app/behavior/session.py`)
- Tracks request sequences per session/IP
- Detects enumeration, high frequency, auth anomalies
- Maintains risk timeline and endpoint sequences
- Persists to PostgreSQL periodically

#### Application Context Engine (`backend/app/context/openapi.py`)
- Parses OpenAPI specifications
- Matches requests to endpoint contracts
- Validates parameters, auth, content types
- Returns contract violation score and reasons

### 3. Risk Engine (`backend/app/risk/engine.py`)
- Weighted combination of all signals
- Configurable thresholds for each decision tier
- Supports Enforce and Shadow modes
- Sensitivity adjustments per endpoint

### 4. Explainability (`backend/app/explainability/explainer.py`)
- Generates structured evidence for each decision
- Maps signals to human-readable explanations
- Provides signal breakdown with visual indicators

### 5. Event Streaming (`backend/app/streaming/events.py`)
- Redis Streams for event persistence
- SSE Manager for real-time dashboard updates
- Automatic reconnection handling

### 6. API Layer (`backend/app/api/`)
- `/api/waf/*` - WAF inspection, policy, feedback
- `/api/events/*` - Live events, sessions, campaigns
- `/api/context/*` - OpenAPI import, endpoints
- `/api/attack-lab/*` - Adversarial testing
- `/api/batch/*` - Bulk analysis
- `/api/models/*` - Model management, evaluation

## Data Flow

### Request Inspection Flow
```
1. HTTP Request received
2. Normalize request (headers, body, query, path)
3. Tokenize for ML model
4. Run Transformer inference → malicious_prob, anomaly_score, attack_class
5. Run rule engine → rule_score, matched_rules
6. Match endpoint in OpenAPI context → app_score, violations
7. Analyze session behavior → session_score, reasons
8. Calculate weighted risk score
9. Apply thresholds → decision (allow/monitor/rate_limit/challenge/block)
10. Generate explanation
11. Persist to PostgreSQL
12. Publish to Redis Stream
13. Return decision to client
14. If allowed, proxy to demo app
```

### Live Dashboard Flow
```
1. WAF publishes event to Redis Stream "waf:events"
2. SSE Manager reads from stream (blocking XREAD)
3. Broadcasts to all connected SSE subscribers
4. Frontend receives events via EventSource
5. Updates live table and stats in real-time
```

### Batch Analysis Flow
```
1. Upload CSV/JSON file
2. Parse into request objects
3. Background worker processes each request through WAF
4. Collect results, calculate metrics if labels present
5. Store run metadata in PostgreSQL
6. Return results via API
```

### Attack Lab Flow
```
1. Select attack family and variant count
2. Generate variants using transformations (encoding, obfuscation)
3. Send each variant through WAF inspection
4. Record detection/miss for each variant
5. Calculate detection rate, latency stats
6. Display detailed results table
```

## Database Schema

```
RequestEvent ──▶ ThreatEvent
     │
     ├──▶ Session
     │
     ├──▶ EndpointProfile
     │
     ├──▶ AttackCampaign
     │
     └──▶ AnalystFeedback

ModelVersion
EvaluationRun
```

## Security Boundaries

- WAF Gateway only proxies to configured `DEMO_APP_URL`
- No outbound internet access from detection pipeline
- Attack Lab only targets local demo endpoints
- Sensitive data redacted before storage
- Model runs locally (no external API calls)

## Scaling Considerations

- ML inference: batch requests, use GPU if available
- Redis Streams: partition by source IP for horizontal scaling
- PostgreSQL: read replicas for dashboard queries
- Session state: Redis-backed for multi-instance deployment

## Deployment Topology

```
                    ┌─────────────┐
                    │   Internet  │
                    └──────┬──────┘
                           │
                    ┌──────▼──────┐
                    │  Load Bal.  │
                    └──────┬──────┘
                           │
          ┌────────────────┼────────────────┐
          ▼                ▼                ▼
    ┌──────────┐     ┌──────────┐     ┌──────────┐
    │ WAF Pod 1│     │ WAF Pod 2│     │ WAF Pod N│
    └────┬─────┘     └────┬─────┘     └────┬─────┘
         │                │                │
         └────────────────┼────────────────┘
                          ▼
              ┌───────────────────────┐
              │   Redis Cluster       │
              │   (Streams + Session) │
              └───────────┬───────────┘
                          │
              ┌───────────▼───────────┐
              │   PostgreSQL Cluster  │
              │   (Primary + Replicas)│
              └───────────────────────┘
```