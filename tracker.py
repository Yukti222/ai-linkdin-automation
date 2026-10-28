# tracker.py  -  Saara database (SQLite) ka kaam yahan hota hai.
import sqlite3
from datetime import datetime, timedelta
import config

DB = "applications_tracker.db"


def _conn():
    return sqlite3.connect(DB)


def init_db():
    c = _conn()
    c.execute("""
    CREATE TABLE IF NOT EXISTS applications (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        company_name TEXT UNIQUE,
        status TEXT,
        last_sent_date TEXT,
        follow_up_count INTEGER DEFAULT 0
    )""")
    c.execute("""
    CREATE TABLE IF NOT EXISTS leads (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT,
        headline TEXT,
        profile_url TEXT UNIQUE,
        status TEXT DEFAULT 'queued',
        sent_at TEXT,
        followup_due TEXT,
        followup_sent_at TEXT
    )""")
    lead_columns = {
        row[1] for row in c.execute("PRAGMA table_info(leads)").fetchall()
    }
    for column, definition in {
        "reply_status": "TEXT NOT NULL DEFAULT 'awaiting'",
        "reply_notes": "TEXT",
        "replied_at": "TEXT",
        "meeting_at": "TEXT",
        "meeting_topic": "TEXT",
        "draft_message": "TEXT",
        "draft_state": "TEXT NOT NULL DEFAULT 'none'",
        "drafted_at": "TEXT",
    }.items():
        if column not in lead_columns:
            c.execute(f"ALTER TABLE leads ADD COLUMN {column} {definition}")
    c.commit()
    c.close()


def get_lead(lead_id):
    c = _conn()
    row = c.execute(
        "SELECT id, name, headline, profile_url, status, draft_message, draft_state, drafted_at "
        "FROM leads WHERE id=?",
        (lead_id,)).fetchone()
    c.close()
    return row


def save_message_draft(lead_id, message, state="preparing"):
    if not message.strip():
        raise ValueError("Draft message cannot be empty.")
    if state not in {"preparing", "prepared", "failed"}:
        raise ValueError("Invalid draft state.")

    c = _conn()
    cur = c.execute(
        """
        UPDATE leads SET draft_message=?, draft_state=?,
            drafted_at=CASE WHEN ?='prepared' THEN ? ELSE drafted_at END
        WHERE id=? AND status='queued' AND sent_at IS NULL
        """,
        (
            message,
            state,
            state,
            datetime.now().isoformat(timespec="seconds"),
            lead_id,
        ))
    c.commit()
    updated = cur.rowcount > 0
    c.close()
    if not updated:
        raise ValueError("Only queued, unsent leads can have a draft prepared.")


def set_draft_state(lead_id, state):
    if state not in {"preparing", "prepared", "failed"}:
        raise ValueError("Invalid draft state.")
    c = _conn()
    c.execute(
        "UPDATE leads SET draft_state=?, drafted_at=? WHERE id=?",
        (
            state,
            datetime.now().isoformat(timespec="seconds") if state == "prepared" else None,
            lead_id,
        ))
    c.commit()
    c.close()


def add_lead(name, headline, url):
    """Naya recruiter save karo. Agar pehle se hai to skip. True = naya tha."""
    c = _conn()
    cur = c.execute(
        "INSERT OR IGNORE INTO leads (name, headline, profile_url) VALUES (?,?,?)",
        (name, headline, url))
    c.commit()
    added = cur.rowcount > 0
    c.close()
    return added


def get_queued(limit):
    c = _conn()
    rows = c.execute(
        "SELECT id, name, profile_url, headline FROM leads WHERE status='queued' LIMIT ?",
        (limit,)).fetchall()
    c.close()
    return rows


def get_failed(limit):
    c = _conn()
    rows = c.execute(
        "SELECT id, name, profile_url, headline FROM leads WHERE status='failed' LIMIT ?",
        (limit,)).fetchall()
    c.close()
    return rows


