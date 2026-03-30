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
                    ft.IconButton(icon="person", on_click=lambda e: self.show_snackbar("Profile feature coming soon")),
                    ft.IconButton(icon="logout", on_click=lambda e: (self.logout(), self.navigate("auth"))),
                ])
            ], horizontal_alignment=ft.CrossAxisAlignment.CENTER, spacing=20)
        else:
            # Show recent plan
            self.current_plan = latest_plan
            plan_data = latest_plan["plan"]
            # plan_data is the full AI JSON: {"patient": {...}, "plan": {"weeks": [...]}}
            # unwrap one level so we get the inner plan dict with "weeks"
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

            for week in weeks[:4]:  # Show first 4 weeks
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
                ft.Text(f"Your Current Plan", size=18, weight="bold"),
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
                    ft.IconButton(icon="history", on_click=lambda e: self.navigate("history")),
                    ft.IconButton(icon="bookmark", on_click=lambda e: self.navigate("plans")),
                    ft.IconButton(icon="logout", on_click=lambda e: (self.logout(), self.navigate("auth"))),
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
                except Exception as exc:
                    add_message(f"⚠️ Plan generated but could not be saved: {exc}", is_user=False)
                # Show save and finish button
                save_btn.visible = True
                finish_btn.visible = True
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
            """Map today's date to the plan's week/day progression."""
            total_days = 0
            for w in weeks:
                total_days += len(w.get("days", []))
            if total_days == 0:
                return None, None, []

            created_at = self.current_plan.get("created_at")
            start_date = datetime.now().date()
            if created_at:
                try:
                    cleaned = created_at.replace("Z", "")
                    start_date = datetime.fromisoformat(cleaned).date()
                except ValueError:
                    pass

            elapsed_days = max(0, (datetime.now().date() - start_date).days)
            day_offset = elapsed_days % total_days

            for w in weeks:
                days = w.get("days", [])
                if day_offset < len(days):
                    week_num = normalize_to_int(w.get("week")) or 1
                    day_item = days[day_offset]
                    day_num = normalize_to_int(day_item.get("day")) or (day_offset + 1)
                    exercises = day_item.get("exercises", [])
                    return week_num, day_num, exercises
                day_offset -= len(days)

            return None, None, []

        week_val, day_val, today_exercises = detect_today_assignment()

        def start_today_training(e):
            """Start live camera monitoring for today's detected exercises."""
            if not today_exercises:
                self.show_snackbar("No exercises scheduled for today.")
                return

            self.show_snackbar("Camera is turning on. Counting will start only when your body is clear in frame.")

            completed = 0
            for ex in today_exercises:
                exercise_name = ex.get("name")
                if not exercise_name:
                    continue

                target_reps = int(ex.get("reps", 10) or 10)
                try:
                    run_result = self.api.run_live_training(
                        exercise_name=exercise_name,
                        target_reps=target_reps,
                        require_clear_start=True,
                        clear_frames_needed=8,
                    )
                    summary = run_result.get("summary", {})
                except Exception as exc:
                    self.show_snackbar(f"Camera training failed for {exercise_name}: {exc}")
                    continue

                completed += 1
                try:
                    self.api.save_training_session({
                        "customer_id": self.current_user["id"],
                        "plan_id": self.current_plan.get("id", 0),
                        "week": week_val or 1,
                        "day": day_val or 1,
                        "exercise_name": exercise_name,
                        "score": int(summary.get("avg_score", 0)),
                        "reps": int(summary.get("reps_completed", 0)),
                        "notes": f"Live monitored training. Target reps: {target_reps}",
                        "video_path": None,
                    })
                except APIClientError as exc:
                    self.show_snackbar(f"Could not save {exercise_name}: {exc}")

            self.show_snackbar(f"Training completed for {completed} exercise(s).")
            self.navigate("history")

        exercise_list = ft.Column()
        for ex in today_exercises:
            exercise_list.controls.append(
                ft.Card(
                    content=ft.Container(
                        content=ft.Column([
                            ft.Text(ex.get("name", "Unknown"), size=14, weight="bold"),
                            ft.Text(f"Sets: {ex.get('sets', 3)} | Reps: {ex.get('reps', 10)}", size=12),
                            ft.Text(ex.get("notes", ""), size=10, italic=True),
                        ], spacing=5),
                        padding=10,
                    )
                )
            )

        if not today_exercises:
            exercise_list.controls.append(ft.Text("No exercises found for today.", size=12))

        start_training_btn = ft.ElevatedButton(
            "Start Training (Live Camera)",
            width=260,
            on_click=start_today_training,
            disabled=not bool(today_exercises),
        )

        self.main_container.content = ft.Column([
            ft.AppBar(
                title=ft.Text("Training Session"),
                bgcolor="#4CAF50",
            ),
            ft.Column([
                ft.Text("Today's Auto-Detected Workout", size=18, weight="bold"),
                ft.Text(f"Week: {week_val if week_val is not None else 'N/A'}", size=12),
                ft.Text(f"Day: {day_val if day_val is not None else 'N/A'}", size=12),
                ft.Divider(),
                ft.Text("Exercises for Today", size=14, weight="bold"),
                exercise_list,
                ft.Container(height=20),
                start_training_btn,
                ft.ElevatedButton("Back to Dashboard", width=300, on_click=lambda e: self.navigate("dashboard"))
            ], spacing=10, scroll=ft.ScrollMode.AUTO, expand=True)
        ], expand=True)
        self.page.update()

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
            history_list.controls.append(
                ft.Card(
                    content=ft.Container(
                        content=ft.Column([
                            ft.Text(session.get("exercise", "Unknown"), size=14, weight="bold"),
                            ft.Text(f"Score: {session.get('score', 'N/A')}/100", size=12),
                            ft.Text(f"Reps: {session.get('reps', 'N/A')}", size=12),
                            ft.Text(f"Date: {session.get('date', 'N/A')}", size=10, italic=True),
                        ], spacing=5),
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