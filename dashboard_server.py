"""Local dashboard server with read-only metrics and explicit engagement updates."""
from datetime import datetime
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
import json
from pathlib import Path
import re
import sqlite3
import subprocess
import sys
import threading
from urllib.parse import urlparse

import config
import tracker


ROOT = Path(__file__).resolve().parent
HOST = "127.0.0.1"
PORT = 8000
REPLY_STATUSES = {"awaiting", "unclassified", "positive", "neutral", "negative"}
MAX_REQUEST_BYTES = 16_384
_draft_processes = {}
_draft_processes_lock = threading.Lock()


def get_dashboard_data():
    tracker.init_db()
    connection = tracker._conn()
    try:
        today = datetime.now().date().isoformat()
        now = datetime.now().isoformat()
        total, queued, failed, contacted = connection.execute(
            """
            SELECT COUNT(*),
                SUM(status='queued'),
                SUM(status='failed'),
                SUM(sent_at IS NOT NULL)
            FROM leads
            """
        ).fetchone()
        drafts_prepared = connection.execute(
            "SELECT COUNT(*) FROM leads WHERE draft_state='prepared'"
        ).fetchone()[0]
        sent_today = connection.execute(
            """
            SELECT COUNT(*) FROM leads
            WHERE substr(sent_at,1,10)=? OR substr(followup_sent_at,1,10)=?
            """,
            (today, today),
        ).fetchone()[0]
        messages_sent = connection.execute(
            """
            SELECT
                (SELECT COUNT(*) FROM leads WHERE sent_at IS NOT NULL) +
                (SELECT COUNT(*) FROM leads WHERE followup_sent_at IS NOT NULL)
            """
        ).fetchone()[0]
        reply_count, unclassified_count, positive_count, neutral_count, negative_count = connection.execute(
            """
            SELECT
                SUM(reply_status IN ('unclassified','positive','neutral','negative')),
                SUM(reply_status='unclassified'),
                SUM(reply_status='positive'),
                SUM(reply_status='neutral'),
                SUM(reply_status='negative')
            FROM leads
            """
        ).fetchone()
        meeting_count = connection.execute(
            "SELECT COUNT(*) FROM leads WHERE meeting_at IS NOT NULL AND meeting_at >= ?",
            (now,),
        ).fetchone()[0]
        leads = connection.execute(
            """
            SELECT id, name, headline, profile_url, status, sent_at,
                   followup_due, reply_status, reply_notes, replied_at,
                   meeting_at, meeting_topic, draft_state, drafted_at
            FROM leads ORDER BY COALESCE(sent_at, '') DESC, id DESC
            """
        ).fetchall()
        meetings = connection.execute(
            """
            SELECT id, name, headline, profile_url, meeting_at, meeting_topic
            FROM leads WHERE meeting_at IS NOT NULL AND meeting_at >= ?
            ORDER BY meeting_at LIMIT 8
            """,
            (now,),
        ).fetchall()
    finally:
        connection.close()

    contacted = contacted or 0
    reply_count = reply_count or 0
    unclassified_count = unclassified_count or 0
    positive_count = positive_count or 0
    neutral_count = neutral_count or 0
    negative_count = negative_count or 0
    return {
        "generated_at": now,
        "stats": {
            "total_leads": total or 0,
            "queued": queued or 0,
            "failed": failed or 0,
            "drafts_prepared": drafts_prepared,
            "messages_sent": messages_sent or 0,
            "messages_sent_today": sent_today,
            "replies": reply_count,
            "unclassified_replies": unclassified_count,
            "positive_replies": positive_count,
            "neutral_replies": neutral_count,
            "negative_replies": negative_count,
            "meetings_scheduled": meeting_count,
            "daily_limit": config.DAILY_LIMIT,
            "reply_rate": round(reply_count / max(contacted, 1) * 100, 1),
        },
        "leads": [
            {
                "id": row[0],
                "name": row[1] or "",
                "headline": row[2] or "",
                "profile_url": row[3] or "",
                "status": row[4] or "queued",
                "sent_at": row[5] or "",
                "followup_due": row[6] or "",
                "reply_status": row[7] or "awaiting",
                "reply_notes": row[8] or "",
                "replied_at": row[9] or "",
                "meeting_at": row[10] or "",
                "meeting_topic": row[11] or "",
                "draft_state": row[12] or "none",
                "drafted_at": row[13] or "",
            }
            for row in leads
        ],
        "meetings": [
            {
                "id": row[0],
                "name": row[1] or "",
                "headline": row[2] or "",
                "profile_url": row[3] or "",
                "meeting_at": row[4],
                "meeting_topic": row[5] or "",
            }
            for row in meetings
        ],
    }


def get_message_preview(lead_id):
    lead = tracker.get_lead(lead_id)
    if lead is None:
        raise LookupError("Lead not found.")
    if lead[4] != "queued":
        raise ValueError("Only queued leads can be prepared as new message drafts.")

    message = lead[5] or config.build_message(((lead[1] or "").split() or ["there"])[0], lead[2] or "")
    return {
        "id": lead[0],
        "name": lead[1] or "",
        "profile_url": lead[3] or "",
        "message": message,
        "draft_state": lead[6] or "none",
        "drafted_at": lead[7] or "",
        "resume_name": Path(config.RESUME_FILE).name,
    }


