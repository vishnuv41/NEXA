# NEXA — Adaptive, Application-Aware Transformer WAF

A production-style Web Application Firewall platform with five core innovations:

1. **Application-Aware WAF** — OpenAPI-driven endpoint contract validation
2. **Session/Sequence-Aware Detection** — Behavioral analysis across request sequences
3. **Adversarial Attack Simulator** — Controlled variant generation and robustness testing
4. **Risk-Adaptive Enforcement** — ALLOW/MONITOR/RATE_LIMIT/CHALLENGE/BLOCK with Shadow Mode
5. **Explainable WAF Decisions** — Structured evidence with signal breakdown

## Architecture

```
Client → WAF Gateway → Detection Pipeline → Risk Engine → Enforcement → Demo App
                                    ↓
                              Redis Streams → SSE → Live Dashboard
```

## Tech Stack

- **Frontend**: Next.js 15, React 19, TypeScript, Tailwind CSS 4.x, shadcn/ui, Recharts, Anime.js
- **Backend**: Python 3.12, FastAPI, Pydantic, SQLAlchemy 2.x, Alembic, HTTPX, SSE
- **ML**: PyTorch, Hugging Face Transformers, scikit-learn, pandas, NumPy
- **Data**: PostgreSQL 18, Redis Streams
- **Deployment**: Docker, Docker Compose

## Quick Start

### Prerequisites

- Docker & Docker Compose
- Python 3.12+ (for local development)
- Node.js 20+ (for local development)

### Using Docker Compose (Recommended)

```bash
docker compose up --build
```

This starts:
- Frontend: http://localhost:3000
- Backend API: http://localhost:8000
- Demo Application: http://localhost:8001
- PostgreSQL: localhost:5432
- Redis: localhost:6379

### Local Development

**Backend:**
```bash
cd backend
pip install -e .
cp .env.example .env
alembic upgrade head
python -m app.main
```

**Frontend:**
```bash
cd frontend
npm install
npm run dev
```

**Demo App:**
```bash
cd demo-app
pip install -r requirements.txt
python app.py
```

## Model Training

```bash
cd ml
python scripts/train_model.py
python scripts/evaluate_model.py
```

## Demo Flow

1. Open http://localhost:3000 (Dashboard)
2. Click "Generate Legitimate Traffic" on Overview
3. Watch Live Monitor for real-time requests
4. Click "Generate Attack Traffic" to test detection
5. Open Event Details to see explainable decisions
6. Navigate to Attack Lab → Run robustness tests
7. Switch to Shadow Mode → Repeat attack → Observe "WOULD BLOCK"
8. Return to Enforcement Mode → Observe BLOCK

## Project Structure

```
project-root/
├── backend/                 # FastAPI backend
│   ├── app/
│   │   ├── main.py         # Application entry
│   │   ├── config.py       # Configuration
│   │   ├── database.py     # Database setup
│   │   ├── models/         # SQLAlchemy models
│   │   ├── schemas/        # Pydantic schemas
│   │   ├── api/            # API routes
│   │   ├── waf/            # WAF gateway
│   │   ├── ml/             # ML inference
│   │   ├── behavior/       # Session analysis
│   │   ├── context/        # OpenAPI context
│   │   ├── risk/           # Risk engine
│   │   ├── explainability/ # Decision explanations
│   │   ├── streaming/      # Redis Streams + SSE
│   │   ├── batch/          # Batch analysis
│   │   ├── attacks/        # Attack lab
│   │   └── services/       # Shared services
│   └── tests/
├── frontend/               # Next.js frontend
│   ├── app/                # App Router pages
│   ├── components/         # React components
│   ├── hooks/              # Custom hooks
│   ├── lib/                # Utilities
│   └── types/              # TypeScript types
├── ml/                     # ML pipeline
│   ├── model/              # Model architecture
│   ├── training/           # Training scripts
│   ├── evaluation/         # Evaluation scripts
│   └── artifacts/          # Model artifacts
├── demo-app/               # Demo application
├── datasets/               # Synthetic datasets
├── scripts/                # Utility scripts
└── tests/                  # Integration/E2E tests
```

## Documentation

- [Architecture](ARCHITECTURE.md)
- [Security](SECURITY.md)
- [Demo Guide](DEMO.md)
- [Model Details](MODEL.md)
- [API Reference](API.md)
- [Development Guide](DEVELOPMENT.md)

## Security Notes

- This is a **prototype** for demonstration and research
- Do not deploy to production without security review
- Attack simulator targets only local demo endpoints
- No external API dependencies for core detection
- Model runs locally (no remote LLM calls)

## License

MIT License - See LICENSE file for details.