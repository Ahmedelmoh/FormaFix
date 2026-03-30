#!/usr/bin/env python
"""
setup.py — FormaFix Setup Script
==================================
Helps you configure FormaFix with API keys and test the setup.
Run this FIRST before starting the app.
"""

import os
import sys
import json
from pathlib import Path


def print_header(text: str):
    """Print a formatted header."""
    print("\n" + "=" * 60)
    print(f"  {text}")
    print("=" * 60)


def print_step(step: int, text: str):
    """Print a numbered step."""
    print(f"\n[Step {step}] {text}")


def check_python_version():
    """Check if Python 3.8+ is installed."""
    if sys.version_info < (3, 8):
        print("❌ Python 3.8+ is required!")
        print(f"   You have: {sys.version}")
        sys.exit(1)
    print(f"✅ Python {sys.version.split()[0]} detected")


def check_dependencies():
    """Check if all required packages are installed."""
    print_step(1, "Checking dependencies...")
    
    required_packages = [
        "flet",
        "opencv-python",
        "mediapipe",
        "numpy",
        "python-dotenv",
        "pyttsx3",
    ]
    
    missing = []
    for package in required_packages:
        try:
            __import__(package.replace("-", "_"))
            print(f"  ✅ {package}")
        except ImportError:
            print(f"  ❌ {package} (missing)")
            missing.append(package)
    
    if missing:
        print(f"\n⚠️  Missing packages: {', '.join(missing)}")
        print("   Run: pip install -r requirements.txt")
        response = input("   Install now? (y/n): ").strip().lower()
        if response == "y":
            os.system("pip install -r requirements.txt")
        else:
            print("   Skipped. Install manually with: pip install -r requirements.txt")
    else:
        print("\n✅ All dependencies installed!")


def setup_env_file():
    """Create and configure .env file."""
    print_step(2, "Configuring .env file...")
    
    env_file = Path(".env")
    example_file = Path(".env.example")
    
    if env_file.exists():
        print(f"  .env file already exists")
        response = input("  Update it? (y/n): ").strip().lower()
        if response != "y":
            return
    
    if not example_file.exists():
        print("  ⚠️  .env.example not found. Creating minimal .env...")
        with open(env_file, "w") as f:
            f.write("AI_PROVIDER=gemini\n")
            f.write("GEMINI_API_KEY=\n")
            f.write("ANTHROPIC_API_KEY=\n")
            f.write("OLLAMA_URL=http://localhost:11434\n")
    else:
        # Copy from example
        with open(example_file) as f:
            content = f.read()
        with open(env_file, "w") as f:
            f.write(content)
    
    print(f"  ✅ Created/updated .env file")
    
    # Ask for API key
    print_api_setup()


def print_api_setup():
    """Guide user through API setup."""
    print("\n" + "=" * 60)
    print("  Which AI provider do you want to use?")
    print("=" * 60)
    print("\n1. Google Gemini (Free tier, 2M requests/month)")
    print("   → Fast and reliable")
    print("   → Get key: https://makersuite.google.com/app/apikey")
    print("\n2. Anthropic Claude (Paid API)")
    print("   → High quality reasoning")
    print("   → Get key: https://console.anthropic.com/")
    print("\n3. Ollama (Local, no API key)")
    print("   → Fully private, offline")
    print("   → Install: https://ollama.ai")
    print("   → Run: ollama serve & ollama pull llama3")
    print("\n4. Skip for now (use default)")
    
    choice = input("\nEnter choice (1-4): ").strip()
    
    env_file = Path(".env")
    content = env_file.read_text() if env_file.exists() else ""
    
    if choice == "1":
        print("\n➜ Get your Gemini API key:")
        print("  1. Visit: https://makersuite.google.com/app/apikey")
        print("  2. Create a new API key")
        print("  3. Copy and paste it below")
        
        api_key = input("\nEnter Gemini API key (or press Enter to skip): ").strip()
        if api_key:
            content = update_env_var(content, "AI_PROVIDER", "gemini")
            content = update_env_var(content, "GEMINI_API_KEY", api_key)
            env_file.write_text(content)
            print("✅ Gemini API key configured!")
    
    elif choice == "2":
        print("\n➜ Get your Anthropic API key:")
        print("  1. Visit: https://console.anthropic.com/")
        print("  2. Create API key in account settings")
        print("  3. Copy and paste it below")
        
        api_key = input("\nEnter Anthropic API key (or press Enter to skip): ").strip()
        if api_key:
            content = update_env_var(content, "AI_PROVIDER", "anthropic")
            content = update_env_var(content, "ANTHROPIC_API_KEY", api_key)
            env_file.write_text(content)
            print("✅ Anthropic API key configured!")
    
    elif choice == "3":
        print("\n➜ Setup Ollama (local):")
        print("  1. Install Ollama: https://ollama.ai")
        print("  2. Open terminal and run:")
        print("     ollama pull llama3")
        print("     ollama serve")
        print("  3. Keep it running in background")
        
        content = update_env_var(content, "AI_PROVIDER", "ollama")
        env_file.write_text(content)
        print("✅ Ollama configured (local mode)")


