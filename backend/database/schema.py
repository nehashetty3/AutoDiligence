from sqlalchemy import (
    create_engine, Column, Integer, String, Float,
    Date, Text, ForeignKey, Numeric, Boolean, DateTime, JSON
)
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, relationship
from datetime import datetime
import os
from dotenv import load_dotenv

load_dotenv()

DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://localhost/ma_diligence")
engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(bind=engine)
Base = declarative_base()


class Company(Base):
    __tablename__ = "companies"
    id = Column(Integer, primary_key=True)
    name = Column(String(255))
    ticker = Column(String(32))
    cik = Column(String(64))
    industry = Column(String(100))
    sector = Column(String(100))
    created_at = Column(DateTime, default=datetime.utcnow)
    filings = relationship("Filing", back_populates="company", cascade="all, delete-orphan")
    news = relationship("NewsArticle", back_populates="company", cascade="all, delete-orphan")
    patents = relationship("Patent", back_populates="company", cascade="all, delete-orphan")
    job_postings = relationship("JobPosting", back_populates="company", cascade="all, delete-orphan")
    risk_assessments = relationship("RiskAssessment", back_populates="company", cascade="all, delete-orphan")
    watchlist_entries = relationship("WatchlistEntry", back_populates="company", cascade="all, delete-orphan")


class Filing(Base):
    __tablename__ = "filings"
    id = Column(Integer, primary_key=True)
    company_id = Column(Integer, ForeignKey("companies.id"))
    filing_type = Column(String(20))
    filing_date = Column(Date)
    raw_text = Column(Text)
    revenue = Column(Numeric)
    net_income = Column(Numeric)
    total_debt = Column(Numeric)
    cash = Column(Numeric)
    company = relationship("Company", back_populates="filings")


class NewsArticle(Base):
    __tablename__ = "news_articles"
    id = Column(Integer, primary_key=True)
    company_id = Column(Integer, ForeignKey("companies.id"))
    headline = Column(Text)
    source = Column(String(100))
    published_date = Column(Date)
    full_text = Column(Text)
    sentiment_score = Column(Float)
    sentiment_label = Column(String(20))
    company = relationship("Company", back_populates="news")


class Patent(Base):
    __tablename__ = "patents"
    id = Column(Integer, primary_key=True)
    company_id = Column(Integer, ForeignKey("companies.id"))
    patent_title = Column(Text)
    abstract = Column(Text)
    filing_date = Column(Date)
    classification_code = Column(String(50))
    company = relationship("Company", back_populates="patents")


class JobPosting(Base):
    __tablename__ = "job_postings"
    id = Column(Integer, primary_key=True)
    company_id = Column(Integer, ForeignKey("companies.id"))
    role_title = Column(String(255))
    department = Column(String(100))
    seniority_level = Column(String(50))
    posted_date = Column(Date)
    location = Column(String(100))
    company = relationship("Company", back_populates="job_postings")


class RiskAssessment(Base):
    __tablename__ = "risk_assessments"
    id = Column(Integer, primary_key=True)
    company_id = Column(Integer, ForeignKey("companies.id"))
    risk_score = Column(Float)
    risk_category = Column(String(20))
    shap_values = Column(JSON)
    report_text = Column(Text)
    created_at = Column(DateTime, default=datetime.utcnow)
    company = relationship("Company", back_populates="risk_assessments")


class WatchlistEntry(Base):
    __tablename__ = "watchlist"
    id = Column(Integer, primary_key=True)
    company_id = Column(Integer, ForeignKey("companies.id"))
    user_email = Column(String(255))
    alert_on_sentiment_change = Column(Boolean, default=True)
    alert_on_risk_change = Column(Boolean, default=True)
    alert_on_anomaly = Column(Boolean, default=True)
    alert_threshold = Column(Float, default=10.0)
    last_risk_score = Column(Float)
    last_sentiment_score = Column(Float)
    created_at = Column(DateTime, default=datetime.utcnow)
    company = relationship("Company", back_populates="watchlist_entries")


class Alert(Base):
    __tablename__ = "alerts"
    id = Column(Integer, primary_key=True)
    company_id = Column(Integer, ForeignKey("companies.id"))
    user_email = Column(String(255))
    alert_type = Column(String(50))
    message = Column(Text)
    old_value = Column(Float)
    new_value = Column(Float)
    sent = Column(Boolean, default=False)
    created_at = Column(DateTime, default=datetime.utcnow)


def init_db():
    Base.metadata.create_all(bind=engine)
    print("Database tables created successfully")


if __name__ == "__main__":
    init_db()
