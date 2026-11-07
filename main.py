"""
main.py - Entry point and interactive controller for Personal Study Planner.
Provides interactive TUI loop and scriptable CLI command-line options.
"""

from __future__ import annotations
import argparse
import sys
from datetime import date, datetime
from typing import Optional

from rich.prompt import Prompt, Confirm, FloatPrompt, IntPrompt

from models import Priority, Status, Task, StudyLog, Milestone
from storage import StorageManager
from planner import StudyPlannerService, parse_academic_date
from ui import ScholarLedgerUI, PALETTE
from sample_data import populate_seed_data


def handle_inscribe_task(service: StudyPlannerService, ui: ScholarLedgerUI) -> None:
    """Interactive workflow to add a new study task or syllabus deadline."""
    ui.print_section_rule("Inscribe New Academic Task")

    # List existing subjects for convenience
    subjects = service.storage.list_subjects()
    if subjects:
        subj_names = ", ".join([s.name for s in subjects])
        ui.console.print(f"[dim {PALETTE['parchment_dim']}]Existing Disciplines: {subj_names}[/]")

    subject = Prompt.ask(f"[bold {PALETTE['gold']}]Discipline / Subject[/]").strip()
    if not subject:
        ui.print_error("Discipline cannot be blank.")
        return

    topic = Prompt.ask(f"[bold {PALETTE['gold']}]Topic / Assignment Title[/]").strip()
    if not topic:
        ui.print_error("Topic title cannot be blank.")
        return

    deadline_raw = Prompt.ask(
        f"[bold {PALETTE['gold']}]Deadline (e.g., 'today', 'tomorrow', '+3d', 'YYYY-MM-DD')[/]",
        default="today",
    )

    try:
        deadline = parse_academic_date(deadline_raw)
    except ValueError as e:
        ui.print_error(str(e))
        return

    priority_str = Prompt.ask(
        f"[bold {PALETTE['gold']}]Priority [H]igh / [M]edium / [L]ow[/]",
        choices=["H", "M", "L", "High", "Medium", "Low"],
        default="M",
    )
    try:
        priority = Priority.from_string(priority_str)
    except ValueError:
        priority = Priority.MEDIUM

    try:
        est_hours_str = Prompt.ask(f"[bold {PALETTE['gold']}]Estimated Hours[/]", default="1.5")
        est_hours = float(est_hours_str)
    except ValueError:
        est_hours = 1.5

    notes = Prompt.ask(f"[bold {PALETTE['gold']}]Scholarly Notes / Syllabus Ref (Optional)[/]", default="").strip()

    try:
        task = service.create_task(
            subject=subject,
            topic=topic,
            deadline_input=deadline,
            priority=priority,
            estimated_hours=est_hours,
            notes=notes,
        )
        ui.print_success(f"Inscribed Ref #{task.id}: '{task.topic}' due {task.deadline} into the ledger.")
    except Exception as exc:
        ui.print_error(f"Failed to inscribe task: {exc}")


def handle_log_study(service: StudyPlannerService, ui: ScholarLedgerUI) -> None:
    """Interactive workflow to record completed study hours."""
    ui.print_section_rule("Log Completed Study Hours")

    subjects = service.storage.list_subjects()
    if subjects:
        subj_names = ", ".join([s.name for s in subjects])
        ui.console.print(f"[dim {PALETTE['parchment_dim']}]Disciplines: {subj_names}[/]")

    subject = Prompt.ask(f"[bold {PALETTE['gold']}]Discipline Studied[/]").strip()
    if not subject:
        ui.print_error("Discipline cannot be blank.")
        return

    topic = Prompt.ask(f"[bold {PALETTE['gold']}]Topic or Chapter Focused Upon[/]", default="General Study").strip()

    try:
        hours_str = Prompt.ask(f"[bold {PALETTE['gold']}]Hours Spent (e.g., 1.5, 2.0)[/]", default="1.0")
        hours = float(hours_str)
        if hours <= 0:
            ui.print_error("Hours spent must be greater than zero.")
            return
    except ValueError:
        ui.print_error("Invalid numeric hours value.")
        return

    date_raw = Prompt.ask(
        f"[bold {PALETTE['gold']}]Session Date ('today', 'yesterday', 'YYYY-MM-DD')[/]",
        default="today",
    )

    notes = Prompt.ask(f"[bold {PALETTE['gold']}]Reflections / Key Takeaways (Optional)[/]", default="").strip()

    try:
        log = service.log_study_session(
            subject=subject,
            topic=topic,
            hours=hours,
            date_input=date_raw,
            notes=notes,
        )
        current_streak, _ = service.storage.calculate_streaks()
        ui.print_success(
            f"Logged {log.hours_spent:.2f}h for [{log.subject}] on {log.session_date}. "
            f"Current Streak: {current_streak} days! 🔥"
        )
    except Exception as exc:
        ui.print_error(f"Failed to log study hours: {exc}")


