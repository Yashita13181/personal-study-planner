"""
app.py - Production-ready Web Interface for Personal Study Planner.
Enables cloud deployment on Render, Railway, or PythonAnywhere with zero modifications
to the underlying business logic, models, or CLI functionality.
"""

from __future__ import annotations
import json
import os
import tempfile
from datetime import date, datetime
from typing import Optional

from flask import (
    Flask,
    render_template,
    request,
    redirect,
    url_for,
    flash,
    send_file,
    jsonify,
)

from models import Priority, Status, Task, StudyLog, Milestone
from storage import StorageManager
from planner import StudyPlannerService, parse_academic_date
from sample_data import populate_seed_data

app = Flask(__name__, template_folder="templates")
app.secret_key = os.environ.get("SECRET_KEY", "the-scholar-academic-ledger-2026-key")

# Initialize storage and planner service
service = StudyPlannerService()

# Auto-seed if database is fresh on first cloud launch
try:
    if not service.storage.list_tasks() and not service.storage.list_study_logs():
        populate_seed_data(service.storage)
except Exception:
    pass


@app.context_processor
def inject_global_template_data():
    """Inject common template variables into every render context."""
    return {
        "now_year": datetime.now().year,
        "today_str": date.today().isoformat(),
    }


# =============================================================================
# HEALTH CHECK (for Render / Cloud monitoring)
# =============================================================================

@app.route("/health")
def health_check():
    """Health check endpoint for cloud load balancers."""
    return jsonify({"status": "healthy", "service": "personal-study-planner", "time": datetime.now().isoformat()}), 200


# =============================================================================
# DASHBOARD
# =============================================================================

@app.route("/")
def dashboard():
    """Main Academic Dashboard."""
    stats = service.get_scholar_stats()
    active_tasks = service.storage.list_tasks(status=Status.PENDING) + service.storage.list_tasks(status=Status.IN_PROGRESS)
    # Sort active tasks by deadline ascending
    active_tasks = sorted(active_tasks, key=lambda t: t.deadline)
    subjects = service.storage.list_subjects()

    return render_template(
        "dashboard.html",
        stats=stats,
        active_tasks=active_tasks,
        subjects=subjects,
    )


# =============================================================================
# TASKS & LEDGER
# =============================================================================

@app.route("/tasks")
def tasks_view():
    """Complete Academic Ledger view with filters."""
    filter_status = request.args.get("status")
    filter_subject = request.args.get("subject")
    filter_overdue = request.args.get("overdue") == "1"

    status_enum = None
    if filter_status:
        try:
            status_enum = Status.from_string(filter_status)
        except ValueError:
            pass

    all_tasks = service.storage.list_tasks(subject=filter_subject, status=status_enum)
    if filter_overdue:
        all_tasks = [t for t in all_tasks if t.is_overdue]

    subjects = service.storage.list_subjects()
    return render_template(
        "tasks.html",
        tasks=all_tasks,
        subjects=subjects,
        filter_status=filter_status,
        filter_subject=filter_subject,
        filter_overdue=filter_overdue,
    )


@app.route("/tasks/add", methods=["POST"])
def task_add():
    """Inscribe a new study assignment or syllabus deadline."""
    subject = request.form.get("subject", "").strip()
    topic = request.form.get("topic", "").strip()
    deadline_raw = request.form.get("deadline", "today").strip()
    priority_raw = request.form.get("priority", "Medium").strip()
    est_hours = float(request.form.get("estimated_hours", 1.5))
    notes = request.form.get("notes", "").strip()

    if not subject or not topic:
        flash("Discipline and Topic cannot be blank.", "error")
        return redirect(url_for("dashboard"))

    try:
        priority = Priority.from_string(priority_raw)
        task = service.create_task(
            subject=subject,
            topic=topic,
            deadline_input=deadline_raw,
            priority=priority,
            estimated_hours=est_hours,
            notes=notes,
        )
        flash(f"Inscribed Ref #{task.id}: '{task.topic}' ({task.subject}) due {task.deadline}.", "success")
    except Exception as exc:
        flash(f"Failed to inscribe task: {exc}", "error")

    return redirect(url_for("tasks_view"))


@app.route("/tasks/<int:task_id>/edit", methods=["GET"])
def task_edit_view(task_id: int):
    """View form to amend a task."""
    task = service.get_task(task_id)
    if not task:
        flash(f"Task Ref #{task_id} not found.", "error")
        return redirect(url_for("tasks_view"))
    return render_template("task_edit.html", task=task)


