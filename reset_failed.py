# reset_failed.py  -  'failed' wale recruiters ko wapas 'queued' kar deta hai.
# Chalao:  python reset_failed.py
import sqlite3

c = sqlite3.connect("applications_tracker.db")
c.execute("UPDATE leads SET status='queued' WHERE status='failed'")
c.commit()
rows = c.execute("SELECT status, COUNT(*) FROM leads GROUP BY status").fetchall()
c.close()
print("Done. Ab status:", dict(rows))