import streamlit as st
from pawpal_system import Owner, Pet, Task, Scheduler

st.set_page_config(page_title="PawPal+", page_icon="🐾", layout="centered")

st.title("🐾 PawPal+")

# ---------------------------------------------------------------------------
# Session state initialisation
# ---------------------------------------------------------------------------

if "owner" not in st.session_state:
    st.session_state.owner     = Owner(name="", available_minutes_per_day=90)
    st.session_state.pets      = {}
    st.session_state.scheduler = None

# ---------------------------------------------------------------------------
# Section 1: Owner profile
# ---------------------------------------------------------------------------

st.subheader("Owner Profile")

with st.form("profile_form"):
    owner_name    = st.text_input("Your name", value=st.session_state.owner.name,
                                  placeholder="e.g. Jordan")
    available_min = st.number_input(
        "Time available today (minutes)",
        min_value=10, max_value=480,
        value=st.session_state.owner.available_minutes_per_day,
    )
    save_profile = st.form_submit_button("Save profile")

if save_profile:
    name = owner_name.strip()
    if not name:
        st.error("Please enter your name.")
    else:
        st.session_state.owner.name                     = name
        st.session_state.owner.available_minutes_per_day = int(available_min)
        st.session_state.scheduler = None
        st.success(f"Profile saved: {name}, {int(available_min)} min/day.")

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
        st.session_state.scheduler  = None
        st.success(f"Added {name} the {new_species}!")

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
    # Task list — sorted by time, with filters and mark-complete buttons
    # ------------------------------------------------------------------
    all_tasks = st.session_state.owner.get_all_tasks()
    if all_tasks:
        st.markdown("**Current tasks** *(sorted by scheduled time)*")

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

        # Build a temporary scheduler to access sort_by_time()
        temp_sched = Scheduler(owner=st.session_state.owner)

        # Sort all tasks chronologically, then apply UI filters
        sorted_all = temp_sched.sort_by_time(all_tasks)
        filtered = [
            (pet, task) for pet, task in sorted_all
            if (pet_filter   == "All" or pet.name == pet_filter)
            and (status_filter == "All"
                 or (status_filter == "Pending"   and not task.completed)
                 or (status_filter == "Completed" and task.completed))
        ]

        if filtered:
            h = st.columns([2, 3, 1, 1, 1, 1, 1])
            for col, label in zip(h, ["Pet", "Task", "Min", "Priority", "Freq", "HH:MM", "Action"]):
                col.markdown(f"**{label}**")

            for i, (pet, task) in enumerate(filtered):
                c = st.columns([2, 3, 1, 1, 1, 1, 1])
                status_icon = "✅" if task.completed else "⏳"
                c[0].write(pet.name)
                c[1].write(f"{status_icon} {task.title}")
                c[2].write(task.duration_minutes)
                c[3].write(task.priority)
                c[4].write(task.frequency)
                c[5].write(task.time)

                btn_key = f"btn_{pet.name}_{task.title}_{i}"
                if not task.completed:
                    if c[6].button("Done", key=btn_key):
                        # Use mark_task_complete so recurring tasks auto-spawn
                        action_sched = Scheduler(owner=st.session_state.owner)
                        next_task    = action_sched.mark_task_complete(pet, task)
                        st.session_state.scheduler = None
                        if next_task:
                            st.toast(
                                f"'{task.title}' done! Next {task.frequency} occurrence "
                                f"scheduled for {next_task.due_date}.",
                                icon="🔁",
                            )
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
    # --- Conflict detection — shown before the user generates ---
    check_sched = Scheduler(owner=st.session_state.owner)
    conflicts   = check_sched.get_conflicts()

    if conflicts:
        with st.expander(f"⚠️ {len(conflicts)} scheduling conflict(s) detected — click to review", expanded=True):
            for msg in conflicts:
                if msg.startswith("WARNING"):
                    # Same-time collision — most urgent
                    st.error(f"🕐 **Same-time clash:** {msg.removeprefix('WARNING: ')}")
                elif "exceeds daily budget" in msg:
                    # Budget overflow
                    st.warning(f"⏱️ **Budget overflow:** {msg}")
                else:
                    # Duplicate category
                    st.warning(f"📋 **Duplicate category:** {msg}")
            st.caption(
                "Resolve conflicts by adjusting task times or removing duplicates above. "
                "The scheduler will still run but may defer lower-priority tasks."
            )
    else:
        st.success("No scheduling conflicts detected.")

    if st.button("Generate schedule"):
        scheduler = Scheduler(owner=st.session_state.owner)
        scheduler.generate_schedule()
        st.session_state.scheduler = scheduler

    if st.session_state.scheduler is not None:
        sched = st.session_state.scheduler

        # Summary metrics
        used      = sched.owner.available_minutes_per_day - sched.get_remaining_time()
        budget    = sched.owner.available_minutes_per_day
        remaining = sched.get_remaining_time()
        deferred  = len(sched.excluded)

        m1, m2, m3, m4 = st.columns(4)
        m1.metric("Tasks scheduled", len(sched.schedule))
        m2.metric("Tasks deferred",  deferred)
        m3.metric("Time used (min)", used)
        m4.metric("Time left (min)", remaining)

        if sched.schedule:
            st.markdown("**Schedule:**")
            rows = []
            for st_item in sched.schedule:
                sh, sm = divmod(st_item.start_time, 60)
                eh, em = divmod(st_item.end_time, 60)
                rows.append({
                    "Time":     f"{sh:02d}:{sm:02d} – {eh:02d}:{em:02d}",
                    "Task":     st_item.task.title,
                    "Pet":      st_item.pet.name,
                    "Priority": st_item.task.priority,
                    "Freq":     st_item.task.frequency,
                    "Min":      st_item.task.duration_minutes,
                })
            st.table(rows)

        if sched.excluded:
            with st.expander(f"Deferred tasks ({deferred})"):
                for ex in sched.excluded:
                    st.markdown(
                        f"- **{ex.task.title}** ({ex.pet.name}) — "
                        f"{ex.task.duration_minutes} min [{ex.task.priority}] — *{ex.reason}*"
                    )
