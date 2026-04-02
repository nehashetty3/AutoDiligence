# AutoDiligence — AI-Powered M&A Due Diligence Platform

AutoDiligence automates M&A due diligence by ingesting real public company data, running multi-layer AI/ML analysis, and generating consultant-grade risk reports in minutes.

## Features
- SEC EDGAR financial analysis with anomaly detection
- FinBERT news sentiment analysis (24-month timeline)
- USPTO patent innovation clustering (LDA topic modeling)
- Hiring trend analysis with SQL window functions
- XGBoost risk scoring with SHAP explainability
- GPT-4 report generation with RAG pipeline
- Competitor benchmarking (auto-identifies top 4 competitors)
- Watchlist & email alerting system
- PDF report export
- React frontend with interactive D3/Recharts visualizations

## Tech Stack
- **Backend:** Python, FastAPI, SQLAlchemy
- **Database:** PostgreSQL
- **ML/NLP:** XGBoost, SHAP, FinBERT, spaCy, scikit-learn
- **LLM:** OpenAI GPT-4 with Pinecone RAG
- **Frontend:** React, Recharts
- **Deployment:** Docker, AWS EC2, Apache Airflow

## Setup Instructions

### Step 1 — Prerequisites (Mac Apple Silicon)
```bash
brew install python@3.11 postgresql@15 git node
brew services start postgresql@15
createdb ma_diligence
```

### Step 2 — Clone and Configure
```bash
git clone <your-repo-url>
cd autodiligence
cp .env.template .env
# Edit .env with your API keys
```

### Step 3 — Run Setup Script
```bash
chmod +x setup.sh
./setup.sh
```

### Step 4 — Start Application
```bash
./start.sh
```

Open http://localhost:3000

## API Keys Required
- **OpenAI:** platform.openai.com (GPT-4 + embeddings)
- **NewsAPI:** newsapi.org (free tier: 100 req/day)
- **Pinecone:** pinecone.io (free tier available)
- **SEC EDGAR:** No key required (free public API)
- **USPTO:** No key required (free public API)

## Project Structure
```
autodiligence/
├── backend/
│   ├── main.py                 # FastAPI application
│   ├── database/schema.py      # PostgreSQL models
│   ├── ingestion/              # Data pipelines
│   ├── analytics/              # NLP & ML analysis
│   ├── models/                 # Risk scoring & SHAP
│   ├── llm/                    # RAG & report generation
│   └── alerts/                 # Watchlist & email alerts
├── frontend/
│   └── src/
│       ├── pages/              # React pages
│       └── components/         # Shared components
├── setup.sh                    # One-click setup
├── start.sh                    # Start application
└── docker-compose.yml          # Docker deployment
```

## Deployment (AWS EC2)
See DEPLOYMENT.md for full AWS deployment guide.

## Research Paper
This project accompanies the paper:
*"AutoDiligence: An AI-Powered M&A Due Diligence Engine Combining NLP, Predictive Analytics, and LLM Synthesis for Automated Risk Assessment"*
