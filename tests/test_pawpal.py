import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from pawpal_system import Task, Pet


def make_task(**overrides):
    """Return a default Task, with any field overridable."""
    defaults = dict(
        title="Morning walk",
        duration_minutes=30,
        priority="high",
        category="walk",
        frequency="daily",
    )
    defaults.update(overrides)
    return Task(**defaults)


# ---------------------------------------------------------------------------
# Test 1: mark_complete() sets completed to True
# ---------------------------------------------------------------------------

def test_mark_complete_sets_completed_true():
    task = make_task()
    assert task.completed is False          # starts incomplete
    task.mark_complete()
    assert task.completed is True           # flipped after calling mark_complete()


# ---------------------------------------------------------------------------
# Test 2: adding a task to a Pet increases the pet's task count
# ---------------------------------------------------------------------------

def test_add_task_increases_pet_task_count():
    pet = Pet(name="Mochi", species="dog", age=3)
    assert len(pet.tasks) == 0             # starts with no tasks
    pet.add_task(make_task(title="Breakfast", category="feed"))
    assert len(pet.tasks) == 1             # one task added
    pet.add_task(make_task(title="Evening walk"))
    assert len(pet.tasks) == 2             # second task added
