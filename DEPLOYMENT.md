# Deployment Guide — AWS EC2

## Step 1 — Launch EC2 Instance
1. Go to AWS Console → EC2 → Launch Instance
2. Choose: Ubuntu 22.04 LTS
3. Instance type: t3.medium (minimum) or t3.large (recommended)
4. Storage: 30GB minimum
5. Security Group: Open ports 22 (SSH), 80 (HTTP), 443 (HTTPS), 8000 (API), 3000 (Frontend)
6. Download your .pem key file

## Step 2 — Connect to Instance
```bash
chmod 400 your-key.pem
ssh -i your-key.pem ubuntu@your-ec2-ip
```

## Step 3 — Install Dependencies on EC2
```bash
sudo apt update && sudo apt upgrade -y
sudo apt install -y python3.11 python3.11-venv python3-pip postgresql postgresql-contrib nodejs npm git

sudo systemctl start postgresql
sudo -u postgres createdb ma_diligence
```

## Step 4 — Deploy Application
```bash
git clone https://github.com/yourusername/autodiligence.git
cd autodiligence
cp .env.template .env
nano .env  # Add your API keys
./setup.sh
```

## Step 5 — Run with Docker (Recommended)
```bash
sudo apt install -y docker.io docker-compose
sudo systemctl start docker
sudo docker-compose up -d
```

## Step 6 — Setup Nginx Reverse Proxy
```bash
sudo apt install nginx -y
sudo nano /etc/nginx/sites-available/autodiligence
```

Paste:
```nginx
server {
    listen 80;
    server_name your-domain.com;
    location / { proxy_pass http://localhost:3000; }
    location /api { proxy_pass http://localhost:8000; }
}
```

```bash
sudo ln -s /etc/nginx/sites-available/autodiligence /etc/nginx/sites-enabled/
sudo nginx -t && sudo systemctl restart nginx
```

## Step 7 — SSL Certificate (Free)
```bash
sudo apt install certbot python3-certbot-nginx -y
sudo certbot --nginx -d your-domain.com
```

## Your live URL
https://your-domain.com
