# PawPal+ (Module 2 Project)

You are building **PawPal+**, a Streamlit app that helps a pet owner plan care tasks for their pet.

## Scenario

A busy pet owner needs help staying consistent with pet care. They want an assistant that can:

- Track pet care tasks (walks, feeding, meds, enrichment, grooming, etc.)
- Consider constraints (time available, priority, owner preferences)
- Produce a daily plan and explain why it chose that plan

Your job is to design the system first (UML), then implement the logic in Python, then connect it to the Streamlit UI.

## What you will build

Your final app should:

- Let a user enter basic owner + pet info
- Let a user add/edit tasks (duration + priority at minimum)
- Generate a daily schedule/plan based on constraints and priorities
- Display the plan clearly (and ideally explain the reasoning)
- Include tests for the most important scheduling behaviors

## Getting started

### Setup

```bash
python -m venv .venv
source .venv/bin/activate  # Windows: .venv\Scripts\activate
pip install -r requirements.txt
```

## Smarter Scheduling

PawPal+ now includes four algorithmic features that make the daily planner more intelligent:

- **Sorting by time** — `Scheduler.sort_by_time()` orders any list of tasks chronologically using a lambda key that converts each task's `HH:MM` string to minutes since midnight, ensuring correct numeric ordering regardless of string length.

- **Filtering by pet or status** — `Scheduler.filter_tasks()` accepts an optional pet name and/or a completion status (`"pending"` or `"completed"`) and returns only the matching `(pet, task)` pairs, making it easy to focus on one animal's workload or review what's already done.

- **Recurring tasks** — `Scheduler.mark_task_complete()` marks a task done and automatically creates the next occurrence using Python's `timedelta`: daily tasks reappear tomorrow (`+ timedelta(days=1)`), weekly tasks reappear in seven days (`+ timedelta(weeks=1)`). One-off `"as-needed"` tasks are simply marked complete with no successor.

- **Conflict detection** — `Scheduler.get_conflicts()` returns human-readable warnings for three conflict types: (1) two or more tasks requesting the exact same `HH:MM` start time, (2) a pet having multiple pending tasks in the same category (e.g., two "walk" entries), and (3) total pending time exceeding the owner's daily budget. The checker returns warning strings rather than raising exceptions, so the app stays running and the user can decide how to resolve each issue.

### Suggested workflow

1. Read the scenario carefully and identify requirements and edge cases.
2. Draft a UML diagram (classes, attributes, methods, relationships).
3. Convert UML into Python class stubs (no logic yet).
4. Implement scheduling logic in small increments.
5. Add tests to verify key behaviors.
6. Connect your logic to the Streamlit UI in `app.py`.
7. Refine UML so it matches what you actually built.
