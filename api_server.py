"""
FastAPI backend for FormaFix.
Exposes auth, plan, agent, and training endpoints consumed by the Flet app.
"""

from __future__ import annotations

import uuid
from typing import Any

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel

from auth_service import AuthService
from database_service import DatabaseService
from plan_service import PlanService
from feedback_engine import FeedbackEngine
from form_evaluator import FormEvaluator
from training_service import TrainingSession, detect_body_points_precheck

app = FastAPI(title="FormaFix API", version="1.0.0")

auth_service = AuthService()
db = DatabaseService()
agent_sessions: dict[str, PlanService] = {}
feedback_engine = FeedbackEngine()
form_evaluator = FormEvaluator()


class RegisterRequest(BaseModel):
    name: str
    email: str
    password: str
    age: int | None = None


class LoginRequest(BaseModel):
    email: str
    password: str


class SavePlanRequest(BaseModel):
    customer_id: int
    plan_data: dict[str, Any]


class AgentStartRequest(BaseModel):
    patient_name: str


class AgentContinueRequest(BaseModel):
    session_id: str
    user_message: str


class TrainingSessionRequest(BaseModel):
    customer_id: int
    plan_id: int
    week: int
    day: int
    exercise_name: str
    score: int
    reps: int
    notes: str | None = None
    video_path: str | None = None


class ExercisesRequest(BaseModel):
    plan_json: dict[str, Any]
    week: int
    day: int


class FormEvaluationRequest(BaseModel):
    exercise: str
    joint_name: str
    current_angle: float


class FeedbackRequest(BaseModel):
    exercise: str
    joint_angles: dict[str, float]


class TrainingPrecheckRequest(BaseModel):
    timeout_sec: int = 6
    visibility_threshold: float = 0.5


class RunLiveTrainingRequest(BaseModel):
    exercise_name: str
    target_reps: int = 10
    require_clear_start: bool = True
    clear_frames_needed: int = 8


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.post("/auth/register")
def register(payload: RegisterRequest) -> dict[str, Any]:
    success, message, customer_id = auth_service.register(
        payload.name,
        payload.email,
        payload.password,
        payload.age,
    )
    return {
        "success": success,
        "message": message,
        "customer_id": customer_id,
    }


@app.post("/auth/login")
def login(payload: LoginRequest) -> dict[str, Any]:
    success, message, customer = auth_service.login(payload.email, payload.password)
    return {
        "success": success,
        "message": message,
        "customer": customer,
    }


@app.post("/agent/start")
def agent_start(payload: AgentStartRequest) -> dict[str, Any]:
    service = PlanService()
    session_id = str(uuid.uuid4())
    initial_message = service.start_plan_creation(payload.patient_name)
    agent_sessions[session_id] = service
    return {
        "session_id": session_id,
        "initial_message": initial_message,
    }


@app.post("/agent/continue")
def agent_continue(payload: AgentContinueRequest) -> dict[str, Any]:
    service = agent_sessions.get(payload.session_id)
    if not service:
        raise HTTPException(status_code=404, detail="Agent session not found")

    response, plan_json = service.continue_conversation(payload.user_message)
    return {
        "response": response,
        "plan_json": plan_json,
    }


@app.post("/plans/save")
def save_plan(payload: SavePlanRequest) -> dict[str, Any]:
    service = PlanService()
    plan_id = service.save_plan(payload.customer_id, payload.plan_data)
    return {"plan_id": plan_id}


@app.get("/plans/latest/{customer_id}")
def get_latest_plan(customer_id: int) -> dict[str, Any]:
    plan = db.get_latest_plan(customer_id)
    return {"plan": plan}


@app.get("/plans/all/{customer_id}")
def get_all_plans(customer_id: int) -> dict[str, Any]:
    plans = db.get_all_plans(customer_id)
    return {"plans": plans}


@app.post("/plans/exercises")
def get_exercises(payload: ExercisesRequest) -> dict[str, Any]:
    service = PlanService()
    exercises = service.get_exercises_for_day(payload.plan_json, payload.week, payload.day)
    return {"exercises": exercises}


@app.post("/training/session")
def save_training_session(payload: TrainingSessionRequest) -> dict[str, Any]:
    session_id = db.save_training_session(payload.model_dump())
    return {"session_id": session_id}


@app.get("/training/history/{customer_id}")
def get_training_history(customer_id: int, limit: int = 10) -> dict[str, Any]:
    history = db.get_training_history(customer_id, limit)
    return {"history": history}


@app.post("/analysis/form")
def evaluate_form(payload: FormEvaluationRequest) -> dict[str, Any]:
    score, feedback = form_evaluator.evaluate(
        payload.exercise,
        payload.joint_name,
        payload.current_angle,
    )
    return {
        "score": score,
        "feedback": feedback,
    }


@app.post("/analysis/feedback")
def generate_feedback(payload: FeedbackRequest) -> dict[str, Any]:
    message = feedback_engine.get_feedback(payload.exercise, payload.joint_angles)
    return {"feedback": message}


@app.post("/training/precheck")
def training_precheck(payload: TrainingPrecheckRequest) -> dict[str, Any]:
    return detect_body_points_precheck(
        timeout_sec=payload.timeout_sec,
        visibility_threshold=payload.visibility_threshold,
    )


@app.post("/training/run-live")
def training_run_live(payload: RunLiveTrainingRequest) -> dict[str, Any]:
    session = TrainingSession(
        exercise_name=payload.exercise_name,
        target_reps=payload.target_reps,
    )
    summary = session.run_live_camera_session(
        require_clear_start=payload.require_clear_start,
        clear_frames_needed=payload.clear_frames_needed,
    )
    return {"summary": summary}
