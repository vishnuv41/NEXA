# NEXA WAF - Demo Guide

## Quick Start

### 1. Start the System
```bash
docker compose up --build
```

Wait for all services to be healthy (check with `docker compose ps`).

### 2. Access the Dashboard
Open http://localhost:3000 in your browser.

### 3. Verify Services
- Frontend: http://localhost:3000
- Backend API: http://localhost:8000/docs
- Demo App: http://localhost:8001

## Demo Scenarios

### Scenario 1: Normal Traffic
1. Go to **Overview** page
2. Click **"Generate Legitimate Traffic"**
3. Observe live requests in **Live Monitor**
4. All requests should show `ALLOW` with low risk scores

### Scenario 2: SQL Injection Attack
1. Go to **Live Monitor**
2. Click **"Generate Attack Traffic"**
3. Observe blocked requests with `BLOCK` decision
4. Click on a blocked event to see **Request Details**
5. Note the evidence: transformer, rules, application context

### Scenario 3: Explainable Decisions
1. In **Live Monitor**, click the eye icon on any event
2. Review the **Signal Breakdown** showing all 5 signals
3. Read the **Evidence** section with specific reasons
4. See **Policy Thresholds** showing which threshold triggered

### Scenario 4: Session Analysis
1. Go to **Sessions** page
2. Generate attack traffic multiple times from same IP
3. Click on a session to see **Request Timeline**
4. Observe risk escalation over time
5. Note behavioral signals: enumeration, frequency, auth anomalies

### Scenario 5: Application-Aware Detection
1. Go to **App Context** page
2. Observe imported endpoints from demo app OpenAPI spec
3. Send request violating contract (e.g., string ID for integer param)
4. See increased application context score in event details

### Scenario 6: Adversarial Robustness Testing
1. Go to **Attack Lab**
2. Select **SQL Injection** family
3. Set **Variant Count** to 25
4. Click **Run Robustness Test**
5. Wait for completion
6. Review results:
   - Detection rate
   - Missed variants
   - Transformation breakdown
7. Test other families: XSS, Path Traversal, Command Injection

### Scenario 7: Shadow Mode
1. Go to **Policies** page
2. Switch to **Shadow Mode**
3. Generate attack traffic
4. Observe `WOULD_BLOCK` decisions (requests still allowed)
5. Switch back to **Enforce Mode**
6. Generate same attack - now `BLOCK`ed

### Scenario 8: Batch Analysis
1. Go to **Batch Analysis**
2. Prepare CSV with test requests (see format below)
3. Upload file with/without labels
4. View results: precision, recall, F1, confusion matrix
5. Export results as CSV/JSON

### Scenario 9: Model Evaluation
1. Go to **Models** page
2. Click **Run Evaluation**
2. Wait for completion
3. View per-class metrics, confusion matrix, latency

## CSV Format for Batch Analysis

```csv
method,path,query,headers,body,source_ip,session_id,user_id,label
GET,/search,q=laptop,{},"",127.0.0.1,session-1,user-1,benign
GET,/search,q=' OR 1=1--,{},"",127.0.0.1,session-2,user-2,sql_injection
POST,/login,,{"content-type":"application/json"},"username=admin",127.0.0.1,session-3,user-3,benign
```

## JSON Format for Batch Analysis

```json
{
  "requests": [
    {
      "method": "GET",
      "path": "/search",
      "query": "q=laptop",
      "headers": {},
      "body": "",
      "source_ip": "127.0.0.1",
      "label": "benign"
    }
  ]
}
```

## Attack Lab Payloads

Default payloads per family:

### SQL Injection
- `' OR '1'='1`
- `' OR 1=1--`
- `' UNION SELECT NULL,NULL,NULL--`
- `'; DROP TABLE users--`
- `admin'--`

### XSS
- `<script>alert('XSS')</script>`
- `<img src=x onerror=alert('XSS')>`
- `<svg onload=alert('XSS')>`
- `javascript:alert('XSS')`

### Path Traversal
- `../../../etc/passwd`
- `..\\..\\..\\windows\\system32\\drivers\\etc\\hosts`
- `%2e%2e%2f%2e%2e%2f%2e%2e%2fetc%2fpasswd`

### Command Injection
- `; cat /etc/passwd`
- `| cat /etc/passwd`
- `` `cat /etc/passwd` ``
- `$(cat /etc/passwd)`

Transformations applied: URL encoding, double encoding, case variation, whitespace, SQL comments, Base64, hex, unicode, HTML entities, null bytes, parameter pollution, JSON/XML wrapping.

## Expected Results

### Normal Traffic
- Risk scores: 0-20%
- Decisions: ALLOW
- Latency: 5-20ms

### Known Attacks
- Risk scores: 70-95%
- Decisions: BLOCK
- Detection rate: >90% on known variants

### Adversarial Variants
- Detection rate varies by transformation
- Encoding often detected
- Heavy obfuscation may reduce detection

### Session Attacks
- Risk escalates over sequential requests
- Enumeration detected after 10+ object IDs
- Auth bypass flagged immediately

## Troubleshooting

### Dashboard not loading
- Check `docker compose logs frontend`
- Ensure backend is healthy: `curl http://localhost:8000/api/waf/health`

### No live events
- Check SSE connection in browser dev tools
- Verify Redis: `docker compose logs redis`
- Check backend logs: `docker compose logs backend`

### Model not loaded
- Check `docker compose logs backend` for model loading errors
- Ensure model artifact exists at `./ml/artifacts/model.pt`
- Run training: `cd backend && python scripts/train_model.py`

### Demo app unreachable
- Check `docker compose logs demo-app`
- Verify port 8001: `curl http://localhost:8001/`

## Stopping the Demo
```bash
docker compose down
```

To remove all data:
```bash
docker compose down -v
```