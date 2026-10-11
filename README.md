<div align="center">

# NEXA

### Adaptive, Application-Aware Transformer Web Application Firewall

**Transformer-based detection · risk-adaptive enforcement · explainable decisions**

[![Live Showcase](https://img.shields.io/badge/Live%20Showcase-Demo%20%26%20Overview-2fdc92?style=for-the-badge)](https://nexa-showcase-464221.netlify.app/)
[![Hackathon](https://img.shields.io/badge/Mitigata-CyberForge%202026-0f1311?style=for-the-badge)](https://nexa-showcase-464221.netlify.app/)
![Theme](https://img.shields.io/badge/Theme-AI%20in%20Cybersecurity-2fdc92?style=for-the-badge)

![Python](https://img.shields.io/badge/Python-3.12-3776AB?logo=python&logoColor=white)
![FastAPI](https://img.shields.io/badge/FastAPI-009688?logo=fastapi&logoColor=white)
![PyTorch](https://img.shields.io/badge/PyTorch-EE4C2C?logo=pytorch&logoColor=white)
![Next.js](https://img.shields.io/badge/Next.js-15-000000?logo=nextdotjs&logoColor=white)
![PostgreSQL](https://img.shields.io/badge/PostgreSQL-4169E1?logo=postgresql&logoColor=white)
![Redis](https://img.shields.io/badge/Redis-DC382D?logo=redis&logoColor=white)
![Docker](https://img.shields.io/badge/Docker-2496ED?logo=docker&logoColor=white)

### 🎬 [**Watch the demo video & full project overview → nexa-showcase-464221.netlify.app**](https://nexa-showcase-464221.netlify.app/)

*Demo video · problem to solution · how the AI works · workflow · impact · team*

</div>

---

## Why NEXA?

Traditional WAFs ask one question: **"Is this request malicious?"**
Modern attacks do not fit that question.

| Challenge | Why signature-based WAFs struggle |
|---|---|
| **Evolving payloads** | Attackers vary syntax, encoding and structure to evade signatures. |
| **Context blindness** | A request can look normal alone but be dangerous for a specific endpoint or session. |
| **Behavioral attacks** | Enumeration and endpoint hopping only appear across a sequence of requests. |
| **Rigid enforcement** | Binary allow/block either hurts real users or misses emerging threats. |

NEXA asks a better question:

> **"How risky is this request in this application and session?"**

---

## Key Innovations

1. **Application-aware WAF.** Imports the app's OpenAPI contract to validate endpoints, parameters, authentication and endpoint sensitivity.
2. **Session and sequence-aware detection.** Correlates requests to catch enumeration, abnormal sequences and behavioral deviations.
3. **Adversarial attack lab.** Generates controlled attack variants and measures detection misses and robustness.
4. **Risk-adaptive enforcement.** Converts multiple signals into one risk score and chooses `ALLOW` / `MONITOR` / `RATE_LIMIT` / `CHALLENGE` / `BLOCK`, with a **Shadow Mode** for safe rollout.
5. **Explainable decisions.** Every decision ships with a signal breakdown and structured evidence, never an unexplained score.

---

## How the AI Works

```
HTTP request ─▶ Normalization ─▶ ┌───────────────────────────┐
                                 │ Transformer classifier    │─┐
                                 │ Hybrid rule engine        │ │
                                 │ Application context       │ ├─▶ Risk Engine ─▶ Enforcement ─▶ App
                                 │ Session behavior          │ │        │
                                 └───────────────────────────┘─┘        ▼
                                                                Explainable evidence
```

**Transformer.** A lightweight byte-level Transformer encoder (4 layers, 4 heads, `d_model` 256) reads the normalized request (method, path, query, headers, body) with structure tokens. It has a classification head over 7 classes (`benign`, `sql_injection`, `xss`, `path_traversal`, `command_injection`, `other_malicious`, `anomalous`) and a separate anomaly head. The model runs locally with no remote LLM calls.

**Signal fusion.** The risk engine combines four independent signals, each kept separate so classification confidence, anomaly score and final risk are never confused:

| Signal | What it contributes |
|---|---|
| Transformer | Attack probability and attack class |
| Rule engine | SQLi, XSS, path traversal and command injection patterns |
| Application context | Parameter deviation, auth state, endpoint sensitivity |
| Session behavior | Sequence deviation, enumeration, request frequency |

**Decision scale**

| Risk score | Action |
|---|---|
| 0.00 – 0.20 | `ALLOW` |
| 0.20 – 0.45 | `MONITOR` |
| 0.45 – 0.65 | `RATE_LIMIT` |
| 0.65 – 0.85 | `CHALLENGE` |
| 0.85 – 1.00 | `BLOCK` |

Thresholds are configurable through `.env`. Details are in [MODEL.md](MODEL.md).

---

## Architecture

```
Client / Traffic Generator / Batch CSV·JSON
        │
        ▼
   WAF Gateway ──▶ Detection Pipeline ──▶ Risk Engine ──▶ Enforcement ──▶ Demo App
                          │
                          ▼
              Redis Streams ──▶ SSE ──▶ Live Dashboard   (+ PostgreSQL)
```

One pipeline serves both **streaming** (live traffic) and **batch** (CSV/JSON log analysis) modes. A feedback loop connects observed outcomes back to policy and validation. See [ARCHITECTURE.md](ARCHITECTURE.md).

---

## Features

- Real-time inspection with a live security event stream
- Batch analysis of uploaded traffic logs
- Security dashboard with live monitor, event details, sessions, application context, policies and models pages
- Attack Lab for robustness testing against the local demo app
- Shadow Mode (`WOULD BLOCK`) versus Enforcement Mode (`BLOCK`)
- Safe redaction of sensitive request data
- Model evaluation reporting precision, recall and F1 per class, plus latency

---

## Quick Start

### Prerequisites

- Docker and Docker Compose (recommended)
- Python 3.12+ and Node.js 20+ (for local development)

### Run with Docker Compose

```bash
git clone https://github.com/vishnuv41/NEXA.git
cd NEXA
cp .env.example .env
docker compose up --build
```

| Service | URL |
|---|---|
| Dashboard | http://localhost:3000 |
| Backend API (docs at `/docs`) | http://localhost:8000 |
| Demo application (protected app) | http://localhost:8001 |
| PostgreSQL / Redis | `localhost:5432` / `localhost:6379` |

### Local development

```bash
# Backend
cd backend && pip install -e . && cp ../.env.example .env && alembic upgrade head && python -m app.main

# Frontend
cd frontend && npm install && npm run dev

# Demo app
cd demo-app && pip install -r requirements.txt && python app.py
```

### Train and evaluate the model

```bash
python scripts/train_model.py
python scripts/evaluate_model.py
```

A sample dataset is included: [`sample_waf_dataset.csv`](sample_waf_dataset.csv).

---

## Demo Walkthrough

> Prefer to watch first? The recorded demo is on the **[showcase page](https://nexa-showcase-464221.netlify.app/)**.

1. Open the dashboard at http://localhost:3000.
2. Click **Generate Legitimate Traffic**. Requests show `ALLOW` with low risk.
3. Click **Generate Attack Traffic** and watch the **Live Monitor** flag and block attacks in real time.
4. Open an event to see the **signal breakdown and evidence**.
5. Go to **Attack Lab** and run robustness tests on generated attack variants.
6. Switch to **Shadow Mode**, repeat the attack and see `WOULD BLOCK`.
7. Return to **Enforcement Mode** and see `BLOCK`.

More scenarios are in [DEMO.md](DEMO.md).

---

## Project Structure

```
NEXA/
├── backend/                 # FastAPI backend
│   └── app/
│       ├── waf/             # WAF gateway
│       ├── ml/              # Transformer model, tokenizer, inference
│       ├── behavior/        # Session analysis
│       ├── context/         # OpenAPI application context
│       ├── risk/            # Risk engine
│       ├── explainability/  # Decision evidence
│       ├── streaming/       # Redis Streams + SSE
│       ├── batch/           # Batch analysis
│       ├── attacks/         # Attack Lab generator
│       └── api/ models/ schemas/ services/
├── frontend/                # Next.js dashboard
├── demo-app/                # Protected demo web application + OpenAPI spec
├── scripts/                 # Model training and evaluation
├── sample_waf_dataset.csv
└── docker-compose.yml
```

---

## Tech Stack

| Layer | Technologies |
|---|---|
| Frontend | Next.js 15, React 19, TypeScript, Tailwind CSS, shadcn/ui, Recharts |
| Backend | Python 3.12, FastAPI, Pydantic, SQLAlchemy 2, Alembic, SSE |
| AI / ML | PyTorch, Hugging Face Transformers, scikit-learn, pandas, NumPy |
| Data | PostgreSQL, Redis Streams |
| Deployment | Docker, Docker Compose |

---

## Documentation

| Doc | Contents |
|---|---|
| [ARCHITECTURE.md](ARCHITECTURE.md) | System design and data flow |
| [MODEL.md](MODEL.md) | Transformer architecture, tokenization, training, evaluation |
| [API.md](API.md) | API reference |
| [DEMO.md](DEMO.md) | Step-by-step demo scenarios |
| [SECURITY.md](SECURITY.md) | Security considerations |
| [DEVELOPMENT.md](DEVELOPMENT.md) | Development guide |

---

## Built in 24 Hours

NEXA was built end to end during **Mitigata CyberForge 2026** (theme: *AI in Cybersecurity*): the Transformer pipeline, rule engine, application and session engines, risk and enforcement logic, streaming and batch modes, live dashboard, attack lab and demo application.

## Team NOD35

| | Role | Focus |
|---|---|---|
| **Vishnu Varman V** (Team Lead) | AI, Backend & Security Engineering | Transformer pipeline, WAF request processing, risk assessment, enforcement logic and backend integration |
| **Sai Darshini M** | Frontend, Product Experience & Presentation | Security dashboard experience, demo flow, visual communication, product walkthrough and presentation of validated results |

---

## Security Notes

- NEXA is a **prototype** for demonstration and research. Do not deploy it to production without a security review.
- The attack simulator targets only the local demo endpoints.
- Core detection has no external API dependencies, and the model runs locally.

## License

MIT License. See the `LICENSE` file for details.

<div align="center">

**[🌐 Live Showcase](https://nexa-showcase-464221.netlify.app/)** · **[📦 Source](https://github.com/vishnuv41/NEXA)** · Built by Team NOD35 for Mitigata CyberForge 2026

</div>
