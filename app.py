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
            self.page = page
            self.main_container = ft.Container(expand=True)
            self.show_auth_page()
            page.add(self.main_container)

        ft.app(target=main)

    # ── Navigation ───────────────────────────────────────────────────────

    def navigate(self, page_name: str):
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
        auth_mode = ["login"]
        login_email    = ft.TextField(label="Email", width=300)
        login_password = ft.TextField(label="Password", password=True, width=300)
        signup_name    = ft.TextField(label="Full Name", width=300)
        signup_email   = ft.TextField(label="Email", width=300)
        signup_password = ft.TextField(label="Password", password=True, width=300)
        signup_age     = ft.TextField(label="Age", width=300, keyboard_type=ft.KeyboardType.NUMBER)
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
            age = None
            if signup_age.value and signup_age.value.strip():
                try:
                    age = int(signup_age.value.strip())
                except ValueError:
                    self.show_snackbar("Age must be a number")
                    return
            try:
                result = self.api.register(signup_name.value, signup_email.value, signup_password.value, age)
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
            auth_mode[0] = "signup"; update_form()

        def toggle_to_login(e):
            auth_mode[0] = "login"; update_form()

        def update_form():
            if auth_mode[0] == "login":
                form_container.content = ft.Column([
                    ft.Text("Login to FormaFix", size=24, weight="bold"),
                    login_email, login_password,
                    ft.ElevatedButton("Login", on_click=login_click, width=300),
                    ft.Container(height=10),
                    ft.Row([ft.Text("Don't have an account?", size=12),
                            ft.TextButton("Sign Up", on_click=toggle_to_signup)], spacing=5)
                ], alignment=ft.MainAxisAlignment.CENTER,
                   horizontal_alignment=ft.CrossAxisAlignment.CENTER, spacing=15)
            else:
                form_container.content = ft.Column([
                    ft.Text("Create FormaFix Account", size=24, weight="bold"),
                    signup_name, signup_email, signup_password, signup_age,
                    ft.ElevatedButton("Sign Up", on_click=signup_click, width=300),
                    ft.Container(height=10),
                    ft.Row([ft.Text("Already have an account?", size=12),
                            ft.TextButton("Login", on_click=toggle_to_login)], spacing=5)
                ], alignment=ft.MainAxisAlignment.CENTER,
                   horizontal_alignment=ft.CrossAxisAlignment.CENTER, spacing=15)
            self.page.update()

        update_form()
        self.main_container.content = form_container

    # ── Dashboard Page ───────────────────────────────────────────────────

    def show_dashboard_page(self):
        try:
            latest_plan = self.api.get_latest_plan(self.current_user["id"])
        except APIClientError as exc:
            self.show_snackbar(str(exc))
            latest_plan = None

        if not latest_plan:
            content = ft.Column([
                ft.Text("Welcome to FormaFix!", size=28, weight="bold"),
                ft.Text(f"Hi {self.current_user['name']}", size=18),
                ft.Text("Get started by creating a rehabilitation plan with our AI agent.", size=14),
                ft.Container(height=40),
                ft.ElevatedButton("Create Plan with Agent", width=250,
                                  on_click=lambda e: self.navigate("agent")),
                ft.Container(height=200),
                ft.Row([
                    ft.IconButton(icon=ft.Icons.PERSON,
                                  on_click=lambda e: self.show_snackbar("Profile feature coming soon")),
                    ft.IconButton(icon=ft.Icons.LOGOUT,
                                  on_click=lambda e: (self.logout(), self.navigate("auth"))),
                ])
            ], horizontal_alignment=ft.CrossAxisAlignment.CENTER, spacing=20)
        else:
            self.current_plan = latest_plan
            plan_data = latest_plan["plan"]
            plan  = plan_data.get("plan", plan_data)
            weeks = plan.get("weeks", [])

            plan_table = ft.DataTable(
                columns=[ft.DataColumn(ft.Text("Week")),
                         ft.DataColumn(ft.Text("Focus")),
                         ft.DataColumn(ft.Text("Days"))],
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
                    ft.ElevatedButton("Start Training", width=150,
                                      on_click=lambda e: self.navigate("training")),
                    ft.ElevatedButton("New Plan", width=150,
                                      on_click=lambda e: self.navigate("agent")),
                ]),
                ft.Divider(),
                ft.Row([
                    ft.IconButton(icon=ft.Icons.HISTORY,
                                  on_click=lambda e: self.navigate("history")),
                    ft.IconButton(icon=ft.Icons.BOOKMARK,
                                  on_click=lambda e: self.navigate("plans")),
                    ft.IconButton(icon=ft.Icons.LOGOUT,
                                  on_click=lambda e: (self.logout(), self.navigate("auth"))),
                ])
            ], spacing=10, scroll=ft.ScrollMode.AUTO)

        self.main_container.content = ft.Column([
            ft.AppBar(title=ft.Text("FormaFix Dashboard"), bgcolor="#FF9800"),
            content
        ], expand=True)
        self.page.update()

    # ── Agent Page ───────────────────────────────────────────────────────

    def show_agent_page(self):
        conversation_scroll = ft.Column(scroll=ft.ScrollMode.AUTO, expand=True)
        user_input = ft.TextField(label="Your response", multiline=True,
                                  min_lines=2, max_lines=4, width=350)
        received_plan = [False]

        def start_plan_creation():
            result = self.api.agent_start(self.current_user["name"])
            self.agent_session_id = result.get("session_id")
            add_message(result.get("initial_message", "Let's start your plan."), is_user=False)
            user_input.value = ""
            self.page.update()

        def send_message(e):
            if not user_input.value.strip():
                return
            user_msg = user_input.value
            add_message(user_msg, is_user=True)
            user_input.value = ""
            self.page.update()
            try:
                if not self.agent_session_id:
                    add_message("⚠️ Agent session not initialized.", is_user=False)
                    self.page.update()
                    return
                result   = self.api.agent_continue(self.agent_session_id, user_msg)
                response = result.get("response", "")
                plan_json = result.get("plan_json")
            except Exception as exc:
                add_message(f"⚠️ Error: {exc}", is_user=False)
                self.page.update()
                return

            if plan_json:
                received_plan[0] = True
                add_message("✅ Plan created successfully!", is_user=False)
                try:
                    save_result = self.api.save_plan(self.current_user["id"], plan_json)
                    plan_id = save_result.get("plan_id")
                    self.current_plan = {"id": plan_id, "plan": plan_json}
                    add_message("✅ Plan saved! Click 'Go to Dashboard' to start training.", is_user=False)
                except Exception as exc:
                    add_message(f"⚠️ Could not save: {exc}", is_user=False)
                save_btn.visible = True
                finish_btn.visible = True
                finish_btn.text = "Go to Dashboard"
            else:
                add_message(response, is_user=False)
            self.page.update()

        def add_message(msg: str, is_user: bool):
            conversation_scroll.controls.append(
                ft.Container(
                    content=ft.Text(msg, size=12, color="white" if is_user else "black"),
                    bgcolor="#2196F3" if is_user else "#EEEEEE",
                    border_radius=10, padding=10,
                    alignment=ft.Alignment.CENTER_RIGHT if is_user else ft.Alignment.CENTER_LEFT,
                    margin=ft.margin.only(left=40, bottom=5) if is_user else ft.margin.only(right=40, bottom=5)
                )
            )

        save_btn   = ft.ElevatedButton("Save Plan", width=150, visible=False,
                                       on_click=lambda e: self.navigate("dashboard"))
        finish_btn = ft.ElevatedButton("Continue", width=150, visible=False,
                                       on_click=lambda e: self.navigate("dashboard"))
        start_plan_creation()

        self.main_container.content = ft.Column([
            ft.AppBar(title=ft.Text("Create Rehabilitation Plan"), bgcolor="#1976D2"),
            conversation_scroll,
            ft.Divider(),
            ft.Column([
                user_input,
                ft.Row([ft.ElevatedButton("Send", width=150, on_click=send_message),
                        save_btn, finish_btn]),
                ft.ElevatedButton("Back to Dashboard", width=300,
                                  on_click=lambda e: self.navigate("dashboard"))
            ], spacing=10)
        ], expand=True)
        self.page.update()

    # ── Training Page ────────────────────────────────────────────────────

    def show_training_page(self):
        self.api.camera_start()

        # 2. Point the UI image to the server's stream endpoint
        # This replaces the "first frame only" issue by using a live MJPEG stream
        stream_img = ft.Image(
            src=f"{self.api.base}/camera/stream",
            width=380,
            height=300,
            fit="cover",
        )
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
        plan  = plan_data.get("plan", plan_data)
        weeks = plan.get("weeks", [])

        if not weeks:
            self.show_snackbar("Plan has no training weeks yet.")
            self.navigate("dashboard")
            return

        def normalize_to_int(value):
            if isinstance(value, int):
                return value
            if value is None:
                return None
            digits = "".join(ch for ch in str(value).strip() if ch.isdigit())
            return int(digits) if digits else None

        def detect_today_assignment():
            all_days = [(w, d) for w in weeks for d in w.get("days", [])]
            if not all_days:
                return None, None, []
            created_at = self.current_plan.get("created_at")
            start_date = datetime.now().date()
            if created_at:
                try:
                    start_date = datetime.fromisoformat(created_at.replace("Z", "")).date()
                except ValueError:
                    pass
            elapsed = max(0, (datetime.now().date() - start_date).days)
            idx = min(elapsed, len(all_days) - 1)
            w, day_item = all_days[idx]
            week_num  = normalize_to_int(w.get("week")) or 1
            day_num   = normalize_to_int(day_item.get("day")) or (idx + 1)
            exercises = day_item.get("exercises", [])
            if not exercises:
                for fw, fd in all_days[idx + 1:]:
                    fe = fd.get("exercises", [])
                    if fe:
                        week_num  = normalize_to_int(fw.get("week")) or week_num
                        day_num   = normalize_to_int(fd.get("day")) or day_num
                        exercises = fe
                        break
            return week_num, day_num, exercises

        plan_id = self.current_plan.get("id", 0)
        try:
            next_day        = self.api.get_next_day(self.current_user["id"], plan_id)
            week_val        = next_day.get("week")
            day_val         = next_day.get("day")
            today_exercises = next_day.get("exercises", [])
            if not today_exercises and next_day.get("focus") == "Plan complete!":
                self._show_plan_complete()
                return
        except Exception:
            week_val, day_val, today_exercises = detect_today_assignment()

        session_results = []

        def show_exercise_card(idx: int):
            if idx >= len(today_exercises):
                show_completion_screen()
                return

            ex       = today_exercises[idx]
            ex_name  = ex.get("name", "Unknown").replace("_", " ").upper()
            ex_sets  = ex.get("sets", 3)
            ex_reps  = ex.get("reps", 10)
            ex_notes = ex.get("notes", "")
            total    = len(today_exercises)

            def start_this_exercise(e):
                target_reps = int(ex.get("reps", 10) or 10)
                target_sets = int(ex.get("sets", 3) or 3)
                injury_text = ""
                try:
                    injury_text = (self.current_plan.get("plan", {})
                                   .get("patient", {}).get("injury", "")).lower()
                except Exception:
                    pass
                injured_side = "right" if "right" in injury_text else "left"

                try:
                    start_res = self.api.web_training_start(
                        exercise_name=ex.get("name", "exercise"),
                        target_reps=target_reps,
                        target_sets=target_sets,
                        injured_side=injured_side,
                    )
                    web_session_id = start_res.get("session_id")
                except Exception as exc:
                    self.show_snackbar(f"Cannot start training: {exc}")
                    return

                self._show_live_camera_training(
                    ex=ex, ex_name=ex_name, ex_sets=ex_sets, ex_reps=ex_reps,
                    web_session_id=web_session_id, target_reps=target_reps,
                    on_done=lambda summary: _on_exercise_done(summary),
                )

            def _on_exercise_done(summary: dict):
                try:
                    self.api.save_training_session({
                        "customer_id": self.current_user["id"],
                        "plan_id": self.current_plan.get("id", 0),
                        "week": week_val or 1,
                        "day":  day_val  or 1,
                        "exercise_name": ex.get("name"),
                        "score": int(summary.get("avg_score", 0)),
                        "reps":  int(summary.get("reps_completed",
                                     summary.get("target_reps", ex.get("reps", 10)))),
                        "notes": f"Sets: {ex_sets} | Target reps: {ex.get('reps', 10)}",
                        "video_path": None,
                    })
                    session_results.append(summary)
                except APIClientError as exc:
                    self.show_snackbar(f"Could not save: {exc}")
                show_exercise_card(idx + 1)

            def skip_exercise(e):
                show_exercise_card(idx + 1)

            self.main_container.content = ft.Column([
                ft.AppBar(
                    title=ft.Text(f"Exercise {idx + 1} of {total}"),
                    bgcolor="#4CAF50",
                    leading=ft.IconButton(icon=ft.Icons.ARROW_BACK,
                                          on_click=lambda e: self.navigate("dashboard")),
                ),
                ft.Container(expand=True, content=ft.Column([
                    ft.Container(height=10),
                    ft.Container(
                        content=ft.Column([
                            ft.Text(ex_name, size=22, weight="bold", color="#2196F3",
                                    text_align=ft.TextAlign.CENTER),
                            ft.Text(f"Goal: {ex_sets} Sets x {ex_reps} Reps", size=14,
                                    text_align=ft.TextAlign.CENTER),
                            ft.Text(ex_notes, size=11, italic=True,
                                    text_align=ft.TextAlign.CENTER, color="grey")
                            if ex_notes else ft.Container(),
                        ], horizontal_alignment=ft.CrossAxisAlignment.CENTER, spacing=6),
                        bgcolor="#1E1E1E", border_radius=12,
                        padding=ft.padding.symmetric(horizontal=15, vertical=12),
                        margin=ft.margin.symmetric(horizontal=10),
                    ),
                    ft.Container(height=10),
                    ft.Container(
                        content=ft.Column([
                            ft.Icon(ft.Icons.VIDEOCAM, size=48, color="#4CAF50"),
                            ft.Text("Camera opens when you start", size=12, color="grey",
                                    text_align=ft.TextAlign.CENTER),
                        ], horizontal_alignment=ft.CrossAxisAlignment.CENTER, spacing=8),
                        bgcolor="#1A1A1A", border_radius=12,
                        width=360, height=200,
                        alignment=ft.Alignment.CENTER,
                        margin=ft.margin.symmetric(horizontal=10),
                    ),
                    ft.Container(height=10),
                    ft.Row(
                        [ft.Container(width=10, height=10, border_radius=5,
                                      bgcolor="#4CAF50" if i <= idx else "#444444")
                         for i in range(total)],
                        alignment=ft.MainAxisAlignment.CENTER, spacing=5,
                    ),
                    ft.Container(expand=True),
                    ft.Container(
                        content=ft.ElevatedButton(
                            content=ft.Row([
                                ft.Icon(ft.Icons.PLAY_ARROW, color="white"),
                                ft.Text("ابدأ التمرين الآن", size=16,
                                        color="white", weight="bold"),
                            ], alignment=ft.MainAxisAlignment.CENTER),
                            width=340, height=55, bgcolor="#4CAF50",
                            on_click=start_this_exercise,
                        ),
                        margin=ft.margin.symmetric(horizontal=10),
                    ),
                    ft.Container(height=6),
                    ft.TextButton("Skip Exercise", on_click=skip_exercise,
                                  style=ft.ButtonStyle(color="grey")),
                    ft.Container(height=15),
                ], horizontal_alignment=ft.CrossAxisAlignment.CENTER,
                   spacing=0, expand=True)),
            ], expand=True)
            self.page.update()
        def stop_training(e):
            self.api.camera_stop()
            self.navigate("dashboard")

        content = ft.Column([
            ft.Text("Live Session", size=20, weight="bold"),
            ft.Container(content=stream_img, border=ft.border.all(1, "grey")),
            ft.ElevatedButton("Finish & Save", on_click=stop_training)
        ], horizontal_alignment=ft.CrossAxisAlignment.CENTER)

        self.main_container.content = content
        self.page.update()
        def show_completion_screen():
            try:
                plan_id = self.current_plan.get("id", 0)
                if week_val and day_val and plan_id:
                    self.api.mark_day_complete(
                        customer_id=self.current_user["id"],
                        plan_id=plan_id, week=week_val, day=day_val)
            except Exception as e:
                print(f"[WARN] Could not mark day: {e}")

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
                    ft.Text(f"You completed {len(session_results)} exercise(s)",
                            size=16, text_align=ft.TextAlign.CENTER),
                    ft.Container(height=10),
                    ft.Container(
                        content=ft.Text(f"Average Score: {avg}/100",
                                        size=20, weight="bold", color="#4CAF50",
                                        text_align=ft.TextAlign.CENTER),
                        bgcolor="#1E1E1E", border_radius=12, padding=15,
                        margin=ft.margin.symmetric(horizontal=30),
                    ),
                    ft.Container(expand=True),
                    ft.ElevatedButton("View History", width=260, height=50,
                                      bgcolor="#2196F3", color="white",
                                      on_click=lambda e: self.navigate("history")),
                    ft.Container(height=10),
                    ft.ElevatedButton("Back to Dashboard", width=260, height=50,
                                      on_click=lambda e: self.navigate("dashboard")),
                    ft.Container(height=30),
                ], horizontal_alignment=ft.CrossAxisAlignment.CENTER, expand=True)),
            ], expand=True)
            self.page.update()

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
                ], horizontal_alignment=ft.CrossAxisAlignment.CENTER, expand=True)),
            ], expand=True)
            self.page.update()
            return

        show_exercise_card(0)

    # ── Live Camera Training Screen ──────────────────────────────────────

    def _show_live_camera_training(self, ex, ex_name, ex_sets, ex_reps,
                                   web_session_id, target_reps, on_done):
        """
        Live training screen.
        - cv2 captures frames in a background thread
        - Each JPEG frame is passed as raw bytes to ft.Image(src=bytes)
          then camera_view.update() is called — this is the only reliable
          way to refresh an image in Flet 0.83 desktop
        - Every 2nd frame is also POSTed to the backend for pose analysis
        """
        import threading
        import cv2

        # ── UI controls ───────────────────────────────────────────────
        reps_text   = ft.Text("0", size=42, weight="bold", color="#4CAF50")
        sets_text   = ft.Text(f"Sets: 0/{ex_sets}", size=18, color="#4CAF50")
        score_text  = ft.Text("Score: —", size=18, color="white")
        tip_text    = ft.Text("Position yourself in front of the camera",
                              size=13, color="#94A3B8",
                              text_align=ft.TextAlign.CENTER)
        status_text = ft.Text("Opening camera…", size=11,
                              color="#64748B", text_align=ft.TextAlign.CENTER)

        # 1×1 white JPEG as valid placeholder bytes
        _blank = (
            b"\xff\xd8\xff\xe0\x00\x10JFIF\x00\x01\x01\x00\x00\x01\x00\x01\x00\x00"
            b"\xff\xdb\x00C\x00\x08\x06\x06\x07\x06\x05\x08\x07\x07\x07\t\t"
            b"\x08\n\x0c\x14\r\x0c\x0b\x0b\x0c\x19\x12\x13\x0f\x14\x1d\x1a"
            b"\x1f\x1e\x1d\x1a\x1c\x1c $.' \",#\x1c\x1c(7),01444\x1f\'9=82<.342\x1e"
            b"\xff\xc0\x00\x0b\x08\x00\x01\x00\x01\x01\x01\x11\x00\xff\xc4"
            b"\x00\x1f\x00\x00\x01\x05\x01\x01\x01\x01\x01\x01\x00\x00\x00"
            b"\x00\x00\x00\x00\x00\x01\x02\x03\x04\x05\x06\x07\x08\t\n\x0b"
            b"\xff\xc4\x00\xb5\x10\x00\x02\x01\x03\x03\x02\x04\x03\x05\x05"
            b"\x04\x04\x00\x00\x01}\x01\x02\x03\x00\x04\x11\x05\x12!1A\x06"
            b"\x13Qa\x07\"q\x142\x81\x91\xa1\x08#B\xb1\xc1\x15R\xd1\xf0$3br"
            b"\x82\t\n\x16\x17\x18\x19\x1a%&\'()*456789:CDEFGHIJSTUVWXYZ"
            b"cdefghijstuvwxyz\x83\x84\x85\x86\x87\x88\x89\x8a\x92\x93\x94"
            b"\x95\x96\x97\x98\x99\x9a\xa2\xa3\xa4\xa5\xa6\xa7\xa8\xa9\xaa"
            b"\xb2\xb3\xb4\xb5\xb6\xb7\xb8\xb9\xba\xc2\xc3\xc4\xc5\xc6\xc7"
            b"\xc8\xc9\xca\xd2\xd3\xd4\xd5\xd6\xd7\xd8\xd9\xda\xe1\xe2\xe3"
            b"\xe4\xe5\xe6\xe7\xe8\xe9\xea\xf1\xf2\xf3\xf4\xf5\xf6\xf7\xf8"
            b"\xf9\xfa\xff\xda\x00\x08\x01\x01\x00\x00?\x00\xfb\xd4P\x00\x00"
            b"\x00?\xff\xd9"
        )

        camera_view = ft.Image(
            src=_blank,
            width=360,
            height=420,
            fit="cover",
            gapless_playback=True,
        )

        finish_clicked = [False]
        camera_stop    = threading.Event()
        poll_stop      = threading.Event()

        # ── Camera capture + frame upload ─────────────────────────────
        def capture_and_send_frames():
            import base64
            cap = None
            try:
                cap = cv2.VideoCapture(0, cv2.CAP_DSHOW)
                if not cap.isOpened():
                    cap = cv2.VideoCapture(0)
                if not cap.isOpened():
                    status_text.value = "❌ Camera not found"
                    status_text.update()
                    return

                # Discard warm-up frames
                for _ in range(8):
                    cap.read()

                status_text.value = "🔴 Live"
                status_text.update()

                frame_count = 0
                while not camera_stop.is_set() and not finish_clicked[0]:
                    ok, frame = cap.read()
                    if not ok:
                        camera_stop.wait(0.04)
                        continue

                    frame = cv2.flip(frame, 1)
                    frame = cv2.resize(frame, (480, 360))
                    ok2, jpeg = cv2.imencode(
                        ".jpg", frame, [cv2.IMWRITE_JPEG_QUALITY, 75]
                    )
                    if not ok2:
                        continue

                    jpeg_bytes = jpeg.tobytes()

                    # ── Update ft.Image with raw bytes — thread safe in Flet 0.83 ──
                    camera_view.src = jpeg_bytes
                    camera_view.update()

                    # Send every 2nd frame to backend for pose analysis
                    frame_count += 1
                    if frame_count % 2 == 0:
                        try:
                            raw_b64 = base64.b64encode(jpeg_bytes).decode()
                            self.api.web_training_frame(
                                web_session_id,
                                f"data:image/jpeg;base64,{raw_b64}",
                            )
                        except Exception:
                            pass

                    camera_stop.wait(0.05)   # ~20 fps
            finally:
                if cap is not None:
                    cap.release()

        # ── Status polling ────────────────────────────────────────────
        def poll_status():
            while not poll_stop.is_set():
                try:
                    data      = self.api._get(f"/training/web/status/{web_session_id}")
                    summary   = data.get("summary", {})
                    reps      = summary.get("reps_completed", 0)
                    score     = summary.get("avg_score", 0)
                    done_sets = summary.get("completed_sets", 0)
                    tip       = data.get("tip", "")
                    finished  = data.get("finished", False)

                    reps_text.value  = str(reps)
                    sets_text.value  = f"Sets: {done_sets}/{ex_sets}"
                    score_text.value = f"Score: {score}/100"
                    if tip:
                        tip_text.value = tip
                    reps_text.update()
                    sets_text.update()
                    score_text.update()
                    tip_text.update()

                    if finished and not finish_clicked[0]:
                        finish_clicked[0] = True
                        poll_stop.set()
                        camera_stop.set()
                        self.page.run_thread(lambda s=summary: on_done(s))
                        return
                except Exception:
                    pass
                poll_stop.wait(0.5)

        def on_finish_click(e):
            if finish_clicked[0]:
                return
            finish_clicked[0] = True
            poll_stop.set()
            camera_stop.set()
            try:
                result  = self.api.web_training_finish(web_session_id)
                summary = result.get("summary", {})
            except Exception:
                summary = {}
            on_done(summary)

        # ── Layout ────────────────────────────────────────────────────
        self.main_container.content = ft.Column([
            ft.AppBar(
                title=ft.Text(ex_name, overflow=ft.TextOverflow.ELLIPSIS),
                bgcolor="#0F172A",
                leading=ft.IconButton(
                    icon=ft.Icons.CLOSE, icon_color="white",
                    on_click=on_finish_click, tooltip="Finish & save",
                ),
            ),

            # Camera feed — centred
            ft.Container(
                content=camera_view,
                expand=True,
                bgcolor="#020617",
                alignment=ft.Alignment.CENTER,
                border_radius=ft.border_radius.only(bottom_left=16, bottom_right=16),
                clip_behavior=ft.ClipBehavior.HARD_EDGE,
            ),
            # Stats bar
            ft.Container(
                content=ft.Row([
                    ft.Container(
                        content=ft.Column([
                            ft.Text("REPS", size=10, color="#64748B", weight="bold"),
                            reps_text,
                        ], horizontal_alignment=ft.CrossAxisAlignment.CENTER, spacing=2),
                        expand=1, alignment=ft.Alignment.CENTER,
                    ),
                    ft.VerticalDivider(width=1, color="#1E293B"),
                    ft.Container(
                        content=ft.Column([
                            sets_text, score_text,
                        ], horizontal_alignment=ft.CrossAxisAlignment.CENTER, spacing=4),
                        expand=2, alignment=ft.Alignment.CENTER,
                    ),
                    ft.VerticalDivider(width=1, color="#1E293B"),
                    ft.Container(
                        content=ft.Column([
                            ft.Text("GOAL", size=10, color="#64748B", weight="bold"),
                            ft.Text(f"{target_reps}×{ex_sets}", size=16, weight="bold", color="white"),
                        ], horizontal_alignment=ft.CrossAxisAlignment.CENTER, spacing=2),
                        expand=1, alignment=ft.Alignment.CENTER,
                    ),
                ], expand=True),
                bgcolor="#0F172A", height=80,
                padding=ft.padding.symmetric(horizontal=8, vertical=8),
            ),

            # Tip + status
            ft.Container(
                content=ft.Column([
                    tip_text, status_text,
                ], horizontal_alignment=ft.CrossAxisAlignment.CENTER, spacing=2),
                bgcolor="#0F172A",
                padding=ft.padding.symmetric(horizontal=12, vertical=6),
                alignment=ft.Alignment.CENTER,
            ),

            # Finish button
            ft.Container(
                content=ft.ElevatedButton(
                    content=ft.Row([
                        ft.Icon(ft.Icons.CHECK_CIRCLE_OUTLINE, color="white"),
                        ft.Text("Finish Exercise", size=15, color="white", weight="bold"),
                    ], alignment=ft.MainAxisAlignment.CENTER),
                    width=340, height=50, bgcolor="#3B82F6",
                    on_click=on_finish_click,
                ),
                bgcolor="#0F172A",
                padding=ft.padding.only(left=16, right=16, bottom=16, top=4),
                alignment=ft.Alignment.CENTER,
            ),
        ], expand=True, spacing=0)
        self.page.update()
        # Launch with Flet's worker executor so control.update() is applied promptly.
        self.page.run_thread(capture_and_send_frames)
        self.page.run_thread(poll_status)

    # ── Plans Page ───────────────────────────────────────────────────────

    def show_plans_page(self):
        try:
            plans = self.api.get_all_plans(self.current_user["id"])
        except APIClientError as exc:
            self.show_snackbar(str(exc))
            plans = []

        plans_list = ft.Column()
        for plan in plans:
            plans_list.controls.append(
                ft.Card(content=ft.Container(
                    content=ft.Column([
                        ft.Text(plan.get("injury_type", "Unknown"), size=14, weight="bold"),
                        ft.Text(f"Pain Level: {plan.get('pain_level', 'N/A')}/10", size=12),
                        ft.Text(f"Goal: {plan.get('goal', 'N/A')}", size=12),
                        ft.Text(f"Date: {plan.get('date', 'N/A')}", size=10, italic=True),
                    ], spacing=5), padding=10))
            )
        if not plans:
            plans_list.controls.append(
                ft.Text("No saved plans yet. Create one to get started!", size=14))

        self.main_container.content = ft.Column([
            ft.AppBar(title=ft.Text("Saved Plans"), bgcolor="#9C27B0"),
            ft.Column([
                ft.Text("Your Rehabilitation Plans", size=18, weight="bold"),
                plans_list, ft.Divider(),
                ft.ElevatedButton("Back to Dashboard", width=300,
                                  on_click=lambda e: self.navigate("dashboard"))
            ], spacing=10, scroll=ft.ScrollMode.AUTO, expand=True)
        ], expand=True)
        self.page.update()

    # ── History Page ─────────────────────────────────────────────────────

    def show_history_page(self):
        try:
            history = self.api.get_training_history(self.current_user["id"])
        except APIClientError as exc:
            self.show_snackbar(str(exc))
            history = []

        history_list = ft.Column()
        for session in history:
            ex_name = session.get("exercise_name") or session.get("exercise", "Unknown")
            score   = session.get("score", "N/A")
            reps    = session.get("reps", "N/A")
            date    = session.get("date") or session.get("created_at", "N/A")
            week    = session.get("week", "")
            day     = session.get("day", "")
            history_list.controls.append(
                ft.Card(content=ft.Container(
                    content=ft.Column([
                        ft.Text(ex_name, size=14, weight="bold"),
                        ft.Row([ft.Text(f"Score: {score}/100", size=12),
                                ft.Text(f"Reps: {reps}", size=12)], spacing=15),
                        ft.Text(f"Week {week} Day {day}" if week and day else "",
                                size=11, color="grey"),
                        ft.Text(str(date)[:16], size=10, italic=True, color="grey"),
                    ], spacing=4), padding=10))
            )

        if not history:
            history_list.controls.append(
                ft.Text("No training sessions yet. Start training!", size=14))

        self.main_container.content = ft.Column([
            ft.AppBar(title=ft.Text("Training History"), bgcolor="#FFA500"),
            ft.Column([
                ft.Text("Your Training Sessions", size=18, weight="bold"),
                history_list, ft.Divider(),
                ft.ElevatedButton("Back to Dashboard", width=300,
                                  on_click=lambda e: self.navigate("dashboard"))
            ], spacing=10, scroll=ft.ScrollMode.AUTO, expand=True)
        ], expand=True)
        self.page.update()

    # ── Utilities ────────────────────────────────────────────────────────

    def _show_plan_complete(self):
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
        snackbar = ft.SnackBar(ft.Text(message))
        self.page.overlay.append(snackbar)
        snackbar.open = True
        self.page.update()

    def logout(self):
        self.current_user = None
        self.current_plan = None


def main():
    app = FormaFixApp()
    app.run()


if __name__ == "__main__":
    main()