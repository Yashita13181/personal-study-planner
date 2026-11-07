"""
models.py - Domain models and data structures for Personal Study Planner.
Classic Academic Ledger Architecture.
"""

from __future__ import annotations
from dataclasses import dataclass, field, asdict
from datetime import date, datetime
from enum import Enum
from typing import Optional, Dict, Any, List


class Priority(str, Enum):
    """Priority levels for academic tasks and topics."""
    HIGH = "High"
    MEDIUM = "Medium"
    LOW = "Low"

    @classmethod
    def from_string(cls, value: str) -> "Priority":
        """Parse case-insensitive input string into a Priority enum."""
        cleaned = value.strip().capitalize()
        for p in cls:
            if p.value == cleaned or p.name.lower() == value.strip().lower() or (len(value) == 1 and p.name.startswith(value.strip().upper())):
                return p
        raise ValueError(f"Invalid priority '{value}'. Expected High (H), Medium (M), or Low (L).")

    @property
    def badge_color(self) -> str:
        """Rich style color for the priority badge."""
        if self == Priority.HIGH:
            return "bold #C85A5A"  # Academic crimson
        if self == Priority.MEDIUM:
            return "#D4AF37"       # Antique amber
        return "#7E9F76"           # Scholar sage

    @property
    def symbol(self) -> str:
        """Academic glyph for priority."""
        if self == Priority.HIGH:
            return "▲"
        if self == Priority.MEDIUM:
            return "■"
        return "▽"

    @property
    def weight(self) -> int:
        """Numeric weight for sorting."""
        if self == Priority.HIGH:
            return 3
        if self == Priority.MEDIUM:
            return 2
        return 1


class Status(str, Enum):
    """Lifecycle status for academic tasks and reading assignments."""
    PENDING = "Pending"
    IN_PROGRESS = "In Progress"
    COMPLETED = "Completed"
    CANCELLED = "Cancelled"

    @classmethod
    def from_string(cls, value: str) -> "Status":
        """Parse case-insensitive string into a Status enum."""
        cleaned = value.strip().lower()
        if cleaned in ("p", "pend", "pending"):
            return cls.PENDING
        if cleaned in ("ip", "in progress", "prog", "in-progress", "progress"):
            return cls.IN_PROGRESS
        if cleaned in ("c", "done", "complete", "completed"):
            return cls.COMPLETED
        if cleaned in ("x", "cancel", "cancelled", "canceled"):
            return cls.CANCELLED
        for s in cls:
            if s.value.lower() == cleaned:
                return s
        raise ValueError(f"Invalid status '{value}'. Expected Pending, In Progress, Completed, or Cancelled.")

    @property
    def badge_color(self) -> str:
        """Rich style color for status."""
        if self == Status.COMPLETED:
            return "bold #5B8A62"  # Laurel green
        if self == Status.IN_PROGRESS:
            return "bold #6B8EAE"  # Antique azure
        if self == Status.PENDING:
            return "#D49B4B"       # Warm ochre
        return "#8C7B64"           # Faded iron

    @property
    def symbol(self) -> str:
        """Academic glyph for status."""
        if self == Status.COMPLETED:
            return "✓"
        if self == Status.IN_PROGRESS:
            return "◐"
        if self == Status.PENDING:
            return "○"
        return "✕"


@dataclass
class Subject:
    """Represents an academic discipline or subject of study."""
    id: Optional[int] = None
    name: str = ""
    target_weekly_hours: float = 5.0
    color_theme: str = "#D4AF37"
    description: str = ""
    created_at: str = field(default_factory=lambda: datetime.now().isoformat())

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "Subject":
        return cls(**data)


@dataclass
class Task:
    """Represents a scheduled study session, reading topic, assignment, or deadline."""
    id: Optional[int] = None
    subject: str = ""
    topic: str = ""
    deadline: str = ""  # Format: YYYY-MM-DD
    priority: Priority = Priority.MEDIUM
    status: Status = Status.PENDING
    estimated_hours: float = 1.0
    notes: str = ""
    created_at: str = field(default_factory=lambda: datetime.now().isoformat())
    completed_at: Optional[str] = None

    def mark_completed(self) -> None:
        """Mark task as completed with current timestamp."""
        self.status = Status.COMPLETED
        self.completed_at = datetime.now().isoformat()

    @property
    def is_overdue(self) -> bool:
        """Determine if task is past its deadline and not completed."""
        if self.status in (Status.COMPLETED, Status.CANCELLED):
            return False
        if not self.deadline:
            return False
        try:
            deadline_date = datetime.strptime(self.deadline, "%Y-%m-%d").date()
            return deadline_date < date.today()
        except ValueError:
            return False

    @property
    def is_due_today(self) -> bool:
        """Check if deadline is today."""
        if not self.deadline:
            return False
        try:
            return datetime.strptime(self.deadline, "%Y-%m-%d").date() == date.today()
        except ValueError:
            return False

    def to_dict(self) -> Dict[str, Any]:
        d = asdict(self)
        d["priority"] = self.priority.value
        d["status"] = self.status.value
        return d

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "Task":
        clean = dict(data)
        if isinstance(clean.get("priority"), str):
            clean["priority"] = Priority.from_string(clean["priority"])
        if isinstance(clean.get("status"), str):
            clean["status"] = Status.from_string(clean["status"])
        return cls(**clean)


@dataclass
class StudyLog:
    """Represents a record of completed study hours for a specific session."""
    id: Optional[int] = None
    subject: str = ""
    topic: str = ""
    hours_spent: float = 0.0
    session_date: str = field(default_factory=lambda: date.today().isoformat())
    notes: str = ""
    created_at: str = field(default_factory=lambda: datetime.now().isoformat())

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "StudyLog":
        return cls(**data)


@dataclass
class Milestone:
    """Represents an academic achievement, exam date, or syllabus milestone."""
    id: Optional[int] = None
    title: str = ""
    subject: str = ""
    target_date: str = ""  # Format: YYYY-MM-DD
    achieved: bool = False
    achieved_at: Optional[str] = None
    description: str = ""
    created_at: str = field(default_factory=lambda: datetime.now().isoformat())

    def mark_achieved(self) -> None:
        """Mark milestone as achieved with current timestamp."""
        self.achieved = True
        self.achieved_at = datetime.now().isoformat()

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "Milestone":
        return cls(**data)


@dataclass
class SubjectProgress:
    """Consolidated progress metrics for an individual academic subject."""
    subject: str
    total_tasks: int = 0
    completed_tasks: int = 0
    task_completion_pct: float = 0.0
    weekly_hours_logged: float = 0.0
    weekly_target_hours: float = 0.0
    weekly_hours_pct: float = 0.0
    lifetime_hours: float = 0.0


@dataclass
class DailySummary:
    """Summary of scholarship activity for a single calendar day."""
    date_str: str
    total_hours: float = 0.0
    sessions_count: int = 0
    tasks_completed: int = 0
    tasks_due: int = 0
    subject_hours: Dict[str, float] = field(default_factory=dict)
    notes_list: List[str] = field(default_factory=list)


@dataclass
class ScholarStats:
    """Global scholarship analytics across all disciplines."""
    current_streak: int = 0
    longest_streak: int = 0
    total_lifetime_hours: float = 0.0
    total_tasks_completed: int = 0
    total_tasks_pending: int = 0
    milestones_achieved: int = 0
    milestones_total: int = 0
    today_hours: float = 0.0
    this_week_hours: float = 0.0
    subjects_count: int = 0
    subject_breakdowns: List[SubjectProgress] = field(default_factory=list)
