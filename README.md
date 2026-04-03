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
