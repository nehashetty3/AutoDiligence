import requests
import pandas as pd
from datetime import datetime, timedelta
import os
import time
from dotenv import load_dotenv
from sqlalchemy.orm import Session
from backend.database.schema import SessionLocal, Company, NewsArticle

load_dotenv()
NEWS_API_KEY = os.getenv("NEWS_API_KEY")

def fetch_company_news(company_name: str, ticker: str, days_back: int = 90) -> list:
    """
    Fetch news with multiple strategies to maximize article count.
    Uses shorter date range to stay within free tier limits.
    """
    end_date = datetime.now()
    start_date = end_date - timedelta(days=days_back)
    articles = []

    # Strategy 1: NewsAPI everything endpoint
    if NEWS_API_KEY and NEWS_API_KEY != "your_newsapi_key_here":
        queries = [
            f'"{company_name}"',
            f'{company_name} stock',
            f'{company_name} earnings',
            f'{ticker}',
        ]
        for query in queries[:2]:  # Limit to 2 queries to save API calls
            try:
                url = "https://newsapi.org/v2/everything"
                params = {
                    "q": query,
                    "from": start_date.strftime("%Y-%m-%d"),
                    "to": end_date.strftime("%Y-%m-%d"),
                    "language": "en",
                    "sortBy": "relevancy",
                    "pageSize": 50,
                    "apiKey": NEWS_API_KEY
                }
                response = requests.get(url, params=params, timeout=10)
                data = response.json()
                if data.get("status") == "ok":
                    for article in data.get("articles", []):
                        if article.get("title") and "[Removed]" not in article.get("title", ""):
                            articles.append({
                                "headline": article["title"],
                                "source": article.get("source", {}).get("name", "Unknown"),
                                "published_date": article["publishedAt"][:10],
                                "full_text": article.get("description", "") or article.get("content", "") or ""
                            })
                elif data.get("code") == "rateLimited":
                    print(f"[News] Rate limited — using RSS fallback")
                    break
                time.sleep(0.5)
            except Exception as e:
                print(f"[News] NewsAPI error: {e}")

    # Strategy 2: RSS feeds as fallback (always free, no key needed)
    rss_articles = fetch_rss_news(company_name, ticker)
    articles.extend(rss_articles)

    # Deduplicate
    seen = set()
    unique = []
    for a in articles:
        if a["headline"] not in seen and len(a["headline"]) > 10:
            seen.add(a["headline"])
            unique.append(a)

    print(f"[News] Total unique articles: {len(unique)}")
    return unique

def fetch_rss_news(company_name: str, ticker: str) -> list:
    """
    Fetch news from free RSS feeds — Yahoo Finance, Google News.
    No API key required, always available.
    """
    from urllib.parse import quote
    articles = []

    rss_sources = [
        f"https://feeds.finance.yahoo.com/rss/2.0/headline?s={ticker}&region=US&lang=en-US",
        f"https://news.google.com/rss/search?q={quote(company_name)}+stock&hl=en-US&gl=US&ceid=US:en",
        f"https://news.google.com/rss/search?q={quote(company_name)}+earnings&hl=en-US&gl=US&ceid=US:en",
    ]

    for url in rss_sources:
        try:
            response = requests.get(url, timeout=8, headers={"User-Agent": "Mozilla/5.0"})
            if response.status_code == 200:
                import xml.etree.ElementTree as ET
                root = ET.fromstring(response.content)
                channel = root.find('channel')
                if channel:
                    for item in channel.findall('item')[:20]:
                        title = item.findtext('title', '')
                        pub_date = item.findtext('pubDate', '')
                        description = item.findtext('description', '')
                        if title and len(title) > 10:
                            try:
                                from email.utils import parsedate_to_datetime
                                dt = parsedate_to_datetime(pub_date)
                                date_str = dt.strftime('%Y-%m-%d')
                            except:
                                date_str = datetime.now().strftime('%Y-%m-%d')
                            articles.append({
                                "headline": title.strip(),
                                "source": "Yahoo Finance / Google News",
                                "published_date": date_str,
                                "full_text": description or title
                            })
        except Exception as e:
            print(f"[News] RSS error for {url[:50]}: {e}")
        time.sleep(0.3)

    return articles

def save_news_to_db(company_id: int, articles: list):
    db: Session = SessionLocal()
    try:
        # Clear old articles for this company to avoid duplicates
        db.query(NewsArticle).filter(NewsArticle.company_id == company_id).delete()
        count = 0
        for article in articles:
            try:
                pub_date = datetime.strptime(article["published_date"], "%Y-%m-%d").date()
            except:
                pub_date = datetime.now().date()
            news = NewsArticle(
                company_id=company_id,
                headline=article["headline"][:500],
                source=article["source"][:100],
                published_date=pub_date,
                full_text=article["full_text"][:2000] if article["full_text"] else "",
                sentiment_score=None
            )
            db.add(news)
            count += 1
        db.commit()
        print(f"[News] Saved {count} articles")
    except Exception as e:
        db.rollback()
        print(f"[News] DB error: {e}")
    finally:
        db.close()

def run_news_pipeline(company_name: str, ticker: str, company_id: int) -> list:
    print(f"[News] Starting pipeline for: {company_name} ({ticker})")
    articles = fetch_company_news(company_name, ticker)
    if articles:
        save_news_to_db(company_id, articles)
    return articles
