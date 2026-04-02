import os
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from datetime import datetime
from sqlalchemy.orm import Session
from backend.database.schema import SessionLocal, Company, WatchlistEntry, Alert

def add_to_watchlist(company_id: int, user_email: str, alert_threshold: float = 10.0,
                     last_risk_score: float = None, last_sentiment_score: float = None) -> dict:
    db = SessionLocal()
    try:
        existing = db.query(WatchlistEntry).filter(
            WatchlistEntry.company_id == company_id,
            WatchlistEntry.user_email == user_email
        ).first()
        if existing:
            return {"status": "already_exists", "id": existing.id, "message": f"{user_email} is already watching this company."}
        entry = WatchlistEntry(
            company_id=company_id,
            user_email=user_email,
            alert_threshold=alert_threshold,
            last_risk_score=last_risk_score,
            last_sentiment_score=last_sentiment_score
        )
        db.add(entry)
        db.commit()
        db.refresh(entry)
        print(f"[Watchlist] Added company {company_id} for {user_email}")
        return {"status": "added", "id": entry.id, "message": f"Now monitoring. You'll receive alerts at {user_email}."}
    except Exception as e:
        db.rollback()
        print(f"[Watchlist] Error: {e}")
        return {"status": "error", "message": str(e)}
    finally:
        db.close()

def remove_from_watchlist(company_id: int, user_email: str) -> dict:
    db = SessionLocal()
    try:
        entry = db.query(WatchlistEntry).filter(
            WatchlistEntry.company_id == company_id,
            WatchlistEntry.user_email == user_email
        ).first()
        if entry:
            db.delete(entry)
            db.commit()
            return {"status": "removed"}
        return {"status": "not_found"}
    finally:
        db.close()

def get_watchlist_for_user(user_email: str) -> list:
    db = SessionLocal()
    try:
        entries = db.query(WatchlistEntry).filter(WatchlistEntry.user_email == user_email).all()
        result = []
        for e in entries:
            company = db.query(Company).filter(Company.id == e.company_id).first()
            result.append({
                "watchlist_id": e.id,
                "company_id": e.company_id,
                "company_name": company.name if company else "Unknown",
                "ticker": company.ticker if company else "",
                "user_email": e.user_email,
                "alert_threshold": e.alert_threshold,
                "last_risk_score": e.last_risk_score,
                "last_sentiment_score": e.last_sentiment_score,
                "created_at": str(e.created_at)
            })
        return result
    finally:
        db.close()

def check_and_create_alerts(company_id: int, new_risk_score: float, new_sentiment_score: float) -> list:
    db = SessionLocal()
    created_alerts = []
    try:
        entries = db.query(WatchlistEntry).filter(WatchlistEntry.company_id == company_id).all()
        company = db.query(Company).filter(Company.id == company_id).first()
        company_name = company.name if company else "Unknown"
        for entry in entries:
            if entry.alert_on_risk_change and entry.last_risk_score is not None:
                risk_change = abs(new_risk_score - entry.last_risk_score)
                if risk_change >= entry.alert_threshold:
                    direction = "increased" if new_risk_score > entry.last_risk_score else "decreased"
                    alert = Alert(
                        company_id=company_id,
                        user_email=entry.user_email,
                        alert_type="risk_score_change",
                        message=f"{company_name} risk score {direction} from {entry.last_risk_score:.1f} to {new_risk_score:.1f}",
                        old_value=entry.last_risk_score,
                        new_value=new_risk_score
                    )
                    db.add(alert)
                    created_alerts.append({"type": "risk_change", "email": entry.user_email, "message": alert.message})
            entry.last_risk_score = new_risk_score
            entry.last_sentiment_score = new_sentiment_score
        db.commit()
        return created_alerts
    except Exception as e:
        db.rollback()
        print(f"[Alerts] Error: {e}")
        return []
    finally:
        db.close()

def send_email_alert(to_email: str, subject: str, body: str) -> bool:
    sender = os.getenv("ALERT_EMAIL_SENDER")
    password = os.getenv("ALERT_EMAIL_PASSWORD")
    if not sender or not password or sender == "your_gmail@gmail.com":
        print(f"[Alerts] Email not configured — alert logged: {subject}")
        return False
    try:
        msg = MIMEMultipart('alternative')
        msg['Subject'] = subject
        msg['From'] = sender
        msg['To'] = to_email
        html = f"""<html><body style="font-family:sans-serif;max-width:560px;margin:0 auto">
        <div style="background:#0A2540;padding:20px;text-align:center">
            <h2 style="color:white;margin:0">AutoDiligence Alert</h2>
        </div>
        <div style="padding:24px;background:#f9f9f9">
            <h3 style="color:#0A2540">{subject}</h3>
            <p style="color:#444;line-height:1.6">{body}</p>
        </div>
        <div style="padding:12px;text-align:center;color:#999;font-size:11px">
            AutoDiligence — {datetime.now().strftime('%Y-%m-%d %H:%M UTC')}
        </div></body></html>"""
        msg.attach(MIMEText(html, 'html'))
        with smtplib.SMTP_SSL('smtp.gmail.com', 465) as server:
            server.login(sender, password)
            server.sendmail(sender, to_email, msg.as_string())
        print(f"[Alerts] Email sent to {to_email}")
        return True
    except Exception as e:
        print(f"[Alerts] Email error: {e}")
        return False

def process_and_send_alerts(company_id: int, new_risk_score: float, new_sentiment_score: float):
    alerts = check_and_create_alerts(company_id, new_risk_score, new_sentiment_score)
    for alert in alerts:
        send_email_alert(alert['email'], f"AutoDiligence Alert: {alert['type'].replace('_', ' ').title()}", alert['message'])
    return len(alerts)
