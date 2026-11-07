"""
planner.py - Business logic, scheduling services, date parsers, and validation
for the Personal Study Planner.
"""

from __future__ import annotations
import re
from datetime import date, datetime, timedelta
from typing import Optional, List, Dict, Any, Tuple

from models import (
    Priority,
    Status,
    Subject,
    Task,
    StudyLog,
    Milestone,
    ScholarStats,
    DailySummary,
)
from storage import StorageManager


def parse_academic_date(date_input: Optional[str]) -> str:
    """
    Parses flexible human-friendly date inputs into ISO YYYY-MM-DD format.
    Supports:
      - 'today', 't', 'now'
      - 'tomorrow', 'tm'
      - 'yesterday', 'yd'
      - '+1d', '+3d', '+1w', '+2w'
      - 'YYYY-MM-DD', 'YYYY/MM/DD', 'DD-MM-YYYY', 'DD/MM/YYYY'
    Raises ValueError with descriptive context if unparseable.
    """
    if not date_input or not date_input.strip():
        return date.today().isoformat()

    cleaned = date_input.strip().lower()
    today = date.today()

    if cleaned in ("today", "t", "now"):
        return today.isoformat()
    if cleaned in ("tomorrow", "tm"):
        return (today + timedelta(days=1)).isoformat()
    if cleaned in ("yesterday", "yd"):
        return (today - timedelta(days=1)).isoformat()

    # Relative offset like +1d, +3d, +2w
    offset_match = re.match(r"^\+(\d+)\s*([dwmy]?)$", cleaned)
    if offset_match:
        qty = int(offset_match.group(1))
        unit = offset_match.group(2) or "d"
        if unit == "d":
            return (today + timedelta(days=qty)).isoformat()
        if unit == "w":
            return (today + timedelta(weeks=qty)).isoformat()
        if unit == "m":
            return (today + timedelta(days=qty * 30)).isoformat()

    # Try common formats
    formats = [
        "%Y-%m-%d",
        "%Y/%m/%d",
        "%d-%m-%Y",
        "%d/%m/%Y",
        "%m/%d/%Y",
        "%Y.%m.%d",
        "%b %d, %Y",
        "%B %d, %Y",
    ]

    for fmt in formats:
        try:
            parsed = datetime.strptime(cleaned, fmt).date()
            return parsed.isoformat()
        except ValueError:
            continue

    raise ValueError(
        f"Unable to decipher date '{date_input}'. Use YYYY-MM-DD or shorthand like 'today', 'tomorrow', '+3d', '+1w'."
    )


