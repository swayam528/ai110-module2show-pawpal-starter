import streamlit as st
from pawpal_system import Owner, Pet, Task, Scheduler

st.set_page_config(page_title="PawPal+", page_icon="🐾", layout="centered")

st.title("🐾 PawPal+")

# ---------------------------------------------------------------------------
# Session state initialisation
#
# st.session_state works like a dictionary that survives across reruns.
# The pattern:
#     if "key" not in st.session_state:
#         st.session_state["key"] = <initial value>
# ensures we only create the object once (on the very first load).
# Every subsequent rerun finds the key already present and skips the block,
# so the stored Owner — including any pets or tasks added — is preserved.
# ---------------------------------------------------------------------------

if "owner" not in st.session_state:
    default_owner = Owner(name="Jordan", available_minutes_per_day=90)
    default_pet   = Pet(name="Mochi", species="dog", age=3)
    default_owner.add_pet(default_pet)
    st.session_state.owner = default_owner
    st.session_state.pets  = {"Mochi": default_pet}
    st.session_state.scheduler = None

# ---------------------------------------------------------------------------
# Section 1: Owner + pet profile
# ---------------------------------------------------------------------------

st.subheader("Owner & Pet Profile")

with st.form("profile_form"):
    owner_name    = st.text_input("Your name", value="Jordan")
    available_min = st.number_input("Time available today (minutes)", min_value=10, max_value=480, value=90)
    pet_name      = st.text_input("Pet name", value="Mochi")
    species       = st.selectbox("Species", ["dog", "cat", "rabbit", "other"])
    age           = st.number_input("Pet age (years)", min_value=0, max_value=30, value=3)
    save_profile  = st.form_submit_button("Save profile")

if save_profile:
    owner = Owner(name=owner_name, available_minutes_per_day=int(available_min))
    pet   = Pet(name=pet_name, species=species, age=int(age))
    owner.add_pet(pet)

    st.session_state.owner = owner
    st.session_state.pets  = {pet_name: pet}
    st.session_state.scheduler = None
    st.success(f"Profile saved: {owner_name} with {pet_name} the {species}.")

# ---------------------------------------------------------------------------
# Section 1b: Add a pet
# ---------------------------------------------------------------------------

st.divider()
st.subheader("Add a Pet")

with st.form("add_pet_form"):
    new_pet_name = st.text_input("Pet name")
    new_species  = st.selectbox("Species", ["dog", "cat", "rabbit", "other"], key="new_species")
    new_age      = st.number_input("Age (years)", min_value=0, max_value=30, value=1, key="new_age")
    add_pet_btn  = st.form_submit_button("Add pet")

if add_pet_btn:
    name = new_pet_name.strip()
    if not name:
        st.error("Please enter a pet name.")
    elif name in st.session_state.pets:
        st.error(f'A pet named "{name}" is already registered.')
    else:
        new_pet = Pet(name=name, species=new_species, age=int(new_age))
        st.session_state.owner.add_pet(new_pet)
        st.session_state.pets[name] = new_pet
        st.session_state.scheduler = None
        st.success(f'Added {name} the {new_species}!')

if st.session_state.pets:
    st.markdown("**Registered pets:**")
    for pet in st.session_state.owner.pets:
        pending = len(pet.get_pending_tasks())
        total   = len(pet.tasks)
        st.markdown(f"- **{pet.name}** ({pet.species}, age {pet.age}) — {pending}/{total} tasks pending")

# ---------------------------------------------------------------------------
# Section 2: Add tasks
# ---------------------------------------------------------------------------

st.divider()
st.subheader("Add a Care Task")

if st.session_state.owner is None:
    st.info("Save a profile above before adding tasks.")
