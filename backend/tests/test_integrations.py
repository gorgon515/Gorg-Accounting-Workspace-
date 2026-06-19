import base64
import unittest

from integrations import schemas, google, outlook


def _b64url(s: str) -> str:
    return base64.urlsafe_b64encode(s.encode()).decode().rstrip("=")


GMAIL = {
    "id": "m1", "snippet": "Please review the invoice by Friday",
    "labelIds": ["UNREAD", "INBOX"],
    "payload": {
        "headers": [
            {"name": "From", "value": "Accounting <acct@firm.com>"},
            {"name": "To", "value": "me@me.com"},
            {"name": "Subject", "value": "Invoice #123 due"},
            {"name": "Date", "value": "Mon, 16 Jun 2025 10:00:00 -0400"},
        ],
        "body": {"data": _b64url("Please review the invoice by Friday and approve.")},
    },
}
GRAPH_MSG = {
    "id": "g1", "subject": "Project sync", "bodyPreview": "Let's meet Tuesday",
    "from": {"emailAddress": {"address": "sam@x.com", "name": "Sam"}},
    "toRecipients": [{"emailAddress": {"address": "me@me.com"}}],
    "receivedDateTime": "2025-06-16T14:00:00Z", "isRead": False,
    "body": {"content": "Let's meet Tuesday at 2."},
}
GCAL_EVT = {"id": "e1", "summary": "Client call", "location": "Zoom",
            "start": {"dateTime": "2025-06-17T10:00:00-04:00"},
            "end": {"dateTime": "2025-06-17T11:00:00-04:00"},
            "attendees": [{"email": "a@b.com"}, {"email": "c@d.com"}]}
GRAPH_EVT = {"id": "ge1", "subject": "Standup", "isAllDay": False,
             "start": {"dateTime": "2025-06-17T09:00:00", "timeZone": "UTC"},
             "end": {"dateTime": "2025-06-17T09:30:00", "timeZone": "UTC"},
             "location": {"displayName": "Office"},
             "attendees": [{"emailAddress": {"address": "x@y.com"}}]}


class NormalizeTest(unittest.TestCase):
    def test_gmail(self):
        e = schemas.normalize_gmail(GMAIL)
        self.assertEqual(e["source"], "gmail")
        self.assertIn("acct@firm.com", e["from"])
        self.assertEqual(e["subject"], "Invoice #123 due")
        self.assertTrue(e["unread"])
        self.assertIn("approve", e["body"])

    def test_graph_message(self):
        e = schemas.normalize_graph_message(GRAPH_MSG)
        self.assertEqual(e["source"], "outlook")
        self.assertEqual(e["from"], "sam@x.com")
        self.assertTrue(e["unread"])

    def test_gcal_event(self):
        ev = schemas.normalize_gcal_event(GCAL_EVT)
        self.assertEqual(ev["title"], "Client call")
        self.assertEqual(ev["start"], "2025-06-17T10:00:00-04:00")
        self.assertEqual(ev["attendees"], ["a@b.com", "c@d.com"])

    def test_graph_event(self):
        ev = schemas.normalize_graph_event(GRAPH_EVT)
        self.assertEqual(ev["title"], "Standup")
        self.assertEqual(ev["location"], "Office")


class OAuthConstructionTest(unittest.TestCase):
    def test_google_auth_url(self):
        url = google.auth_url("cid123", "http://localhost/cb")
        self.assertIn("client_id=cid123", url)
        self.assertIn("access_type=offline", url)
        self.assertIn("accounts.google.com", url)

    def test_google_token_params(self):
        ex = google.exchange_params("code1", "cid", "secret", "http://cb")
        self.assertEqual(ex["grant_type"], "authorization_code")
        rf = google.refresh_params("rt", "cid", "secret")
        self.assertEqual(rf["grant_type"], "refresh_token")

    def test_outlook_auth_url(self):
        url = outlook.auth_url("oid", "http://localhost/cb", tenant="common")
        self.assertIn("login.microsoftonline.com/common", url)
        self.assertIn("client_id=oid", url)


if __name__ == "__main__":
    unittest.main()
