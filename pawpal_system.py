from dataclasses import dataclass, field

PRIORITY_RANK = {"high": 0, "medium": 1, "low": 2}


# ---------------------------------------------------------------------------
# Task
# ---------------------------------------------------------------------------

@dataclass
class Task:
    title: str
    duration_minutes: int
    priority: str    # "high", "medium", or "low"
    category: str    # e.g. "walk", "feed", "meds", "grooming", "enrichment"
    frequency: str   # "daily", "weekly", or "as-needed"
    completed: bool = False

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
        return f"{time_range}  |  {label:<30}  {priority_tag:<8}  {self.task.duration_minutes} min"


# ---------------------------------------------------------------------------
# Scheduler  -the core logic layer
# ---------------------------------------------------------------------------

class Scheduler:
    """
    Builds a greedy daily schedule across all pets owned by `owner`.

    Algorithm:
      1. Collect every pending task from every pet.
      2. Sort by priority (high → medium → low); ties broken alphabetically.
      3. Walk the sorted list, assigning consecutive time slots until the
         owner's daily budget is exhausted.
      4. Tasks that don't fit are stored in `excluded` with a reason.
    """

    DEFAULT_START_MINUTES = 8 * 60  # 8:00 AM

    def __init__(self, owner: Owner) -> None:
        """Initialise the scheduler with an owner whose pets and tasks it will manage."""
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

    # ------------------------------------------------------------------
    # Core scheduling
    # ------------------------------------------------------------------

    def generate_schedule(self, start_time: int = DEFAULT_START_MINUTES) -> list[ScheduledTask]:
        """
        Build today's schedule. Safe to call multiple times -each call
        resets and rebuilds `schedule` and `excluded` from scratch.
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

        # Sort: high → medium → low; alphabetical within the same priority
        pending.sort(
            key=lambda pt: (PRIORITY_RANK.get(pt[1].priority, 99), pt[1].title)
        )

        for pet, task in pending:
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

        width = 60
        used = self.owner.available_minutes_per_day - self.get_remaining_time()
        budget = self.owner.available_minutes_per_day
        col_header = f"  {'TIME':18}  {'TASK (PET)':<30}  {'PRIORITY':<8}  DURATION"

        lines = [
            "",
            f"  TODAY'S SCHEDULE  -  {self.owner.name}",
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
                lines.append(
                    f"  {'--:-- - --:--':18}  {label:<30}  "
                    f"{f'[{st.task.priority}]':<8}  {st.task.duration_minutes} min"
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
