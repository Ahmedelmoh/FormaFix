"""
ai_client.py — FormaFix
========================
Unified AI client — بيدعم 3 providers:
  - Anthropic (Claude)
  - Google Gemini
  - Ollama (محلي)

الاستخدام:
  from ai_client import ask_ai
  response = ask_ai(messages, system_prompt)
"""

import json
import os
import urllib.request
import urllib.error
from dotenv import load_dotenv

load_dotenv()

# ── Config من الـ .env ───────────────────────────────────────────────────────
PROVIDER = os.getenv("AI_PROVIDER", "gemini").lower()

ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY", "")
GEMINI_API_KEY    = os.getenv("GEMINI_API_KEY", "")
GEMINI_MODEL      = os.getenv("GEMINI_MODEL", "gemini-2.0-flash")
OLLAMA_MODEL      = os.getenv("OLLAMA_MODEL", "llama3")
OLLAMA_URL        = os.getenv("OLLAMA_URL", "http://localhost:11434")


# ─────────────────────────────────────────────────────────────────────────────
# Anthropic (Claude)
# ─────────────────────────────────────────────────────────────────────────────
def _call_anthropic(messages: list, system: str) -> str:
    payload = json.dumps({
        "model":      "claude-sonnet-4-20250514",
        "max_tokens": 2000,
        "system":     system,
        "messages":   messages,
    }).encode("utf-8")

    req = urllib.request.Request(
        "https://api.anthropic.com/v1/messages",
        data=payload,
        headers={
            "Content-Type":      "application/json",
            "x-api-key":         ANTHROPIC_API_KEY,
            "anthropic-version": "2023-06-01",
        },
        method="POST"
    )

    with urllib.request.urlopen(req) as resp:
        data = json.loads(resp.read().decode("utf-8"))
        return data["content"][0]["text"]


# ─────────────────────────────────────────────────────────────────────────────
# Google Gemini
# ─────────────────────────────────────────────────────────────────────────────
def _call_gemini(messages: list, system: str) -> str:
    """
    Gemini API بتستخدم format مختلف:
    - system prompt بيتحط في systemInstruction
    - messages بتتحول من {role, content} لـ {role, parts}
    """

    # تحويل الـ messages لـ Gemini format
    gemini_messages = []
    for msg in messages:
        role = "user" if msg["role"] == "user" else "model"
        gemini_messages.append({
            "role":  role,
            "parts": [{"text": msg["content"]}]
        })

    payload = json.dumps({
        "system_instruction": {
            "parts": [{"text": system}]
        },
        "contents": gemini_messages,
        "generationConfig": {
            "maxOutputTokens": 8000,
            "temperature":     0.7,
        }
    }).encode("utf-8")

    url = ( f"https://generativelanguage.googleapis.com/v1beta/"
           f"models/gemini-2.5-flash:generateContent" 
           f"?key={GEMINI_API_KEY}" )

    req = urllib.request.Request(
        url,
        data=payload,
        headers={"Content-Type": "application/json"},
        method="POST"
    )

    with urllib.request.urlopen(req) as resp:
        data = json.loads(resp.read().decode("utf-8"))
        return data["candidates"][0]["content"]["parts"][0]["text"]


# ─────────────────────────────────────────────────────────────────────────────
# Ollama (محلي)
# ─────────────────────────────────────────────────────────────────────────────
def _call_ollama(messages: list, system: str) -> str:
    """
    Ollama بيستخدم OpenAI-compatible API.
    لازم Ollama يكون شغّال على الجهاز:
      ollama serve
      ollama pull llama3
    """

    # ضيف الـ system كأول رسالة
    full_messages = [{"role": "system", "content": system}] + messages

    payload = json.dumps({
        "model":    OLLAMA_MODEL,
        "messages": full_messages,
        "stream":   False,
        "options":  {"num_predict": 2000}
    }).encode("utf-8")

    req = urllib.request.Request(
        f"{OLLAMA_URL}/api/chat",
        data=payload,
        headers={"Content-Type": "application/json"},
        method="POST"
    )

    with urllib.request.urlopen(req, timeout=60) as resp:
        data = json.loads(resp.read().decode("utf-8"))
        return data["message"]["content"]


# ─────────────────────────────────────────────────────────────────────────────
# الدالة الرئيسية — استخدم دي في كل الكود
# ─────────────────────────────────────────────────────────────────────────────
def ask_ai(messages: list, system_prompt: str = "") -> str:
    """
    بيبعت messages للـ AI provider المختار في .env
    وبيرجع الرد كـ string.

    Parameters
    ----------
    messages      : list of {"role": "user"/"assistant", "content": "..."}
    system_prompt : التعليمات الثابتة للـ AI

    Returns
    -------
    str : رد الـ AI
    """
    try:
        if PROVIDER == "anthropic":
            if not ANTHROPIC_API_KEY:
                raise ValueError("ANTHROPIC_API_KEY is missing in .env")
            return _call_anthropic(messages, system_prompt)

        elif PROVIDER == "gemini":
            if not GEMINI_API_KEY:
                raise ValueError("GEMINI_API_KEY is missing in .env")
            return _call_gemini(messages, system_prompt)

        elif PROVIDER == "ollama":
            return _call_ollama(messages, system_prompt)

        else:
            raise ValueError(
                f"Unknown AI_PROVIDER '{PROVIDER}'. "
                "Choose: anthropic / gemini / ollama"
            )

    except urllib.error.HTTPError as e:
        error_body = e.read().decode("utf-8")
        raise RuntimeError(f"[{PROVIDER}] HTTP {e.code}: {error_body}")

    except urllib.error.URLError as e:
        if PROVIDER == "ollama":
            raise RuntimeError(
                "[Ollama] Cannot connect. Make sure Ollama is running:\n"
                "  ollama serve\n"
                f"  ollama pull {OLLAMA_MODEL}"
            )
        raise RuntimeError(f"[{PROVIDER}] Connection error: {e}")


# ─────────────────────────────────────────────────────────────────────────────
# اختبار سريع
# ─────────────────────────────────────────────────────────────────────────────
if __name__ == "__main__":
    print(f"Testing AI client — Provider: {PROVIDER}")
    print("-" * 40)

    response = ask_ai(
        messages=[{"role": "user", "content": "Say hello in one sentence."}],
        system_prompt="You are a helpful physiotherapy assistant."
    )

    print(f"Response: {response}")
    print("\n[OK] AI client is working!")