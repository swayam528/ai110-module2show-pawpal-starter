import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from datetime import date, timedelta
from pawpal_system import Task, Pet, Owner, Scheduler


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def make_task(**overrides):
    """Return a Task with sensible defaults; any field can be overridden."""
    defaults = dict(
        title="Morning walk",
        duration_minutes=30,
        priority="high",
        category="walk",
        frequency="daily",
        preferred_time="morning",
        time="08:00",
        due_date=date.today(),
    )
    defaults.update(overrides)
    return Task(**defaults)


def make_scheduler(available_minutes=240):
    """Return an Owner+Pet+Scheduler triple ready to use."""
    owner = Owner(name="Jordan", available_minutes_per_day=available_minutes)
    pet   = Pet(name="Mochi", species="dog", age=3)
    owner.add_pet(pet)
    return Scheduler(owner=owner), owner, pet


# ---------------------------------------------------------------------------
# Original tests (preserved)
# ---------------------------------------------------------------------------

def test_mark_complete_sets_completed_true():
    """mark_complete() flips completed from False to True."""
    task = make_task()
    assert task.completed is False
    task.mark_complete()
    assert task.completed is True


def test_add_task_increases_pet_task_count():
    """add_task() appends to pet.tasks."""
    pet = Pet(name="Mochi", species="dog", age=3)
    assert len(pet.tasks) == 0
    pet.add_task(make_task(title="Breakfast", category="feed"))
    assert len(pet.tasks) == 1
    pet.add_task(make_task(title="Evening walk"))
    assert len(pet.tasks) == 2


# ---------------------------------------------------------------------------
# Sorting
# ---------------------------------------------------------------------------

def test_sort_by_time_returns_chronological_order():
    """Tasks added out of order are returned sorted earliest → latest."""
    scheduler, owner, pet = make_scheduler()
    t1 = make_task(title="Dinner",    time="18:00")
    t2 = make_task(title="Breakfast", time="07:30")
    t3 = make_task(title="Lunch",     time="12:00")
    for t in (t1, t2, t3):
        pet.add_task(t)

    sorted_tasks = scheduler.sort_by_time(owner.get_all_tasks())
    times = [task.time for _, task in sorted_tasks]
    assert times == ["07:30", "12:00", "18:00"]


def test_sort_by_time_handles_same_hour():
    """Tasks in the same hour are ordered by minute."""
    scheduler, owner, pet = make_scheduler()
    t1 = make_task(title="B", time="08:45")
    t2 = make_task(title="A", time="08:00")
    t3 = make_task(title="C", time="08:20")
    for t in (t1, t2, t3):
        pet.add_task(t)

    sorted_tasks = scheduler.sort_by_time(owner.get_all_tasks())
    times = [task.time for _, task in sorted_tasks]
    assert times == ["08:00", "08:20", "08:45"]


def test_sort_by_time_empty_list():
    """sort_by_time() on an empty list returns an empty list without error."""
    scheduler, _, _ = make_scheduler()
    assert scheduler.sort_by_time([]) == []


# ---------------------------------------------------------------------------
# Filtering
# ---------------------------------------------------------------------------

def test_filter_by_pet_name():
    """filter_tasks(pet_name=...) returns only that pet's tasks."""
    owner = Owner(name="Jordan", available_minutes_per_day=240)
    mochi = Pet(name="Mochi", species="dog", age=3)
    luna  = Pet(name="Luna",  species="cat", age=5)
    owner.add_pet(mochi)
    owner.add_pet(luna)
    mochi.add_task(make_task(title="Walk",  category="walk"))
    luna.add_task( make_task(title="Meds",  category="meds"))
    scheduler = Scheduler(owner=owner)

    result = scheduler.filter_tasks(pet_name="Mochi")
    assert all(pet.name == "Mochi" for pet, _ in result)
    assert len(result) == 1


def test_filter_pending_excludes_completed():
    """filter_tasks(status='pending') omits completed tasks."""
    scheduler, _, pet = make_scheduler()
    t1 = make_task(title="Walk")
    t2 = make_task(title="Feed", category="feed")
    pet.add_task(t1)
    pet.add_task(t2)
    t1.mark_complete()

    pending = scheduler.filter_tasks(status="pending")
    titles = [task.title for _, task in pending]
    assert "Walk" not in titles
    assert "Feed" in titles


def test_filter_completed_excludes_pending():
    """filter_tasks(status='completed') omits incomplete tasks."""
    scheduler, _, pet = make_scheduler()
    t1 = make_task(title="Walk")
    t2 = make_task(title="Feed", category="feed")
    pet.add_task(t1)
    pet.add_task(t2)
    t1.mark_complete()

    completed = scheduler.filter_tasks(status="completed")
    titles = [task.title for _, task in completed]
    assert "Walk" in titles
    assert "Feed" not in titles


def test_filter_pet_with_no_tasks():
    """Filtering for a pet that has no tasks returns an empty list."""
    owner = Owner(name="Jordan", available_minutes_per_day=240)
    empty_pet = Pet(name="Buddy", species="rabbit", age=1)
    owner.add_pet(empty_pet)
    scheduler = Scheduler(owner=owner)

    result = scheduler.filter_tasks(pet_name="Buddy")
    assert result == []


# ---------------------------------------------------------------------------
# Recurring tasks
# ---------------------------------------------------------------------------

