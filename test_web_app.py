"""
test_web_app.py - Integration tests for the Flask Web Interface.
Ensures web routes render without errors and preserve underlying storage integrity.
"""

import os
import tempfile
import unittest

from app import app
from storage import StorageManager
from sample_data import populate_seed_data


class TestWebApp(unittest.TestCase):
    """Test web routes and application endpoints."""

    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.db_path = os.path.join(self.temp_dir.name, "test_web.db")
        os.environ["DATABASE_PATH"] = self.db_path

        # Configure Flask app for testing
        app.config["TESTING"] = True
        app.config["WTF_CSRF_ENABLED"] = False
        self.client = app.test_client()

        # Seed sample data
        storage = StorageManager(self.db_path)
        populate_seed_data(storage)

    def tearDown(self):
        if "DATABASE_PATH" in os.environ:
            del os.environ["DATABASE_PATH"]
        self.temp_dir.cleanup()

    def test_health_endpoint(self):
        response = self.client.get("/health")
        self.assertEqual(response.status_code, 200)
        data = response.get_json()
        self.assertEqual(data["status"], "healthy")

    def test_dashboard_route(self):
        response = self.client.get("/")
        self.assertEqual(response.status_code, 200)
        self.assertIn(b"The Scholar's Academic Ledger", response.data)
        self.assertIn(b"Scholarly Streak", response.data)

    def test_tasks_view_route(self):
        response = self.client.get("/tasks")
        self.assertEqual(response.status_code, 200)
        self.assertIn(b"Active Ledger", response.data)

    def test_daily_view_route(self):
        response = self.client.get("/daily")
        self.assertEqual(response.status_code, 200)
        self.assertIn(b"Daily Academic Journal", response.data)

    def test_weekly_view_route(self):
        response = self.client.get("/weekly")
        self.assertEqual(response.status_code, 200)
        self.assertIn(b"Weekly Curriculum Schedule", response.data)

    def test_analytics_view_route(self):
        response = self.client.get("/analytics")
        self.assertEqual(response.status_code, 200)
        self.assertIn(b"Scholarly Progress &amp; Streak Analytics", response.data)

    def test_milestones_view_route(self):
        response = self.client.get("/milestones")
        self.assertEqual(response.status_code, 200)
        self.assertIn(b"Academic Laurels &amp; Milestones", response.data)

    def test_timer_view_route(self):
        response = self.client.get("/timer")
        self.assertEqual(response.status_code, 200)
        self.assertIn(b"Focus Hourglass", response.data)

    def test_backup_view_and_export(self):
        response = self.client.get("/backup")
        self.assertEqual(response.status_code, 200)

        export_resp = self.client.get("/export")
        self.assertEqual(export_resp.status_code, 200)
        self.assertIn("application/json", export_resp.headers.get("Content-Type", ""))


if __name__ == "__main__":
    unittest.main()