def count_failed():
    c = _conn()
    count = c.execute(
        "SELECT COUNT(*) FROM leads WHERE status='failed'").fetchone()[0]
    c.close()
    return count


def get_followups_due(limit):
    now = datetime.now().isoformat()
    c = _conn()
    rows = c.execute(
        "SELECT id, name, profile_url, headline FROM leads "
        "WHERE status='sent' AND followup_due <= ? LIMIT ?", (now, limit)).fetchall()
    c.close()
    return rows


def mark_sent(lead_id):
    now = datetime.now()
    due = now + timedelta(days=config.FOLLOWUP_AFTER_DAYS)
    c = _conn()
    c.execute("UPDATE leads SET status='sent', sent_at=?, followup_due=? WHERE id=?",
              (now.isoformat(), due.isoformat(), lead_id))
    c.commit()
    c.close()


def mark_followed_up(lead_id):
    c = _conn()
    c.execute("UPDATE leads SET status='followed_up', followup_sent_at=? WHERE id=?",
              (datetime.now().isoformat(), lead_id))
    c.commit()
    c.close()


def mark_replied(lead_id):
    c = _conn()
    c.execute(
        "UPDATE leads SET status='replied', reply_status='unclassified', replied_at=? WHERE id=?",
        (datetime.now().isoformat(timespec="seconds"), lead_id))
    c.commit()
    c.close()


def mark_failed(lead_id):
    c = _conn()
    c.execute("UPDATE leads SET status='failed' WHERE id=?", (lead_id,))
    c.commit()
    c.close()


def count_sent_today():
    today = datetime.now().strftime("%Y-%m-%d")
    c = _conn()
    leads_sent = c.execute(
        "SELECT COUNT(*) FROM leads WHERE substr(sent_at,1,10)=? OR substr(followup_sent_at,1,10)=?",
        (today, today)).fetchone()[0]
    applications_sent = c.execute(
        "SELECT COUNT(*) FROM applications "
        "WHERE lower(status)='sent' AND substr(last_sent_date,1,10)=?",
        (today,)).fetchone()[0]
    c.close()
    return leads_sent + applications_sent


def show_summary():
    c = _conn()
    rows = c.execute("SELECT status, COUNT(*) FROM leads GROUP BY status").fetchall()
    c.close()
    print("Database summary:", dict(rows))


def can_send_message(company_name):
    """Check company cooldown and the shared daily message limit."""
    company_name = company_name.strip()
    if not company_name:
        return False, "Company name is required."

    c = _conn()
    existing = c.execute(
        "SELECT status, last_sent_date FROM applications "
        "WHERE company_name = ? COLLATE NOCASE",
        (company_name,)).fetchone()
    c.close()

    if existing and (existing[0] or "").lower() == "sent":
        if not existing[1]:
            return False, f"{company_name} is already marked as sent."
        last_sent = datetime.fromisoformat(existing[1])
        cooldown_ends = last_sent + timedelta(days=config.FOLLOWUP_AFTER_DAYS)
        if datetime.now() < cooldown_ends:
            return False, f"{company_name} is in cooldown until {cooldown_ends.date()}."

    sent_today = count_sent_today()
    if sent_today >= config.DAILY_LIMIT:
        return False, f"Daily message limit reached ({sent_today}/{config.DAILY_LIMIT})."

    return True, "Ready to send."


def log_application(company_name, status="Sent"):
    """Create or update a company record, recording send date only for sent messages."""
    company_name = company_name.strip()
    if not company_name:
        raise ValueError("Company name is required.")

    sent_at = datetime.now().isoformat() if status.lower() == "sent" else None
    c = _conn()
    c.execute(
        """
        INSERT INTO applications (company_name, status, last_sent_date, follow_up_count)
        VALUES (?, ?, ?, 0)
        ON CONFLICT(company_name) DO UPDATE SET
            status=excluded.status,
            last_sent_date=CASE
                WHEN lower(excluded.status)='sent' THEN excluded.last_sent_date
                ELSE applications.last_sent_date
            END
        """,
        (company_name, status, sent_at))
    c.commit()
    c.close()