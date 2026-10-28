import tempfile
import unittest
from pathlib import Path
from unittest.mock import Mock, patch

import config
import dashboard_server
import tracker


class DashboardDataTests(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.original_db = tracker.DB
        tracker.DB = str(Path(self.temp_dir.name) / "dashboard.sqlite")
        tracker.init_db()
        tracker.add_lead(
            "Asha Sharma",
            "Technical Recruiter",
            "https://www.linkedin.com/in/asha-sharma",
        )
        connection = tracker._conn()
        try:
            connection.execute(
                "UPDATE leads SET status='sent', sent_at='2026-10-28T09:00:00' WHERE id=1"
            )
            connection.commit()
        finally:
            connection.close()
        dashboard_server._draft_processes.clear()

    def tearDown(self):
        tracker.DB = self.original_db
        self.temp_dir.cleanup()

    def test_dashboard_reports_sent_activity_without_inventing_replies(self):
        data = dashboard_server.get_dashboard_data()
        self.assertEqual(data["stats"]["messages_sent"], 1)
        self.assertEqual(data["stats"]["replies"], 0)
        self.assertEqual(data["stats"]["positive_replies"], 0)
        self.assertEqual(data["stats"]["meetings_scheduled"], 0)
        self.assertEqual(data["leads"][0]["reply_status"], "awaiting")

    def test_positive_reply_and_meeting_are_saved_and_counted(self):
        result = dashboard_server.update_lead_engagement(1, {
            "reply_status": "positive",
            "reply_notes": "Interested in an AI internship interview.",
            "meeting_at": "2099-04-15T14:30",
            "meeting_topic": "AI internship introduction",
        })

        self.assertEqual(result["dashboard"]["stats"]["replies"], 1)
        self.assertEqual(result["dashboard"]["stats"]["unclassified_replies"], 0)
        self.assertEqual(result["dashboard"]["stats"]["positive_replies"], 1)
        self.assertEqual(result["dashboard"]["stats"]["meetings_scheduled"], 1)
        self.assertEqual(result["dashboard"]["stats"]["messages_sent"], 1)
        self.assertEqual(result["dashboard"]["leads"][0]["status"], "replied")
        self.assertEqual(len(result["dashboard"]["meetings"]), 1)

    def test_partial_meeting_and_invalid_sentiment_are_rejected(self):
        with self.assertRaises(ValueError):
            dashboard_server.update_lead_engagement(1, {
                "reply_status": "positive",
                "reply_notes": "",
                "meeting_at": "2099-04-15T14:30",
                "meeting_topic": "",
            })
        with self.assertRaises(ValueError):
            dashboard_server.update_lead_engagement(1, {
                "reply_status": "unknown",
                "reply_notes": "",
                "meeting_at": "",
                "meeting_topic": "",
            })

    def test_unknown_lead_is_rejected(self):
        with self.assertRaises(LookupError):
            dashboard_server.update_lead_engagement(999, {
                "reply_status": "awaiting",
                "reply_notes": "",
                "meeting_at": "",
                "meeting_topic": "",
            })

    def test_detected_reply_is_counted_until_sentiment_is_reviewed(self):
        tracker.mark_replied(1)

        data = dashboard_server.get_dashboard_data()
        self.assertEqual(data["stats"]["replies"], 1)
        self.assertEqual(data["stats"]["unclassified_replies"], 1)
        self.assertEqual(data["stats"]["messages_sent"], 1)

    def test_queued_lead_preview_builds_a_personalized_message(self):
        tracker.add_lead(
            "Rahul Mehta",
            "Technical Recruiter",
            "https://www.linkedin.com/in/rahul-mehta",
        )
        lead_id = tracker.get_queued(10)[0][0]

        preview = dashboard_server.get_message_preview(lead_id)

        self.assertIn("Hi Rahul,", preview["message"])
        self.assertEqual(preview["draft_state"], "none")
        self.assertEqual(preview["resume_name"], Path(config.RESUME_FILE).name)

    def test_prepare_action_saves_draft_and_never_marks_it_sent(self):
        tracker.add_lead(
            "Rahul Mehta",
            "Technical Recruiter",
            "https://www.linkedin.com/in/rahul-mehta",
        )
        lead_id = tracker.get_queued(10)[0][0]
        process = Mock(pid=1234)
        process.poll.return_value = None

        with patch("dashboard_server.Path.is_file", return_value=True), patch(
            "dashboard_server.subprocess.Popen", return_value=process
        ) as popen:
            result = dashboard_server.launch_message_draft(lead_id, "Reviewed draft text")

        self.assertTrue(result["ok"])
        popen.assert_called_once()
        saved_lead = tracker.get_lead(lead_id)
        self.assertEqual(saved_lead[4], "queued")
        self.assertEqual(saved_lead[5], "Reviewed draft text")
        self.assertEqual(saved_lead[6], "preparing")
        self.assertEqual(dashboard_server.get_dashboard_data()["stats"]["messages_sent"], 1)

    def test_sent_leads_cannot_open_a_new_draft(self):
        with self.assertRaises(ValueError):
            dashboard_server.get_message_preview(1)

    def test_empty_draft_is_rejected_without_launching_process(self):
        tracker.add_lead(
            "Rahul Mehta",
            "Technical Recruiter",
            "https://www.linkedin.com/in/rahul-mehta",
        )
        lead_id = tracker.get_queued(10)[0][0]
        with patch("dashboard_server.subprocess.Popen") as popen:
            with self.assertRaises(ValueError):
                dashboard_server.launch_message_draft(lead_id, "  ")
        popen.assert_not_called()


if __name__ == "__main__":
    unittest.main()
