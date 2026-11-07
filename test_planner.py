"""
test_planner.py - Unit and integration test suite for Personal Study Planner.
Tests domain models, SQLite persistence, streak calculations, date parsing,
and JSON data interchange using Python's standard unittest.
"""

import os
import tempfile
import unittest
from datetime import date, datetime, timedelta

from models import (
    Priority,
    Status,
    Subject,
    Task,
    StudyLog,
    Milestone,
)
from storage import StorageManager
from planner import StudyPlannerService, parse_academic_date
from sample_data import populate_seed_data


class TestDomainModels(unittest.TestCase):
    """Test model invariants, enum parsing, and convenience properties."""

    def test_priority_parsing(self):
        self.assertEqual(Priority.from_string("High"), Priority.HIGH)
        self.assertEqual(Priority.from_string("h"), Priority.HIGH)
        self.assertEqual(Priority.from_string("MEDIUM"), Priority.MEDIUM)
        self.assertEqual(Priority.from_string("m"), Priority.MEDIUM)
        self.assertEqual(Priority.from_string("low"), Priority.LOW)
        self.assertEqual(Priority.from_string("L"), Priority.LOW)
        with self.assertRaises(ValueError):
            Priority.from_string("UltraHigh")

    def test_status_parsing(self):
        self.assertEqual(Status.from_string("pending"), Status.PENDING)
        self.assertEqual(Status.from_string("p"), Status.PENDING)
        self.assertEqual(Status.from_string("In Progress"), Status.IN_PROGRESS)
        self.assertEqual(Status.from_string("ip"), Status.IN_PROGRESS)
        self.assertEqual(Status.from_string("completed"), Status.COMPLETED)
        self.assertEqual(Status.from_string("done"), Status.COMPLETED)
        self.assertEqual(Status.from_string("c"), Status.COMPLETED)
        with self.assertRaises(ValueError):
            Status.from_string("unknown_status")

    def test_task_overdue_and_due_today(self):
        today = date.today().isoformat()
        yesterday = (date.today() - timedelta(days=1)).isoformat()
        tomorrow = (date.today() + timedelta(days=1)).isoformat()

        task_due_today = Task(subject="Math", topic="Topology", deadline=today)
        self.assertTrue(task_due_today.is_due_today)
        self.assertFalse(task_due_today.is_overdue)

        task_overdue = Task(subject="History", topic="Rome", deadline=yesterday)
        self.assertTrue(task_overdue.is_overdue)
        self.assertFalse(task_overdue.is_due_today)

        # Completed tasks should not report as overdue
        task_overdue.mark_completed()
        self.assertFalse(task_overdue.is_overdue)
        self.assertEqual(task_overdue.status, Status.COMPLETED)
        self.assertIsNotNone(task_overdue.completed_at)

        task_future = Task(subject="Physics", topic="Optics", deadline=tomorrow)
        self.assertFalse(task_future.is_due_today)
        self.assertFalse(task_future.is_overdue)


class TestDateParser(unittest.TestCase):
    """Test natural language academic date parsing."""

    def test_relative_keywords(self):
        today = date.today().isoformat()
        tomorrow = (date.today() + timedelta(days=1)).isoformat()
        yesterday = (date.today() - timedelta(days=1)).isoformat()

        self.assertEqual(parse_academic_date("today"), today)
        self.assertEqual(parse_academic_date("t"), today)
        self.assertEqual(parse_academic_date("tomorrow"), tomorrow)
        self.assertEqual(parse_academic_date("tm"), tomorrow)
        self.assertEqual(parse_academic_date("yesterday"), yesterday)

    def test_relative_offsets(self):
        in_3_days = (date.today() + timedelta(days=3)).isoformat()
        in_2_weeks = (date.today() + timedelta(weeks=2)).isoformat()

        self.assertEqual(parse_academic_date("+3d"), in_3_days)
        self.assertEqual(parse_academic_date("+3"), in_3_days)
        self.assertEqual(parse_academic_date("+2w"), in_2_weeks)

    def test_standard_formats(self):
        self.assertEqual(parse_academic_date("2026-12-31"), "2026-12-31")
        self.assertEqual(parse_academic_date("2026/12/31"), "2026-12-31")

    def test_invalid_date(self):
        with self.assertRaises(ValueError):
            parse_academic_date("invalid_date_string_123")