@app.route("/tasks/<int:task_id>/edit", methods=["POST"])
def task_edit_post(task_id: int):
    """Save amendments to a task."""
    topic = request.form.get("topic", "").strip()
    subject = request.form.get("subject", "").strip()
    deadline = request.form.get("deadline", "").strip()
    priority_raw = request.form.get("priority", "").strip()
    status_raw = request.form.get("status", "").strip()
    est_hours = float(request.form.get("estimated_hours", 1.5))
    notes = request.form.get("notes", "").strip()

    p_enum = None
    if priority_raw:
        try:
            p_enum = Priority.from_string(priority_raw)
        except ValueError:
            pass

    s_enum = None
    if status_raw:
        try:
            s_enum = Status.from_string(status_raw)
        except ValueError:
            pass

    try:
        service.edit_task(
            task_id=task_id,
            topic=topic or None,
            subject=subject or None,
            deadline=deadline or None,
            priority=p_enum,
            status=s_enum,
            estimated_hours=est_hours,
            notes=notes,
        )
        flash(f"Task Ref #{task_id} amended successfully.", "success")
    except Exception as exc:
        flash(f"Failed to amend task: {exc}", "error")

    return redirect(url_for("tasks_view"))


@app.route("/tasks/<int:task_id>/status", methods=["POST"])
def task_toggle_status(task_id: int):
    """Update status of a task (e.g. mark Completed or Reopen)."""
    new_status_str = request.form.get("status", "Completed")
    try:
        new_status = Status.from_string(new_status_str)
        service.update_task_status(task_id, new_status)
        flash(f"Task Ref #{task_id} status updated to {new_status.value}.", "success")
    except Exception as exc:
        flash(f"Status update failed: {exc}", "error")

    return redirect(request.referrer or url_for("tasks_view"))


@app.route("/tasks/<int:task_id>/delete", methods=["POST"])
def task_delete(task_id: int):
    """Delete a task from the ledger."""
    if service.delete_task(task_id):
        flash(f"Task Ref #{task_id} removed from the ledger.", "success")
    else:
        flash(f"Task Ref #{task_id} could not be deleted.", "error")
    return redirect(request.referrer or url_for("tasks_view"))


# =============================================================================
# STUDY HOURS LOGGING
# =============================================================================

@app.route("/log", methods=["POST"])
def log_study():
    """Inscribe completed study hours into the ledger."""
    subject = request.form.get("subject", "").strip()
    topic = request.form.get("topic", "General Study").strip()
    hours = float(request.form.get("hours", 1.0))
    date_input = request.form.get("date", "today").strip()
    notes = request.form.get("notes", "").strip()

    if not subject:
        flash("Discipline name cannot be left blank.", "error")
        return redirect(request.referrer or url_for("dashboard"))

    try:
        log = service.log_study_session(
            subject=subject,
            topic=topic,
            hours=hours,
            date_input=date_input,
            notes=notes,
        )
        curr_streak, _ = service.storage.calculate_streaks()
        flash(
            f"Logged {log.hours_spent:.2f}h for [{log.subject}] on {log.session_date}. "
            f"Active Streak: {curr_streak} days! 🔥",
            "success",
        )
    except Exception as exc:
        flash(f"Failed to log study hours: {exc}", "error")

    return redirect(request.referrer or url_for("dashboard"))


# =============================================================================
# DAILY & WEEKLY VIEWS
# =============================================================================

@app.route("/daily")
def daily_view():
    """Daily academic agenda and session summary."""
    target_date = request.args.get("date", "today")
    try:
        daily_data = service.get_daily_view(target_date)
    except Exception:
        daily_data = service.get_daily_view("today")
    return render_template("daily.html", daily_data=daily_data)


@app.route("/weekly")
def weekly_view():
    """Weekly curriculum schedule (Monday to Sunday)."""
    target_date = request.args.get("date", "today")
    try:
        weekly_data = service.get_weekly_view(target_date)
    except Exception:
        weekly_data = service.get_weekly_view("today")
    return render_template("weekly.html", weekly_data=weekly_data)


# =============================================================================
# PROGRESS & ANALYTICS
# =============================================================================

@app.route("/analytics")
def analytics_view():
    """Holistic scholarship analytics and progress bars."""
    stats = service.get_scholar_stats()
    return render_template("analytics.html", stats=stats)


