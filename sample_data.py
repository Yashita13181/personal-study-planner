"""
sample_data.py - Curated academic seed dataset for Personal Study Planner.
Provides a realistic scholar's journal with disciplines, reading schedules,
and historical study sessions.
"""

from datetime import date, timedelta
from models import Priority, Status, Subject, Task, StudyLog, Milestone
from storage import StorageManager


def populate_seed_data(storage: StorageManager) -> None:
    """Populate the database with a classic scholar's curriculum."""
    today = date.today()

    # 1. Subjects
    subjects = [
        Subject(
            name="Algorithmic Complexity",
            target_weekly_hours=7.0,
            color_theme="#D4AF37",
            description="Dynamic programming, graph algorithms, and asymptotic proofs.",
        ),
        Subject(
            name="Computer Systems",
            target_weekly_hours=6.0,
            color_theme="#6B8EAE",
            description="Memory hierarchies, cache coherence, concurrent runtime kernels.",
        ),
        Subject(
            name="Classical Philosophy",
            target_weekly_hours=4.0,
            color_theme="#C5A059",
            description="Epistemology, Aristotelian ethics, and dialectical inquiries.",
        ),
        Subject(
            name="Linear Algebra",
            target_weekly_hours=5.0,
            color_theme="#7E9F76",
            description="Eigenvalue decompositions, vector spaces, and convex optimization.",
        ),
    ]

    for subj in subjects:
        try:
            storage.add_subject(subj)
        except Exception:
            pass

    # 2. Historical Study Logs (To create an active 5-day study streak!)
    logs = [
        # Today
        StudyLog(
            subject="Algorithmic Complexity",
            topic="Tarjan's SCC & Topological Sorting",
            hours_spent=2.0,
            session_date=today.isoformat(),
            notes="Implemented iterative DFS for SCC identification.",
        ),
        # Yesterday
        StudyLog(
            subject="Computer Systems",
            topic="Virtual Memory & Page Table Translation",
            hours_spent=2.5,
            session_date=(today - timedelta(days=1)).isoformat(),
            notes="Derived two-level page table memory overhead formulas.",
        ),
        # 2 days ago
        StudyLog(
            subject="Linear Algebra",
            topic="Singular Value Decomposition (SVD)",
            hours_spent=1.5,
            session_date=(today - timedelta(days=2)).isoformat(),
            notes="Proved orthogonality of U and V matrices in SVD.",
        ),
        # 3 days ago
        StudyLog(
            subject="Classical Philosophy",
            topic="Aristotle's Nicomachean Ethics - Book II",
            hours_spent=1.5,
            session_date=(today - timedelta(days=3)).isoformat(),
            notes="Reflected on the Golden Mean and cultivation of virtue.",
        ),
        # 4 days ago
        StudyLog(
            subject="Algorithmic Complexity",
            topic="Network Flow & Ford-Fulkerson Algorithm",
            hours_spent=3.0,
            session_date=(today - timedelta(days=4)).isoformat(),
            notes="Walked through residual capacity and augmenting paths.",
        ),
    ]

    for log in logs:
        storage.add_study_log(log)

    # 3. Tasks / Syllabus Schedule
    tasks = [
        Task(
            subject="Algorithmic Complexity",
            topic="Solve 5 Dynamic Programming Problems on Trees",
            deadline=today.isoformat(),
            priority=Priority.HIGH,
            status=Status.IN_PROGRESS,
            estimated_hours=2.5,
            notes="Focus on post-order traversal state caching.",
        ),
        Task(
            subject="Computer Systems",
            topic="Implement Cache Simulator in C (L1/L2)",
            deadline=(today + timedelta(days=1)).isoformat(),
            priority=Priority.HIGH,
            status=Status.PENDING,
            estimated_hours=4.0,
            notes="LRU replacement policy with 64-byte line size.",
        ),
        Task(
            subject="Linear Algebra",
            topic="Solve Problem Set 4: Principal Component Analysis",
            deadline=(today + timedelta(days=2)).isoformat(),
            priority=Priority.MEDIUM,
            status=Status.PENDING,
            estimated_hours=2.0,
            notes="Verify variance projection theorems.",
        ),
        Task(
            subject="Classical Philosophy",
            topic="Read Plato's Theaetetus (Sections 142a–160e)",
            deadline=(today + timedelta(days=3)).isoformat(),
            priority=Priority.LOW,
            status=Status.PENDING,
            estimated_hours=1.5,
            notes="Examine the definition of knowledge as perception.",
        ),
        Task(
            subject="Algorithmic Complexity",
            topic="Read CLRS Chapter 22: Graph Representation",
            deadline=(today - timedelta(days=1)).isoformat(),
            priority=Priority.MEDIUM,
            status=Status.COMPLETED,
            estimated_hours=1.5,
            notes="Completed exercises 22.1-1 through 22.1-6.",
            completed_at=(today - timedelta(days=1)).isoformat(),
        ),
        Task(
            subject="Computer Systems",
            topic="Review Assembly Calling Conventions (x86-64 System V)",
            deadline=(today - timedelta(days=2)).isoformat(),
            priority=Priority.HIGH,
            status=Status.COMPLETED,
            estimated_hours=2.0,
            notes="Annotated stack frame alignments and register preservation.",
            completed_at=(today - timedelta(days=2)).isoformat(),
        ),
    ]

    for task in tasks:
        storage.add_task(task)

    # 4. Academic Milestones
    milestones = [
        Milestone(
            title="Syllabus Milestone: Foundations of Computability",
            subject="Algorithmic Complexity",
            target_date=(today - timedelta(days=10)).isoformat(),
            achieved=True,
            achieved_at=(today - timedelta(days=10)).isoformat(),
            description="Mastered Turing equivalence, reductions, and NP-completeness proofs.",
        ),
        Milestone(
            title="Midterm Defense: Distributed Consensus & Paxos",
            subject="Computer Systems",
            target_date=(today + timedelta(days=14)).isoformat(),
            achieved=False,
            description="Oral presentation on Raft vs Paxos safety invariants.",
        ),
        Milestone(
            title="Final Term Paper: Epistemic Foundationalism",
            subject="Classical Philosophy",
            target_date=(today + timedelta(days=28)).isoformat(),
            achieved=False,
            description="3,500 word thesis comparing Cartesian doubt with Agrippa's Trilemma.",
        ),
    ]

    for m in milestones:
        storage.add_milestone(m)