def launch_message_draft(lead_id, message):
    if not isinstance(message, str) or not message.strip():
        raise ValueError("Draft message cannot be empty.")
    if len(message) > 10_000:
        raise ValueError("Draft message is too long.")
    if not Path(config.RESUME_FILE).is_file():
        raise FileNotFoundError(f"Resume file does not exist: {config.RESUME_FILE}")

    get_message_preview(lead_id)
    with _draft_processes_lock:
        active = _draft_processes.get(lead_id)
        if active is not None and active.poll() is None:
            raise ValueError("A draft window is already open for this lead.")

        tracker.save_message_draft(lead_id, message, state="preparing")
        command = [sys.executable, str(ROOT / "prepare_draft.py"), str(lead_id)]
        creation_flags = getattr(subprocess, "CREATE_NEW_CONSOLE", 0)
        try:
            process = subprocess.Popen(
                command,
                cwd=str(ROOT),
                creationflags=creation_flags,
            )
        except OSError:
            tracker.set_draft_state(lead_id, "failed")
            raise
        _draft_processes[lead_id] = process

    return {"ok": True, "pid": process.pid, "draft_state": "preparing"}


def update_lead_engagement(lead_id, payload):
    if not isinstance(payload, dict):
        raise ValueError("Request body must be a JSON object.")

    reply_status = payload.get("reply_status", "awaiting")
    if reply_status not in REPLY_STATUSES:
        raise ValueError("Reply status must be awaiting, positive, neutral, or negative.")

    reply_notes = payload.get("reply_notes", "")
    meeting_topic = payload.get("meeting_topic", "")
    meeting_at = payload.get("meeting_at", "")
    if not all(isinstance(value, str) for value in (reply_notes, meeting_topic, meeting_at)):
        raise ValueError("Reply notes, meeting topic, and meeting time must be text.")
    if len(reply_notes) > 4000 or len(meeting_topic) > 500:
        raise ValueError("Reply notes or meeting topic exceeds the allowed length.")
    if bool(meeting_at) != bool(meeting_topic.strip()):
        raise ValueError("Enter both a meeting time and meeting topic, or clear both.")
    if meeting_at:
        try:
            meeting_at = datetime.fromisoformat(meeting_at).isoformat(timespec="minutes")
        except ValueError as exc:
            raise ValueError("Meeting time must be a valid local date and time.") from exc

    connection = tracker._conn()
    try:
        row = connection.execute(
            "SELECT status, sent_at, followup_sent_at FROM leads WHERE id=?",
            (lead_id,),
        ).fetchone()
        if row is None:
            raise LookupError("Lead not found.")

        status, sent_at, followup_sent_at = row
        if reply_status in {"unclassified", "positive", "neutral", "negative"}:
            status = "replied"
            replied_at = datetime.now().isoformat(timespec="seconds")
        else:
            replied_at = None
            if status == "replied":
                status = "followed_up" if followup_sent_at else "sent" if sent_at else "queued"

        connection.execute(
            """
            UPDATE leads SET status=?, reply_status=?, reply_notes=?, replied_at=?,
                meeting_at=?, meeting_topic=?
            WHERE id=?
            """,
            (
                status,
                reply_status,
                reply_notes.strip(),
                replied_at,
                meeting_at or None,
                meeting_topic.strip() or None,
                lead_id,
            ),
        )
        connection.commit()
    finally:
        connection.close()

    return {"ok": True, "dashboard": get_dashboard_data()}


class DashboardHandler(SimpleHTTPRequestHandler):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=str(ROOT), **kwargs)

    def do_GET(self):
        path = urlparse(self.path).path
        if path == "/api/dashboard":
            self._send_json(200, get_dashboard_data())
            return
        draft_match = re.fullmatch(r"/api/leads/(\d+)/draft", path)
        if draft_match:
            try:
                self._send_json(200, get_message_preview(int(draft_match.group(1))))
            except LookupError as exc:
                self._send_json(404, {"error": str(exc)})
            except ValueError as exc:
                self._send_json(409, {"error": str(exc)})
            return
        if path == "/":
            self.path = "/outreach_site.html"
        elif path != "/outreach_site.html":
            self.send_error(404)
            return
        super().do_GET()

    def do_POST(self):
        path = urlparse(self.path).path
        engagement_match = re.fullmatch(r"/api/leads/(\d+)/engagement", path)
        draft_match = re.fullmatch(r"/api/leads/(\d+)/prepare-draft", path)
        if not engagement_match and not draft_match:
            self._send_json(404, {"error": "Endpoint not found."})
            return
        try:
            length = int(self.headers.get("Content-Length", "0"))
            if length <= 0 or length > MAX_REQUEST_BYTES:
                raise ValueError("Request body is empty or too large.")
            payload = json.loads(self.rfile.read(length))
            if engagement_match:
                result = update_lead_engagement(int(engagement_match.group(1)), payload)
            else:
                if not isinstance(payload, dict):
                    raise ValueError("Request body must be a JSON object.")
                result = launch_message_draft(
                    int(draft_match.group(1)),
                    payload.get("message"),
                )
        except (ValueError, json.JSONDecodeError) as exc:
            self._send_json(400, {"error": str(exc)})
        except LookupError as exc:
            self._send_json(404, {"error": str(exc)})
        except OSError as exc:
            self._send_json(500, {"error": f"Could not start LinkedIn draft window: {exc}"})
        except sqlite3.Error:
            self._send_json(500, {"error": "Could not update the local database."})
        else:
            self._send_json(200, result)

    def _send_json(self, status, payload):
        body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(body)

    def log_message(self, format, *args):
        print(f"[dashboard] {self.address_string()} {format % args}")


def main():
    tracker.init_db()
    server = ThreadingHTTPServer((HOST, PORT), DashboardHandler)
    print(f"Dashboard running at http://127.0.0.1:{PORT}/")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nDashboard server stopped.")
    finally:
        server.server_close()


if __name__ == "__main__":
    main()
