"""
HTTP client used by Flet app to consume FormaFix FastAPI endpoints.
"""

from __future__ import annotations

import os
from typing import Any

import requests


class APIClientError(Exception):
    """Raised when API communication fails."""


class APIClient:
    def __init__(self, base_url: str | None = None, timeout: int = 60, agent_timeout: int = 120, training_timeout: int = 3600):
        self.base_url = (base_url or os.getenv("API_BASE_URL") or "http://127.0.0.1:8000").rstrip("/")
        self.timeout = timeout
        self.agent_timeout = agent_timeout
        self.training_timeout = training_timeout

    def _url(self, path: str) -> str:
        return f"{self.base_url}{path}"

    def _get(self, path: str, params: dict[str, Any] | None = None) -> dict[str, Any]:
        try:
            response = requests.get(self._url(path), params=params, timeout=self.timeout)
            response.raise_for_status()
            return response.json()
        except requests.RequestException as exc:
            raise APIClientError(f"GET {path} failed: {exc}") from exc

    def _post(self, path: str, payload: dict[str, Any], timeout: int | None = None) -> dict[str, Any]:
        try:
            response = requests.post(self._url(path), json=payload, timeout=timeout or self.timeout)
            response.raise_for_status()
            return response.json()
        except requests.RequestException as exc:
            raise APIClientError(f"POST {path} failed: {exc}") from exc

    def register(self, name: str, email: str, password: str, age: int | None) -> dict[str, Any]:
        return self._post(
            "/auth/register",
            {"name": name, "email": email, "password": password, "age": age},
        )

    def login(self, email: str, password: str) -> dict[str, Any]:
        return self._post("/auth/login", {"email": email, "password": password})

    def agent_start(self, patient_name: str) -> dict[str, Any]:
        return self._post("/agent/start", {"patient_name": patient_name})

    def agent_continue(self, session_id: str, user_message: str) -> dict[str, Any]:
        return self._post(
            "/agent/continue",
            {"session_id": session_id, "user_message": user_message},
            timeout=self.agent_timeout,
        )

    def save_plan(self, customer_id: int, plan_data: dict[str, Any]) -> dict[str, Any]:
        return self._post("/plans/save", {"customer_id": customer_id, "plan_data": plan_data})

    def get_latest_plan(self, customer_id: int) -> dict[str, Any] | None:
        data = self._get(f"/plans/latest/{customer_id}")
        return data.get("plan")

    def get_all_plans(self, customer_id: int) -> list[dict[str, Any]]:
        data = self._get(f"/plans/all/{customer_id}")
        return data.get("plans", [])

    def get_exercises_for_day(self, plan_json: dict[str, Any], week: int, day: int) -> list[dict[str, Any]]:
        data = self._post("/plans/exercises", {"plan_json": plan_json, "week": week, "day": day})
        return data.get("exercises", [])

    def save_training_session(self, session_data: dict[str, Any]) -> dict[str, Any]:
        return self._post("/training/session", session_data)

    def get_training_history(self, customer_id: int, limit: int = 10) -> list[dict[str, Any]]:
        data = self._get(f"/training/history/{customer_id}", params={"limit": limit})
        return data.get("history", [])

    def evaluate_form(self, exercise: str, joint_name: str, current_angle: float) -> dict[str, Any]:
        return self._post(
            "/analysis/form",
            {
                "exercise": exercise,
                "joint_name": joint_name,
                "current_angle": current_angle,
            },
        )

    def generate_feedback(self, exercise: str, joint_angles: dict[str, float]) -> str:
        data = self._post(
            "/analysis/feedback",
            {
                "exercise": exercise,
                "joint_angles": joint_angles,
            },
        )
        return data.get("feedback", "Keep going!")

    def training_precheck(self, timeout_sec: int = 6, visibility_threshold: float = 0.5) -> dict[str, Any]:
        return self._post(
            "/training/precheck",
            {
                "timeout_sec": timeout_sec,
                "visibility_threshold": visibility_threshold,
            },
            timeout=max(self.timeout, timeout_sec + 10),
        )

    def run_live_training(
        self,
        exercise_name: str,
        target_reps: int = 10,
        require_clear_start: bool = True,
        clear_frames_needed: int = 8,
    ) -> dict[str, Any]:
        return self._post(
            "/training/run-live",
            {
                "exercise_name": exercise_name,
                "target_reps": target_reps,
                "require_clear_start": require_clear_start,
                "clear_frames_needed": clear_frames_needed,
            },
            timeout=self.training_timeout,
        )