def handle_view_tasks(service: StudyPlannerService, ui: ScholarLedgerUI) -> None:
    """Display tasks with optional filters."""
    ui.print_section_rule("Academic Ledger - Task Inscriptions")

    ui.console.print(
        f" [A] All Tasks   [P] Pending Only   [C] Completed Only   [S] Filter by Discipline   [O] Overdue Only"
    )
    filter_choice = Prompt.ask(
        f"[bold {PALETTE['gold']}]Select Filter[/]",
        choices=["A", "P", "C", "S", "O"],
        default="A",
    ).upper()

    tasks = []
    title = "All Recorded Tasks"

    if filter_choice == "A":
        tasks = service.storage.list_tasks()
        title = "Complete Academic Ledger"
    elif filter_choice == "P":
        tasks = service.storage.list_tasks(status=Status.PENDING)
        title = "Pending Syllabus Deadlines"
    elif filter_choice == "C":
        tasks = service.storage.list_tasks(status=Status.COMPLETED)
        title = "Completed Scholarly Milestones"
    elif filter_choice == "S":
        subj_choice = Prompt.ask(f"[bold {PALETTE['gold']}]Enter Discipline Name[/]").strip()
        tasks = service.storage.list_tasks(subject=subj_choice)
        title = f"Discipline: {subj_choice}"
    elif filter_choice == "O":
        all_tasks = service.storage.list_tasks()
        tasks = [t for t in all_tasks if t.is_overdue]
        title = "Overdue Assignments ⚠"

    ui.render_tasks_table(tasks, title=title)


def handle_daily_journal(service: StudyPlannerService, ui: ScholarLedgerUI) -> None:
    """Display daily journal view for today or a chosen date."""
    ui.print_section_rule("Daily Academic Journal")
    date_input = Prompt.ask(
        f"[bold {PALETTE['gold']}]Target Date ('today', 'yesterday', '+1d', 'YYYY-MM-DD')[/]",
        default="today",
    )
    try:
        daily_data = service.get_daily_view(date_input)
        ui.render_daily_view(daily_data)
    except Exception as exc:
        ui.print_error(f"Failed to compile daily journal: {exc}")


def handle_weekly_schedule(service: StudyPlannerService, ui: ScholarLedgerUI) -> None:
    """Display weekly schedule view."""
    ui.print_section_rule("Weekly Curriculum Schedule")
    date_input = Prompt.ask(
        f"[bold {PALETTE['gold']}]Reference Date within Target Week ('today', 'YYYY-MM-DD')[/]",
        default="today",
    )
    try:
        weekly_data = service.get_weekly_view(date_input)
        ui.render_weekly_view(weekly_data)
    except Exception as exc:
        ui.print_error(f"Failed to compile weekly schedule: {exc}")


def handle_progress_analytics(service: StudyPlannerService, ui: ScholarLedgerUI) -> None:
    """Display progress dashboard, subject completion, and streak statistics."""
    ui.print_section_rule("Scholarly Progress & Streak Analytics")
    stats = service.get_scholar_stats()
    ui.render_progress_dashboard(stats)


