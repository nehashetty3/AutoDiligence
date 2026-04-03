# AutoDiligence

AutoDiligence is an AI-powered M&A due diligence platform that ingests public company data, evaluates cross-functional risk signals, benchmarks targets against competitors, and produces consultant-style diligence outputs in minutes.

## Core Capabilities
- Financial anomaly detection from SEC, Yahoo Finance, and exchange-specific fallbacks
- News sentiment scoring and trend analysis
- Patent activity and innovation velocity tracking
- Hiring health and hiring trend analysis
- Multi-signal M&A risk scoring
- Competitor benchmarking and industry-relative positioning
- Historical risk tracking and acquisition premium estimation
- PDF report export
- Watchlist and alert workflow

## Stack
- Backend: FastAPI, SQLAlchemy, PostgreSQL
- Frontend: React, Axios, Recharts
- ML/NLP: XGBoost, SHAP, transformers, torch, spaCy, scikit-learn
- Data: SEC filings, Yahoo Finance, NewsAPI, patents, hiring signals
- Deployment: Docker Compose, AWS EC2, Netlify, Caddy

## Repository Layout
- `backend/` - ingestion pipelines, analytics, database models, API routes
- `frontend/` - React application
- `docker-compose.yml` - full stack container deployment
- `DEPLOYMENT.md` - detailed infrastructure notes

## Full Stack
- Presentation layer: React frontend with analysis tabs, charts, benchmarking views, and export actions
- API layer: FastAPI backend for company analysis, benchmarking, history, competitors, and reporting
- Data layer: PostgreSQL for companies, risk assessments, cached outputs, and historical analysis records
- Analytics layer: financial anomaly detection, sentiment analysis, hiring analysis, patent trend analysis, and peer benchmarking
- ML/NLP layer: XGBoost-style risk modeling, SHAP-style interpretation, transformers, torch, and spaCy preprocessing
- Infrastructure layer: local development, Docker Compose, AWS EC2 hosting, Netlify hosting, and Caddy HTTPS proxying

## Project Motivation
Traditional M&A due diligence is fragmented across filings, market data, news, hiring signals, and sector comparisons. AutoDiligence was built to bring those early-stage diligence checks into one workflow so a user can get a fast, structured first-pass view of company risk.

The platform is designed to accelerate the initial diligence cycle, not replace full transaction work. Its main value is reducing manual context switching and turning scattered public signals into a single explainable risk narrative.

## How It Works
1. The user enters a company name or ticker.
2. The backend resolves the company and normalizes aliases.
3. Multiple ingestion pipelines gather financial, news, patent, hiring, and benchmark data.
4. Analytics modules score those signals and synthesize them into a final risk profile.
5. The frontend presents the result as an analyst-friendly diligence dashboard with tabs, comparisons, and report export.

## Analysis Pipeline

### 1. Company Resolution
- maps user input to the correct legal entity or ticker
- handles aliases, partial names, and ticker ambiguity
- reduces wrong-company matches for common short names

### 2. Financial Intelligence
- fetches company financial and market data
- detects anomalies across revenue, margins, leverage, cash health, and operating consistency
- turns raw financial signals into diligence-oriented warnings

### 3. News and Sentiment
- ingests company news coverage
- scores tone and tracks whether sentiment is improving or declining
- incorporates sentiment as a supporting diligence signal rather than a standalone decision

### 4. Innovation and Patents
- evaluates patent activity and recent innovation momentum
- highlights whether the company appears stable, accelerating, or stagnant on the innovation side

### 5. Hiring Signals
- estimates hiring health and hiring trend
- uses employment momentum as a proxy for business confidence, scaling pressure, or contraction

### 6. Risk Synthesis
- combines analytics signals into a final risk score
- classifies the company into low, medium, or high risk
- exposes supporting factors so the score remains interpretable

### 7. Competitor Benchmarking
- compares the target against industry-relevant peers
- shows whether the company is stronger or weaker than sector context
- filters out obviously unrelated competitors

## Key Product Screens
- `Analyze`: search and run a new diligence workflow
- `Overview`: consolidated score and primary diligence metrics
- `Financials`: financial anomaly and benchmark context
- `Sentiment & News`: tone, coverage, and trend direction
- `Hiring`: hiring health and trend view
- `Report`: summary-ready view for export and presentation
- `Competitors`: peer set and industry-relative comparison
- `Compare`: side-by-side target review
- `Watchlist`: repeat monitoring workflow

## Architecture

### Frontend
- React single-page application
- environment-based API routing for local, split, and hosted deployments
- tab-based UX designed for rapid diligence review

### Backend
- FastAPI service that orchestrates ingestion, analysis, persistence, and reporting
- route layer for analysis, competitors, benchmark, history, and PDF workflows
- analytics-first response shaping for frontend consumption

### Data Storage
- PostgreSQL stores normalized companies, assessments, and historical results
- persistent records support repeat analysis and trend tracking over time

### Hosting
- frontend can run locally or on Netlify
- backend can run locally, in Docker, or on EC2
- Caddy terminates TLS for the split Netlify + EC2 deployment

## Deployment Architecture

