"""
api_client.py — FormaFix
=========================
HTTP client — بيتكلم مع الـ FastAPI server
"""

import httpx
from typing import Optional

SERVER_URL = "http://localhost:8000"  # هنغيره لما نعمل deploy


class APIClientError(Exception):
    pass


class APIClient:

    def __init__(self, base_url: str = SERVER_URL):
        self.base = base_url
        self.client = httpx.Client(timeout=60)

    def _post(self, endpoint: str, data: dict) -> dict:
        try:
            r = self.client.post(f"{self.base}{endpoint}", json=data)
            r.raise_for_status()
            return r.json()
        except httpx.HTTPStatusError as e:
            raise APIClientError(f"Server error: {e.response.status_code}")
        except httpx.ConnectError:
            raise APIClientError("Cannot connect to server. Is it running?")
        except Exception as e:
            raise APIClientError(str(e))

    def _get(self, endpoint: str) -> dict:
        try:
            r = self.client.get(f"{self.base}{endpoint}")
            r.raise_for_status()
            return r.json()
        except httpx.ConnectError:
            raise APIClientError("Cannot connect to server. Is it running?")
        except Exception as e:
            raise APIClientError(str(e))

    # ── Auth ─────────────────────────────────────────────────────
    def register(self, name, email, password, age=None):
        return self._post("/register", {
            "name": name, "email": email,
            "password": password, "age": age
        })

    def login(self, email, password):
        return self._post("/login", {
            "email": email, "password": password
        })

    # ── Agent ────────────────────────────────────────────────────
    def agent_start(self, patient_name: str):
        return self._post("/agent/start", {"patient_name": patient_name})

    def agent_continue(self, session_id: str, message: str):
        return self._post("/agent/continue", {
            "session_id": session_id, "message": message
        })

    # ── Plans ────────────────────────────────────────────────────
    def save_plan(self, customer_id: str, plan_json: dict):
        return self._post("/plans/save", {
            "customer_id": customer_id, "plan_json": plan_json
        })

    def get_latest_plan(self, customer_id: str):
        return self._get(f"/plans/latest/{customer_id}")

    def get_all_plans(self, customer_id: str):
        return self._get(f"/plans/all/{customer_id}")

    # ── Sessions ─────────────────────────────────────────────────
    def save_training_session(self, data: dict):
        return self._post("/sessions/save", data)

    def get_training_history(self, customer_id: str):
        return self._get(f"/sessions/history/{customer_id}")

    # ── Training ─────────────────────────────────────────────────
    def run_live_training(self, exercise_name: str, target_reps: int = 10,
                          target_sets: int = 3, injured_side: str = "left", **kwargs):
        params = (f"?exercise_name={exercise_name}"
                  f"&target_reps={target_reps}"
                  f"&target_sets={target_sets}"
                  f"&injured_side={injured_side}")
        return self._post(f"/training/live{params}", {})

    def mark_day_complete(self, customer_id: str, plan_id: int, week: int, day: int):
        return self._post("/plans/mark_day", {
            "customer_id": customer_id, "plan_id": plan_id,
            "week": week, "day": day,
        })

    def get_next_day(self, customer_id: str, plan_id: int):
        return self._get(f"/plans/next_day/{customer_id}/{plan_id}")

    def camera_start(self):
        return self._get("/camera/start")

    def camera_stop(self):
        return self._get("/camera/stop")
    
    def get_latest_stats(self):
        # Helper to pull rep counts from server if needed
        return self._get("/training/stats")

    # ── Web Training (browser-camera) ────────────────────────────────────
    def web_training_start(self, exercise_name: str, target_reps: int = 10,
                           target_sets: int = 1, injured_side: str = "left"):
        return self._post("/training/web/start", {
            "exercise_name": exercise_name,
            "target_reps": target_reps,
            "target_sets": target_sets,
            "injured_side": injured_side,
        })

    def web_training_frame(self, session_id: str, image_b64: str):
        """Send a base-64 encoded JPEG frame; returns tip + summary + finished."""
        return self._post(f"/training/web/frame/{session_id}", {"image": image_b64})

    def web_training_finish(self, session_id: str):
        return self._post(f"/training/web/finish/{session_id}", {})