def handle_modify_task(service: StudyPlannerService, ui: ScholarLedgerUI) -> None:
    """Interactive menu to complete, edit, or delete a task."""
    ui.print_section_rule("Modify or Inscribe Status on Task")

    try:
        task_id_str = Prompt.ask(f"[bold {PALETTE['gold']}]Enter Task Ref #[/]")
        task_id = int(task_id_str.strip())
    except ValueError:
        ui.print_error("Invalid task reference number.")
        return

    task = service.get_task(task_id)
    if not task:
        ui.print_error(f"Task with Ref #{task_id} not found in the ledger.")
        return

    ui.console.print(
        f"\n[bold {PALETTE['gold']}]Selected Task #{task.id}:[/] [{PALETTE['azure']}]{task.subject}[/] — "
        f"[{PALETTE['parchment']}]{task.topic}[/] | Status: [{task.status.badge_color}]{task.status.value}[/] | "
        f"Deadline: {task.deadline}\n"
    )

    action = Prompt.ask(
        f"[bold {PALETTE['gold']}]Action: [C]omplete, [P]end, [I]n Progress, [E]dit details, [D]elete, [B]ack[/]",
        choices=["C", "P", "I", "E", "D", "B"],
        default="C",
    ).upper()

    if action == "C":
        service.update_task_status(task_id, Status.COMPLETED)
        ui.print_success(f"Task #{task_id} marked as COMPLETED! ✓")

        # Prompt to log study hours for this completed task
        if Confirm.ask(f"[bold {PALETTE['gold']}]Inscribe study hours spent on this task now?[/]", default=True):
            try:
                hrs_input = Prompt.ask(f"[bold {PALETTE['gold']}]Hours spent[/]", default=str(task.estimated_hours))
                hours = float(hrs_input)
                service.log_study_session(
                    subject=task.subject,
                    topic=task.topic,
                    hours=hours,
                    notes=f"Completed task #{task.id}",
                )
                ui.print_success(f"Logged {hours:.2f}h towards [{task.subject}].")
            except Exception as e:
                ui.print_error(f"Error logging hours: {e}")

    elif action == "P":
        service.update_task_status(task_id, Status.PENDING)
        ui.print_success(f"Task #{task_id} reset to PENDING.")
    elif action == "I":
        service.update_task_status(task_id, Status.IN_PROGRESS)
        ui.print_success(f"Task #{task_id} marked IN PROGRESS ◐.")
    elif action == "D":
        if Confirm.ask(f"[bold {PALETTE['crimson']}]Confirm permanent deletion of Task #{task_id}?[/]", default=False):
            service.delete_task(task_id)
            ui.print_success(f"Task #{task_id} deleted from ledger.")
        else:
            ui.print_warning("Deletion aborted.")
    elif action == "E":
        new_topic = Prompt.ask(f"[bold {PALETTE['gold']}]New Topic (leave blank to keep current)[/]", default="").strip()
        new_deadline = Prompt.ask(f"[bold {PALETTE['gold']}]New Deadline (leave blank to keep current)[/]", default="").strip()
        new_priority_str = Prompt.ask(
            f"[bold {PALETTE['gold']}]New Priority [H/M/L] (leave blank to keep current)[/]", default=""
        ).strip()
        new_p = None
        if new_priority_str:
            try:
                new_p = Priority.from_string(new_priority_str)
            except ValueError:
                pass

        service.edit_task(
            task_id=task_id,
            topic=new_topic or None,
            deadline=new_deadline or None,
            priority=new_p,
        )
        ui.print_success(f"Task #{task_id} successfully amended.")


