"""
ui.py - Terminal User Interface for Personal Study Planner.
Classic Academic Ledger Style rendered via the 'rich' library.
"""

from __future__ import annotations
import math
import sys
import time
from datetime import date, datetime
from typing import List, Optional, Dict, Any, Tuple

from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich.text import Text
from rich.prompt import Prompt, Confirm, FloatPrompt, IntPrompt
from rich.progress import (
    Progress,
    BarColumn,
    TextColumn,
    TimeRemainingColumn,
    SpinnerColumn,
)
from rich.rule import Rule
from rich.columns import Columns
from rich.align import Align
from rich import box

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


# Academic Ledger Color Palette
PALETTE = {
    "parchment": "#F4EDE2",
    "parchment_dim": "#C8BFA8",
    "gold": "#D4AF37",
    "amber": "#E6C280",
    "crimson": "#C85A5A",
    "azure": "#6B8EAE",
    "sage": "#7E9F76",
    "charcoal": "#262421",
    "ink": "#1A1917",
    "border": "#8C7B64",
}

console = Console()


class ScholarLedgerUI:
    """Renders the classic academic ledger UI components and menus."""

    def __init__(self, console_instance: Optional[Console] = None):
        self.console = console_instance or console

    # -------------------------------------------------------------------------
    # Banners and Mottos
    # -------------------------------------------------------------------------

    def display_banner(self) -> None:
        """Display the scholar's journal header banner."""
        banner_text = Text()
        banner_text.append("╔════════════════════════════════════════════════════════════════════════════════╗\n", style=f"bold {PALETTE['gold']}")
        banner_text.append("║                   ✦  THE SCHOLAR'S ACADEMIC LEDGER  ✦                         ║\n", style=f"bold {PALETTE['parchment']}")
        banner_text.append("║             Personal Study Planner & Progress Analytics Journal                ║\n", style=f"italic {PALETTE['amber']}")
        banner_text.append("║                    « Nulla dies sine linea — Pliny the Elder »                 ║\n", style=f"dim {PALETTE['parchment_dim']}")
        banner_text.append("╚════════════════════════════════════════════════════════════════════════════════╝", style=f"bold {PALETTE['gold']}")

        self.console.print(Align.center(banner_text))
        self.console.print()

    def print_section_rule(self, title: str) -> None:
        """Draw an academic separator rule with gold embellishment."""
        self.console.print(
            Rule(
                f"[bold {PALETTE['gold']}]✦ {title.upper()} ✦[/]",
                characters="─",
                style=PALETTE["border"],
            )
        )
        self.console.print()

    # -------------------------------------------------------------------------
    # Task Ledger Table
    # -------------------------------------------------------------------------

    def render_tasks_table(self, tasks: List[Task], title: str = "Active Academic Ledger") -> None:
        """Render a formatted, bookkeeper-style table of study tasks."""
        if not tasks:
            empty_panel = Panel(
                Align.center(
                    f"[italic {PALETTE['parchment_dim']}]No assignments or study sessions recorded under this query.\n"
                    f"Press [bold {PALETTE['gold']}][1][/] in the main menu to inscribe a new study session.[/]"
                ),
                title=f"[bold {PALETTE['gold']}]✦ {title} ✦[/]",
                border_style=PALETTE["border"],
                box=box.ROUNDED,
                padding=(1, 2),
            )
            self.console.print(empty_panel)
            return

        table = Table(
            title=f"[bold {PALETTE['gold']}]✦ {title} ✦[/]",
            box=box.HEAVY_EDGE,
            header_style=f"bold {PALETTE['parchment']} on #2B2824",
            border_style=PALETTE["border"],
            title_style=f"bold {PALETTE['gold']}",
            expand=True,
            show_lines=True,
        )

        table.add_column("Ref #", justify="center", style=f"bold {PALETTE['gold']}", width=6)
        table.add_column("Discipline", style=f"bold {PALETTE['azure']}", min_width=16, ratio=2)
        table.add_column("Topic / Assignment", style=PALETTE["parchment"], min_width=24, ratio=4)
        table.add_column("Deadline", justify="center", width=12)
        table.add_column("Priority", justify="center", width=11)
        table.add_column("Status", justify="center", width=14)
        table.add_column("Est. Hrs", justify="right", width=9, style=PALETTE["amber"])

        today = date.today()

        for t in tasks:
            # Format deadline with indicators
            deadline_display = t.deadline
            if t.is_overdue:
                deadline_display = f"[bold {PALETTE['crimson']}]{t.deadline} ⚠[/]"
            elif t.is_due_today:
                deadline_display = f"[bold {PALETTE['gold']}]{t.deadline} ★[/]"
            else:
                deadline_display = f"[{PALETTE['parchment_dim']}]{t.deadline}[/]"

            # Format priority badge
            p_badge = f"[{t.priority.badge_color}]{t.priority.symbol} {t.priority.value}[/]"

            # Format status badge
            s_badge = f"[{t.status.badge_color}]{t.status.symbol} {t.status.value}[/]"

            # Topic title with optional notes annotation
            topic_text = Text()
            if t.status == Status.COMPLETED:
                topic_text.append(t.topic, style="strike dim")
            else:
                topic_text.append(t.topic, style=PALETTE["parchment"])

            if t.notes:
                topic_text.append(f"\n↳ {t.notes}", style=f"italic dim {PALETTE['parchment_dim']}")

            table.add_row(
                str(t.id),
                t.subject,
                topic_text,
                deadline_display,
                p_badge,
                s_badge,
                f"{t.estimated_hours:.1f}h",
            )

        self.console.print(table)
        self.console.print(
            f"[dim italic {PALETTE['parchment_dim']}]Total recorded entries: {len(tasks)} | "
            f"Symbols: ★ Due Today | ⚠ Overdue | ✓ Completed | ◐ In Progress | ○ Pending[/]\n"
        )

    # -------------------------------------------------------------------------
    # Daily View
    # -------------------------------------------------------------------------

    def render_daily_view(self, daily_data: Dict[str, Any]) -> None:
        """Render scholarly journal for a specific single day."""
        dt: date = daily_data["date"]
        date_str = dt.strftime("%A, %B %d, %Y")
        summary: DailySummary = daily_data["summary"]
        tasks_due: List[Task] = daily_data["tasks_due"]
        study_logs: List[StudyLog] = daily_data["study_logs"]

        # Header card
        header_content = (
            f"[bold {PALETTE['gold']}]Date:[/] {date_str}   "
            f"[bold {PALETTE['gold']}]| Total Study Hours Logged:[/] [bold {PALETTE['sage']}]{summary.total_hours:.2f}h[/]   "
            f"[bold {PALETTE['gold']}]| Sessions:[/] {summary.sessions_count}   "
            f"[bold {PALETTE['gold']}]| Tasks Due:[/] {summary.tasks_due}"
        )
        self.console.print(
            Panel(
                Align.center(header_content),
                title=f"[bold {PALETTE['gold']}]✦ DAILY ACADEMIC JOURNAL ✦[/]",
                border_style=PALETTE["border"],
                box=box.ROUNDED,
            )
        )

        # 1. Tasks Due on this day
        if tasks_due:
            self.console.print(f"[bold {PALETTE['amber']}]◆ Assignments & Deadlines for {dt.strftime('%b %d')}:[/]")
            self.render_tasks_table(tasks_due, title=f"Tasks Due: {dt.strftime('%b %d, %Y')}")
        else:
            self.console.print(
                f"[dim italic {PALETTE['parchment_dim']}]No specific task deadlines fall on this calendar date.[/]\n"
            )

        # 2. Study Sessions Logged for this day
        if study_logs:
            log_table = Table(
                title=f"[bold {PALETTE['gold']}]✦ Study Sessions Logged on {dt.strftime('%b %d')} ✦[/]",
                box=box.SIMPLE_HEAVY,
                header_style=f"bold {PALETTE['parchment']}",
                border_style=PALETTE["border"],
                expand=True,
            )
            log_table.add_column("Ref #", justify="center", width=6, style=PALETTE["gold"])
            log_table.add_column("Discipline", style=PALETTE["azure"], width=22)
            log_table.add_column("Topic / Focus", style=PALETTE["parchment"])
            log_table.add_column("Hours Spent", justify="right", width=12, style=f"bold {PALETTE['sage']}")
            log_table.add_column("Reflections / Notes", style=f"italic {PALETTE['parchment_dim']}")

            for log in study_logs:
                log_table.add_row(
                    str(log.id),
                    log.subject,
                    log.topic,
                    f"{log.hours_spent:.2f}h",
                    log.notes or "—",
                )
            self.console.print(log_table)
        else:
            self.console.print(
                f"[dim italic {PALETTE['parchment_dim']}]No study hours logged for this date yet. Use option [2] to record study time.[/]\n"
            )

        # Subject breakdown pill
        if summary.subject_hours:
            breakdown_str = "  |  ".join(
                f"[bold {PALETTE['azure']}]{subj}:[/] [{PALETTE['parchment']}]{h:.2f}h[/]"
                for subj, h in summary.subject_hours.items()
            )
            self.console.print(
                Panel(
                    f"[bold {PALETTE['gold']}]Discipline Distribution:[/] {breakdown_str}",
                    border_style=PALETTE["border"],
                    box=box.SQUARE,
                )
            )
        self.console.print()

    # -------------------------------------------------------------------------
    # Weekly View
    # -------------------------------------------------------------------------

    def render_weekly_view(self, weekly_data: Dict[str, Any]) -> None:
        """Render an organized Monday-to-Sunday weekly schedule grid."""
        week_str = weekly_data["week_str"]
        total_hours = weekly_data["total_hours"]
        days = weekly_data["days"]
        subject_breakdown = weekly_data["subject_breakdown"]

        self.console.print(
            Panel(
                Align.center(
                    f"[bold {PALETTE['gold']}]Academic Week:[/] {week_str}\n"
                    f"[bold {PALETTE['gold']}]Total Study Volume:[/] [bold {PALETTE['sage']}]{total_hours:.2f} hours[/] "
                    f"across {len(subject_breakdown)} disciplines"
                ),
                title=f"[bold {PALETTE['gold']}]✦ WEEKLY CURRICULUM & SCHEDULE ✦[/]",
                border_style=PALETTE["border"],
                box=box.ROUNDED,
            )
        )

        weekly_table = Table(
            box=box.HEAVY_EDGE,
            header_style=f"bold {PALETTE['parchment']} on #2B2824",
            border_style=PALETTE["border"],
            expand=True,
            show_lines=True,
        )

        weekly_table.add_column("Day", width=14, style=f"bold {PALETTE['gold']}")
        weekly_table.add_column("Date", justify="center", width=12, style=PALETTE["parchment_dim"])
        weekly_table.add_column("Study Hours", justify="center", width=14, style=f"bold {PALETTE['sage']}")
        weekly_table.add_column("Deadlines & Scheduled Topics", style=PALETTE["parchment"], ratio=5)

        for d in days:
            day_label = d["day_name"]
            if d["is_today"]:
                day_label = f"★ {day_label} (Today)"

            # Tasks text
            topics_text = Text()
            if d["tasks"]:
                for idx, t in enumerate(d["tasks"]):
                    status_icon = "✓" if t.status == Status.COMPLETED else "○"
                    priority_glyph = t.priority.symbol
                    topics_text.append(f"{status_icon} [{t.subject}] {t.topic} ({priority_glyph})\n")
            else:
                topics_text.append("— No due dates —", style="dim")

            hours_str = f"{d['hours']:.1f}h" if d["hours"] > 0 else "0.0h"
            if d["hours"] > 0:
                hours_str = f"[{PALETTE['sage']}]{hours_str}[/]"
            else:
                hours_str = f"[dim {PALETTE['parchment_dim']}]{hours_str}[/]"

            weekly_table.add_row(
                day_label,
                d["date_str"],
                hours_str,
                topics_text,
            )

        self.console.print(weekly_table)

        # Subject breakdown panel
        if subject_breakdown:
            pills = []
            for subj, hrs in subject_breakdown.items():
                pills.append(f"[bold {PALETTE['azure']}]{subj}:[/] [bold {PALETTE['parchment']}]{hrs:.1f}h[/]")
            self.console.print(
                Panel(
                    "   ✦   ".join(pills),
                    title=f"[bold {PALETTE['gold']}]Weekly Discipline Totals[/]",
                    border_style=PALETTE["border"],
                    box=box.ROUNDED,
                )
            )
        self.console.print()

    # -------------------------------------------------------------------------
    # Progress & Analytics Dashboard
    # -------------------------------------------------------------------------

    def render_progress_dashboard(self, stats: ScholarStats) -> None:
        """
        Render visual progress bars, streak ribbon, completion rates,
        and scholarly milestones.
        """
        # 1. Streak & Scholarly Honours Banner
        flame = "🔥" if stats.current_streak > 0 else "❄️"
        streak_banner = (
            f"[bold {PALETTE['gold']}]SCHOLAR'S STREAK:[/] {flame} [bold {PALETTE['parchment']}]{stats.current_streak} Consecutive Days[/]   "
            f"[dim]|[/]   [bold {PALETTE['gold']}]Record Streak:[/] [{PALETTE['amber']}]{stats.longest_streak} Days[/]   "
            f"[dim]|[/]   [bold {PALETTE['gold']}]Lifetime Study:[/] [bold {PALETTE['sage']}]{stats.total_lifetime_hours:.1f} Hours[/]   "
            f"[dim]|[/]   [bold {PALETTE['gold']}]Today:[/] [{PALETTE['parchment']}]{stats.today_hours:.1f}h[/]   "
            f"[dim]|[/]   [bold {PALETTE['gold']}]This Week:[/] [{PALETTE['parchment']}]{stats.this_week_hours:.1f}h[/]"
        )
        self.console.print(
            Panel(
                Align.center(streak_banner),
                title=f"[bold {PALETTE['gold']}]✦ SCHOLARSHIP STATS & STREAK COUNTER ✦[/]",
                border_style=PALETTE["gold"],
                box=box.DOUBLE,
                padding=(1, 2),
            )
        )

        # 2. Overall Task Completion Metrics
        total_tasks = stats.total_tasks_completed + stats.total_tasks_pending
        task_completion_pct = (stats.total_tasks_completed / total_tasks * 100.0) if total_tasks > 0 else 0.0

        overall_metrics = Table(box=box.SIMPLE, show_header=False, expand=True)
        overall_metrics.add_column("Metric", style=f"bold {PALETTE['gold']}")
        overall_metrics.add_column("Value", style=PALETTE["parchment"])
        overall_metrics.add_column("Progress Bar", ratio=2)

        bar_overall = self._render_mini_bar(task_completion_pct, 100.0, color="#5B8A62")
        overall_metrics.add_row(
            "Overall Task Completion",
            f"{stats.total_tasks_completed} / {total_tasks} completed ({task_completion_pct:.1f}%)",
            bar_overall,
        )

        self.console.print(
            Panel(
                overall_metrics,
                title=f"[bold {PALETTE['gold']}]✦ Global Syllabus Completion ✦[/]",
                border_style=PALETTE["border"],
                box=box.ROUNDED,
            )
        )

        # 3. Subject-by-Subject Progress Ledger Table
        if stats.subject_breakdowns:
            subj_table = Table(
                title=f"[bold {PALETTE['gold']}]✦ Discipline Progress & Weekly Targets ✦[/]",
                box=box.HEAVY_EDGE,
                header_style=f"bold {PALETTE['parchment']} on #2B2824",
                border_style=PALETTE["border"],
                expand=True,
                show_lines=True,
            )
            subj_table.add_column("Academic Discipline", style=f"bold {PALETTE['azure']}", width=22)
            subj_table.add_column("Tasks Completed", justify="center", width=16)
            subj_table.add_column("Syllabus Rate", width=22)
            subj_table.add_column("Week Hours", justify="center", width=14, style=f"bold {PALETTE['sage']}")
            subj_table.add_column("Target Goal", justify="center", width=12, style=PALETTE["amber"])
            subj_table.add_column("Weekly Target Bar", width=22)
            subj_table.add_column("Total Hours", justify="right", width=12, style=PALETTE["parchment"])

            for s in stats.subject_breakdowns:
                task_ratio_str = f"{s.completed_tasks}/{s.total_tasks} ({s.task_completion_pct:.0f}%)"
                task_bar = self._render_mini_bar(s.task_completion_pct, 100.0, color="#7E9F76")

                weekly_hours_str = f"{s.weekly_hours_logged:.1f}h"
                weekly_target_str = f"{s.weekly_target_hours:.1f}h"
                hours_bar = self._render_mini_bar(s.weekly_hours_logged, s.weekly_target_hours, color="#D4AF37")

                subj_table.add_row(
                    s.subject,
                    task_ratio_str,
                    task_bar,
                    weekly_hours_str,
                    weekly_target_str,
                    hours_bar,
                    f"{s.lifetime_hours:.1f}h",
                )

            self.console.print(subj_table)
        else:
            self.console.print(
                f"[italic dim {PALETTE['parchment_dim']}]No subjects registered yet. Add tasks or subjects to begin tracking progress.[/]\n"
            )

        self.console.print()

    def _render_mini_bar(self, current: float, target: float, width: int = 15, color: str = "#D4AF37") -> str:
        """Generate a compact Unicode text progress bar."""
        if target <= 0:
            target = 1.0
        pct = min(max(current / target, 0.0), 1.0)
        filled = int(round(pct * width))
        empty = width - filled
        bar = "█" * filled + "░" * empty
        pct_num = (current / target * 100.0)
        return f"[{color}]{bar}[/] [dim {PALETTE['parchment_dim']}]{pct_num:3.0f}%[/]"

    # -------------------------------------------------------------------------
    # Milestones View
    # -------------------------------------------------------------------------

    def render_milestones_table(self, milestones: List[Milestone]) -> None:
        """Render academic milestones and exam laurels."""
        if not milestones:
            self.console.print(
                Panel(
                    Align.center(f"[italic {PALETTE['parchment_dim']}]No major academic milestones inscribed yet.[/]"),
                    title=f"[bold {PALETTE['gold']}]✦ Academic Laurels & Milestones ✦[/]",
                    border_style=PALETTE["border"],
                    box=box.ROUNDED,
                )
            )
            return

        table = Table(
            title=f"[bold {PALETTE['gold']}]✦ Academic Laurels & Milestones ✦[/]",
            box=box.HEAVY_EDGE,
            header_style=f"bold {PALETTE['parchment']} on #2B2824",
            border_style=PALETTE["border"],
            expand=True,
            show_lines=True,
        )
        table.add_column("Ref #", justify="center", width=6, style=PALETTE["gold"])
        table.add_column("Milestone / Scholarly Laurels", style=PALETTE["parchment"], ratio=4)
        table.add_column("Discipline", style=PALETTE["azure"], width=20)
        table.add_column("Target Date", justify="center", width=13)
        table.add_column("Status", justify="center", width=14)
        table.add_column("Description", style=f"italic {PALETTE['parchment_dim']}", ratio=3)

        for m in milestones:
            status_badge = (
                f"[bold {PALETTE['sage']}]🏆 Achieved[/]"
                if m.achieved
                else f"[{PALETTE['amber']}]⏳ Pending[/]"
            )
            title_text = m.title
            if m.achieved:
                title_text = f"[strike dim]{m.title}[/]"

            table.add_row(
                str(m.id),
                title_text,
                m.subject,
                m.target_date,
                status_badge,
                m.description or "—",
            )

        self.console.print(table)
        self.console.print()

    # -------------------------------------------------------------------------
    # Focus Hourglass / Timer
    # -------------------------------------------------------------------------

    def run_focus_hourglass(self, minutes: float = 25.0) -> Tuple[bool, float]:
        """
        Interactive scholar's focus hourglass countdown with live updates.
        Returns (completed_bool, minutes_elapsed).
        """
        total_seconds = int(minutes * 60)
        if total_seconds <= 0:
            total_seconds = 60

        self.console.print(
            Panel(
                Align.center(
                    f"[bold {PALETTE['gold']}]⏳ THE SCHOLAR'S FOCUS HOURGLASS ⏳[/]\n"
                    f"[italic {PALETTE['parchment']}]Duration: {minutes:.1f} minutes ({total_seconds} seconds)[/]\n"
                    f"[dim {PALETTE['parchment_dim']}]Enter a state of deep scholarly immersion. Press Ctrl+C at any time to pause or log partial time.[/]"
                ),
                border_style=PALETTE["gold"],
                box=box.DOUBLE,
                padding=(1, 2),
            )
        )

        completed = False
        start_time = time.time()
        elapsed_seconds = 0

        try:
            with Progress(
                SpinnerColumn(spinner_name="dots"),
                TextColumn("[bold #D4AF37]{task.description}"),
                BarColumn(complete_style="#D4AF37", finished_style="#5B8A62"),
                TextColumn("[bold #F4EDE2]{task.percentage:>3.0f}%"),
                TimeRemainingColumn(),
                console=self.console,
            ) as progress:
                timer_task = progress.add_task("Studying in silence...", total=total_seconds)

                while not progress.finished:
                    time.sleep(1)
                    elapsed_seconds = int(time.time() - start_time)
                    progress.update(timer_task, completed=min(elapsed_seconds, total_seconds))
                    if elapsed_seconds >= total_seconds:
                        completed = True
                        break

            self.console.print(
                Panel(
                    Align.center(
                        f"[bold {PALETTE['sage']}]✦ FOCUS SESSION CONCLUDED ✦[/]\n"
                        f"[italic {PALETTE['parchment']}]\"Labor omnia vincit\" — Work conquers all.[/]\n"
                        f"You devoted {minutes:.1f} uninterrupted minutes of scholarship."
                    ),
                    border_style=PALETTE["sage"],
                    box=box.ROUNDED,
                )
            )

        except KeyboardInterrupt:
            elapsed_seconds = int(time.time() - start_time)
            mins_elapsed = round(elapsed_seconds / 60.0, 2)
            self.console.print(
                f"\n[bold {PALETTE['amber']}]Hourglass paused early after {mins_elapsed:.1f} minutes.[/]"
            )
            return False, mins_elapsed

        return True, round(elapsed_seconds / 60.0, 2)

    # -------------------------------------------------------------------------
    # Prompts & Menus
    # -------------------------------------------------------------------------

    def prompt_menu_choice(self) -> str:
        """Display the main academic ledger menu and prompt for action."""
        menu_text = Text()
        menu_text.append(" [1] ", style=f"bold {PALETTE['gold']}")
        menu_text.append("Inscribe Task / Assignment   ", style=PALETTE["parchment"])
        menu_text.append(" [2] ", style=f"bold {PALETTE['gold']}")
        menu_text.append("Log Study Hours Session     ", style=PALETTE["parchment"])
        menu_text.append(" [3] ", style=f"bold {PALETTE['gold']}")
        menu_text.append("View Active Ledger (Tasks)\n", style=PALETTE["parchment"])

        menu_text.append(" [4] ", style=f"bold {PALETTE['gold']}")
        menu_text.append("Daily Journal View           ", style=PALETTE["parchment"])
        menu_text.append(" [5] ", style=f"bold {PALETTE['gold']}")
        menu_text.append("Weekly Curriculum Schedule  ", style=PALETTE["parchment"])
        menu_text.append(" [6] ", style=f"bold {PALETTE['gold']}")
        menu_text.append("Progress & Streak Analytics\n", style=PALETTE["parchment"])

        menu_text.append(" [7] ", style=f"bold {PALETTE['gold']}")
        menu_text.append("Modify / Complete Task       ", style=PALETTE["parchment"])
        menu_text.append(" [8] ", style=f"bold {PALETTE['gold']}")
        menu_text.append("Academic Laurels (Milestones)", style=PALETTE["parchment"])
        menu_text.append(" [9] ", style=f"bold {PALETTE['gold']}")
        menu_text.append("Focus Hourglass (Timer)\n", style=PALETTE["parchment"])

        menu_text.append(" [B] ", style=f"bold {PALETTE['gold']}")
        menu_text.append("Data Backup & JSON Export    ", style=PALETTE["parchment"])
        menu_text.append(" [S] ", style=f"bold {PALETTE['gold']}")
        menu_text.append("Seed Sample Curriculum       ", style=PALETTE["parchment"])
        menu_text.append(" [0/Q] ", style=f"bold {PALETTE['crimson']}")
        menu_text.append("Close Journal (Exit)\n", style=f"dim {PALETTE['parchment_dim']}")

        menu_panel = Panel(
            menu_text,
            title=f"[bold {PALETTE['gold']}]✦ SCHOLAR'S DESK DIRECTORY ✦[/]",
            border_style=PALETTE["border"],
            box=box.ROUNDED,
            padding=(0, 2),
        )
        self.console.print(menu_panel)

        choice = Prompt.ask(
            f"[bold {PALETTE['gold']}]Enter Ledger Action[/]",
            default="3",
            show_default=True,
        )
        return choice.strip().upper()

    def print_success(self, message: str) -> None:
        """Print a success confirmation."""
        self.console.print(f"[bold {PALETTE['sage']}]✓ {message}[/]\n")

    def print_warning(self, message: str) -> None:
        """Print a warning message."""
        self.console.print(f"[bold {PALETTE['amber']}]⚠ {message}[/]\n")

    def print_error(self, message: str) -> None:
        """Print an error message."""
        self.console.print(f"[bold {PALETTE['crimson']}]✕ Error:[/] {message}\n")
