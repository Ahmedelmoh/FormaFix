"""
database_service.py — FormaFix
===============================
SQLite database service for managing customers, plans, and training sessions.
"""

import sqlite3
import json
from datetime import datetime
from pathlib import Path

DB_PATH = "formafix.db"


class DatabaseService:
    """Manages all database operations for FormaFix."""

    def __init__(self, db_path: str = DB_PATH):
        self.db_path = db_path
        self.init_db()

    def get_connection(self):
        """Get a database connection."""
        return sqlite3.connect(self.db_path)

    def init_db(self):
        """Initialize database tables if they don't exist."""
        conn = self.get_connection()
        cursor = conn.cursor()

        # Customers table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS customers (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                email TEXT UNIQUE NOT NULL,
                password TEXT NOT NULL,
                age INTEGER,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)

        # Plans table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS plans (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                customer_id INTEGER NOT NULL,
                injury_type TEXT,
                injury_date TEXT,
                surgery BOOLEAN DEFAULT 0,
                surgery_date TEXT,
                pain_level INTEGER,
                mobility TEXT,
                previous_treatment TEXT,
                goal TEXT,
                plan_json TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (customer_id) REFERENCES customers(id)
            )
        """)

        # Training sessions table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS training_sessions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                customer_id INTEGER NOT NULL,
                plan_id INTEGER NOT NULL,
                week INTEGER,
                day INTEGER,
                exercise_name TEXT,
                score INTEGER,
                reps INTEGER,
                notes TEXT,
                video_path TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (customer_id) REFERENCES customers(id),
                FOREIGN KEY (plan_id) REFERENCES plans(id)
            )
        """)

        conn.commit()
        conn.close()

    # ── Customer operations ──────────────────────────────────────────────

    def create_customer(self, name: str, email: str, password: str, age: int = None) -> int:
        """Create a new customer. Returns customer_id."""
        conn = self.get_connection()
        cursor = conn.cursor()
        try:
            cursor.execute(
                "INSERT INTO customers (name, email, password, age) VALUES (?, ?, ?, ?)",
                (name, email, password, age)
            )
            conn.commit()
            return cursor.lastrowid
        finally:
            conn.close()

    def get_customer(self, email: str) -> dict:
        """Get customer by email."""
        conn = self.get_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT id, name, email, password, age, created_at FROM customers WHERE email = ?", (email,))
        row = cursor.fetchone()
        conn.close()
        if row:
            return {
                "id": row[0],
                "name": row[1],
                "email": row[2],
                "password": row[3],
                "age": row[4],
                "created_at": row[5],
            }
        return None

    def customer_exists(self, email: str) -> bool:
        """Check if customer exists."""
        return self.get_customer(email) is not None

    # ── Plan operations ──────────────────────────────────────────────────

    def create_plan(self, customer_id: int, plan_data: dict) -> int:
        """Create a new plan. plan_data should contain injury details and plan_json."""
        conn = self.get_connection()
        cursor = conn.cursor()
        try:
            cursor.execute("""
                INSERT INTO plans (
                    customer_id, injury_type, injury_date, surgery, surgery_date,
                    pain_level, mobility, previous_treatment, goal, plan_json
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                customer_id,
                plan_data.get("injury_type"),
                plan_data.get("injury_date"),
                plan_data.get("surgery", False),
                plan_data.get("surgery_date"),
                plan_data.get("pain_level"),
                plan_data.get("mobility"),
                plan_data.get("previous_treatment"),
                plan_data.get("goal"),
                json.dumps(plan_data.get("plan_json", {}))
            ))
            conn.commit()
            return cursor.lastrowid
        finally:
            conn.close()

    def get_latest_plan(self, customer_id: int) -> dict :
        """Get the most recent plan for a customer."""
        conn = self.get_connection()
        cursor = conn.cursor()
        cursor.execute("""
            SELECT id, customer_id, injury_type, pain_level, goal, plan_json, created_at
            FROM plans
            WHERE customer_id = ?
            ORDER BY created_at DESC
            LIMIT 1
        """, (customer_id,))
        row = cursor.fetchone()
        conn.close()
        if row:
            return {
                "id": row[0],
                "customer_id": row[1],
                "injury_type": row[2],
                "pain_level": row[3],
                "goal": row[4],
                "plan": json.loads(row[5]),
                "created_at": row[6],
            }
        return None

    def get_all_plans(self, customer_id: int) -> list:
        """Get all plans for a customer."""
        conn = self.get_connection()
        cursor = conn.cursor()
        cursor.execute("""
            SELECT id, injury_type, pain_level, goal, created_at
            FROM plans
            WHERE customer_id = ?
            ORDER BY created_at DESC
        """, (customer_id,))
        rows = cursor.fetchall()
        conn.close()
        return [{"id": r[0], "injury_type": r[1], "pain_level": r[2], "goal": r[3], "date": r[4]} for r in rows]

    # ── Training session operations ──────────────────────────────────────

    def save_training_session(self, session_data: dict) -> int:
        """Save a training session. Returns session_id."""
        conn = self.get_connection()
        cursor = conn.cursor()
        try:
            cursor.execute("""
                INSERT INTO training_sessions (
                    customer_id, plan_id, week, day, exercise_name,
                    score, reps, notes, video_path
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                session_data.get("customer_id"),
                session_data.get("plan_id"),
                session_data.get("week"),
                session_data.get("day"),
                session_data.get("exercise_name"),
                session_data.get("score"),
                session_data.get("reps"),
                session_data.get("notes"),
                session_data.get("video_path"),
            ))
            conn.commit()
            return cursor.lastrowid
        finally:
            conn.close()

    def get_training_history(self, customer_id: int, limit: int = 10) -> list:
        """Get recent training sessions for a customer."""
        conn = self.get_connection()
        cursor = conn.cursor()
        cursor.execute("""
            SELECT id, exercise_name, score, reps, created_at
            FROM training_sessions
            WHERE customer_id = ?
            ORDER BY created_at DESC
            LIMIT ?
        """, (customer_id, limit))
        rows = cursor.fetchall()
        conn.close()
        return [
            {
                "id": r[0],
                "exercise": r[1],
                "score": r[2],
                "reps": r[3],
                "date": r[4],
            }
            for r in rows
        ]

    def get_exercise_stats(self, customer_id: int, exercise_name: str) -> dict:
        """Get statistics for a specific exercise."""
        conn = self.get_connection()
        cursor = conn.cursor()
        cursor.execute("""
            SELECT AVG(score), MAX(score), COUNT(*), SUM(reps)
            FROM training_sessions
            WHERE customer_id = ? AND exercise_name = ?
        """, (customer_id, exercise_name))
        row = cursor.fetchone()
        conn.close()
        if row and row[2]:
            return {
                "avg_score": round(row[0], 1),
                "best_score": row[1],
                "attempts": row[2],
                "total_reps": row[3],
            }
        return {"avg_score": 0, "best_score": 0, "attempts": 0, "total_reps": 0}
