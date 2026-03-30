"""
auth_service.py — FormaFix
===========================
Authentication service for user login and registration.
"""

import hashlib
from database_service import DatabaseService


class AuthService:
    """Handles user authentication."""

    def __init__(self):
        self.db = DatabaseService()

    @staticmethod
    def hash_password(password: str) -> str:
        """Hash password using SHA-256."""
        return hashlib.sha256(password.encode()).hexdigest()

    def register(self, name: str, email: str, password: str, age: int = None) -> tuple[bool, str, int or None]:
        """
        Register a new customer.
        Returns (success: bool, message: str, customer_id: int or None)
        """
        if not email or not password or not name:
            return False, "All fields are required", None

        if self.db.customer_exists(email):
            return False, "Email already registered", None

        try:
            hashed_pw = self.hash_password(password)
            customer_id = self.db.create_customer(name, email, hashed_pw, age)
            return True, "Registration successful!", customer_id
        except Exception as e:
            return False, f"Registration failed: {str(e)}", None

    def login(self, email: str, password: str) -> tuple[bool, str, dict or None]:
        """
        Login user.
        Returns (success: bool, message: str, customer_data: dict or None)
        """
        if not email or not password:
            return False, "Email and password required", None

        customer = self.db.get_customer(email)
        if not customer:
            return False, "Customer not found", None

        hashed_pw = self.hash_password(password)
        if customer["password"] == hashed_pw:
            return True, "Login successful!", customer
        else:
            return False, "Invalid password", None
