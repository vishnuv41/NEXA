# NEXA WAF - Development Guide

## Prerequisites

- Python 3.12+
- Node.js 20+
- Docker & Docker Compose
- PostgreSQL 16 (if not using Docker)
- Redis 7 (if not using Docker)

## Project Structure

```
waf/
├── backend/                 # FastAPI backend
│   ├── app/
│   │   ├── main.py         # App entry point
│   │   ├── config.py       # Settings
│   │   ├── database.py     # DB connection
│   │   ├── models/         # SQLAlchemy models
│   │   ├── schemas/        # Pydantic schemas
│   │   ├── api/            # API routes
│   │   ├── waf/            # WAF gateway
│   │   ├── ml/             # ML inference
│   │   ├── behavior/       # Session analysis
│   │   ├── context/        # OpenAPI context
│   │   ├── risk/           # Risk engine
│   │   ├── explainability/ # Decision explanations
│   │   ├── streaming/      # Redis/SSE
│   │   ├── batch/          # Batch analysis
│   │   └── attacks/        # Attack lab
│   ├── tests/
│   ├── pyproject.toml
│   └── Dockerfile
├── frontend/                # Next.js dashboard
│   ├── app/                # App Router pages
│   ├── components/         # React components
│   ├── hooks/              # Custom hooks
│   ├── lib/                # Utilities
│   ├── types/              # TypeScript types
│   ├── package.json
│   └── Dockerfile
├── ml/                      # ML pipeline
│   ├── model/              # Model architecture
│   ├── training/           # Training scripts
│   ├── evaluation/         # Evaluation scripts
│   └── artifacts/          # Model checkpoints
├── demo-app/               # Target application
│   ├── app.py
│   ├── openapi.yaml
│   └── Dockerfile
├── scripts/                # Utility scripts
├── docker-compose.yml
└── docs/
```

## Local Development

### Backend

```bash
cd backend

# Create virtual environment
python -m venv .venv
source .venv/bin/activate  # Windows: .venv\Scripts\activate

# Install dependencies
pip install -e ".[dev]"

# Copy env file
cp ../.env.example .env

# Run migrations
alembic upgrade head

# Start server
python -m app.main
```

Server runs at http://localhost:8000
API docs at http://localhost:8000/docs

### Frontend

```bash
cd frontend

# Install dependencies
npm install

# Start dev server
npm run dev
```

Frontend runs at http://localhost:3000
Proxies API calls to http://localhost:8000

### Demo App

```bash
cd demo-app

# Install dependencies
pip install -r requirements.txt

# Run
python app.py
```

Demo app runs at http://localhost:8001

### Database & Redis (without Docker)

```bash
# PostgreSQL
# Create database and user
createdb waf
createuser waf
psql -c "ALTER USER waf WITH PASSWORD 'waf'; GRANT ALL PRIVILEGES ON DATABASE waf TO waf;"

# Redis
redis-server
```

## Database Migrations

```bash
cd backend

# Create new migration
alembic revision --autogenerate -m "description"

# Apply migrations
alembic upgrade head

# Downgrade
alembic downgrade -1

# Show history
alembic history
```

## Code Quality

### Backend (Python)

```bash
# Format
ruff format .

# Lint
ruff check .

# Type check
mypy app

# Tests
pytest

# Tests with coverage
pytest --cov=app --cov-report=html
```

### Frontend (TypeScript)

```bash
cd frontend

# Format
npx prettier --write .

# Lint
npm run lint

# Type check
npm run type-check

# Tests
npm test
```

## ML Pipeline

### Training

```bash
cd backend
python scripts/train_model.py
```

Options:
```bash
python scripts/train_model.py --epochs 20 --batch-size 64 --samples 20000
```

### Evaluation

```bash
cd backend
python scripts/evaluate_model.py
```

### Model Artifacts

Trained models saved to `ml/artifacts/`:
- `model.pt` - Best checkpoint
- `config.json` - Model configuration

## Adding New Attack Rules

1. Edit `backend/app/waf/rules.py`
2. Add new `Rule` to `_load_default_rules()`
3. Assign unique ID, category, regex pattern
4. Test with Attack Lab

Example:
```python
Rule(
    id="sqli_008",
    name="SQL Comment Bypass",
    category=RuleCategory.SQL_INJECTION,
    pattern=re.compile(r"(?i)/\*.*\*/", re.IGNORECASE),
    severity=0.85,
    description="Inline SQL comment bypass",
)
```