class StudyPlannerService:
    """
    High-level business service coordinating storage operations,
    input sanitization, scheduling calculations, and academic statistics.
    """

    def __init__(self, storage: Optional[StorageManager] = None):
        self.storage = storage or StorageManager()

    # -------------------------------------------------------------------------
    # Task Operations
    # -------------------------------------------------------------------------

    def create_task(
        self,
        subject: str,
        topic: str,
        deadline_input: str,
        priority: Priority = Priority.MEDIUM,
        estimated_hours: float = 1.5,
        notes: str = "",
    ) -> Task:
        """Create and validate a new academic task."""
        if not subject or not subject.strip():
            raise ValueError("Discipline/Subject cannot be left blank.")
        if not topic or not topic.strip():
            raise ValueError("Topic/Assignment name cannot be left blank.")

        deadline = parse_academic_date(deadline_input)
        task = Task(
            subject=subject.strip(),
            topic=topic.strip(),
            deadline=deadline,
            priority=priority,
            status=Status.PENDING,
            estimated_hours=max(0.1, float(estimated_hours)),
            notes=notes.strip(),
        )
        task_id = self.storage.add_task(task)
        task.id = task_id
        return task

    def update_task_status(self, task_id: int, new_status: Status) -> Optional[Task]:
        """Update the status of an existing task."""
        task = self.storage.get_task(task_id)
        if not task:
            return None

        task.status = new_status
        if new_status == Status.COMPLETED:
            task.completed_at = datetime.now().isoformat()
        else:
            task.completed_at = None

        self.storage.update_task(task)
        return task

    def edit_task(
        self,
        task_id: int,
        topic: Optional[str] = None,
        subject: Optional[str] = None,
        deadline: Optional[str] = None,
        priority: Optional[Priority] = None,
        status: Optional[Status] = None,
        estimated_hours: Optional[float] = None,
        notes: Optional[str] = None,
    ) -> Optional[Task]:
        """Modify fields on an existing task."""
        task = self.storage.get_task(task_id)
        if not task:
            return None

        if topic is not None and topic.strip():
            task.topic = topic.strip()
        if subject is not None and subject.strip():
            task.subject = subject.strip()
        if deadline is not None and deadline.strip():
            task.deadline = parse_academic_date(deadline)
        if priority is not None:
            task.priority = priority
        if status is not None:
            task.status = status
            if status == Status.COMPLETED and not task.completed_at:
                task.completed_at = datetime.now().isoformat()
            elif status != Status.COMPLETED:
                task.completed_at = None
        if estimated_hours is not None:
            task.estimated_hours = max(0.1, float(estimated_hours))
        if notes is not None:
            task.notes = notes.strip()

        self.storage.update_task(task)
        return task

    def delete_task(self, task_id: int) -> bool:
        """Remove a task from the ledger."""
        return self.storage.delete_task(task_id)

    def get_task(self, task_id: int) -> Optional[Task]:
        """Fetch single task by ID."""
        return self.storage.get_task(task_id)

    # -------------------------------------------------------------------------
    # Study Log Operations
    # -------------------------------------------------------------------------

    def log_study_session(
        self,
        subject: str,
        topic: str,
        hours: float,
        date_input: Optional[str] = None,
        notes: str = "",
    ) -> StudyLog:
        """Record completed study hours in the ledger."""
        if not subject or not subject.strip():
            raise ValueError("Discipline/Subject cannot be blank.")
        if hours <= 0:
            raise ValueError("Study hours must be greater than zero.")

        session_date = parse_academic_date(date_input)
        log = StudyLog(
            subject=subject.strip(),
            topic=topic.strip() or "General Study",
            hours_spent=round(float(hours), 2),
            session_date=session_date,
            notes=notes.strip(),
        )
        log_id = self.storage.add_study_log(log)
        log.id = log_id
        return log

    # -------------------------------------------------------------------------
    # Milestone Operations
    # -------------------------------------------------------------------------

    def add_milestone(
        self,
        title: str,
        subject: str,
        target_date_input: str,
        description: str = "",
    ) -> Milestone:
        """Record a major scholar milestone or syllabus exam."""
        if not title or not title.strip():
            raise ValueError("Milestone title cannot be empty.")
        if not subject or not subject.strip():
            raise ValueError("Subject cannot be empty.")

        target_date = parse_academic_date(target_date_input)
        milestone = Milestone(
            title=title.strip(),
            subject=subject.strip(),
            target_date=target_date,
            description=description.strip(),
        )
        m_id = self.storage.add_milestone(milestone)
        milestone.id = m_id
        return milestone

    def mark_milestone_achieved(self, milestone_id: int) -> bool:
        """Mark a milestone as reached."""
        return self.storage.mark_milestone_achieved(milestone_id)

    # -------------------------------------------------------------------------
    # Views & Agendas
    # -------------------------------------------------------------------------

    def get_daily_view(self, target_date_input: Optional[str] = None) -> Dict[str, Any]:
        """
        Produce a comprehensive ledger view for a single day:
        - Target date info
        - Tasks due on that day
        - Study sessions recorded on that day
        - Daily summary metrics
        """
        date_str = parse_academic_date(target_date_input)
        target_dt = datetime.strptime(date_str, "%Y-%m-%d").date()

        tasks_due = self.storage.list_tasks(start_date=date_str, end_date=date_str)
        logs_today = self.storage.list_study_logs(start_date=date_str, end_date=date_str)
        daily_summary = self.storage.get_daily_summary(target_dt)

        return {
            "date": target_dt,
            "date_str": date_str,
            "tasks_due": tasks_due,
            "study_logs": logs_today,
            "summary": daily_summary,
        }

    def get_weekly_view(self, ref_date_input: Optional[str] = None) -> Dict[str, Any]:
        """
        Produce a weekly academic ledger view:
        - Week start (Monday) to week end (Sunday)
        - Day-by-day mapping with tasks due and study hours logged
        - Cumulative weekly hours and breakdown per subject
        """
        date_str = parse_academic_date(ref_date_input)
        ref_dt = datetime.strptime(date_str, "%Y-%m-%d").date()

        # Monday start
        monday = ref_dt - timedelta(days=ref_dt.weekday())
        sunday = monday + timedelta(days=6)

        week_start_str = monday.isoformat()
        week_end_str = sunday.isoformat()

        tasks_this_week = self.storage.list_tasks(
            start_date=week_start_str, end_date=week_end_str
        )
        logs_this_week = self.storage.list_study_logs(
            start_date=week_start_str, end_date=week_end_str, limit=500
        )

        # Build day-by-day map
        days_data = []
        total_hours = 0.0

        for offset in range(7):
            current_day = monday + timedelta(days=offset)
            current_day_str = current_day.isoformat()

            day_tasks = [t for t in tasks_this_week if t.deadline == current_day_str]
            day_logs = [l for l in logs_this_week if l.session_date == current_day_str]
            day_hours = sum(l.hours_spent for l in day_logs)
            total_hours += day_hours

            days_data.append(
                {
                    "date": current_day,
                    "date_str": current_day_str,
                    "day_name": current_day.strftime("%A"),
                    "tasks": day_tasks,
                    "logs": day_logs,
                    "hours": round(day_hours, 2),
                    "is_today": current_day == date.today(),
                }
            )

        # Subject totals this week
        subject_breakdown: Dict[str, float] = {}
        for l in logs_this_week:
            subject_breakdown[l.subject] = (
                subject_breakdown.get(l.subject, 0.0) + l.hours_spent
            )

        return {
            "monday": monday,
            "sunday": sunday,
            "week_str": f"{monday.strftime('%b %d, %Y')} – {sunday.strftime('%b %d, %Y')}",
            "days": days_data,
            "total_hours": round(total_hours, 2),
            "subject_breakdown": subject_breakdown,
            "total_tasks_due": len(tasks_this_week),
        }

    def get_scholar_stats(self) -> ScholarStats:
        """Fetch global analytics and progress stats."""
        return self.storage.get_scholar_stats()