def handle_milestones(service: StudyPlannerService, ui: ScholarLedgerUI) -> None:
    """View and manage scholarly laurels and milestones."""
    ui.print_section_rule("Academic Laurels & Milestones")
    milestones = service.storage.list_milestones()
    ui.render_milestones_table(milestones)

    action = Prompt.ask(
        f"[bold {PALETTE['gold']}][A]dd Milestone, [M]ark Achieved, [D]elete Milestone, [B]ack[/]",
        choices=["A", "M", "D", "B"],
        default="B",
    ).upper()

    if action == "A":
        title = Prompt.ask(f"[bold {PALETTE['gold']}]Milestone / Exam Title[/]").strip()
        subject = Prompt.ask(f"[bold {PALETTE['gold']}]Discipline[/]").strip()
        date_raw = Prompt.ask(f"[bold {PALETTE['gold']}]Target Date ('+2w', 'YYYY-MM-DD')[/]", default="+2w")
        desc = Prompt.ask(f"[bold {PALETTE['gold']}]Description / Syllabus Objectives[/]", default="").strip()

        try:
            m = service.add_milestone(title=title, subject=subject, target_date_input=date_raw, description=desc)
            ui.print_success(f"Inscribed Milestone #{m.id}: '{m.title}' target: {m.target_date}.")
        except Exception as e:
            ui.print_error(f"Failed to record milestone: {e}")

    elif action == "M":
        try:
            m_id = int(Prompt.ask(f"[bold {PALETTE['gold']}]Enter Milestone Ref #[/]").strip())
            if service.mark_milestone_achieved(m_id):
                ui.print_success(f"Milestone #{m_id} marked as ACHIEVED! 🏆 Laurels conferred.")
            else:
                ui.print_error(f"Milestone #{m_id} not found.")
        except ValueError:
            ui.print_error("Invalid milestone reference number.")

    elif action == "D":
        try:
            m_id = int(Prompt.ask(f"[bold {PALETTE['gold']}]Enter Milestone Ref # to delete[/]").strip())
            if service.storage.delete_milestone(m_id):
                ui.print_success(f"Milestone #{m_id} removed.")
            else:
                ui.print_error(f"Milestone #{m_id} not found.")
        except ValueError:
            ui.print_error("Invalid milestone reference number.")


def handle_focus_hourglass(service: StudyPlannerService, ui: ScholarLedgerUI, default_mins: float = 25.0) -> None:
    """Run focus hourglass and offer automatic ledger logging."""
    ui.print_section_rule("Scholar's Focus Hourglass")
    try:
        mins_str = Prompt.ask(f"[bold {PALETTE['gold']}]Focus Session Duration (minutes)[/]", default=str(default_mins))
        mins = float(mins_str)
    except ValueError:
        mins = 25.0

    finished, elapsed = ui.run_focus_hourglass(mins)

    if elapsed > 0:
        if Confirm.ask(f"[bold {PALETTE['gold']}]Inscribe this {elapsed:.1f}-minute session into your study ledger?[/]", default=True):
            subjects = service.storage.list_subjects()
            if subjects:
                subj_names = ", ".join([s.name for s in subjects])
                ui.console.print(f"[dim {PALETTE['parchment_dim']}]Disciplines: {subj_names}[/]")

            subject = Prompt.ask(f"[bold {PALETTE['gold']}]Discipline[/]").strip() or "General Study"
            topic = Prompt.ask(f"[bold {PALETTE['gold']}]Topic Focused Upon[/]", default="Deep Focus Session").strip()
            hours = round(elapsed / 60.0, 2)

            service.log_study_session(
                subject=subject,
                topic=topic,
                hours=hours,
                notes=f"Recorded from {elapsed:.1f} min Focus Hourglass session",
            )
            ui.print_success(f"Logged {hours:.2f}h towards [{subject}]!")


def handle_backup_export(service: StudyPlannerService, ui: ScholarLedgerUI) -> None:
    """Export or import data via JSON."""
    ui.print_section_rule("Data Persistence & JSON Interchange")
    ui.console.print(
        f"[bold {PALETTE['gold']}]Database File:[/] [italic {PALETTE['parchment']}]{service.storage.db_path}[/]\n"
        f"[bold {PALETTE['gold']}]JSON Interchange Path:[/] [italic {PALETTE['parchment']}]{service.storage.json_path}[/]\n"
    )

    action = Prompt.ask(
        f"[bold {PALETTE['gold']}][E]xport to JSON, [I]mport from JSON, [B]ack[/]",
        choices=["E", "I", "B"],
        default="E",
    ).upper()

    if action == "E":
        path = Prompt.ask(f"[bold {PALETTE['gold']}]Target JSON file path[/]", default=service.storage.json_path)
        try:
            exported_path = service.storage.export_to_json(path)
            ui.print_success(f"Ledger successfully exported to: {exported_path}")
        except Exception as e:
            ui.print_error(f"Export failed: {e}")

    elif action == "I":
        path = Prompt.ask(f"[bold {PALETTE['gold']}]Source JSON file path[/]", default=service.storage.json_path)
        overwrite = Confirm.ask(f"[bold {PALETTE['crimson']}]Overwrite existing database contents?[/]", default=False)
        try:
            counts = service.storage.import_from_json(path, overwrite=overwrite)
            ui.print_success(
                f"Import complete! Added {counts['subjects']} subjects, {counts['tasks']} tasks, "
                f"{counts['study_logs']} study logs, and {counts['milestones']} milestones."
            )
        except Exception as e:
            ui.print_error(f"Import failed: {e}")


