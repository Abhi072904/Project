"""
Auth + per-user data isolation tests. These exercise the real Flask app
(via its test client) rather than calling services.py directly, since the
thing being verified here - that one user genuinely cannot see or modify
another user's rows through the API - is an HTTP-layer guarantee.
"""
import tempfile
import unittest
from pathlib import Path

from app.main import create_app


class TestAuthAndIsolation(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.NamedTemporaryFile(suffix=".db", delete=False)
        self._tmp.close()
        self.app = create_app(database_path=self._tmp.name)
        self.app.testing = True
        self.client = self.app.test_client()

    def tearDown(self):
        Path(self._tmp.name).unlink(missing_ok=True)

    def _signup(self, client, email, password="password123"):
        return client.post("/auth/signup", json={"email": email, "password": password})

    def test_signup_then_protected_route_succeeds(self):
        self._signup(self.client, "a@example.com")
        res = self.client.get("/subscriptions")
        self.assertEqual(res.status_code, 200)

    def test_unauthenticated_request_is_rejected(self):
        res = self.client.get("/subscriptions")
        self.assertEqual(res.status_code, 401)

    def test_duplicate_email_signup_is_rejected(self):
        self._signup(self.client, "dup@example.com")
        res = self._signup(self.app.test_client(), "dup@example.com")
        self.assertEqual(res.status_code, 409)

    def test_wrong_password_login_is_rejected(self):
        self._signup(self.client, "b@example.com", password="correcthorse")
        res = self.app.test_client().post(
            "/auth/login", json={"email": "b@example.com", "password": "wrongpass"}
        )
        self.assertEqual(res.status_code, 401)

    def test_logout_revokes_access(self):
        self._signup(self.client, "c@example.com")
        self.assertEqual(self.client.get("/subscriptions").status_code, 200)
        self.client.post("/auth/logout")
        self.assertEqual(self.client.get("/subscriptions").status_code, 401)

    def test_users_cannot_see_or_modify_each_others_subscriptions(self):
        client_a = self.app.test_client()
        client_b = self.app.test_client()
        self._signup(client_a, "userA@example.com")
        self._signup(client_b, "userB@example.com")

        subs_a = client_a.get("/subscriptions").get_json()
        subs_b = client_b.get("/subscriptions").get_json()
        self.assertGreater(len(subs_a), 0)
        self.assertGreater(len(subs_b), 0)

        # Both users get their own private copy of the same seed data, so
        # ids can legitimately collide across users - that's the point.
        target_id = subs_b[0]["id"]
        original_status = subs_b[0]["status"]

        # User A tries to cancel a subscription id that belongs to user B's
        # namespace - since ids aren't globally unique in meaning, this
        # should 404 for A (no row with that id AND user_id=A exists) rather
        # than silently succeeding or leaking B's data.
        res = client_a.patch(f"/subscriptions/{target_id}", json={"status": "cancelled"})
        # Either 404 (A has no subscription with this id) or, if A
        # coincidentally also has a row with this id, it must be A's own row
        # that changed - never B's.
        subs_b_after = client_b.get("/subscriptions").get_json()
        b_row_after = next(r for r in subs_b_after if r["id"] == target_id)
        self.assertEqual(b_row_after["status"], original_status)

    def test_seed_data_is_private_per_user(self):
        client_a = self.app.test_client()
        client_b = self.app.test_client()
        self._signup(client_a, "priv1@example.com")
        self._signup(client_b, "priv2@example.com")

        subs_a = client_a.get("/subscriptions").get_json()
        target = subs_a[0]
        client_a.patch(f"/subscriptions/{target['id']}", json={"status": "cancelled"})

        subs_a_after = client_a.get("/subscriptions").get_json()
        subs_b_after = client_b.get("/subscriptions").get_json()
        row_a = next(r for r in subs_a_after if r["id"] == target["id"])
        # ids are a global autoincrement, not per-user - so user B's copy of
        # the same seeded merchant has a different id. Match on merchant
        # name instead to find B's equivalent row.
        row_b = next(r for r in subs_b_after if r["merchant_normalized"] == target["merchant_normalized"])
        self.assertEqual(row_a["status"], "cancelled")
        self.assertEqual(row_b["status"], "active")  # untouched, different row entirely


if __name__ == "__main__":
    unittest.main()
