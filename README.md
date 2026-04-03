# AutoDiligence

AutoDiligence is an AI-powered M&A due diligence platform that ingests public company data, runs multi-layer analytics, and generates consultant-style risk assessments and reports.

## Core Capabilities
- Financial anomaly detection from SEC, Yahoo Finance, and exchange-specific fallbacks
- News sentiment analysis with FinBERT-backed scoring and trajectory tracking
- Patent clustering and innovation trend analysis
- Hiring health and red-flag analysis
- Risk scoring with SHAP-style driver explanation
- Competitor benchmarking and industry-relative positioning
- PDF report export
- Watchlist and alert workflow

## Stack
- Backend: FastAPI, SQLAlchemy, PostgreSQL
- Frontend: React, Recharts
- ML/NLP: XGBoost, SHAP, FinBERT, spaCy, scikit-learn
- LLM/RAG: Groq, local embeddings fallback, Pinecone optional
- Deployment: Docker Compose, AWS EC2

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
# Fill in API keys in .env
./setup.sh
```

### Run
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

## Docker / EC2 Deployment
```bash
cp .env.example .env
# Fill in production values in .env
./setup.sh docker
docker compose up --build -d
```

Frontend is served on port `80`. The backend stays internal to Docker and is reached through the frontend reverse proxy.

For the full EC2 flow, see [DEPLOYMENT.md](/Users/neha/autodiligence/DEPLOYMENT.md).

## Netlify + EC2 Deployment

If you want a cheaper split deployment:

- deploy the frontend from `/frontend` on Netlify
- deploy the backend and PostgreSQL on AWS EC2

For Netlify:

```bash
cd frontend
cp .env.example .env
```

Set:

```bash
REACT_APP_API_BASE_URL=http://YOUR_EC2_PUBLIC_IP:8000
```

Netlify settings:

- Base directory: `frontend`
- Build command: `npm run build`
- Publish directory: `frontend/build`

The included [frontend/netlify.toml](/Users/neha/autodiligence/frontend/netlify.toml) handles SPA routing.
