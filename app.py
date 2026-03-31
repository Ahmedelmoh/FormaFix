"""
app.py — FormaFix
=================
Main Flet application with all pages:
1. Authentication (Sign up/Login)
2. Dashboard (Welcome if no plan, or show recent plan)
3. Agent (Conversational plan creation)
4. Training (Live exercise tracking)
5. Plans (View all saved plans)
6. History (Training history)
"""

import flet as ft
from datetime import datetime
from api_client import APIClient, APIClientError


class FormaFixApp:
    """Main application controller."""

    def __init__(self):
        self.api = APIClient()

        self.current_user = None
        self.current_plan = None
        self.current_page = "auth"
        self.agent_session_id = None

    def run(self):
        """Run the Flet app."""
        def main(page: ft.Page):
            page.title = "FormaFix — Rehabilitation Companion"
            page.window.width = 400
            page.window.height = 800

            # Container to hold current page
            self.page = page
            self.main_container = ft.Container(expand=True)

            # Show auth page initially
            self.show_auth_page()

            page.add(self.main_container)

        ft.app(target=main)

    # ── Navigation ───────────────────────────────────────────────────────

    def navigate(self, page_name: str):
        """Navigate to a page."""
        self.current_page = page_name
        if page_name == "auth":
            self.show_auth_page()
        elif page_name == "dashboard":
            self.show_dashboard_page()
        elif page_name == "agent":
            self.show_agent_page()
        elif page_name == "training":
            self.show_training_page()
        elif page_name == "plans":
            self.show_plans_page()
        elif page_name == "history":
            self.show_history_page()

    # ── Auth Page ────────────────────────────────────────────────────────

    def show_auth_page(self):
        """Show authentication page (sign up / login)."""
        # State for toggling between login and signup
        auth_mode = ["login"]  # Use list to make it mutable in nested functions
        
        # Login form fields
        login_email = ft.TextField(label="Email", width=300)
        login_password = ft.TextField(label="Password", password=True, width=300)
        
        # Signup form fields
        signup_name = ft.TextField(label="Full Name", width=300)
        signup_email = ft.TextField(label="Email", width=300)
        signup_password = ft.TextField(label="Password", password=True, width=300)
        signup_age = ft.TextField(label="Age", width=300, keyboard_type=ft.KeyboardType.NUMBER)
        
        # Container to hold current form
        form_container = ft.Container()
        
        def login_click(e):
            try:
                result = self.api.login(login_email.value, login_password.value)
                if result.get("success"):
                    self.current_user = result.get("customer")
                    self.navigate("dashboard")
                else:
                    self.show_snackbar(result.get("message", "Login failed"))
            except APIClientError as exc:
                self.show_snackbar(str(exc))

        def signup_click(e):
            # Safely parse age — show error if non-numeric
            age = None
            if signup_age.value and signup_age.value.strip():
                try:
                    age = int(signup_age.value.strip())
                except ValueError:
                    self.show_snackbar("Age must be a number")
                    return

            try:
                result = self.api.register(
                    signup_name.value,
                    signup_email.value,
                    signup_password.value,
                    age,
                )
                if not result.get("success"):
                    self.show_snackbar(result.get("message", "Registration failed"))
                    return

                login_result = self.api.login(signup_email.value, signup_password.value)
                if not login_result.get("success"):
                    self.show_snackbar("Account created. Please login manually.")
                    toggle_to_login(None)
                    return

                self.current_user = login_result.get("customer")
                self.navigate("dashboard")
            except APIClientError as exc:
                self.show_snackbar(str(exc))

        def toggle_to_signup(e):
            auth_mode[0] = "signup"
            update_form()

        def toggle_to_login(e):
            auth_mode[0] = "login"
            update_form()

        def update_form():
            if auth_mode[0] == "login":
                form_container.content = ft.Column([
                    ft.Text("Login to FormaFix", size=24, weight="bold"),
                    login_email,
                    login_password,
                    ft.ElevatedButton("Login", on_click=login_click, width=300),
                    ft.Container(height=10),
                    ft.Row([
                        ft.Text("Don't have an account?", size=12),
                        ft.TextButton("Sign Up", on_click=toggle_to_signup)
                    ], spacing=5)
                ], alignment=ft.MainAxisAlignment.CENTER, horizontal_alignment=ft.CrossAxisAlignment.CENTER, spacing=15)
            else:
                form_container.content = ft.Column([
                    ft.Text("Create FormaFix Account", size=24, weight="bold"),
                    signup_name,
                    signup_email,
                    signup_password,
                    signup_age,
                    ft.ElevatedButton("Sign Up", on_click=signup_click, width=300),
                    ft.Container(height=10),
                    ft.Row([
                        ft.Text("Already have an account?", size=12),
                        ft.TextButton("Login", on_click=toggle_to_login)
                    ], spacing=5)
                ], alignment=ft.MainAxisAlignment.CENTER, horizontal_alignment=ft.CrossAxisAlignment.CENTER, spacing=15)
            self.page.update()

        # Initialize form
        update_form()

        self.main_container.content = form_container

    # ── Dashboard Page ───────────────────────────────────────────────────

    def show_dashboard_page(self):
        """Show dashboard (main page with recent plan or welcome)."""
        try:
            latest_plan = self.api.get_latest_plan(self.current_user["id"])
        except APIClientError as exc:
            self.show_snackbar(str(exc))
            latest_plan = None

        if not latest_plan:
            # Welcome page
            content = ft.Column([
                ft.Text("Welcome to FormaFix!", size=28, weight="bold"),
                ft.Text(f"Hi {self.current_user['name']}", size=18),
                ft.Text("Get started by creating a rehabilitation plan with our AI agent.", size=14),
                ft.Container(height=40),
                ft.ElevatedButton(
                    "Create Plan with Agent",
                    width=250,
                    on_click=lambda e: self.navigate("agent")
                ),
                ft.Container(height=200),
                ft.Row([
                    ft.IconButton(icon=ft.Icons.PERSON, on_click=lambda e: self.show_snackbar("Profile feature coming soon")),
                    ft.IconButton(icon=ft.Icons.LOGOUT, on_click=lambda e: (self.logout(), self.navigate("auth"))),
                ])
            ], horizontal_alignment=ft.CrossAxisAlignment.CENTER, spacing=20)
        else:
            # Show recent plan
            self.current_plan = latest_plan
            plan_data = latest_plan["plan"]
            plan = plan_data.get("plan", plan_data)
            weeks = plan.get("weeks", [])

            def go_to_training():
                self.navigate("training")

            plan_table = ft.DataTable(
                columns=[
                    ft.DataColumn(ft.Text("Week")),
                    ft.DataColumn(ft.Text("Focus")),
                    ft.DataColumn(ft.Text("Days")),
                ],
                rows=[]
            )

            for week in weeks[:4]:
                try:
                    plan_table.rows.append(ft.DataRow(cells=[
                        ft.DataCell(ft.Text(str(week.get("week")))),
                        ft.DataCell(ft.Text(week.get("focus", "")[:20])),
                        ft.DataCell(ft.Text(f"Days: {len(week.get('days', []))}")),
                    ]))
                except:
                    pass

            content = ft.Column([
                ft.Text(f"Welcome, {self.current_user['name']}!", size=24, weight="bold"),
                ft.Divider(),
                ft.Text("Your Current Plan", size=18, weight="bold"),
                ft.Text(f"Injury: {latest_plan.get('injury_type', 'N/A')}", size=12),
                ft.Text(f"Goal: {latest_plan.get('goal', 'N/A')}", size=12),
                ft.Text(f"Created: {latest_plan.get('created_at', 'N/A')}", size=10),
                ft.Divider(),
                ft.Text("Weekly Schedule", size=14, weight="bold"),
                plan_table,
                ft.Container(height=20),
                ft.Row([
                    ft.ElevatedButton("Start Training", width=150, on_click=lambda e: go_to_training()),
                    ft.ElevatedButton("New Plan", width=150, on_click=lambda e: self.navigate("agent")),
                ]),
                ft.Divider(),
                ft.Row([
                    ft.IconButton(icon=ft.Icons.HISTORY, on_click=lambda e: self.navigate("history")),
                    ft.IconButton(icon=ft.Icons.BOOKMARK, on_click=lambda e: self.navigate("plans")),
                    ft.IconButton(icon=ft.Icons.LOGOUT, on_click=lambda e: (self.logout(), self.navigate("auth"))),
                ])
            ], spacing=10, scroll=ft.ScrollMode.AUTO)

        self.main_container.content = ft.Column([
            ft.AppBar(
                title=ft.Text("FormaFix Dashboard"),
                bgcolor="#FF9800",
            ),
            content
        ], expand=True)
        self.page.update()

    # ── Agent Page ───────────────────────────────────────────────────────

    def show_agent_page(self):
        """Show conversational agent page for plan creation."""
        conversation_scroll = ft.Column(scroll=ft.ScrollMode.AUTO, expand=True)
        user_input = ft.TextField(
            label="Your response",
            multiline=True,
            min_lines=2,
            max_lines=4,
            width=350
        )
        sent_messages = []
        received_plan = [False]

        def start_plan_creation():
            """Start the conversation."""
            result = self.api.agent_start(self.current_user["name"])
            self.agent_session_id = result.get("session_id")
            initial_msg = result.get("initial_message", "Let's start your plan.")
            # Add to conversation UI
            add_message(initial_msg, is_user=False)
            user_input.value = ""
            self.page.update()

        def send_message(e):
            """Send user message and get response."""
            if not user_input.value.strip():
                return

            user_msg = user_input.value
            add_message(user_msg, is_user=True)
            user_input.value = ""
            self.page.update()

            # Get AI response
            try:
                if not self.agent_session_id:
                    add_message("⚠️ Agent session not initialized.", is_user=False)
                    self.page.update()
                    return
                result = self.api.agent_continue(self.agent_session_id, user_msg)
                response = result.get("response", "")
                plan_json = result.get("plan_json")
            except Exception as exc:
                add_message(f"⚠️ Error communicating with AI: {exc}", is_user=False)
                self.page.update()
                return

            if plan_json:
                # Plan is ready
                received_plan[0] = True
                add_message("✅ Plan created successfully! Review below:", is_user=False)
                # Save plan
                try:
                    save_result = self.api.save_plan(self.current_user["id"], plan_json)
                    plan_id = save_result.get("plan_id")
                    self.current_plan = {"id": plan_id, "plan": plan_json}
                    add_message("✅ Plan saved! Click 'Go to Dashboard' to start training.", is_user=False)
                except Exception as exc:
                    add_message(f"⚠️ Plan generated but could not be saved: {exc}", is_user=False)
                # Show finish button
                save_btn.visible = True
                finish_btn.visible = True
                finish_btn.text = "Go to Dashboard"
            else:
                add_message(response, is_user=False)

            self.page.update()

        def add_message(msg: str, is_user: bool):
            """Add message to conversation UI."""
            if is_user:
                conversation_scroll.controls.append(
                    ft.Container(
                        content=ft.Text(msg, size=12, color="white"),
                        bgcolor="#2196F3",
                        border_radius=10,
                        padding=10,
                        alignment=ft.Alignment.CENTER_RIGHT,
                        margin=ft.margin.only(left=40, bottom=5)
                    )
                )
            else:
                conversation_scroll.controls.append(
                    ft.Container(
                        content=ft.Text(msg, size=12, color="black"),
                        bgcolor="#EEEEEE",
                        border_radius=10,
                        padding=10,
                        alignment=ft.Alignment.CENTER_LEFT,
                        margin=ft.margin.only(right=40, bottom=5)
                    )
                )

        def finish_plan(e):
            """Finish plan creation and go to dashboard."""
            self.navigate("dashboard")

        save_btn = ft.ElevatedButton("Save Plan", width=150, visible=False, on_click=lambda e: finish_plan(e))
        finish_btn = ft.ElevatedButton("Continue", width=150, visible=False, on_click=lambda e: finish_plan(e))

        # Start conversation immediately
        start_plan_creation()

        self.main_container.content = ft.Column([
            ft.AppBar(
                title=ft.Text("Create Rehabilitation Plan"),
                bgcolor="#1976D2",
            ),
            conversation_scroll,
            ft.Divider(),
            ft.Column([
                user_input,
                ft.Row([
                    ft.ElevatedButton("Send", width=150, on_click=send_message),
                    save_btn,
                    finish_btn
                ]),
                ft.ElevatedButton("Back to Dashboard", width=300, on_click=lambda e: self.navigate("dashboard"))
            ], spacing=10)
        ], expand=True)
        self.page.update()

    # ── Training Page ────────────────────────────────────────────────────

    def show_training_page(self):
        """Auto-detect today's plan and run live monitored training."""
        if not self.current_plan:
            try:
                latest_plan = self.api.get_latest_plan(self.current_user["id"])
            except APIClientError as exc:
                self.show_snackbar(str(exc))
                latest_plan = None
            if latest_plan:
                self.current_plan = latest_plan
            else:
                self.show_snackbar("No plan available. Create one first!")
                self.navigate("dashboard")
                return

        plan_data = self.current_plan["plan"]
        plan = plan_data.get("plan", plan_data)
        weeks = plan.get("weeks", [])

        if not weeks:
            self.show_snackbar("Plan has no training weeks yet.")
            self.navigate("dashboard")
            return

        def normalize_to_int(value):
            """Convert values like 1, '1', 'Day 1', 'week-2' to int when possible."""
            if isinstance(value, int):
                return value
            if value is None:
                return None
            text = str(value).strip()
            if not text:
                return None
            digits = "".join(ch for ch in text if ch.isdigit())
            return int(digits) if digits else None

        def detect_today_assignment():
            """Map today's date to the correct week/day — skips rest days."""
            # Build a flat list of ALL days (including rest days) in order
            all_days = []
            for w in weeks:
                for d in w.get("days", []):
                    all_days.append((w, d))

            if not all_days:
                return None, None, []

            # Determine start date from plan creation
            created_at = self.current_plan.get("created_at")
            start_date = datetime.now().date()
            if created_at:
                try:
                    cleaned = created_at.replace("Z", "")
                    start_date = datetime.fromisoformat(cleaned).date()
                except ValueError:
                    pass

            # How many calendar days since plan started
            elapsed = max(0, (datetime.now().date() - start_date).days)

            # Find today's day slot (no wrap-around — clamp to last day)
            idx = min(elapsed, len(all_days) - 1)
            w, day_item = all_days[idx]

            week_num = normalize_to_int(w.get("week")) or 1
            day_num  = normalize_to_int(day_item.get("day")) or (idx + 1)
            exercises = day_item.get("exercises", [])

            # If today is a rest day, find the next training day
            if not exercises:
                for future_w, future_d in all_days[idx + 1:]:
                    future_ex = future_d.get("exercises", [])
                    if future_ex:
                        week_num  = normalize_to_int(future_w.get("week")) or week_num
                        day_num   = normalize_to_int(future_d.get("day")) or day_num
                        exercises = future_ex
                        break

            return week_num, day_num, exercises

        # ── Use server's next_day endpoint (respects completed days) ──────
        plan_id = self.current_plan.get("id", 0)
        try:
            next_day = self.api.get_next_day(self.current_user["id"], plan_id)
            week_val       = next_day.get("week")
            day_val        = next_day.get("day")
            today_exercises = next_day.get("exercises", [])
            if not today_exercises and next_day.get("focus") == "Plan complete!":
                self._show_plan_complete()
                return
        except Exception as exc:
            # Fallback to local detection
            week_val, day_val, today_exercises = detect_today_assignment()

        # ── Per-exercise flow ──────────────────────────────────────────
        # index[0] tracks which exercise we are currently on
        ex_index = [0]
        session_results = []

        def show_exercise_card(idx: int):
            """Show the pre-exercise screen for exercises[idx]."""
            if idx >= len(today_exercises):
                # All exercises done — show completion screen
                show_completion_screen()
                return

            ex = today_exercises[idx]
            ex_name  = ex.get("name", "Unknown").replace("_", " ").upper()
            ex_sets  = ex.get("sets", 3)
            ex_reps  = ex.get("reps", 10)
            ex_notes = ex.get("notes", "")
            total    = len(today_exercises)

            def start_this_exercise(e):
                """Launch camera for this exercise, then advance to next."""
                target_reps = int(ex.get("reps", 10) or 10)
                # Get injured side from plan
                injury_text = ""
                try:
                    injury_text = (self.current_plan.get("plan", {})
                                   .get("patient", {})
                                   .get("injury", "")).lower()
                except Exception:
                    pass
                injured_side = "right" if "right" in injury_text else "left"

                try:
                    run_result = self.api.run_live_training(
                        exercise_name=ex.get("name"),
                        target_reps=target_reps,
                        injured_side=injured_side,
                    )
                    summary = run_result.get("summary", {})
                except Exception as exc:
                    self.show_snackbar(f"Error: {exc}")
                    summary = {}

                # Save session result
                try:
                    self.api.save_training_session({
                        "customer_id": self.current_user["id"],
                        "plan_id": self.current_plan.get("id", 0),
                        "week": week_val or 1,
                        "day":  day_val  or 1,
                        "exercise_name": ex.get("name"),
                        "score": int(summary.get("avg_score", 0)),
                        "reps":  int(summary.get("reps_completed", summary.get("target_reps", target_reps))),
                        "notes": f"Sets: {ex_sets} | Target reps: {target_reps}",
                        "video_path": None,
                    })
                    session_results.append(summary)
                except APIClientError as exc:
                    self.show_snackbar(f"Could not save: {exc}")

                # Advance to next exercise
                show_exercise_card(idx + 1)

            def skip_exercise(e):
                """Skip this exercise and go to next."""
                show_exercise_card(idx + 1)

            # ── Build per-exercise screen ───────────────────────────────
            # Camera view using MJPEG stream from server
            STREAM_URL = f"{self.api.base}/camera/stream"

            cam_view = ft.Image(
                src=STREAM_URL,
                width=360,
                height=200,
                fit="cover",
                border_radius=ft.border_radius.all(12),
                error_content=ft.Container(
                    content=ft.Column([
                        ft.Icon(ft.Icons.VIDEOCAM_OFF, size=40, color="grey"),
                        ft.Text("Camera will open when you start",
                                size=11, color="grey",
                                text_align=ft.TextAlign.CENTER),
                    ], horizontal_alignment=ft.CrossAxisAlignment.CENTER,
                       spacing=5),
                    bgcolor="#1A1A1A",
                    border_radius=12,
                    width=360, height=200,
                    alignment=ft.Alignment.CENTER
                ),
            )

            self.main_container.content = ft.Column([
                ft.AppBar(
                    title=ft.Text(f"Exercise {idx + 1} of {total}"),
                    bgcolor="#4CAF50",
                    leading=ft.IconButton(
                        icon=ft.Icons.ARROW_BACK,
                        on_click=lambda e: self.navigate("dashboard"),
                    ),
                ),
                ft.Container(expand=True, content=ft.Column([
                    ft.Container(height=10),
                    # Exercise name + info card
                    ft.Container(
                        content=ft.Column([
                            ft.Text(ex_name, size=22, weight="bold",
                                    color="#2196F3",
                                    text_align=ft.TextAlign.CENTER),
                            ft.Text(
                                f"Goal: {ex_sets} Sets x {ex_reps} Reps",
                                size=14, text_align=ft.TextAlign.CENTER,
                            ),
                            ft.Text(
                                ex_notes,
                                size=11, italic=True,
                                text_align=ft.TextAlign.CENTER,
                                color="grey",
                            ) if ex_notes else ft.Container(),
                        ],
                        horizontal_alignment=ft.CrossAxisAlignment.CENTER,
                        spacing=6),
                        bgcolor="#1E1E1E",
                        border_radius=12,
                        padding=ft.padding.symmetric(horizontal=15, vertical=12),
                        margin=ft.margin.symmetric(horizontal=10),
                    ),
                    ft.Container(height=10),
                    # Live camera view
                    ft.Container(
                        content=cam_view,
                        margin=ft.margin.symmetric(horizontal=10),
                        border_radius=12,
                        clip_behavior=ft.ClipBehavior.HARD_EDGE,
                    ),
                    ft.Container(height=10),
                    # Progress dots
                    ft.Row(
                        [ft.Container(
                            width=10, height=10,
                            border_radius=5,
                            bgcolor="#4CAF50" if i <= idx else "#444444",
                        ) for i in range(total)],
                        alignment=ft.MainAxisAlignment.CENTER,
                        spacing=5,
                    ),
                    ft.Container(expand=True),
                    # Start button
                    ft.Container(
                        content=ft.ElevatedButton(
                            content=ft.Row([
                                ft.Icon(ft.Icons.PLAY_ARROW, color="white"),
                                ft.Text("ابدأ التمرين الآن", size=16,
                                        color="white", weight="bold"),
                            ], alignment=ft.MainAxisAlignment.CENTER),
                            width=340,
                            height=55,
                            bgcolor="#4CAF50",
                            on_click=start_this_exercise,
                        ),
                        margin=ft.margin.symmetric(horizontal=10),
                    ),
                    ft.Container(height=6),
                    ft.TextButton(
                        "Skip Exercise",
                        on_click=skip_exercise,
                        style=ft.ButtonStyle(color="grey"),
                    ),
                    ft.Container(height=15),
                ],
                horizontal_alignment=ft.CrossAxisAlignment.CENTER,
                spacing=0,
                expand=True)),
            ], expand=True)
            self.page.update()

        def show_completion_screen():
            """Show session complete screen after all exercises."""
            # Mark this day as completed so it won't repeat
            try:
                plan_id = self.current_plan.get("id", 0)
                if week_val and day_val and plan_id:
                    self.api.mark_day_complete(
                        customer_id=self.current_user["id"],
                        plan_id=plan_id,
                        week=week_val,
                        day=day_val,
                    )
            except Exception as e:
                print(f"[WARN] Could not mark day: {e}")

            total_done = len(session_results)
            scores = [r.get("avg_score", 0) for r in session_results if r.get("avg_score", 0) > 0]
            avg = round(sum(scores) / len(scores)) if scores else 0

            self.main_container.content = ft.Column([
                ft.AppBar(title=ft.Text("Session Complete!"), bgcolor="#4CAF50"),
                ft.Container(expand=True, content=ft.Column([
                    ft.Container(height=40),
                    ft.Icon(ft.Icons.CHECK_CIRCLE, size=80, color="#4CAF50"),
                    ft.Container(height=20),
                    ft.Text("Great Work!", size=28, weight="bold",
                            text_align=ft.TextAlign.CENTER),
                    ft.Text(
                        f"You completed {total_done} exercise(s)",
                        size=16, text_align=ft.TextAlign.CENTER,
                    ),
                    ft.Container(height=10),
                    ft.Container(
                        content=ft.Text(
                            f"Average Score: {avg}/100",
                            size=20, weight="bold", color="#4CAF50",
                            text_align=ft.TextAlign.CENTER,
                        ),
                        bgcolor="#1E1E1E",
                        border_radius=12,
                        padding=15,
                        margin=ft.margin.symmetric(horizontal=30),
                    ),
                    ft.Container(expand=True),
                    ft.ElevatedButton(
                        "View History",
                        width=260,
                        height=50,
                        bgcolor="#2196F3",
                        color="white",
                        on_click=lambda e: self.navigate("history"),
                    ),
                    ft.Container(height=10),
                    ft.ElevatedButton(
                        "Back to Dashboard",
                        width=260,
                        height=50,
                        on_click=lambda e: self.navigate("dashboard"),
                    ),
                    ft.Container(height=30),
                ],
                horizontal_alignment=ft.CrossAxisAlignment.CENTER,
                expand=True)),
            ], expand=True)
            self.page.update()

        # ── Start with first exercise ───────────────────────────────────
        if not today_exercises:
            self.main_container.content = ft.Column([
                ft.AppBar(title=ft.Text("Training Session"), bgcolor="#4CAF50"),
                ft.Container(expand=True, content=ft.Column([
                    ft.Container(height=60),
                    ft.Icon(ft.Icons.EVENT_BUSY, size=60, color="grey"),
                    ft.Text("Rest Day", size=24, weight="bold",
                            text_align=ft.TextAlign.CENTER),
                    ft.Text("No exercises scheduled for today.",
                            size=14, text_align=ft.TextAlign.CENTER, color="grey"),
                    ft.Container(height=40),
                    ft.ElevatedButton("Back to Dashboard", width=260,
                                      on_click=lambda e: self.navigate("dashboard")),
                ],
                horizontal_alignment=ft.CrossAxisAlignment.CENTER,
                expand=True)),
            ], expand=True)
            self.page.update()
            return

        show_exercise_card(0)

    # ── Plans Page ───────────────────────────────────────────────────────

    def show_plans_page(self):
        """Show all saved plans."""
        try:
            plans = self.api.get_all_plans(self.current_user["id"])
        except APIClientError as exc:
            self.show_snackbar(str(exc))
            plans = []

        plans_list = ft.Column()
        for plan in plans:
            plans_list.controls.append(
                ft.Card(
                    content=ft.Container(
                        content=ft.Column([
                            ft.Text(plan.get("injury_type", "Unknown"), size=14, weight="bold"),
                            ft.Text(f"Pain Level: {plan.get('pain_level', 'N/A')}/10", size=12),
                            ft.Text(f"Goal: {plan.get('goal', 'N/A')}", size=12),
                            ft.Text(f"Date: {plan.get('date', 'N/A')}", size=10, italic=True),
                        ], spacing=5),
                        padding=10
                    )
                )
            )

        if not plans:
            plans_list.controls.append(
                ft.Text("No saved plans yet. Create one to get started!", size=14)
            )

        self.main_container.content = ft.Column([
            ft.AppBar(
                title=ft.Text("Saved Plans"),
                bgcolor="#9C27B0",
            ),
            ft.Column([
                ft.Text("Your Rehabilitation Plans", size=18, weight="bold"),
                plans_list,
                ft.Divider(),
                ft.ElevatedButton("Back to Dashboard", width=300, on_click=lambda e: self.navigate("dashboard"))
            ], spacing=10, scroll=ft.ScrollMode.AUTO, expand=True)
        ], expand=True)
        self.page.update()

    # ── History Page ─────────────────────────────────────────────────────

    def show_history_page(self):
        """Show training history."""
        try:
            history = self.api.get_training_history(self.current_user["id"])
        except APIClientError as exc:
            self.show_snackbar(str(exc))
            history = []

        history_list = ft.Column()
        for session in history:
            # Support both 'exercise' and 'exercise_name' keys
            ex_name = session.get("exercise_name") or session.get("exercise", "Unknown")
            score   = session.get("score", "N/A")
            reps    = session.get("reps", "N/A")
            date    = session.get("date") or session.get("created_at", "N/A")
            week    = session.get("week", "")
            day     = session.get("day", "")

            history_list.controls.append(
                ft.Card(
                    content=ft.Container(
                        content=ft.Column([
                            ft.Text(ex_name, size=14, weight="bold"),
                            ft.Row([
                                ft.Text(f"Score: {score}/100", size=12),
                                ft.Text(f"Reps: {reps}", size=12),
                            ], spacing=15),
                            ft.Text(
                                f"Week {week} Day {day}" if week and day else "",
                                size=11, color="grey"
                            ),
                            ft.Text(str(date)[:16], size=10, italic=True, color="grey"),
                        ], spacing=4),
                        padding=10
                    )
                )
            )

        if not history:
            history_list.controls.append(
                ft.Text("No training sessions yet. Start training!", size=14)
            )

        self.main_container.content = ft.Column([
            ft.AppBar(
                title=ft.Text("Training History"),
                bgcolor="#FFA500",
            ),
            ft.Column([
                ft.Text("Your Training Sessions", size=18, weight="bold"),
                history_list,
                ft.Divider(),
                ft.ElevatedButton("Back to Dashboard", width=300, on_click=lambda e: self.navigate("dashboard"))
            ], spacing=10, scroll=ft.ScrollMode.AUTO, expand=True)
        ], expand=True)
        self.page.update()

    # ── Utilities ────────────────────────────────────────────────────────

    def _show_plan_complete(self):
        """Show plan complete screen."""
        self.main_container.content = ft.Column([
            ft.AppBar(title=ft.Text("Plan Complete!"), bgcolor="#4CAF50"),
            ft.Container(expand=True, content=ft.Column([
                ft.Container(height=60),
                ft.Icon(ft.Icons.EMOJI_EVENTS, size=80, color="#FFD700"),
                ft.Container(height=20),
                ft.Text("Congratulations!", size=28, weight="bold",
                        text_align=ft.TextAlign.CENTER),
                ft.Text("You completed your entire rehabilitation plan!",
                        size=14, text_align=ft.TextAlign.CENTER, color="grey"),
                ft.Container(height=40),
                ft.ElevatedButton("Create New Plan", width=260,
                                  on_click=lambda e: self.navigate("agent")),
                ft.Container(height=10),
                ft.ElevatedButton("Back to Dashboard", width=260,
                                  on_click=lambda e: self.navigate("dashboard")),
            ], horizontal_alignment=ft.CrossAxisAlignment.CENTER, expand=True)),
        ], expand=True)
        self.page.update()

    def show_snackbar(self, message: str):
        """Show a snackbar notification."""
        snackbar = ft.SnackBar(ft.Text(message))
        self.page.overlay.append(snackbar)
        snackbar.open = True
        self.page.update()

    def logout(self):
        """Logout current user."""
        self.current_user = None
        self.current_plan = None


def main():
    """Entry point."""
    app = FormaFixApp()
    app.run()


if __name__ == "__main__":
    main()