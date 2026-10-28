import contextlib
import io
import tempfile
import unittest
from pathlib import Path

import config
import tracker
from agent_runner import run_agent_workflow


class TrackerCompatibilityTests(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.original_db = tracker.DB
        self.original_daily_limit = config.DAILY_LIMIT
        self.original_cooldown = config.FOLLOWUP_AFTER_DAYS
        tracker.DB = str(Path(self.temp_dir.name) / "tracker.sqlite")
        config.DAILY_LIMIT = 2
        config.FOLLOWUP_AFTER_DAYS = 10
        tracker.init_db()

    def tearDown(self):
        tracker.DB = self.original_db
        config.DAILY_LIMIT = self.original_daily_limit
        config.FOLLOWUP_AFTER_DAYS = self.original_cooldown
        self.temp_dir.cleanup()

    def test_sent_company_is_blocked_during_cooldown(self):
        self.assertEqual(tracker.can_send_message("Acme"), (True, "Ready to send."))

        tracker.log_application("Acme", status="Sent")

        allowed, reason = tracker.can_send_message("acme")
        self.assertFalse(allowed)
        self.assertIn("cooldown", reason)

    def test_daily_limit_counts_legacy_and_lead_messages(self):
        tracker.log_application("Acme", status="Sent")
        tracker.log_application("Beta", status="Sent")

        self.assertEqual(tracker.count_sent_today(), 2)
        allowed, reason = tracker.can_send_message("Gamma")
        self.assertFalse(allowed)
        self.assertIn("Daily message limit", reason)

    def test_draft_does_not_consume_daily_limit(self):
        tracker.log_application("Acme", status="Drafted")

        self.assertEqual(tracker.count_sent_today(), 0)
        self.assertEqual(tracker.can_send_message("Acme"), (True, "Ready to send."))

    def test_lead_draft_state_changes_do_not_change_queued_status(self):
        tracker.add_lead("Asha Sharma", "Technical Recruiter", "https://example.test/asha")
        lead_id = tracker.get_queued(1)[0][0]

        tracker.save_message_draft(lead_id, "A reviewed draft", state="preparing")
        self.assertEqual(tracker.get_lead(lead_id)[4:7], ("queued", "A reviewed draft", "preparing"))

        tracker.set_draft_state(lead_id, "prepared")
        prepared = tracker.get_lead(lead_id)
        self.assertEqual(prepared[4:7], ("queued", "A reviewed draft", "prepared"))
        self.assertTrue(prepared[7])
        self.assertEqual(tracker.count_sent_today(), 0)

    def test_empty_company_name_is_rejected(self):
        self.assertFalse(tracker.can_send_message(" ")[0])
        with self.assertRaises(ValueError):
            tracker.log_application(" ")

    def test_failed_leads_can_be_selected_for_explicit_retry(self):
        tracker.add_lead("Test Lead", "Recruiter", "https://example.test/profile")
        connection = tracker._conn()
        try:
            lead_id = connection.execute(
                "SELECT id FROM leads WHERE profile_url='https://example.test/profile'"
            ).fetchone()[0]
            connection.execute(
                "UPDATE leads SET status='failed' WHERE id=?",
                (lead_id,))
            connection.commit()
        finally:
            connection.close()

        self.assertEqual(len(tracker.get_failed(1)), 1)
        self.assertEqual(tracker.count_failed(), 1)

    def test_draft_workflow_does_not_mark_a_message_as_sent(self):
        with contextlib.redirect_stdout(io.StringIO()):
            run_agent_workflow("Acme", "Python internship", "Python student")

        connection = tracker._conn()
        try:
            row = connection.execute(
                "SELECT status, last_sent_date FROM applications WHERE company_name='Acme'"
            ).fetchone()
        finally:
            connection.close()
        self.assertEqual(row, ("Drafted", None))
        self.assertEqual(tracker.count_sent_today(), 0)


if __name__ == "__main__":
    unittest.main()
