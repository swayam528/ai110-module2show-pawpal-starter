from datetime import date
from pawpal_system import Owner, Pet, Task, Scheduler

# ---------------------------------------------------------------------------
# Setup
# ---------------------------------------------------------------------------

jordan = Owner(name="Jordan", available_minutes_per_day=120)

mochi = Pet(name="Mochi", species="dog", age=3)
luna  = Pet(name="Luna",  species="cat", age=5)

jordan.add_pet(mochi)
jordan.add_pet(luna)

# ---------------------------------------------------------------------------
# Tasks added INTENTIONALLY OUT OF ORDER to demonstrate sort_by_time()
# Notice the times jump around: 19:00, 07:30, 12:00, 08:00, 17:00, 09:00
# ---------------------------------------------------------------------------

mochi.add_task(Task(
    title="Evening walk",
    duration_minutes=20, priority="medium", category="walk",
    frequency="daily", preferred_time="evening", time="19:00",
))
mochi.add_task(Task(
    title="Breakfast",
    duration_minutes=10, priority="high",   category="feed",
    frequency="daily", preferred_time="morning", time="07:30",
))
mochi.add_task(Task(
    title="Grooming brush",
    duration_minutes=15, priority="low",    category="grooming",
    frequency="weekly", preferred_time="afternoon", time="12:00",
))

luna.add_task(Task(
    title="Medication",
    duration_minutes=5,  priority="high",   category="meds",
    frequency="daily", preferred_time="morning", time="08:00",
))
luna.add_task(Task(
    title="Enrichment play",
    duration_minutes=25, priority="medium", category="enrichment",
    frequency="daily", preferred_time="evening", time="17:00",
))
luna.add_task(Task(
    title="Lunch",
    duration_minutes=5,  priority="high",   category="feed",
    frequency="daily", preferred_time="afternoon", time="09:00",
))

scheduler = Scheduler(owner=jordan)

# ---------------------------------------------------------------------------
# 1. Demonstrate sort_by_time()
#    Tasks were added out of order above — sort_by_time() returns them in
#    chronological order using a lambda key on the HH:MM time field.
# ---------------------------------------------------------------------------

print("=" * 60)
print("  TASKS SORTED BY TIME  (added out of order above)")
print("=" * 60)
all_tasks = jordan.get_all_tasks()
sorted_tasks = scheduler.sort_by_time(all_tasks)
for pet, task in sorted_tasks:
    status = "[done]" if task.completed else "[ ]"
    print(
        f"  {status}  {task.time}  {task.title:<20}  "
        f"({pet.name})  [{task.priority}]  [{task.frequency}]"
    )

# ---------------------------------------------------------------------------
# 2. Demonstrate filter_tasks()
#    Filter by pet name, then by completion status.
# ---------------------------------------------------------------------------

print()
print("=" * 60)
print("  FILTER: Mochi's tasks only")
print("=" * 60)
for pet, task in scheduler.filter_tasks(pet_name="Mochi"):
    print(f"  {task.time}  {task.title}  [{task.priority}]")

print()
print("=" * 60)
print("  FILTER: All PENDING tasks (none completed yet)")
print("=" * 60)
for pet, task in scheduler.filter_tasks(status="pending"):
    print(f"  {task.time}  {task.title:<20}  ({pet.name})")

# Mark a couple tasks complete to show the status filter working
mochi.tasks[1].mark_complete()   # Breakfast
luna.tasks[0].mark_complete()    # Medication

print()
print("=" * 60)
print("  FILTER: COMPLETED tasks  (after marking 2 done)")
print("=" * 60)
for pet, task in scheduler.filter_tasks(status="completed"):
    print(f"  [done]  {task.time}  {task.title:<20}  ({pet.name})")

print()
print("=" * 60)
print("  FILTER: PENDING tasks  (after marking 2 done)")
print("=" * 60)
for pet, task in scheduler.filter_tasks(status="pending"):
    print(f"  [ ]  {task.time}  {task.title:<20}  ({pet.name})")

# ---------------------------------------------------------------------------
# 3. Generate and print today's schedule (uses the same sort logic internally)
# ---------------------------------------------------------------------------

print()
scheduler.generate_schedule()
print(scheduler.explain_plan())

# ---------------------------------------------------------------------------
# 4. Demonstrate recurring tasks
#    Mark Mochi's "Breakfast" complete via mark_task_complete().
#    Because it is a "daily" task, a new occurrence is auto-created for
#    tomorrow (today + 1 day via timedelta).
# ---------------------------------------------------------------------------

print("=" * 60)
print("  RECURRING TASKS DEMO")
print("=" * 60)

breakfast_task = mochi.tasks[1]   # "Breakfast"
print(f"  Before: Mochi has {len(mochi.tasks)} task(s), "
      f'"{breakfast_task.title}" due {breakfast_task.due_date}, '
      f"completed={breakfast_task.completed}")

next_breakfast = scheduler.mark_task_complete(mochi, breakfast_task)

print(f"  After:  Mochi has {len(mochi.tasks)} task(s)")
if next_breakfast:
    print(f"  New recurring task created: "
          f'"{next_breakfast.title}" due {next_breakfast.due_date} '
          f"(tomorrow, auto-scheduled by timedelta)")

# ---------------------------------------------------------------------------
# 5. Demonstrate same-time conflict detection
#    Add two tasks deliberately set to the same time "08:00".
# ---------------------------------------------------------------------------

print()
print("=" * 60)
print("  CONFLICT DETECTION DEMO")
print("=" * 60)

conflict_task_1 = Task(
    title="Morning meds",
    duration_minutes=5, priority="high", category="meds",
    frequency="daily", preferred_time="morning", time="08:00",
    due_date=date.today(),
)
conflict_task_2 = Task(
    title="Morning weigh-in",
    duration_minutes=5, priority="medium", category="enrichment",
    frequency="daily", preferred_time="morning", time="08:00",
    due_date=date.today(),
)
scheduler.add_task(luna, conflict_task_1)
scheduler.add_task(luna, conflict_task_2)

warnings = scheduler.get_conflicts()
if warnings:
    print("  Conflicts detected:")
    for w in warnings:
        print(f"    [!] {w}")
else:
    print("  No conflicts detected.")