def handle_seed_data(service: StudyPlannerService, ui: ScholarLedgerUI) -> None:
    """Populate database with sample classical curriculum."""
    ui.print_section_rule("Seed Sample Curriculum")
    if Confirm.ask(
        f"[bold {PALETTE['gold']}]Populate ledger with classical curriculum and sample 5-day study history?[/]",
        default=True,
    ):
        populate_seed_data(service.storage)
        ui.print_success("Curriculum seeded! Disciplines, tasks, milestones, and streak logs populated.")


# -----------------------------------------------------------------------------
# Main Application Loop
# -----------------------------------------------------------------------------

def interactive_session() -> None:
    """Main interactive terminal session."""
    service = StudyPlannerService()
    ui = ScholarLedgerUI()

    ui.display_banner()

    # If database is completely empty, offer to seed initial curriculum
    all_tasks = service.storage.list_tasks()
    all_logs = service.storage.list_study_logs()
    if not all_tasks and not all_logs:
        ui.console.print(
            f"[italic {PALETTE['parchment']}]Welcome, scholar. Your academic ledger is currently pristine and empty.[/]\n"
        )
        if Confirm.ask(
            f"[bold {PALETTE['gold']}]Would you like to seed a sample academic curriculum (Algorithmic Complexity, Systems, Philosophy) to explore?[/]",
            default=True,
        ):
            populate_seed_data(service.storage)
            ui.print_success("Sample curriculum inscribed into your ledger.")

    while True:
        try:
            choice = ui.prompt_menu_choice()
            if choice in ("0", "Q", "QUIT", "EXIT"):
                ui.console.print(
                    f"\n[italic {PALETTE['gold']}]✦ Closing the scholar's journal. \"Faber est suae quisque fortunae\" ✦[/]\n"
                )
                break
            elif choice == "1":
                handle_inscribe_task(service, ui)
            elif choice == "2":
                handle_log_study(service, ui)
            elif choice == "3":
                handle_view_tasks(service, ui)
            elif choice == "4":
                handle_daily_journal(service, ui)
            elif choice == "5":
                handle_weekly_schedule(service, ui)
            elif choice == "6":
                handle_progress_analytics(service, ui)
            elif choice == "7":
                handle_modify_task(service, ui)
            elif choice == "8":
                handle_milestones(service, ui)
            elif choice == "9":
                handle_focus_hourglass(service, ui)
            elif choice == "B":
                handle_backup_export(service, ui)
            elif choice == "S":
                handle_seed_data(service, ui)
            else:
                ui.print_warning(f"Unrecognized ledger command '{choice}'.")

        except (KeyboardInterrupt, EOFError):
            ui.console.print(
                f"\n\n[italic {PALETTE['gold']}]✦ Session suspended. Ledger securely preserved on disk. ✦[/]\n"
            )
            break
        except Exception as e:
            ui.print_error(f"Unexpected exception: {e}")


# -----------------------------------------------------------------------------
# CLI Arguments Parser
# -----------------------------------------------------------------------------

