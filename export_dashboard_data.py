# export_dashboard_data.py  -  SQLite se data padhke dashboard_data.json banata hai.
# Ye script sirf READ karta hai. Kuch change nahi hota.
#
# Chalane ka tarika:   python export_dashboard_data.py
# Phir:  outreach_site.html browser mein kholo  (File > Open)
#
import sqlite3
import json
from datetime import datetime, timedelta

DB = "applications_tracker.db"
OUT = "dashboard_data.json"


def main():
    c = sqlite3.connect(DB)

    # ── 1. Status counts ──────────────────────────────────────────────
    rows = c.execute("SELECT status, COUNT(*) FROM leads GROUP BY status").fetchall()
    status_counts = {r[0]: r[1] for r in rows}

    total        = sum(status_counts.values())
    queued       = status_counts.get("queued", 0)
    sent         = status_counts.get("sent", 0)
    followed_up  = status_counts.get("followed_up", 0)
    replied      = status_counts.get("replied", 0)
    failed       = status_counts.get("failed", 0)

    # ── 2. Today's sent count ─────────────────────────────────────────
    today = datetime.now().strftime("%Y-%m-%d")
    sent_today = c.execute(
        "SELECT COUNT(*) FROM leads "
        "WHERE substr(sent_at,1,10)=? OR substr(followup_sent_at,1,10)=?",
        (today, today)
    ).fetchone()[0]

    # ── 3. Config values (import safe) ───────────────────────────────
    try:
        import config
        daily_limit   = config.DAILY_LIMIT
        slot_limit    = config.SLOT_LIMIT
        followup_days = config.FOLLOWUP_AFTER_DAYS
        delay_min     = config.DELAY_MIN
        delay_max     = config.DELAY_MAX
    except Exception:
        daily_limit = 20; slot_limit = 5
        followup_days = 10; delay_min = 90; delay_max = 240

    inmail_credits = 48   # hardcoded per brief (remaining)

    # ── 4. Leads table (last 100, newest first) ───────────────────────
    lead_rows = c.execute(
        "SELECT name, headline, profile_url, status, sent_at, "
        "followup_due, followup_sent_at "
        "FROM leads ORDER BY ROWID DESC LIMIT 100"
    ).fetchall()

    leads = []
    for r in lead_rows:
        leads.append({
            "name":             r[0] or "",
            "headline":         r[1] or "",
            "profile_url":      r[2] or "",
            "status":           r[3] or "queued",
            "sent_at":          (r[4] or "")[:16],
            "followup_due":     (r[5] or "")[:16],
            "followup_sent_at": (r[6] or "")[:16],
        })

    # ── 5. Followups due soon (next 3 days) ───────────────────────────
    in_3d = (datetime.now() + timedelta(days=3)).isoformat()
    followup_soon = c.execute(
        "SELECT COUNT(*) FROM leads WHERE status='sent' AND followup_due <= ?",
        (in_3d,)
    ).fetchone()[0]

    c.close()

    # ── 6. Assemble payload ───────────────────────────────────────────
    payload = {
        "generated_at":   datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "is_sample":      False,
        "stats": {
            "total":          total,
            "queued":         queued,
            "sent":           sent,
            "followed_up":    followed_up,
            "replied":        replied,
            "failed":         failed,
            "sent_today":     sent_today,
            "daily_limit":    daily_limit,
            "slot_limit":     slot_limit,
            "followup_days":  followup_days,
            "delay_min":      delay_min,
            "delay_max":      delay_max,
            "inmail_credits": inmail_credits,
            "followup_soon":  followup_soon,
        },
        "leads": leads,
    }

    with open(OUT, "w", encoding="utf-8") as f:
        json.dump(payload, f, ensure_ascii=False, indent=2)

    print(f"Exported {len(leads)} leads -> {OUT}")
    print(f"   Stats: {dict(status_counts)}")
    print(f"   Aaj bheje: {sent_today} / {daily_limit}")
    print(f"\nAb outreach_site.html browser mein kholo (File > Open).")


if __name__ == "__main__":
    main()