def test_daily_task_creates_next_day_occurrence():
    """mark_task_complete() on a daily task adds a new task due tomorrow."""
    scheduler, _, pet = make_scheduler()
    today = date.today()
    task  = make_task(title="Walk", frequency="daily", due_date=today)
    pet.add_task(task)

    next_task = scheduler.mark_task_complete(pet, task)

    assert task.completed is True
    assert next_task is not None
    assert next_task.due_date == today + timedelta(days=1)
    assert next_task.title == task.title
    assert len(pet.tasks) == 2


def test_weekly_task_creates_next_week_occurrence():
    """mark_task_complete() on a weekly task adds a new task due in 7 days."""
    scheduler, _, pet = make_scheduler()
    today = date.today()
    task  = make_task(title="Grooming", frequency="weekly", due_date=today)
    pet.add_task(task)

    next_task = scheduler.mark_task_complete(pet, task)

    assert next_task is not None
    assert next_task.due_date == today + timedelta(weeks=1)


def test_as_needed_task_does_not_recur():
    """mark_task_complete() on an as-needed task creates no new occurrence."""
    scheduler, _, pet = make_scheduler()
    task = make_task(title="Vet visit", frequency="as-needed")
    pet.add_task(task)

    next_task = scheduler.mark_task_complete(pet, task)

    assert task.completed is True
    assert next_task is None
    assert len(pet.tasks) == 1   # no new task appended


def test_recurring_task_inherits_all_fields():
    """The auto-created next occurrence copies title, duration, priority, etc."""
    scheduler, _, pet = make_scheduler()
    task = make_task(
        title="Meds", duration_minutes=5, priority="high",
        category="meds", frequency="daily", time="08:00",
    )
    pet.add_task(task)

    next_task = scheduler.mark_task_complete(pet, task)

    assert next_task.title            == task.title
    assert next_task.duration_minutes == task.duration_minutes
    assert next_task.priority         == task.priority
    assert next_task.category         == task.category
    assert next_task.time             == task.time
    assert next_task.completed        is False   # new task starts incomplete


# ---------------------------------------------------------------------------
# Conflict detection
# ---------------------------------------------------------------------------

def test_conflict_same_time_detected():
    """Two pending tasks at identical HH:MM produce a same-time warning."""
    scheduler, _, pet = make_scheduler()
    pet.add_task(make_task(title="Task A", time="08:00"))
    pet.add_task(make_task(title="Task B", time="08:00", category="feed"))

    conflicts = scheduler.get_conflicts()
    assert any("08:00" in c for c in conflicts)


def test_no_conflict_different_times():
    """Tasks at different times produce no same-time conflict warning."""
    scheduler, _, pet = make_scheduler()
    pet.add_task(make_task(title="Walk", time="08:00"))
    pet.add_task(make_task(title="Feed", time="12:00", category="feed"))

    conflicts = scheduler.get_conflicts()
    # no same-time warning — there may be other conflicts (duplicate category
    # is not the case here) but none should mention a time collision
    assert not any("WARNING" in c for c in conflicts)


def test_conflict_duplicate_category_same_pet():
    """A pet with two pending tasks in the same category triggers a warning."""
    scheduler, _, pet = make_scheduler()
    pet.add_task(make_task(title="Morning walk", category="walk", time="08:00"))
    pet.add_task(make_task(title="Evening walk", category="walk", time="18:00"))

    conflicts = scheduler.get_conflicts()
    assert any("walk" in c for c in conflicts)


def test_conflict_budget_overflow():
    """Total pending time exceeding the daily budget triggers an overflow warning."""
    scheduler, _, pet = make_scheduler(available_minutes=30)
    pet.add_task(make_task(title="Long walk", duration_minutes=60))

    conflicts = scheduler.get_conflicts()
    assert any("exceeds daily budget" in c for c in conflicts)


def test_no_conflicts_on_empty_schedule():
    """A pet with no tasks produces no conflict warnings."""
    scheduler, *_ = make_scheduler()
    assert scheduler.get_conflicts() == []


def test_completed_tasks_ignored_by_conflict_checker():
    """Completed same-time tasks are not flagged as conflicts."""
    scheduler, owner, pet = make_scheduler()
    t1 = make_task(title="Task A", time="08:00")
    t2 = make_task(title="Task B", time="08:00", category="feed")
    t1.mark_complete()
    pet.add_task(t1)
    pet.add_task(t2)

    conflicts = scheduler.get_conflicts()
    # only t2 is pending — no pair to collide with
    assert not any("WARNING" in c for c in conflicts)


# ---------------------------------------------------------------------------
# Schedule generation
# ---------------------------------------------------------------------------

def test_generate_schedule_fits_within_budget():
    """Scheduled tasks never exceed the owner's daily time budget."""
    scheduler, owner, pet = make_scheduler(available_minutes=60)
    pet.add_task(make_task(title="Walk",     duration_minutes=30, time="08:00"))
    pet.add_task(make_task(title="Feed",     duration_minutes=10, category="feed", time="09:00"))
    pet.add_task(make_task(title="Grooming", duration_minutes=45, category="grooming", time="10:00"))

    scheduler.generate_schedule()
    total = sum(st.duration() for st in scheduler.schedule)
    assert total <= owner.available_minutes_per_day


def test_excluded_tasks_do_not_fit():
    """Tasks that did not fit are stored in scheduler.excluded."""
    scheduler, owner, pet = make_scheduler(available_minutes=20)
    pet.add_task(make_task(title="Short",  duration_minutes=10, time="08:00"))
    pet.add_task(make_task(title="Long",   duration_minutes=60, category="feed", time="09:00"))

    scheduler.generate_schedule()
    excluded_titles = [st.task.title for st in scheduler.excluded]
    assert "Long" in excluded_titles