else:
    pet_options = list(st.session_state.pets.keys())

    with st.form("task_form"):
        selected_pet   = st.selectbox("Which pet?", pet_options)
        task_title     = st.text_input("Task title", value="Morning walk")
        duration       = st.number_input("Duration (minutes)", min_value=1, max_value=240, value=20)
        priority       = st.selectbox("Priority", ["high", "medium", "low"])
        category       = st.selectbox("Category", ["walk", "feed", "meds", "grooming", "enrichment", "other"])
        frequency      = st.selectbox("Frequency", ["daily", "weekly", "as-needed"])
        preferred_time = st.selectbox("Preferred time of day", ["any", "morning", "afternoon", "evening"])
        task_time      = st.text_input("Start time (HH:MM, 24-hr)", value="08:00")
        add_task       = st.form_submit_button("Add task")

    if add_task:
        task = Task(
            title=task_title,
            duration_minutes=int(duration),
            priority=priority,
            category=category,
            frequency=frequency,
            preferred_time=preferred_time,
            time=task_time,
        )
        st.session_state.pets[selected_pet].add_task(task)
        st.session_state.scheduler = None
        st.success(f"Added '{task_title}' to {selected_pet}.")

    # ------------------------------------------------------------------
    # Task list with filters and mark-complete buttons
    # ------------------------------------------------------------------
    all_tasks = st.session_state.owner.get_all_tasks()
    if all_tasks:
        st.markdown("**Current tasks:**")

        # Filter controls
        col_f1, col_f2 = st.columns(2)
        with col_f1:
            pet_filter = st.selectbox(
                "Filter by pet",
                ["All"] + list(st.session_state.pets.keys()),
                key="pet_filter",
            )
        with col_f2:
            status_filter = st.selectbox(
                "Filter by status",
                ["All", "Pending", "Completed"],
                key="status_filter",
            )

        # Apply filters
        filtered = []
        for pet, task in all_tasks:
            if pet_filter != "All" and pet.name != pet_filter:
                continue
            if status_filter == "Pending" and task.completed:
                continue
            if status_filter == "Completed" and not task.completed:
                continue
            filtered.append((pet, task))

        if filtered:
            # Column headers
            h = st.columns([2, 3, 1, 1, 1, 1, 1])
            for col, label in zip(h, ["Pet", "Task", "Min", "Priority", "Category", "HH:MM", "Action"]):
                col.markdown(f"**{label}**")

            for i, (pet, task) in enumerate(filtered):
                c = st.columns([2, 3, 1, 1, 1, 1, 1])
                status_icon = "✅" if task.completed else "⏳"
                c[0].write(pet.name)
                c[1].write(f"{status_icon} {task.title}")
                c[2].write(task.duration_minutes)
                c[3].write(task.priority)
                c[4].write(task.category)
                c[5].write(task.time)

                btn_key = f"btn_{pet.name}_{task.title}_{i}"
                if not task.completed:
                    if c[6].button("Done", key=btn_key):
                        task.mark_complete()
                        st.session_state.scheduler = None
                        st.rerun()
                else:
                    if c[6].button("Reset", key=btn_key):
                        task.reset()
                        st.session_state.scheduler = None
                        st.rerun()
        else:
            st.info("No tasks match the current filters.")
    else:
        st.info("No tasks yet. Add one above.")

# ---------------------------------------------------------------------------
# Section 3: Generate schedule
# ---------------------------------------------------------------------------

st.divider()
st.subheader("Build Today's Schedule")

if st.session_state.owner is None:
    st.info("Save a profile and add tasks before generating a schedule.")
else:
    # --- Conflict detection (runs before schedule generation) ---
    temp_scheduler = Scheduler(owner=st.session_state.owner)
    conflicts = temp_scheduler.get_conflicts()
    if conflicts:
        st.warning("**Schedule warnings detected:**")
        for msg in conflicts:
            st.warning(f"• {msg}")

    if st.button("Generate schedule"):
        scheduler = Scheduler(owner=st.session_state.owner)
        scheduler.generate_schedule()
        st.session_state.scheduler = scheduler

    if st.session_state.scheduler is not None:
        sched = st.session_state.scheduler
        st.text(sched.explain_plan())
