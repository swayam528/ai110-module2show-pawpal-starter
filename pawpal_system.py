from dataclasses import dataclass, field
from collections import defaultdict
from datetime import date, timedelta

PRIORITY_RANK = {"high": 0, "medium": 1, "low": 2}

# Time-slot ordering for sorting tasks by preferred time of day
TIME_SLOT_ORDER = {"morning": 0, "afternoon": 1, "evening": 2, "any": 3}

# Minute-of-day where each time slot begins (used to advance the scheduler cursor)
TIME_SLOT_START = {
    "morning":   6 * 60,   # 06:00
    "afternoon": 12 * 60,  # 12:00
    "evening":   17 * 60,  # 17:00
    "any":        8 * 60,  # 08:00 (default)
}


# ---------------------------------------------------------------------------
# Task
# ---------------------------------------------------------------------------

@dataclass
class Task:
    title: str
    duration_minutes: int
    priority: str       # "high", "medium", or "low"
    category: str       # e.g. "walk", "feed", "meds", "grooming", "enrichment"
    frequency: str      # "daily", "weekly", or "as-needed"
    preferred_time: str = "any"   # "morning", "afternoon", "evening", or "any"
    time: str = "08:00"           # requested start time in HH:MM (24-hour clock)
    completed: bool = False
    due_date: date = field(default_factory=date.today)

    def mark_complete(self) -> None:
        """Mark this task as done for the current day."""
        self.completed = True

    def reset(self) -> None:
        """Clear completion status so the task reappears tomorrow."""
        self.completed = False

    def is_high_priority(self) -> bool:
        """Return True if this task's priority is 'high'."""
        return self.priority == "high"


# ---------------------------------------------------------------------------
# Pet
# ---------------------------------------------------------------------------

@dataclass
class Pet:
    name: str
    species: str
    age: int
    tasks: list[Task] = field(default_factory=list)

    def add_task(self, task: Task) -> None:
        """Register a care task for this pet."""
        self.tasks.append(task)

    def remove_task(self, task: Task) -> None:
        """Remove a care task by object identity."""
        self.tasks.remove(task)

    def get_pending_tasks(self) -> list[Task]:
        """Return all tasks that have not been completed yet."""
        return [t for t in self.tasks if not t.completed]

    def get_profile_summary(self) -> str:
        """Return a one-line description of the pet and its pending task count."""
        total = len(self.tasks)
        pending = len(self.get_pending_tasks())
        return (
            f"{self.name} ({self.species}, age {self.age}) -"
            f"{pending} of {total} task(s) pending"
        )


# ---------------------------------------------------------------------------
# Owner
# ---------------------------------------------------------------------------

@dataclass
class Owner:
    name: str
    available_minutes_per_day: int
    preferences: dict = field(default_factory=dict)
    pets: list[Pet] = field(default_factory=list)

    def add_pet(self, pet: Pet) -> None:
        """Add a pet to this owner's care list."""
        self.pets.append(pet)

    def remove_pet(self, pet: Pet) -> None:
        """Remove a pet from this owner's care list."""
        self.pets.remove(pet)

    def get_all_tasks(self) -> list[tuple[Pet, Task]]:
        """Return every task across all pets as (pet, task) pairs."""
        return [(pet, task) for pet in self.pets for task in pet.tasks]

    def get_available_time(self) -> int:
        """Return the owner's total daily time budget in minutes."""
        return self.available_minutes_per_day

    def update_preferences(self, prefs: dict) -> None:
        """Merge new preference entries into the existing dict."""
        self.preferences.update(prefs)


# ---------------------------------------------------------------------------
# ScheduledTask  (output wrapper produced by Scheduler)
# ---------------------------------------------------------------------------

