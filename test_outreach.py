import contextlib
import io
import unittest
from unittest.mock import MagicMock, Mock, patch

import config
import full_agent_runner
from linkedln_outreach_agent import run_linkedin_outreach
from common import configure_console, is_auth_or_security_interstitial
from find_leads import build_search_url, canonical_profile_url, is_first_degree_connection
from run_slot import _visible_message_compose_url, attach_resume, main as run_slot_main


class OutreachMessageTests(unittest.TestCase):
    def test_message_uses_recruiter_name_and_resume_claim(self):
        message = config.build_message("Asha")

        self.assertTrue(message.startswith("Hi Asha,"))
        self.assertIn("B.Tech AI/ML student (3rd semester)", message)
        self.assertIn("MediRush", message)
        self.assertIn("Prompt Pioneers Hackathon", message)
        self.assertIn("I have attached my resume here.", message)
        self.assertTrue(message.endswith("Best regards,\nYukti Yadav"))

    def test_resume_attachment_rejects_missing_file_before_browser_interaction(self):
        with self.assertRaises(FileNotFoundError):
            attach_resume(None, "missing-resume.pdf")

    def test_only_explicit_first_degree_connections_are_accepted(self):
        self.assertTrue(is_first_degree_connection("Asha Sharma\n1st\nTalent Acquisition"))
        self.assertTrue(is_first_degree_connection("Asha Sharma\n1st degree connection"))
        self.assertTrue(is_first_degree_connection("Asha Sharma\n• 1st\nTalent Acquisition"))
        self.assertTrue(is_first_degree_connection("Asha Sharma\n� 1st\nTalent Acquisition"))
        self.assertFalse(is_first_degree_connection("Asha Sharma\n2nd"))
        self.assertFalse(is_first_degree_connection("Asha Sharma\n3rd degree connection"))
        self.assertFalse(is_first_degree_connection("Asha Sharma\n1st year recruiter"))

    def test_search_is_limited_to_first_degree_connections(self):
        url = build_search_url(2)
        self.assertIn("keywords=recruiter", url)
        self.assertIn("network=%5B%22F%22%5D", url)
        self.assertIn("page=2", url)

    def test_profile_urls_are_canonicalized(self):
        self.assertEqual(
            canonical_profile_url(
                "https://www.linkedin.com/in/aman-kuar/details/?tracking=search"
            ),
            "https://www.linkedin.com/in/aman-kuar/",
        )
        self.assertIsNone(canonical_profile_url("https://www.linkedin.com/feed/"))

    def test_compose_link_is_opened_as_same_origin_linkedin_route(self):
        class FakeLocator:
            def __init__(self, href):
                self.href = href

            def count(self):
                return 1

            def nth(self, index):
                if index != 0:
                    raise AssertionError("The fake locator only contains one element.")
                return self

            def is_visible(self):
                return True

            def get_attribute(self, name):
                return self.href if name == "href" else None

        class FakeScope:
            def __init__(self, href):
                self.href = href
                self.requested_roles = []

            def get_by_role(self, role, name):
                self.requested_roles.append((role, name))
                if role != "link":
                    raise AssertionError("The compose URL lookup should inspect links.")
                return FakeLocator(self.href)

        class FakePage:
            url = "https://www.linkedin.com/in/example/"

        page = FakePage()
        scope = FakeScope("/messaging/compose/?recipient=123")
        self.assertEqual(
            _visible_message_compose_url(page, scope),
            "https://www.linkedin.com/messaging/compose/?recipient=123",
        )
        self.assertEqual(scope.requested_roles[0][0], "link")
        self.assertIsNone(
            _visible_message_compose_url(
                page, FakeScope("https://example.test/messaging/compose/")
            )
        )

    def test_login_and_security_interstitials_are_detected(self):
        class FakePage:
            def __init__(self, url, title):
                self.url = url
                self._title = title

            def title(self):
                return self._title

        self.assertTrue(is_auth_or_security_interstitial(
            FakePage("https://www.linkedin.com/uas/login", "LinkedIn Login")))
        self.assertTrue(is_auth_or_security_interstitial(
            FakePage("https://www.linkedin.com/feed/", "Attention Required! | Cloudflare")))
        self.assertFalse(is_auth_or_security_interstitial(
            FakePage("https://www.linkedin.com/feed/", "LinkedIn")))

    def test_console_configuration_uses_safe_unicode_replacement(self):
        stream = Mock()
        stream.reconfigure = Mock()
        with patch("common.sys.stdout", stream):
            configure_console()
        stream.reconfigure.assert_called_once_with(errors="replace")

    def test_command_line_sender_is_disabled(self):
        output = io.StringIO()
        with patch("run_slot.configure_console"), contextlib.redirect_stdout(output):
            run_slot_main()
        self.assertIn("Automated sending is disabled", output.getvalue())

    def test_legacy_linkedin_sender_is_disabled(self):
        output = io.StringIO()
        with contextlib.redirect_stdout(output):
            result = run_linkedin_outreach()
        self.assertFalse(result)
        self.assertIn("auto-sending is disabled", output.getvalue())

    def test_browser_demo_does_not_log_a_unsaved_draft(self):
        manager = MagicMock()
        browser = manager.__enter__.return_value.chromium.launch.return_value
        output = io.StringIO()
        with (
            patch("full_agent_runner.sync_playwright", return_value=manager),
            patch("full_agent_runner.can_send_message", return_value=(True, "Ready to send.")),
            patch("full_agent_runner.generate_cold_message", return_value="Message preview"),
            patch("full_agent_runner.init_db"),
            patch("full_agent_runner.log_application", create=True) as log_application,
            contextlib.redirect_stdout(output),
        ):
            full_agent_runner.run_full_automation(
                "Example company",
                "AI internship",
                "Student resume",
                "https://example.test/",
            )
        log_application.assert_not_called()
        browser.close.assert_called_once()
        self.assertIn("not sent or saved as a draft", output.getvalue())


if __name__ == "__main__":
    unittest.main()