def build_cli_parser() -> argparse.ArgumentParser:
    """Build command line interface parser for scriptable actions."""
    parser = argparse.ArgumentParser(
        prog="study-planner",
        description="The Scholar's Ledger: Personal Study Planner and Progress Tracker.",
    )

    subparsers = parser.add_subparsers(dest="command", help="Ledger Subcommands")

    # Command: inscribe / add task
    add_p = subparsers.add_parser("add", help="Inscribe a new task or assignment")
    add_p.add_argument("subject", type=str, help="Subject/Discipline")
    add_p.add_argument("topic", type=str, help="Topic or Assignment title")
    add_p.add_argument("--deadline", "-d", type=str, default="today", help="Deadline (e.g. today, tomorrow, +3d)")
    add_p.add_argument("--priority", "-p", choices=["High", "Medium", "Low", "H", "M", "L"], default="Medium")
    add_p.add_argument("--hours", "-e", type=float, default=1.5, help="Estimated study hours")
    add_p.add_argument("--notes", "-n", type=str, default="", help="Notes or references")

    # Command: log study session
    log_p = subparsers.add_parser("log", help="Log completed study hours")
    log_p.add_argument("subject", type=str, help="Subject/Discipline")
    log_p.add_argument("hours", type=float, help="Study hours spent")
    log_p.add_argument("--topic", "-t", type=str, default="General Study", help="Topic focused on")
    log_p.add_argument("--date", "-d", type=str, default="today", help="Session date (YYYY-MM-DD or today)")
    log_p.add_argument("--notes", "-n", type=str, default="", help="Reflections / notes")

    # Command: list tasks
    tasks_p = subparsers.add_parser("tasks", help="List active ledger tasks")
    tasks_p.add_argument("--subject", "-s", type=str, default=None, help="Filter by discipline")
    tasks_p.add_argument("--pending", action="store_true", help="Show only pending tasks")
    tasks_p.add_argument("--completed", action="store_true", help="Show only completed tasks")
    tasks_p.add_argument("--daily", action="store_true", help="Show daily view for today")
    tasks_p.add_argument("--weekly", action="store_true", help="Show weekly schedule")

    # Command: stats
    subparsers.add_parser("stats", help="Display progress and streak analytics")

    # Command: timer
    timer_p = subparsers.add_parser("timer", help="Run focus hourglass timer")
    timer_p.add_argument("minutes", type=float, nargs="?", default=25.0, help="Timer duration in minutes")

    # Command: export
    export_p = subparsers.add_parser("export", help="Export ledger to JSON")
    export_p.add_argument("path", type=str, nargs="?", default="study_data.json", help="Destination file path")

    # Command: seed
    subparsers.add_parser("seed", help="Seed sample curriculum into ledger")

    return parser


def main() -> None:
    """Primary execution dispatch."""
    parser = build_cli_parser()
    args = parser.parse_args()

    # If no subcommand supplied, launch the rich interactive ledger
    if not args.command:
        interactive_session()
        return

    service = StudyPlannerService()
    ui = ScholarLedgerUI()

    try:
        if args.command == "add":
            priority = Priority.from_string(args.priority)
            task = service.create_task(
                subject=args.subject,
                topic=args.topic,
                deadline_input=args.deadline,
                priority=priority,
                estimated_hours=args.hours,
                notes=args.notes,
            )
            ui.print_success(f"Inscribed Ref #{task.id}: '{task.topic}' ({task.subject}) due {task.deadline}.")

        elif args.command == "log":
            log = service.log_study_session(
                subject=args.subject,
                topic=args.topic,
                hours=args.hours,
                date_input=args.date,
                notes=args.notes,
            )
            current_streak, _ = service.storage.calculate_streaks()
            ui.print_success(
                f"Logged {log.hours_spent:.2f}h on {log.session_date} for [{log.subject}]. "
                f"Current Streak: {current_streak} days! 🔥"
            )

        elif args.command == "tasks":
            if args.daily:
                daily_data = service.get_daily_view("today")
                ui.render_daily_view(daily_data)
            elif args.weekly:
                weekly_data = service.get_weekly_view("today")
                ui.render_weekly_view(weekly_data)
            else:
                status_filter = None
                if args.pending:
                    status_filter = Status.PENDING
                elif args.completed:
                    status_filter = Status.COMPLETED

                tasks = service.storage.list_tasks(subject=args.subject, status=status_filter)
                ui.render_tasks_table(tasks, title="Academic Ledger Tasks")

        elif args.command == "stats":
            stats = service.get_scholar_stats()
            ui.render_progress_dashboard(stats)

        elif args.command == "timer":
            handle_focus_hourglass(service, ui, default_mins=args.minutes)

        elif args.command == "export":
            out = service.storage.export_to_json(args.path)
            ui.print_success(f"Exported academic ledger to {out}")

        elif args.command == "seed":
            populate_seed_data(service.storage)
            ui.print_success("Seeded sample curriculum and historical logs into ledger.")

    except Exception as exc:
        ui.print_error(str(exc))
        sys.exit(1)


if __name__ == "__main__":
    main()
