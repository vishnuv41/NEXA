# NEXA WAF - Security Considerations

## Threat Model

### Assets Protected
- Demo application endpoints
- Request/response data
- Model artifacts
- Configuration/policies
- Analyst feedback data

### Attack Surface
1. **WAF Gateway** - HTTP endpoint accepting arbitrary requests
2. **Demo Application** - Target of proxied requests
3. **API Endpoints** - Management interfaces
4. **Event Streaming** - Redis/SSE communication
5. **Database** - Persistent storage

### Trust Boundaries
```
Internet → WAF Gateway → Detection Pipeline → Demo App
                ↓
         PostgreSQL + Redis
                ↓
         Frontend (Dashboard)
```

## Security Controls

### Input Validation
- All API inputs validated via Pydantic schemas
- Request body size limited (10MB default)
- Path length limited (2048 chars)
- Header values truncated (500 chars)

### Output Encoding
- JSON responses properly encoded
- SSE events JSON-encoded
- No HTML rendering of user input

### Authentication & Authorization
- **Current**: No auth (local development)
- **Production**: Add JWT/OAuth2 for API endpoints
- **Demo App**: Bearer token demo auth

### Secrets Management
- No secrets in code or config
- `.env` file for local development
- Docker secrets for production
- Model artifacts not encrypted (public model)

### Data Protection
- **PII Redaction**: Headers (Authorization, Cookie, API keys) redacted before storage
- **Request Bodies**: Truncated to 500 chars in summaries
- **Database**: No encryption at rest (local dev)
- **Network**: TLS recommended for production

### Rate Limiting
- Per-IP rate limiting on WAF gateway
- Configurable thresholds
- Redis-backed for distributed deployment

## WAF-Specific Security

### Detection Pipeline
- **No external dependencies** for core detection
- Model runs locally (PyTorch)
- Rule engine deterministic
- No code execution from request data

### Attack Lab
- **Targets only local demo app**
- No external target configuration
- Variant generation sandboxed
- Results not executable

### Shadow Mode
- Logs decisions without enforcement
- Safe for testing new policies
- No request modification

## Known Vulnerabilities & Mitigations

### Potential Issues
| Component | Risk | Mitigation |
|-----------|------|------------|
| Request parsing | DoS via large bodies | Size limits, streaming parse |
| Regex rules | ReDoS | Timeout, simplified patterns |
| ML inference | GPU OOM | Batch size limits, CPU fallback |
| Redis streams | Memory exhaustion | Maxlen trimming, TTL |
| SSE connections | Connection exhaustion | Heartbeat, max connections |

### Dependency Security
- Regular `pip-audit` / `npm audit`
- Pinned versions in lockfiles
- Minimal dependency trees

## Secure Deployment Checklist

### Development
- [ ] Use `.env` with strong secrets
- [ ] Don't commit `.env` files
- [ ] Run with `DEBUG=false` in shared envs

### Production
- [ ] Enable TLS everywhere
- [ ] Configure proper CORS origins
- [ ] Set up WAF auth (API keys/OAuth)
- [ ] Enable database encryption
- [ ] Configure Redis AUTH
- [ ] Set up log aggregation
- [ ] Enable metrics/alerting
- [ ] Regular security scans
- [ ] Backup strategy for PostgreSQL
- [ ] Incident response plan

## Incident Response

### Detection
- Monitor `/api/waf/stats` for anomaly spikes
- Alert on blocked request rate increase
- Log all `BLOCK` decisions with context

### Response
1. Isolate affected components
2. Review recent decisions in dashboard
3. Check Attack Lab for similar patterns
4. Update rules/policy if needed
5. Document incident

### Recovery
- Restore from database backup if corrupted
- Re-deploy model if compromised
- Rotate secrets if exposed

## Compliance Notes

### Data Handling
- No persistent PII storage (redacted)
- Analyst feedback contains only labels
- Session data: IP + behavioral metrics only

### Retention
- Events: Configurable (default 30 days via cleanup job)
- Sessions: TTL-based (1 hour default)
- Model versions: Indefinite

## Reporting Security Issues

For security issues in this prototype:
1. Do not create public issues
2. Contact maintainers directly
3. Include reproduction steps
4. Allow time for fix before disclosure