@dataclass
class ScheduledTask:
    task: Task
    pet: Pet
    start_time: int    # minutes from midnight (e.g. 480 = 8:00 AM)
    end_time: int
    reason: str = ""

    def duration(self) -> int:
        """Return the length of this time slot in minutes."""
        return self.end_time - self.start_time

    def summary(self) -> str:
        """Human-readable one-liner for UI display."""
        start_h, start_m = divmod(self.start_time, 60)
        end_h, end_m = divmod(self.end_time, 60)
        time_range = f"{start_h:02d}:{start_m:02d} - {end_h:02d}:{end_m:02d}"
        label = f"{self.task.title} ({self.pet.name})"
        priority_tag = f"[{self.task.priority}]"
        freq_tag = f"[{self.task.frequency}]" if self.task.frequency != "daily" else ""
        line = f"{time_range}  |  {label:<30}  {priority_tag:<8}  {self.task.duration_minutes} min"
        if freq_tag:
            line += f"  {freq_tag}"
        return line


# ---------------------------------------------------------------------------
# Scheduler  — the core logic layer
# ---------------------------------------------------------------------------

class Scheduler:
    """
    Builds a greedy daily schedule across all pets owned by `owner`.

    Algorithm:
      1. Collect every pending task from every pet.
      2. Sort by preferred time slot (morning → afternoon → evening → any),
         then by priority (high → medium → low), then alphabetically.
      3. When moving into a new time slot, advance the cursor to that slot's
         start time if the cursor hasn't reached it yet.
      4. Walk the sorted list, assigning consecutive time slots until the
         owner's daily budget is exhausted.
      5. Tasks that don't fit are stored in `excluded` with a reason.
    """

    DEFAULT_START_MINUTES = 8 * 60  # 8:00 AM

    def __init__(self, owner: Owner) -> None:
        self.owner = owner
        self.schedule: list[ScheduledTask] = []
        self.excluded: list[ScheduledTask] = []
        self._generated = False

    # ------------------------------------------------------------------
    # Task management (delegates to the correct Pet)
    # ------------------------------------------------------------------

    def add_task(self, pet: Pet, task: Task) -> None:
        """Add a task directly to a pet. Raises ValueError if pet not found."""
        if pet not in self.owner.pets:
            raise ValueError(f"{pet.name} is not registered under {self.owner.name}.")
        pet.add_task(task)

    def remove_task(self, pet: Pet, task: Task) -> None:
        """Remove a task from a pet. Raises ValueError if pet not found."""
        if pet not in self.owner.pets:
            raise ValueError(f"{pet.name} is not registered under {self.owner.name}.")
        pet.remove_task(task)

    def mark_task_complete(self, pet: Pet, task: Task) -> Task | None:
        """
        Mark *task* as complete and, for recurring tasks, automatically add
        the next occurrence to *pet*.

        Recurrence rules:
          - "daily"  → next due_date is task.due_date + 1 day
          - "weekly" → next due_date is task.due_date + 7 days
          - "as-needed" → no next occurrence is created

        Returns the newly created Task if one was scheduled, otherwise None.

        Why timedelta?
          timedelta arithmetic handles month/year rollovers automatically, so
          adding 1 day to 2026-03-31 correctly yields 2026-04-01 without any
          manual calendar logic.
        """
        task.mark_complete()

        delta = {"daily": timedelta(days=1), "weekly": timedelta(weeks=1)}.get(task.frequency)
        if delta is None:
            return None

        next_task = Task(
            title=task.title,
            duration_minutes=task.duration_minutes,
            priority=task.priority,
            category=task.category,
            frequency=task.frequency,
            preferred_time=task.preferred_time,
            time=task.time,
            due_date=task.due_date + delta,
        )
        pet.add_task(next_task)
        return next_task

    # ------------------------------------------------------------------
    # Filtering
    # ------------------------------------------------------------------

    def filter_tasks(
        self,
        pet_name: str | None = None,
        status: str | None = None,  # "pending", "completed", or None for all
    ) -> list[tuple[Pet, Task]]:
        """Return (pet, task) pairs filtered by pet name and/or completion status."""
        result = []
        for pet, task in self.owner.get_all_tasks():
            if pet_name and pet.name != pet_name:
                continue
            if status == "pending" and task.completed:
                continue
            if status == "completed" and not task.completed:
                continue
            result.append((pet, task))
        return result

    # ------------------------------------------------------------------
    # Sorting
    # ------------------------------------------------------------------

    def sort_by_time(
        self, tasks: list[tuple[Pet, Task]]
    ) -> list[tuple[Pet, Task]]:
        """
        Return a new list of (pet, task) pairs sorted by each task's 'time'
        field (HH:MM, 24-hour clock).

        Why the lambda works:
          "HH:MM" strings are zero-padded, so they sort lexicographically
          in the correct order ("08:00" < "12:30" < "17:45"). Converting to
          minutes-since-midnight makes the intent explicit and handles any
          edge case where a caller passes a non-zero-padded string.

          key = lambda pt: int(pt[1].time[:2]) * 60 + int(pt[1].time[3:])
                           └─ hours part ──┘             └─ minutes part ┘
        """
        return sorted(
            tasks,
            key=lambda pt: int(pt[1].time[:2]) * 60 + int(pt[1].time[3:]),
        )

    # ------------------------------------------------------------------
    # Conflict detection
    # ------------------------------------------------------------------

    def get_conflicts(self) -> list[str]:
        """
        Detect three types of scheduling conflicts:
          1. Same-time collision: two or more pending tasks share an exact HH:MM start time.
          2. Duplicate category: same pet has multiple pending tasks in the same category.
          3. Budget overflow: total pending time exceeds the owner's daily budget.

        Returns a list of human-readable warning strings (empty list = no conflicts).

        Tradeoff — exact-time matching only:
          Collision detection compares the task's requested 'time' field exactly
          (e.g. "08:00" == "08:00"). It does NOT check whether two tasks *overlap*
          (e.g. a 30-min task at 08:00 and a 15-min task at 08:20 would conflict
          in real life but pass undetected here). This keeps the check O(n) and
          avoids the complexity of interval arithmetic, which is acceptable for a
          simple daily planner where most tasks are assigned to coarse time slots.
        """
        conflicts = []

        # --- Same-time collision (across all pets) ---
        time_slots: dict[str, list[str]] = defaultdict(list)
        for pet, task in self.owner.get_all_tasks():
            if not task.completed:
                time_slots[task.time].append(f"{task.title} ({pet.name})")
        for time_str, labels in time_slots.items():
            if len(labels) > 1:
                conflicts.append(
                    f"WARNING: {len(labels)} tasks are scheduled at {time_str}: "
                    + ", ".join(f'"{lbl}"' for lbl in labels)
                )

        # --- Duplicate category per pet ---
        pet_categories: dict[tuple[str, str], list[str]] = defaultdict(list)
        for pet, task in self.owner.get_all_tasks():
            if not task.completed:
                pet_categories[(pet.name, task.category)].append(task.title)
        for (pet_name, category), titles in pet_categories.items():
            if len(titles) > 1:
                conflicts.append(
                    f"{pet_name} has {len(titles)} '{category}' tasks: "
                    + ", ".join(f'"{t}"' for t in titles)
                )

        # --- Budget overflow ---
        total_pending = sum(
            task.duration_minutes
            for _, task in self.owner.get_all_tasks()
            if not task.completed
        )
        budget = self.owner.available_minutes_per_day
        if total_pending > budget:
            overflow = total_pending - budget
            conflicts.append(
                f"Total pending task time ({total_pending} min) exceeds daily budget "
                f"({budget} min) by {overflow} min — some tasks will be deferred."
            )

        return conflicts

    # ------------------------------------------------------------------
    # Core scheduling
    # ------------------------------------------------------------------

    def generate_schedule(self, start_time: int = DEFAULT_START_MINUTES) -> list[ScheduledTask]:
        """
        Build today's schedule. Safe to call multiple times — each call
        resets and rebuilds `schedule` and `excluded` from scratch.

        Sorting: time slot preference (morning → afternoon → evening → any),
        then priority (high → medium → low), then task title alphabetically.

        Recurring tasks:
          - 'daily'     tasks are always included.
          - 'weekly'    tasks are scheduled but flagged in the output.
          - 'as-needed' tasks are scheduled but flagged in the output.
        """
        self.schedule = []
        self.excluded = []
        self._generated = True

        budget_end = start_time + self.owner.available_minutes_per_day
        cursor = start_time

        # Gather all incomplete tasks from every pet
        pending: list[tuple[Pet, Task]] = [
            (pet, task)
            for pet in self.owner.pets
            for task in pet.get_pending_tasks()
        ]

        # Sort: time slot → HH:MM time → priority → title
        # Using the same lambda from sort_by_time() as the second key converts
        # the HH:MM string to minutes so we get a correct numeric comparison.
        pending.sort(
            key=lambda pt: (
                TIME_SLOT_ORDER.get(pt[1].preferred_time, 3),
                int(pt[1].time[:2]) * 60 + int(pt[1].time[3:]),
                PRIORITY_RANK.get(pt[1].priority, 99),
                pt[1].title,
            )
        )

        current_slot: str | None = None

        for pet, task in pending:
            slot = task.preferred_time
            slot_start = TIME_SLOT_START.get(slot, start_time)

            # Advance cursor to the time slot's start only if it falls within the budget window
            if slot != "any" and slot != current_slot:
                if cursor < slot_start < budget_end:
                    cursor = slot_start
                current_slot = slot

            if cursor + task.duration_minutes <= budget_end:
                self.schedule.append(ScheduledTask(
                    task=task,
                    pet=pet,
                    start_time=cursor,
                    end_time=cursor + task.duration_minutes,
                    reason="fits within daily time budget",
                ))
                cursor += task.duration_minutes
            else:
                self.excluded.append(ScheduledTask(
                    task=task,
                    pet=pet,
                    start_time=0,
                    end_time=0,
                    reason="skipped: would exceed daily time budget",
                ))

        return self.schedule

    # ------------------------------------------------------------------
    # Reporting
    # ------------------------------------------------------------------

    def get_remaining_time(self) -> int:
        """Minutes left in the day after all scheduled tasks."""
        self._require_generated()
        return self.owner.available_minutes_per_day - sum(
            st.duration() for st in self.schedule
        )

    def explain_plan(self) -> str:
        """Return a human-readable summary of the schedule and deferrals."""
        self._require_generated()

        width = 70
        used = self.owner.available_minutes_per_day - self.get_remaining_time()
        budget = self.owner.available_minutes_per_day
        col_header = f"  {'TIME':18}  {'TASK (PET)':<30}  {'PRIORITY':<8}  DURATION"

        lines = [
            "",
            f"  TODAY'S SCHEDULE  —  {self.owner.name}",
            "  " + "=" * width,
        ]

        if self.schedule:
            lines.append(col_header)
            lines.append("  " + "-" * width)
            for st in self.schedule:
                lines.append(f"  {st.summary()}")
        else:
            lines.append("  (no tasks could be scheduled today)")

        if self.excluded:
            lines.append("")
            lines.append(f"  DEFERRED  (did not fit in {budget}-min budget)")
            lines.append("  " + "-" * width)
            for st in self.excluded:
                label = f"{st.task.title} ({st.pet.name})"
                freq_tag = f"[{st.task.frequency}]" if st.task.frequency != "daily" else ""
                lines.append(
                    f"  {'--:-- - --:--':18}  {label:<30}  "
                    f"{f'[{st.task.priority}]':<8}  {st.task.duration_minutes} min  {freq_tag}".rstrip()
                )

        lines += [
            "",
            "  " + "-" * width,
            f"  Time used:      {used} / {budget} min",
            f"  Time remaining: {self.get_remaining_time()} min",
            "",
        ]
        return "\n".join(lines)

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _require_generated(self) -> None:
        """Raise RuntimeError if generate_schedule() has not been called yet."""
        if not self._generated:
            raise RuntimeError(
                "No schedule has been generated yet. Call generate_schedule() first."
            )
