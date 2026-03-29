from pawpal_system import Owner, Pet, Task, Scheduler

# --- Setup ---
jordan = Owner(name="Jordan", available_minutes_per_day=90)

mochi = Pet(name="Mochi", species="dog", age=3)
luna  = Pet(name="Luna",  species="cat", age=5)

jordan.add_pet(mochi)
jordan.add_pet(luna)

# --- Mochi's tasks ---
mochi.add_task(Task(title="Morning walk",   duration_minutes=30, priority="high",   category="walk",       frequency="daily"))
mochi.add_task(Task(title="Breakfast",      duration_minutes=10, priority="high",   category="feed",       frequency="daily"))
mochi.add_task(Task(title="Grooming brush", duration_minutes=20, priority="low",    category="grooming",   frequency="weekly"))

# --- Luna's tasks ---
luna.add_task(Task(title="Breakfast",       duration_minutes=5,  priority="high",   category="feed",       frequency="daily"))
luna.add_task(Task(title="Medication",      duration_minutes=5,  priority="high",   category="meds",       frequency="daily"))
luna.add_task(Task(title="Enrichment play", duration_minutes=25, priority="medium", category="enrichment", frequency="daily"))

# --- Schedule ---
scheduler = Scheduler(owner=jordan)
scheduler.generate_schedule()

print(scheduler.explain_plan())
