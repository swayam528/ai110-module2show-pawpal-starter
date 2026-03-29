from dataclasses import dataclass, field
from typing import Optional


@dataclass
class Owner:
    name: str
    available_minutes_per_day: int
    preferences: dict = field(default_factory=dict)

    def get_available_time(self) -> int:
        pass

    def update_preferences(self, prefs: dict) -> None:
        pass


@dataclass
class Pet:
    name: str
    species: str
    age: int
    owner: Owner = field(default=None)

    def get_profile_summary(self) -> str:
        pass


@dataclass
class Task:
    title: str
    duration_minutes: int
    priority: str          # "high", "medium", or "low"
    category: str          # e.g. "walk", "feed", "meds", "grooming", "enrichment"
    completed: bool = False

    def mark_complete(self) -> None:
        pass

    def is_high_priority(self) -> bool:
        pass


@dataclass
class ScheduledTask:
    task: Task
    start_time: int        # minutes from start of day (e.g. 480 = 8:00 AM)
    end_time: int
    reason: str = ""

    def duration(self) -> int:
        pass

    def summary(self) -> str:
        pass


class Scheduler:
    def __init__(self, owner: Owner, pet: Pet):
        self.owner = owner
        self.pet = pet
        self.tasks: list[Task] = []
        self.schedule: list[ScheduledTask] = []
        self.excluded: list[ScheduledTask] = []

    def add_task(self, task: Task) -> None:
        pass

    def remove_task(self, task: Task) -> None:
        pass

    def generate_schedule(self) -> list[ScheduledTask]:
        pass

    def get_remaining_time(self) -> int:
        pass

    def explain_plan(self) -> str:
        pass
