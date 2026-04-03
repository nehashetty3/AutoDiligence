# Deployment Guide — AWS EC2

AutoDiligence is easiest to deploy on AWS EC2 with Docker Compose. The frontend is served by Nginx inside the frontend container, and API traffic is proxied to the FastAPI backend container.

## Architecture

- `frontend` serves the React build on port `80`
- `backend` serves FastAPI on port `8000`
- `db` runs PostgreSQL 15

Only port `80` needs to be public for a basic deployment.

## 1. Launch an EC2 Instance

Recommended baseline:

- AMI: `Ubuntu 22.04 LTS`
- Instance type: `t3.large` recommended, `t3.medium` minimum
- Storage: `30 GB` or more

Security group:

- `22` for SSH from your IP
- `80` for HTTP
- `443` for HTTPS if you later add TLS

## 2. Connect to the Instance

```bash
chmod 400 your-key.pem
ssh -i your-key.pem ubuntu@your-ec2-public-ip
```

## 3. Install Docker and Git

```bash
sudo apt update
sudo apt install -y docker.io docker-compose-v2 git
sudo systemctl enable docker
sudo systemctl start docker
sudo usermod -aG docker $USER
newgrp docker
```

## 4. Clone the Repository

```bash
git clone https://github.com/nehashetty3/AutoDiligence.git
cd AutoDiligence
```

## 5. Configure Environment Variables

```bash
cp .env.example .env
nano .env
```

Minimum values to review in `.env`:

- `GROQ_API_KEY`
- `NEWS_API_KEY`
- `PINECONE_API_KEY`
- `OPENAI_API_KEY=skip`
- `DATABASE_URL=postgresql://postgres:postgres@db:5432/ma_diligence`
- `FRONTEND_URL=http://your-ec2-public-ip`

If you plan to use watchlist email alerts, also set:

- `ALERT_EMAIL_SENDER`
- `ALERT_EMAIL_PASSWORD`
- `ALERT_EMAIL_RECIPIENT`

## 6. Build and Start the Stack

```bash
docker compose up --build -d
```

Check status:

```bash
docker compose ps
docker compose logs backend --tail=100
```

The app should be available at:

- `http://your-ec2-public-ip`

Health check:

- `http://your-ec2-public-ip/health`

## 7. Updating the Deployment

```bash
git pull origin master
docker compose up --build -d
```

## 8. Optional: Domain and HTTPS

If you attach a domain later, point it to the EC2 public IP and place Nginx or Caddy on the host for TLS termination, or attach an AWS load balancer with ACM certificates.

## Troubleshooting

View running containers:

```bash
docker compose ps
```

Backend logs:

```bash
docker compose logs backend --tail=200
```

Frontend logs:

```bash
docker compose logs frontend --tail=200
```

Database logs:

```bash
docker compose logs db --tail=200
```

Restart everything:

```bash
docker compose down
docker compose up --build -d
```

## Alternative: Netlify Frontend + EC2 Backend

If you want to reduce EC2 load and cost, you can host only the React frontend on Netlify and keep FastAPI plus PostgreSQL on EC2.

### EC2 backend

On EC2, run the backend and database locally or with Docker. If you use the split setup, make sure the FastAPI server is reachable on port `8000`.

Security group for this setup:

- `22` for SSH
- `80` for your website if you also host anything else
- `8000` for the API

### Netlify frontend

In Netlify:

- connect the GitHub repo
- set the base directory to `frontend`
- set the build command to `npm run build`
- set the publish directory to `build`

Environment variable:

- `REACT_APP_API_BASE_URL=http://YOUR_EC2_PUBLIC_IP:8000`

The frontend already supports this through [frontend/src/api.js](/Users/neha/autodiligence/frontend/src/api.js), and [frontend/netlify.toml](/Users/neha/autodiligence/frontend/netlify.toml) provides the SPA redirect.