class TestStorageAndAnalytics(unittest.TestCase):
    """Test SQLite storage manager, CRUD, streak algorithms, and JSON export."""

    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.db_path = os.path.join(self.temp_dir.name, "test_tracker.db")
        self.storage = StorageManager(self.db_path)
        self.service = StudyPlannerService(self.storage)

    def tearDown(self):
        self.temp_dir.cleanup()

    def test_task_crud(self):
        task = self.service.create_task(
            subject="Algorithms",
            topic="Dynamic Programming",
            deadline_input="today",
            priority=Priority.HIGH,
            estimated_hours=3.0,
            notes="Memoization tables",
        )
        self.assertIsNotNone(task.id)

        # Retrieve
        fetched = self.service.get_task(task.id)
        self.assertIsNotNone(fetched)
        self.assertEqual(fetched.topic, "Dynamic Programming")
        self.assertEqual(fetched.priority, Priority.HIGH)
        self.assertEqual(fetched.status, Status.PENDING)

        # Update status
        self.service.update_task_status(task.id, Status.COMPLETED)
        updated = self.service.get_task(task.id)
        self.assertEqual(updated.status, Status.COMPLETED)
        self.assertIsNotNone(updated.completed_at)

        # Edit fields
        self.service.edit_task(task.id, topic="Advanced DP", estimated_hours=4.5)
        edited = self.service.get_task(task.id)
        self.assertEqual(edited.topic, "Advanced DP")
        self.assertEqual(edited.estimated_hours, 4.5)

        # Delete
        self.assertTrue(self.service.delete_task(task.id))
        self.assertIsNone(self.service.get_task(task.id))

    def test_streak_calculation(self):
        today = date.today()
        # Case 1: No study logs -> streak 0, 0
        curr, longest = self.storage.calculate_streaks()
        self.assertEqual(curr, 0)
        self.assertEqual(longest, 0)

        # Case 2: Log for today only -> streak 1, 1
        self.storage.add_study_log(
            StudyLog(subject="Math", topic="Calculus", hours_spent=2.0, session_date=today.isoformat())
        )
        curr, longest = self.storage.calculate_streaks()
        self.assertEqual(curr, 1)
        self.assertEqual(longest, 1)

        # Case 3: Log for yesterday and day before -> 3 days streak
        self.storage.add_study_log(
            StudyLog(
                subject="Math",
                topic="Calculus",
                hours_spent=1.5,
                session_date=(today - timedelta(days=1)).isoformat(),
            )
        )
        self.storage.add_study_log(
            StudyLog(
                subject="Math",
                topic="Calculus",
                hours_spent=1.0,
                session_date=(today - timedelta(days=2)).isoformat(),
            )
        )
        curr, longest = self.storage.calculate_streaks()
        self.assertEqual(curr, 3)
        self.assertEqual(longest, 3)

        # Case 4: Gap of 2 days, then a historical 4-day streak
        base_past = today - timedelta(days=10)
        for offset in range(4):
            d = (base_past + timedelta(days=offset)).isoformat()
            self.storage.add_study_log(
                StudyLog(subject="History", topic="War", hours_spent=1.0, session_date=d)
            )

        curr, longest = self.storage.calculate_streaks()
        self.assertEqual(curr, 3)  # current streak is still 3 days (today, -1, -2)
        self.assertEqual(longest, 4)  # historical streak was 4 days

    def test_daily_and_weekly_views(self):
        today = date.today().isoformat()
        self.service.create_task("Algorithms", "Trees", "today", Priority.MEDIUM)
        self.service.log_study_session("Algorithms", "Trees", 2.5, "today")

        daily_data = self.service.get_daily_view("today")
        self.assertEqual(len(daily_data["tasks_due"]), 1)
        self.assertEqual(len(daily_data["study_logs"]), 1)
        self.assertEqual(daily_data["summary"].total_hours, 2.5)

        weekly_data = self.service.get_weekly_view("today")
        self.assertGreaterEqual(weekly_data["total_hours"], 2.5)
        self.assertIn("Algorithms", weekly_data["subject_breakdown"])

    def test_milestone_management(self):
        m = self.service.add_milestone(
            title="Syllabus Defense",
            subject="Algorithms",
            target_date_input="+2w",
            description="Oral examination",
        )
        self.assertIsNotNone(m.id)
        self.assertFalse(m.achieved)

        self.service.mark_milestone_achieved(m.id)
        milestones = self.storage.list_milestones()
        self.assertEqual(len(milestones), 1)
        self.assertTrue(milestones[0].achieved)

    def test_json_export_and_import(self):
        # Populate with sample data
        populate_seed_data(self.storage)

        json_file = os.path.join(self.temp_dir.name, "export_test.json")
        exported_path = self.storage.export_to_json(json_file)
        self.assertTrue(os.path.exists(exported_path))

        # Create new blank database and import
        new_db_path = os.path.join(self.temp_dir.name, "imported_tracker.db")
        new_storage = StorageManager(new_db_path)
        counts = new_storage.import_from_json(exported_path)

        self.assertGreater(counts["subjects"], 0)
        self.assertGreater(counts["tasks"], 0)
        self.assertGreater(counts["study_logs"], 0)
        self.assertGreater(counts["milestones"], 0)

        imported_tasks = new_storage.list_tasks()
        self.assertGreaterEqual(len(imported_tasks), 4)


if __name__ == "__main__":
    unittest.main()