# =============================================================================
# MILESTONES & LAURELS
# =============================================================================

@app.route("/milestones")
def milestones_view():
    """Academic Laurels & Milestones."""
    milestones = service.storage.list_milestones()
    subjects = service.storage.list_subjects()
    return render_template("milestones.html", milestones=milestones, subjects=subjects)


@app.route("/milestones/add", methods=["POST"])
def milestone_add():
    """Add a new milestone."""
    title = request.form.get("title", "").strip()
    subject = request.form.get("subject", "").strip()
    target_date = request.form.get("target_date", "+2w").strip()
    desc = request.form.get("description", "").strip()

    if not title or not subject:
        flash("Title and Discipline are required for milestones.", "error")
        return redirect(url_for("milestones_view"))

    try:
        m = service.add_milestone(title=title, subject=subject, target_date_input=target_date, description=desc)
        flash(f"Inscribed Milestone #{m.id}: '{m.title}' target {m.target_date}.", "success")
    except Exception as exc:
        flash(f"Failed to inscribe milestone: {exc}", "error")

    return redirect(url_for("milestones_view"))


@app.route("/milestones/<int:milestone_id>/achieve", methods=["POST"])
def milestone_achieve(milestone_id: int):
    """Mark milestone as achieved."""
    if service.mark_milestone_achieved(milestone_id):
        flash(f"Milestone #{milestone_id} achieved! 🏆 Laurels awarded.", "success")
    else:
        flash(f"Milestone #{milestone_id} not found.", "error")
    return redirect(url_for("milestones_view"))


@app.route("/milestones/<int:milestone_id>/delete", methods=["POST"])
def milestone_delete(milestone_id: int):
    """Delete a milestone."""
    if service.storage.delete_milestone(milestone_id):
        flash(f"Milestone #{milestone_id} removed.", "success")
    else:
        flash(f"Milestone #{milestone_id} not found.", "error")
    return redirect(url_for("milestones_view"))


# =============================================================================
# FOCUS HOURGLASS (POMODORO TIMER)
# =============================================================================

@app.route("/timer")
def timer_view():
    """Interactive Focus Hourglass."""
    subjects = service.storage.list_subjects()
    return render_template("timer.html", subjects=subjects)


# =============================================================================
# BACKUP, SYNC & SAMPLE SEEDING
# =============================================================================

@app.route("/backup")
def backup_view():
    """Data persistence and JSON backup/sync view."""
    return render_template("backup.html")


@app.route("/export")
def export_json():
    """Export and download current ledger as study_data.json."""
    temp_file = tempfile.NamedTemporaryFile(suffix=".json", delete=False)
    temp_path = temp_file.name
    temp_file.close()

    service.storage.export_to_json(temp_path)
    return send_file(
        temp_path,
        as_attachment=True,
        download_name="study_data.json",
        mimetype="application/json",
    )


@app.route("/import", methods=["POST"])
def import_json():
    """Import ledger data from uploaded JSON."""
    file = request.files.get("json_file")
    if not file or not file.filename:
        flash("No JSON file selected for upload.", "error")
        return redirect(url_for("backup_view"))

    overwrite = request.form.get("overwrite") == "1"
    temp_file = tempfile.NamedTemporaryFile(suffix=".json", delete=False)
    temp_path = temp_file.name
    temp_file.close()

    try:
        file.save(temp_path)
        counts = service.storage.import_from_json(temp_path, overwrite=overwrite)
        flash(
            f"Successfully imported {counts['subjects']} subjects, {counts['tasks']} tasks, "
            f"{counts['study_logs']} logs, and {counts['milestones']} milestones.",
            "success",
        )
    except Exception as exc:
        flash(f"Import failed: {exc}", "error")
    finally:
        if os.path.exists(temp_path):
            os.remove(temp_path)

    return redirect(url_for("dashboard"))


@app.route("/seed", methods=["POST"])
def seed_curriculum():
    """Seed sample classical curriculum."""
    try:
        populate_seed_data(service.storage)
        flash("Sample academic curriculum and 5-day study history seeded successfully! 🔥", "success")
    except Exception as exc:
        flash(f"Seeding failed: {exc}", "error")
    return redirect(url_for("dashboard"))


# =============================================================================
# ENTRY POINT
# =============================================================================

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port, debug=False)