## Adding New API Endpoints

1. Create schema in `backend/app/schemas/__init__.py`
2. Add route in appropriate `backend/app/api/*.py`
3. Include router in `backend/app/main.py`
4. Add TypeScript types in `frontend/types/api.ts`
5. Create API function in `frontend/lib/api.ts`
6. Build UI component/page

## Frontend Component Development

### Creating a New Page

1. Create component in `frontend/components/pages/`
2. Add route in `frontend/app/` (App Router)
3. Use shared UI components from `frontend/components/ui/`
4. Use hooks from `frontend/hooks/`
5. Use API from `frontend/lib/api.ts`

### State Management

- Global: Zustand store (`frontend/hooks/useAppStore.ts`)
- Local: React useState/useReducer
- Server: React Query / SWR (if added)

### Styling

- Tailwind CSS 4.x utility classes
- CSS variables in `globals.css` for theming
- `cn()` utility for conditional classes
- Respect `prefers-reduced-motion`

## Testing

### Unit Tests

```bash
# Backend
cd backend && pytest tests/ -v

# Frontend
cd frontend && npm test
```

### Integration Tests

```bash
# Backend
cd backend && pytest tests/integration/ -v
```

### E2E Tests

```bash
# Frontend (Playwright)
cd frontend && npx playwright test
```

### Test Data

Fixtures in `tests/fixtures/`:
- Sample requests
- Expected decisions
- Attack payloads

## Debugging

### Backend Logs
```bash
docker compose logs -f backend
# or
python -m app.main  # with DEBUG=true
```

### Frontend Logs
```bash
docker compose logs -f frontend
# or browser dev tools
```

### Database Access
```bash
docker compose exec postgres psql -U waf -d waf
```

### Redis Access
```bash
docker compose exec redis redis-cli
```

### Model Inspection
```python
from app.ml.inference import get_inference_service
service = get_inference_service()
print(service.get_model_info())
```

## Common Tasks

### Reset Database
```bash
docker compose down -v
docker compose up -d postgres
# wait for healthy
docker compose up -d backend
```

### Rebuild Model
```bash
cd backend
python scripts/train_model.py
docker compose restart backend
```

### Update OpenAPI Spec
```bash
# Replace demo-app/openapi.yaml
# Restart backend to reload
docker compose restart backend
```

### Add Demo Data
```bash
# Use the "Generate Traffic" buttons in dashboard
# Or call API directly:
curl -X POST http://localhost:8000/api/waf/inspect-and-proxy \
  -H "Content-Type: application/json" \
  -d '{"method":"GET","path":"/search","query":"q=test","headers":{},"body":"","source_ip":"127.0.0.1"}'
```

## Performance Profiling

### Backend
```bash
# Profiling
python -m cProfile -o profile.stats -m app.main
# Analyze
python -c "import pstats; p = pstats.Stats('profile.stats'); p.sort_stats('cumulative').print_stats(20)"
```

### Frontend
- React DevTools Profiler
- Chrome DevTools Performance tab
- Lighthouse for production build

## Contributing

1. Fork repository
2. Create feature branch
3. Make changes with tests
4. Run quality checks
5. Submit PR

### Commit Convention
```
feat: new feature
fix: bug fix
docs: documentation
style: formatting
refactor: code restructuring
test: adding tests
chore: maintenance
```

### PR Requirements
- All tests pass
- Type checks pass
- Linting passes
- Documentation updated
- No security regressions

## Troubleshooting

### Port Conflicts
```bash
# Check what's using ports
lsof -i :3000 -i :8000 -i :8001 -i :5432 -i :6379
```

### Database Connection Issues
```bash
# Check PostgreSQL logs
docker compose logs postgres
# Verify connection string
echo $DATABASE_URL
```

### Redis Connection Issues
```bash
# Check Redis logs
docker compose logs redis
# Test connection
redis-cli ping
```

### Model Loading Fails
```bash
# Check model file exists
ls -la ml/artifacts/
# Check backend logs
docker compose logs backend | grep -i model
# Retrain if needed
cd backend && python scripts/train_model.py
```

### Frontend Build Fails
```bash
cd frontend
rm -rf .next node_modules
npm install
npm run build
```

## Release Process

1. Update version in `pyproject.toml` and `package.json`
2. Update CHANGELOG.md
3. Create git tag
4. Build Docker images
5. Deploy to staging
6. Run smoke tests
7. Deploy to production