### Option A: Full Stack on EC2 with Docker
- React frontend served through Nginx
- FastAPI backend behind the frontend service
- PostgreSQL in Docker
- good fit for a single-machine full-stack deployment

### Option B: Netlify Frontend + EC2 Backend
- React frontend hosted on Netlify
- FastAPI and PostgreSQL hosted on EC2
- Caddy provides HTTPS for the backend
- useful when you want a lighter frontend host and more direct control over backend infrastructure

### Current Working Hosted Setup
- frontend deployed on Netlify
- backend deployed on AWS EC2
- backend exposed securely through Caddy and `sslip.io`
- frontend configured with `REACT_APP_API_BASE_URL` pointing to the secure backend host

## Current Limitations
- model performance metrics are internally benchmarked and not fully validated on real historical M&A outcome datasets
- some premium and benchmark components remain heuristic rather than calibrated on proprietary deal datasets
- public-data coverage varies by company, geography, and exchange
- the current hosted backend is functional but not production-hardened for scale
- split deployment depends on backend HTTPS; browser security blocks insecure API calls from secure frontends

## Future Improvements
- validate the scoring system on real external M&A outcome datasets
- improve acquisition premium calibration with historical comparable transactions
- expand and refine competitor universe construction
- move the backend to a persistent process manager or systemd service
- add a custom domain for a cleaner public-facing deployment
- improve observability, long-running ingestion resilience, and operational monitoring
- broaden non-US company coverage and exchange support
- surface clearer confidence and explanation layers for the final score

## Local Development

### Prerequisites
```bash
brew install python@3.11 postgresql@15 git node
brew services start postgresql@15
createdb ma_diligence
```

### Setup
```bash
git clone https://github.com/nehashetty3/AutoDiligence.git
cd AutoDiligence
cp .env.example .env
# fill in your API keys in .env
./setup.sh
```

### Run Locally
Backend:
```bash
cd /path/to/AutoDiligence
source venv/bin/activate
python -m uvicorn backend.main:app --host 0.0.0.0 --port 8000 --reload
```

Frontend:
```bash
cd /path/to/AutoDiligence/frontend
npm start
```

Open [http://localhost:3000](http://localhost:3000)

## Environment Variables

Backend values are defined in [.env.example](/Users/neha/autodiligence/.env.example).

Common values to set:
- `GROQ_API_KEY`
- `NEWS_API_KEY`
- `PINECONE_API_KEY`
- `OPENAI_API_KEY=skip`
- `DATABASE_URL`
- `FRONTEND_URL`

Frontend production API configuration is controlled through [frontend/.env.example](/Users/neha/autodiligence/frontend/.env.example):

```bash
REACT_APP_API_BASE_URL=http://YOUR_API_HOST
```

## Deployment Options

### 1. Full EC2 Docker Deployment

Use this when you want the full app on one server:

```bash
cp .env.example .env
# fill in production values
./setup.sh docker
docker compose up --build -d
```

In this setup:
- frontend is served on port `80`
- backend runs behind the frontend container
- PostgreSQL runs in Docker

See [DEPLOYMENT.md](/Users/neha/autodiligence/DEPLOYMENT.md) for the full EC2 flow.

### 2. Netlify Frontend + EC2 Backend

This is the cheaper split deployment used for the live project setup:

- deploy the React frontend from `frontend/` on Netlify
- run FastAPI and PostgreSQL on EC2
- place Caddy in front of the backend for HTTPS

Netlify settings:
- Base directory: `frontend`
- Build command: `npm run build`
- Publish directory: `build`

Netlify environment variable:

```bash
REACT_APP_API_BASE_URL=https://YOUR_SECURE_BACKEND_HOST
```

Example secure backend host:

```bash
https://autodiligence.16.16.139.126.sslip.io
```

Important:
- if the frontend is deployed on `https`, the backend must also be reachable over `https`
- a plain `http` EC2 API will be blocked by the browser as mixed content

The included [netlify.toml](/Users/neha/autodiligence/netlify.toml) and [frontend/netlify.toml](/Users/neha/autodiligence/frontend/netlify.toml) handle the frontend build and SPA routing.

## Production Notes
- `requirements.txt` includes `yfinance`, which is required by the financial ingestion pipeline
- the backend is expected to run with Python `3.11`
- for public EC2 deployment, expect internet scanners to hit random paths; `404` responses for those are normal
- if you use the split deployment, make sure the backend process is supervised so it survives SSH disconnects and server reboots

## Troubleshooting
- `No module named 'yfinance'`
  - make sure dependencies were installed from the latest [requirements.txt](/Users/neha/autodiligence/requirements.txt)
- Netlify frontend loads but cannot analyze companies
  - verify `REACT_APP_API_BASE_URL` points to the secure backend host
  - trigger `Clear cache and deploy site`
- HTTPS backend returns certificate or timeout errors
  - make sure EC2 security group allows ports `80` and `443`
  - verify your reverse proxy can reach FastAPI on `127.0.0.1:8000`

## Project Status
- local development supported
- full Docker deployment supported
- split Netlify + EC2 deployment supported
- secure HTTPS backend routing supported through Caddy
