"""
storage.py - SQLite & JSON persistence layer for Personal Study Planner.
Provides transactional storage, schema initialization, analytical queries,
and JSON data interchange.
"""

from __future__ import annotations
import json
import os
import sqlite3
from contextlib import contextmanager
from datetime import date, datetime, timedelta
from pathlib import Path
from typing import List, Optional, Dict, Any, Tuple

from models import (
    Priority,
    Status,
    Subject,
    Task,
    StudyLog,
    Milestone,
    SubjectProgress,
    DailySummary,
    ScholarStats,
)


class StorageManager:
    """
    Manages persistent SQLite ledger storage and optional JSON import/export.
    Guarantees ACID transactions, thread safety, and auto-creation of tables.
    """

    DEFAULT_DB_FILENAME = "tracker.db"
    DEFAULT_JSON_FILENAME = "study_data.json"

    def __init__(self, db_path: Optional[str] = None):
        """Initialize the storage engine with the specified database path."""
        if db_path is None:
            # Check environment variable for cloud deployment persistence
            env_db = os.environ.get("DATABASE_PATH")
            if env_db:
                self.db_path = env_db
                self.json_path = os.environ.get(
                    "JSON_PATH", str(Path(env_db).with_name(self.DEFAULT_JSON_FILENAME))
                )
            else:
                base_dir = Path(__file__).resolve().parent
                self.db_path = str(base_dir / self.DEFAULT_DB_FILENAME)
                self.json_path = str(base_dir / self.DEFAULT_JSON_FILENAME)
        else:
            self.db_path = db_path
            self.json_path = str(Path(db_path).with_name(self.DEFAULT_JSON_FILENAME))

        self._init_db()

    @contextmanager
    def _get_connection(self):
        """Context manager yielding a SQLite connection with row factory enabled."""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA foreign_keys = ON;")
        conn.execute("PRAGMA journal_mode = WAL;")
        try:
            yield conn
            conn.commit()
        except Exception:
            conn.rollback()
            raise
        finally:
            conn.close()

    def _init_db(self) -> None:
        """Create database tables and performance indexes if they do not exist."""
        with self._get_connection() as conn:
            conn.executescript("""
                CREATE TABLE IF NOT EXISTS subjects (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    name TEXT UNIQUE NOT NULL,
                    target_weekly_hours REAL DEFAULT 5.0,
                    color_theme TEXT DEFAULT '#D4AF37',
                    description TEXT DEFAULT '',
                    created_at TEXT NOT NULL
                );

                CREATE TABLE IF NOT EXISTS tasks (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    subject TEXT NOT NULL,
                    topic TEXT NOT NULL,
                    deadline TEXT NOT NULL,
                    priority TEXT NOT NULL,
                    status TEXT NOT NULL,
                    estimated_hours REAL DEFAULT 1.0,
                    notes TEXT DEFAULT '',
                    created_at TEXT NOT NULL,
                    completed_at TEXT
                );

                CREATE TABLE IF NOT EXISTS study_logs (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    subject TEXT NOT NULL,
                    topic TEXT NOT NULL,
                    hours_spent REAL NOT NULL,
                    session_date TEXT NOT NULL,
                    notes TEXT DEFAULT '',
                    created_at TEXT NOT NULL
                );

                CREATE TABLE IF NOT EXISTS milestones (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    title TEXT NOT NULL,
                    subject TEXT NOT NULL,
                    target_date TEXT NOT NULL,
                    achieved INTEGER DEFAULT 0,
                    achieved_at TEXT,
                    description TEXT DEFAULT '',
                    created_at TEXT NOT NULL
                );

                CREATE INDEX IF NOT EXISTS idx_tasks_deadline ON tasks(deadline);
                CREATE INDEX IF NOT EXISTS idx_tasks_subject ON tasks(subject);
                CREATE INDEX IF NOT EXISTS idx_tasks_status ON tasks(status);
                CREATE INDEX IF NOT EXISTS idx_logs_date ON study_logs(session_date);
                CREATE INDEX IF NOT EXISTS idx_logs_subject ON study_logs(subject);
                CREATE INDEX IF NOT EXISTS idx_milestones_date ON milestones(target_date);
            """)

    # =========================================================================
    # SUBJECT CRUD
    # =========================================================================

    def add_subject(self, subject: Subject) -> int:
        """Add a new subject to the ledger."""
        with self._get_connection() as conn:
            cursor = conn.execute(
                """
                INSERT INTO subjects (name, target_weekly_hours, color_theme, description, created_at)
                VALUES (?, ?, ?, ?, ?)
                """,
                (
                    subject.name.strip(),
                    subject.target_weekly_hours,
                    subject.color_theme,
                    subject.description.strip(),
                    subject.created_at,
                ),
            )
            subject.id = cursor.lastrowid
            return cursor.lastrowid

    def get_subject_by_name(self, name: str) -> Optional[Subject]:
        """Fetch subject details by unique name."""
        with self._get_connection() as conn:
            row = conn.execute(
                "SELECT * FROM subjects WHERE LOWER(name) = LOWER(?)", (name.strip(),)
            ).fetchone()
            if row:
                return Subject(
                    id=row["id"],
                    name=row["name"],
                    target_weekly_hours=row["target_weekly_hours"],
                    color_theme=row["color_theme"],
                    description=row["description"],
                    created_at=row["created_at"],
                )
            return None

    def list_subjects(self) -> List[Subject]:
        """List all registered subjects."""
        with self._get_connection() as conn:
            rows = conn.execute("SELECT * FROM subjects ORDER BY name ASC").fetchall()
            return [
                Subject(
                    id=row["id"],
                    name=row["name"],
                    target_weekly_hours=row["target_weekly_hours"],
                    color_theme=row["color_theme"],
                    description=row["description"],
                    created_at=row["created_at"],
                )
                for row in rows
            ]

    def delete_subject(self, name: str) -> bool:
        """Delete a subject from the ledger."""
        with self._get_connection() as conn:
            cursor = conn.execute(
                "DELETE FROM subjects WHERE LOWER(name) = LOWER(?)", (name.strip(),)
            )
            return cursor.rowcount > 0

    # =========================================================================
    # TASK CRUD
    # =========================================================================

    def add_task(self, task: Task) -> int:
        """Create a new study task or reading deadline."""
        with self._get_connection() as conn:
            cursor = conn.execute(
                """
                INSERT INTO tasks (subject, topic, deadline, priority, status, estimated_hours, notes, created_at, completed_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    task.subject.strip(),
                    task.topic.strip(),
                    task.deadline.strip(),
                    task.priority.value,
                    task.status.value,
                    max(0.1, float(task.estimated_hours)),
                    task.notes.strip(),
                    task.created_at,
                    task.completed_at,
                ),
            )
            task.id = cursor.lastrowid

            # Ensure subject exists in subjects table
            self._ensure_subject_exists(conn, task.subject)
            return cursor.lastrowid

    def update_task(self, task: Task) -> bool:
        """Update existing task details."""
        if not task.id:
            return False
        with self._get_connection() as conn:
            cursor = conn.execute(
                """
                UPDATE tasks
                SET subject = ?, topic = ?, deadline = ?, priority = ?, status = ?,
                    estimated_hours = ?, notes = ?, completed_at = ?
                WHERE id = ?
                """,
                (
                    task.subject.strip(),
                    task.topic.strip(),
                    task.deadline.strip(),
                    task.priority.value,
                    task.status.value,
                    task.estimated_hours,
                    task.notes.strip(),
                    task.completed_at,
                    task.id,
                ),
            )
            self._ensure_subject_exists(conn, task.subject)
            return cursor.rowcount > 0

    def get_task(self, task_id: int) -> Optional[Task]:
        """Retrieve task by numeric ID."""
        with self._get_connection() as conn:
            row = conn.execute("SELECT * FROM tasks WHERE id = ?", (task_id,)).fetchone()
            if row:
                return self._row_to_task(row)
            return None

    def delete_task(self, task_id: int) -> bool:
        """Permanently delete a task by ID."""
        with self._get_connection() as conn:
            cursor = conn.execute("DELETE FROM tasks WHERE id = ?", (task_id,))
            return cursor.rowcount > 0

    def list_tasks(
        self,
        subject: Optional[str] = None,
        status: Optional[Status] = None,
        priority: Optional[Priority] = None,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
        order_by_deadline: bool = True,
    ) -> List[Task]:
        """List tasks with optional filters."""
        query = "SELECT * FROM tasks WHERE 1=1"
        params: List[Any] = []

        if subject:
            query += " AND LOWER(subject) = LOWER(?)"
            params.append(subject.strip())
        if status:
            query += " AND status = ?"
            params.append(status.value)
        if priority:
            query += " AND priority = ?"
            params.append(priority.value)
        if start_date:
            query += " AND deadline >= ?"
            params.append(start_date)
        if end_date:
            query += " AND deadline <= ?"
            params.append(end_date)

        if order_by_deadline:
            query += " ORDER BY deadline ASC, priority DESC, id ASC"
        else:
            query += " ORDER BY id DESC"

        with self._get_connection() as conn:
            rows = conn.execute(query, params).fetchall()
            return [self._row_to_task(row) for row in rows]

    def _row_to_task(self, row: sqlite3.Row) -> Task:
        """Convert a SQLite row into a Task dataclass."""
        return Task(
            id=row["id"],
            subject=row["subject"],
            topic=row["topic"],
            deadline=row["deadline"],
            priority=Priority.from_string(row["priority"]),
            status=Status.from_string(row["status"]),
            estimated_hours=row["estimated_hours"],
            notes=row["notes"],
            created_at=row["created_at"],
            completed_at=row["completed_at"],
        )

    # =========================================================================
    # STUDY LOGS CRUD
    # =========================================================================

    def add_study_log(self, log: StudyLog) -> int:
        """Record completed study time in the ledger."""
        with self._get_connection() as conn:
            cursor = conn.execute(
                """
                INSERT INTO study_logs (subject, topic, hours_spent, session_date, notes, created_at)
                VALUES (?, ?, ?, ?, ?, ?)
                """,
                (
                    log.subject.strip(),
                    log.topic.strip(),
                    max(0.01, float(log.hours_spent)),
                    log.session_date.strip(),
                    log.notes.strip(),
                    log.created_at,
                ),
            )
            log.id = cursor.lastrowid
            self._ensure_subject_exists(conn, log.subject)
            return cursor.lastrowid

    def list_study_logs(
        self,
        subject: Optional[str] = None,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
        limit: int = 100,
    ) -> List[StudyLog]:
        """List study logs with filtering options."""
        query = "SELECT * FROM study_logs WHERE 1=1"
        params: List[Any] = []

        if subject:
            query += " AND LOWER(subject) = LOWER(?)"
            params.append(subject.strip())
        if start_date:
            query += " AND session_date >= ?"
            params.append(start_date)
        if end_date:
            query += " AND session_date <= ?"
            params.append(end_date)

        query += " ORDER BY session_date DESC, id DESC LIMIT ?"
        params.append(limit)

        with self._get_connection() as conn:
            rows = conn.execute(query, params).fetchall()
            return [
                StudyLog(
                    id=row["id"],
                    subject=row["subject"],
                    topic=row["topic"],
                    hours_spent=row["hours_spent"],
                    session_date=row["session_date"],
                    notes=row["notes"],
                    created_at=row["created_at"],
                )
                for row in rows
            ]

    def delete_study_log(self, log_id: int) -> bool:
        """Delete a study log entry."""
        with self._get_connection() as conn:
            cursor = conn.execute("DELETE FROM study_logs WHERE id = ?", (log_id,))
            return cursor.rowcount > 0

    # =========================================================================
    # MILESTONES CRUD
    # =========================================================================

    def add_milestone(self, milestone: Milestone) -> int:
        """Register a new major academic milestone or exam date."""
        with self._get_connection() as conn:
            cursor = conn.execute(
                """
                INSERT INTO milestones (title, subject, target_date, achieved, achieved_at, description, created_at)
                VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    milestone.title.strip(),
                    milestone.subject.strip(),
                    milestone.target_date.strip(),
                    1 if milestone.achieved else 0,
                    milestone.achieved_at,
                    milestone.description.strip(),
                    milestone.created_at,
                ),
            )
            milestone.id = cursor.lastrowid
            self._ensure_subject_exists(conn, milestone.subject)
            return cursor.lastrowid

    def list_milestones(self, subject: Optional[str] = None) -> List[Milestone]:
        """List all milestones."""
        query = "SELECT * FROM milestones WHERE 1=1"
        params: List[Any] = []
        if subject:
            query += " AND LOWER(subject) = LOWER(?)"
            params.append(subject.strip())
        query += " ORDER BY target_date ASC, id ASC"

        with self._get_connection() as conn:
            rows = conn.execute(query, params).fetchall()
            return [
                Milestone(
                    id=row["id"],
                    title=row["title"],
                    subject=row["subject"],
                    target_date=row["target_date"],
                    achieved=bool(row["achieved"]),
                    achieved_at=row["achieved_at"],
                    description=row["description"],
                    created_at=row["created_at"],
                )
                for row in rows
            ]

    def mark_milestone_achieved(self, milestone_id: int) -> bool:
        """Mark milestone as achieved with timestamp."""
        now_str = datetime.now().isoformat()
        with self._get_connection() as conn:
            cursor = conn.execute(
                """
                UPDATE milestones
                SET achieved = 1, achieved_at = ?
                WHERE id = ?
                """,
                (now_str, milestone_id),
            )
            return cursor.rowcount > 0

    def delete_milestone(self, milestone_id: int) -> bool:
        """Delete milestone from ledger."""
        with self._get_connection() as conn:
            cursor = conn.execute("DELETE FROM milestones WHERE id = ?", (milestone_id,))
            return cursor.rowcount > 0

    # =========================================================================
    # ANALYTICS & STATS ENGINE
    # =========================================================================

    def calculate_streaks(self) -> Tuple[int, int]:
        """
        Calculate (current_streak, longest_streak) in consecutive calendar days.
        A day counts toward a streak if at least one study session was logged.
        """
        with self._get_connection() as conn:
            rows = conn.execute(
                "SELECT DISTINCT session_date FROM study_logs WHERE hours_spent > 0 ORDER BY session_date DESC"
            ).fetchall()

        if not rows:
            return 0, 0

        study_dates = []
        for r in rows:
            try:
                study_dates.append(datetime.strptime(r["session_date"], "%Y-%m-%d").date())
            except ValueError:
                continue

        if not study_dates:
            return 0, 0

        # Sort descending
        study_dates = sorted(list(set(study_dates)), reverse=True)

        today = date.today()
        yesterday = today - timedelta(days=1)

        # Calculate current streak
        current_streak = 0
        if study_dates[0] == today:
            # Streak active today
            current_streak = 1
            expected = today - timedelta(days=1)
            for d in study_dates[1:]:
                if d == expected:
                    current_streak += 1
                    expected -= timedelta(days=1)
                else:
                    break
        elif study_dates[0] == yesterday:
            # Did not study yet today, but studied yesterday (streak still alive)
            current_streak = 1
            expected = yesterday - timedelta(days=1)
            for d in study_dates[1:]:
                if d == expected:
                    current_streak += 1
                    expected -= timedelta(days=1)
                else:
                    break
        else:
            # Streak broken
            current_streak = 0

        # Calculate longest streak historically
        longest_streak = 1
        current_run = 1
        sorted_asc = sorted(study_dates)
        for i in range(1, len(sorted_asc)):
            if sorted_asc[i] == sorted_asc[i - 1] + timedelta(days=1):
                current_run += 1
                if current_run > longest_streak:
                    longest_streak = current_run
            elif sorted_asc[i] > sorted_asc[i - 1] + timedelta(days=1):
                current_run = 1

        longest_streak = max(longest_streak, current_streak)
        return current_streak, longest_streak

    def get_daily_summary(self, target_date: Optional[date] = None) -> DailySummary:
        """Compile a summary of study sessions and tasks for a given date."""
        if target_date is None:
            target_date = date.today()
        date_str = target_date.isoformat()

        with self._get_connection() as conn:
            # Logs for date
            log_rows = conn.execute(
                "SELECT subject, hours_spent, notes FROM study_logs WHERE session_date = ?",
                (date_str,),
            ).fetchall()

            total_hours = sum(r["hours_spent"] for r in log_rows)
            sessions_count = len(log_rows)
            subject_hours: Dict[str, float] = {}
            notes_list: List[str] = []

            for r in log_rows:
                subj = r["subject"]
                subject_hours[subj] = subject_hours.get(subj, 0.0) + r["hours_spent"]
                if r["notes"] and r["notes"].strip():
                    notes_list.append(f"{subj}: {r['notes'].strip()}")

            # Tasks completed on this date
            completed_count = conn.execute(
                "SELECT COUNT(*) as c FROM tasks WHERE status = ? AND completed_at LIKE ?",
                (Status.COMPLETED.value, f"{date_str}%"),
            ).fetchone()["c"]

            # Tasks due on this date
            due_count = conn.execute(
                "SELECT COUNT(*) as c FROM tasks WHERE deadline = ?", (date_str,)
            ).fetchone()["c"]

        return DailySummary(
            date_str=date_str,
            total_hours=round(total_hours, 2),
            sessions_count=sessions_count,
            tasks_completed=completed_count,
            tasks_due=due_count,
            subject_hours=subject_hours,
            notes_list=notes_list,
        )

    def get_subject_progress_list(self) -> List[SubjectProgress]:
        """Compute task completion percentage and weekly hours for each subject."""
        today = date.today()
        # Find start of current week (Monday)
        start_of_week = today - timedelta(days=today.weekday())
        start_of_week_str = start_of_week.isoformat()

        subjects = self.list_subjects()
        subject_names = [s.name for s in subjects]

        with self._get_connection() as conn:
            # Task counts
            task_rows = conn.execute(
                """
                SELECT subject,
                       COUNT(*) as total,
                       SUM(CASE WHEN status = 'Completed' THEN 1 ELSE 0 END) as completed
                FROM tasks
                GROUP BY subject
                """
            ).fetchall()
            task_map = {r["subject"]: (r["total"], r["completed"] or 0) for r in task_rows}

            # Weekly hours
            weekly_rows = conn.execute(
                """
                SELECT subject, SUM(hours_spent) as hours
                FROM study_logs
                WHERE session_date >= ?
                GROUP BY subject
                """,
                (start_of_week_str,),
            ).fetchall()
            weekly_map = {r["subject"]: (r["hours"] or 0.0) for r in weekly_rows}

            # Lifetime hours
            life_rows = conn.execute(
                """
                SELECT subject, SUM(hours_spent) as hours
                FROM study_logs
                GROUP BY subject
                """
            ).fetchall()
            life_map = {r["subject"]: (r["hours"] or 0.0) for r in life_rows}

        results: List[SubjectProgress] = []
        # Include all known subjects plus any subjects present in tasks/logs
        all_names = sorted(list(set(subject_names + list(task_map.keys()) + list(weekly_map.keys()))))

        for name in all_names:
            total_tasks, completed_tasks = task_map.get(name, (0, 0))
            task_pct = (completed_tasks / total_tasks * 100.0) if total_tasks > 0 else 0.0

            subj_obj = next((s for s in subjects if s.name.lower() == name.lower()), None)
            target_hours = subj_obj.target_weekly_hours if subj_obj else 5.0
            weekly_hours = weekly_map.get(name, 0.0)
            weekly_pct = (weekly_hours / target_hours * 100.0) if target_hours > 0 else 0.0
            lifetime_hours = life_map.get(name, 0.0)

            results.append(
                SubjectProgress(
                    subject=name,
                    total_tasks=total_tasks,
                    completed_tasks=completed_tasks,
                    task_completion_pct=round(task_pct, 1),
                    weekly_hours_logged=round(weekly_hours, 2),
                    weekly_target_hours=round(target_hours, 1),
                    weekly_hours_pct=round(weekly_pct, 1),
                    lifetime_hours=round(lifetime_hours, 2),
                )
            )

        return results

    def get_scholar_stats(self) -> ScholarStats:
        """Compile holistic progress statistics across all study tracks."""
        current_streak, longest_streak = self.calculate_streaks()
        subject_progress = self.get_subject_progress_list()

        today_str = date.today().isoformat()
        start_of_week_str = (date.today() - timedelta(days=date.today().weekday())).isoformat()

        with self._get_connection() as conn:
            lifetime_h = conn.execute(
                "SELECT SUM(hours_spent) as h FROM study_logs"
            ).fetchone()["h"] or 0.0

            today_h = conn.execute(
                "SELECT SUM(hours_spent) as h FROM study_logs WHERE session_date = ?",
                (today_str,),
            ).fetchone()["h"] or 0.0

            week_h = conn.execute(
                "SELECT SUM(hours_spent) as h FROM study_logs WHERE session_date >= ?",
                (start_of_week_str,),
            ).fetchone()["h"] or 0.0

            tasks_completed = conn.execute(
                "SELECT COUNT(*) as c FROM tasks WHERE status = ?", (Status.COMPLETED.value,)
            ).fetchone()["c"]

            tasks_pending = conn.execute(
                "SELECT COUNT(*) as c FROM tasks WHERE status IN (?, ?)",
                (Status.PENDING.value, Status.IN_PROGRESS.value),
            ).fetchone()["c"]

            milestones_achieved = conn.execute(
                "SELECT COUNT(*) as c FROM milestones WHERE achieved = 1"
            ).fetchone()["c"]

            milestones_total = conn.execute(
                "SELECT COUNT(*) as c FROM milestones"
            ).fetchone()["c"]

            subjects_count = conn.execute("SELECT COUNT(*) as c FROM subjects").fetchone()["c"]

        return ScholarStats(
            current_streak=current_streak,
            longest_streak=longest_streak,
            total_lifetime_hours=round(lifetime_h, 2),
            total_tasks_completed=tasks_completed,
            total_tasks_pending=tasks_pending,
            milestones_achieved=milestones_achieved,
            milestones_total=milestones_total,
            today_hours=round(today_h, 2),
            this_week_hours=round(week_h, 2),
            subjects_count=subjects_count,
            subject_breakdowns=subject_progress,
        )

    # =========================================================================
    # JSON DATA BACKUP & INTERCHANGE
    # =========================================================================

    def export_to_json(self, json_filepath: Optional[str] = None) -> str:
        """Export all ledger subjects, tasks, logs, and milestones to a JSON file."""
        target_path = json_filepath or self.json_path
        with self._get_connection() as conn:
            subjects = [dict(r) for r in conn.execute("SELECT * FROM subjects").fetchall()]
            tasks = [dict(r) for r in conn.execute("SELECT * FROM tasks").fetchall()]
            logs = [dict(r) for r in conn.execute("SELECT * FROM study_logs").fetchall()]
            milestones = [dict(r) for r in conn.execute("SELECT * FROM milestones").fetchall()]

        data = {
            "version": "1.0",
            "exported_at": datetime.now().isoformat(),
            "subjects": subjects,
            "tasks": tasks,
            "study_logs": logs,
            "milestones": milestones,
        }

        with open(target_path, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)

        return target_path

    def import_from_json(self, json_filepath: Optional[str] = None, overwrite: bool = False) -> Dict[str, int]:
        """
        Import ledger subjects, tasks, logs, and milestones from a JSON file.
        Returns the counts of imported records.
        """
        target_path = json_filepath or self.json_path
        if not os.path.exists(target_path):
            raise FileNotFoundError(f"JSON data file not found at {target_path}")

        with open(target_path, "r", encoding="utf-8") as f:
            data = json.load(f)

        counts = {"subjects": 0, "tasks": 0, "study_logs": 0, "milestones": 0}

        with self._get_connection() as conn:
            if overwrite:
                conn.execute("DELETE FROM milestones")
                conn.execute("DELETE FROM study_logs")
                conn.execute("DELETE FROM tasks")
                conn.execute("DELETE FROM subjects")

            # Subjects
            for s in data.get("subjects", []):
                try:
                    conn.execute(
                        """
                        INSERT OR IGNORE INTO subjects (name, target_weekly_hours, color_theme, description, created_at)
                        VALUES (?, ?, ?, ?, ?)
                        """,
                        (
                            s["name"],
                            s.get("target_weekly_hours", 5.0),
                            s.get("color_theme", "#D4AF37"),
                            s.get("description", ""),
                            s.get("created_at", datetime.now().isoformat()),
                        ),
                    )
                    counts["subjects"] += 1
                except Exception:
                    pass

            # Tasks
            for t in data.get("tasks", []):
                try:
                    conn.execute(
                        """
                        INSERT INTO tasks (subject, topic, deadline, priority, status, estimated_hours, notes, created_at, completed_at)
                        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                        """,
                        (
                            t["subject"],
                            t["topic"],
                            t["deadline"],
                            t.get("priority", "Medium"),
                            t.get("status", "Pending"),
                            t.get("estimated_hours", 1.0),
                            t.get("notes", ""),
                            t.get("created_at", datetime.now().isoformat()),
                            t.get("completed_at"),
                        ),
                    )
                    counts["tasks"] += 1
                except Exception:
                    pass

            # Logs
            for l in data.get("study_logs", []):
                try:
                    conn.execute(
                        """
                        INSERT INTO study_logs (subject, topic, hours_spent, session_date, notes, created_at)
                        VALUES (?, ?, ?, ?, ?, ?)
                        """,
                        (
                            l["subject"],
                            l["topic"],
                            l["hours_spent"],
                            l["session_date"],
                            l.get("notes", ""),
                            l.get("created_at", datetime.now().isoformat()),
                        ),
                    )
                    counts["study_logs"] += 1
                except Exception:
                    pass

            # Milestones
            for m in data.get("milestones", []):
                try:
                    conn.execute(
                        """
                        INSERT INTO milestones (title, subject, target_date, achieved, achieved_at, description, created_at)
                        VALUES (?, ?, ?, ?, ?, ?, ?)
                        """,
                        (
                            m["title"],
                            m["subject"],
                            m["target_date"],
                            1 if m.get("achieved") else 0,
                            m.get("achieved_at"),
                            m.get("description", ""),
                            m.get("created_at", datetime.now().isoformat()),
                        ),
                    )
                    counts["milestones"] += 1
                except Exception:
                    pass

        return counts

    def _ensure_subject_exists(self, conn: sqlite3.Connection, subject_name: str) -> None:
        """Helper to auto-register new subject names if they don't exist yet."""
        clean_name = subject_name.strip()
        if not clean_name:
            return
        conn.execute(
            """
            INSERT OR IGNORE INTO subjects (name, target_weekly_hours, color_theme, description, created_at)
            VALUES (?, 5.0, '#D4AF37', 'Auto-created discipline', ?)
            """,
            (clean_name, datetime.now().isoformat()),
        )