def update_env_var(content: str, key: str, value: str) -> str:
    """Update or add environment variable in content."""
    lines = content.split("\n")
    found = False
    
    for i, line in enumerate(lines):
        if line.startswith(f"{key}="):
            lines[i] = f"{key}={value}"
            found = True
            break
    
    if not found:
        lines.append(f"{key}={value}")
    
    return "\n".join(lines)


def test_database():
    """Test database initialization."""
    print_step(3, "Initializing database...")
    
    try:
        from database_service import DatabaseService
        db = DatabaseService()
        print("  ✅ Database initialized successfully")
        
        # Test create customer
        test_customer_id = db.create_customer(
            "Test User",
            "test@example.com",
            "test_password"
        )
        print(f"  ✅ Test customer created (ID: {test_customer_id})")
    except Exception as e:
        print(f"  ❌ Database error: {e}")


def test_ai_client():
    """Test AI client configuration."""
    print_step(4, "Testing AI client...")
    
    try:
        from ai_client import ask_ai, PROVIDER
        print(f"  Current provider: {PROVIDER}")
        
        # Simple test
        test_messages = [
            {"role": "user", "content": "Say 'FormaFix is ready to go' in 5 words or less."}
        ]
        print("  Testing AI connection...")
        response = ask_ai(test_messages, "You are a helpful assistant.")
        
        print(f"  ✅ AI client working!")
        print(f"  Response: {response[:100]}...")
    except Exception as e:
        print(f"  ⚠️  AI client error: {e}")
        print("     Make sure your API key is correct and you're connected to the internet")


def test_pose_estimation():
    """Test MediaPipe setup."""
    print_step(5, "Testing pose estimation...")
    
    try:
        import mediapipe as mp
        print("  ✅ MediaPipe installed")
        
        from angle_calculator import get_all_angles
        print("  ✅ Angle calculator ready")
        
        from feedback_engine import FeedbackEngine
        print("  ✅ Feedback engine ready")
        
        from form_evaluator import FormEvaluator
        print("  ✅ Form evaluator ready")
    except Exception as e:
        print(f"  ❌ Pose estimation error: {e}")


def create_app_shortcut():
    """Create a shortcut to run the app."""
    print_step(6, "Creating app launcher...")
    
    if sys.platform == "win32":
        # Windows batch file
        batch_file = Path("run_app.bat")
        batch_file.write_text("@echo off\npython app.py\npause\n")
        print(f"  ✅ Created {batch_file}")
        print(f"     Double-click it to run the app!")
    else:
        # Unix shell script
        script_file = Path("run_app.sh")
        script_file.write_text("#!/bin/bash\npython app.py\n")
        os.chmod(script_file, 0o755)
        print(f"  ✅ Created {script_file}")
        print(f"     Run with: ./run_app.sh")


def show_next_steps():
    """Show user what to do next."""
    print_header("Setup Complete! 🎉")
    
    print("\nNext steps:")
    print("\n1. Verify your API key is working:")
    print("   python setup.py")
    
    print("\n2. Start the FormaFix app:")
    print("   python app.py")
    
    print("\n3. Create your account and start using FormaFix!")
    
    print("\nDocumentation:")
    print("  - Full guide: APP_README.md")
    print("  - API docs: See docstrings in code")
    
    print("\nTroubleshooting:")
    print("  - Missing packages? → pip install -r requirements.txt")
    print("  - API errors? → Check .env file has correct keys")
    print("  - Ollama issues? → Run 'ollama serve' first")
    
    print("\n" + "=" * 60)


def main():
    """Run the setup process."""
    print_header("FormaFix Setup Wizard")
    
    print("\nThis wizard will help you configure FormaFix.")
    print("It will:")
    print("  1. Check your Python version")
    print("  2. Install required packages")
    print("  3. Set up .env configuration")
    print("  4. Test AI client")
    print("  5. Initialize database")
    print("  6. Create app launcher")
    
    input("\nPress Enter to start...")
    
    try:
        check_python_version()
        check_dependencies()
        setup_env_file()
        test_database()
        test_ai_client()
        test_pose_estimation()
        create_app_shortcut()
        show_next_steps()
        
        print("\n✅ Setup complete! You can now run: python app.py")
    except KeyboardInterrupt:
        print("\n\n❌ Setup cancelled by user")
        sys.exit(1)
    except Exception as e:
        print(f"\n\n❌ Setup failed: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
