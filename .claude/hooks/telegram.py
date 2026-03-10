#!/usr/bin/env python3
"""
Claude Code hook — Telegram notifications.

Usage (invoked by Claude Code hooks via settings.json):
  python3 .claude/hooks/telegram.py stop
  python3 .claude/hooks/telegram.py post_tool
  python3 .claude/hooks/telegram.py notification
"""

import json
import os
import sys
import urllib.request
import urllib.parse
from datetime import datetime, timezone
from pathlib import Path


# ── Config ───────────────────────────────────────────────────────────────────

def load_config() -> dict:
    """Load .env from .claude/hooks/.env relative to cwd."""
    env_path = Path(".claude/hooks/.env")
    config = {}
    if env_path.exists():
        for line in env_path.read_text().splitlines():
            line = line.strip()
            if line and not line.startswith("#") and "=" in line:
                key, _, value = line.partition("=")
                config[key.strip()] = value.strip()
    return config


# ── Telegram API ─────────────────────────────────────────────────────────────

def send_telegram(token: str, chat_id: str, message: str, silent: bool = True) -> bool:
    """Send a message via Telegram Bot API. Returns True on success."""
    url = f"https://api.telegram.org/bot{token}/sendMessage"
    data = urllib.parse.urlencode({
        "chat_id": chat_id,
        "text": message,
        "parse_mode": "HTML",
        "disable_notification": "true" if silent else "false",
    }).encode()
    try:
        req = urllib.request.Request(url, data=data, method="POST")
        with urllib.request.urlopen(req, timeout=10) as resp:
            return resp.status == 200
    except Exception as e:
        print(f"[telegram hook] send failed: {e}", file=sys.stderr)
        return False


# ── Transcript helpers ────────────────────────────────────────────────────────

def get_turn_elapsed_minutes(transcript_path: str) -> float:
    """
    Read transcript JSONL, find last user message timestamp,
    return elapsed minutes from then to now.
    """
    try:
        path = Path(transcript_path)
        if not path.exists():
            return 0.0

        lines = path.read_text().splitlines()
        last_user_ts = None

        for line in reversed(lines):
            line = line.strip()
            if not line:
                continue
            try:
                entry = json.loads(line)
            except Exception:
                continue
            if entry.get("type") == "user" and entry.get("message", {}).get("role") == "user":
                ts_str = entry.get("timestamp")
                if ts_str:
                    last_user_ts = datetime.fromisoformat(ts_str.replace("Z", "+00:00"))
                    break

        if last_user_ts is None:
            return 0.0

        return (datetime.now(timezone.utc) - last_user_ts).total_seconds() / 60.0

    except Exception as e:
        print(f"[telegram hook] transcript timing error: {e}", file=sys.stderr)
        return 0.0


def get_last_assistant_message(transcript_path: str) -> str:
    """Extract the last assistant text response from the transcript."""
    try:
        path = Path(transcript_path)
        if not path.exists():
            return ""

        lines = path.read_text().splitlines()

        for line in reversed(lines):
            line = line.strip()
            if not line:
                continue
            try:
                entry = json.loads(line)
            except Exception:
                continue
            if entry.get("type") != "assistant":
                continue

            content = entry.get("message", {}).get("content", [])
            if isinstance(content, list):
                for block in content:
                    if isinstance(block, dict) and block.get("type") == "text":
                        text = block.get("text", "").strip()
                        if text:
                            return text[:300] + ("…" if len(text) > 300 else "")
            elif isinstance(content, str) and content.strip():
                text = content.strip()
                return text[:300] + ("…" if len(text) > 300 else "")

        return ""
    except Exception as e:
        print(f"[telegram hook] transcript summary error: {e}", file=sys.stderr)
        return ""


# ── Event handlers ────────────────────────────────────────────────────────────

def handle_stop(payload: dict, config: dict, token: str, chat_id: str):
    """Send turn completion notification based on elapsed time."""
    silent_below = float(config.get("SILENT_BELOW_MINUTES", 2))
    long_task = float(config.get("LONG_TASK_MINUTES", 10))
    transcript_path = payload.get("transcript_path", "")

    elapsed = get_turn_elapsed_minutes(transcript_path)

    if elapsed < silent_below:
        return

    elapsed_str = f"{int(elapsed)} min"

    if elapsed >= long_task:
        summary = get_last_assistant_message(transcript_path)
        text = f"⏱ <b>Wallet — tarea larga ({elapsed_str})</b>"
        if summary:
            text += f"\n\n{summary}"
    else:
        text = f"✅ <b>Wallet — tarea completada ({elapsed_str})</b>"

    send_telegram(token, chat_id, text)


def handle_post_tool(payload: dict, token: str, chat_id: str):
    """Detect test runs and notify pass/fail."""
    if payload.get("tool_name") != "Bash":
        return

    command = payload.get("tool_input", {}).get("command", "")
    tool_response = payload.get("tool_response", {})
    output = tool_response.get("output", "") or tool_response.get("stdout", "") or ""
    exit_code = tool_response.get("exit_code") or 0

    message = detect_test_run(command, output, int(exit_code))
    if message:
        send_telegram(token, chat_id, message)


def detect_test_run(command: str, output: str, exit_code: int) -> str | None:
    """Returns formatted message if Bash call was a test run, else None."""
    import re

    if "pytest" in command:
        if exit_code == 0:
            match = re.search(r"(\d+ passed[^\n]*)", output)
            summary = match.group(1) if match else "passed"
            return f"✅ Tests BE: {summary}"
        else:
            match = re.search(r"(\d+ failed[^\n]*)", output)
            summary = match.group(1) if match else "failed"
            return f"❌ Tests BE fallaron: {summary}"

    if "npm run type-check" in command:
        if exit_code == 0:
            return "✅ FE type-check: sin errores"
        else:
            lines = [l for l in output.splitlines() if "error TS" in l]
            count = len(lines)
            return f"❌ FE type-check: {count} error{'es' if count != 1 else ''}"

    if "npm run lint" in command:
        if exit_code == 0:
            return "✅ FE lint: sin errores"
        else:
            import re
            match = re.search(r"(\d+) problem", output)
            count = match.group(1) if match else "?"
            return f"❌ FE lint: {count} problema{'s' if count != '1' else ''}"

    if "npm run test" in command or "vitest" in command:
        if exit_code == 0:
            import re
            match = re.search(r"Tests\s+(\d+ passed[^\n]*)", output)
            summary = match.group(1) if match else "passed"
            return f"✅ Tests FE: {summary}"
        else:
            import re
            match = re.search(r"Tests\s+(\d+ failed[^\n]*)", output)
            summary = match.group(1) if match else "failed"
            return f"❌ Tests FE fallaron: {summary}"

    return None


def get_last_ask_user_question(transcript_path: str) -> str:
    """
    Find the last AskUserQuestion tool call in the transcript and format
    it as question + options for display in Telegram.
    """
    try:
        path = Path(transcript_path)
        if not path.exists():
            return ""

        lines = path.read_text().splitlines()

        for line in reversed(lines):
            line = line.strip()
            if not line:
                continue
            try:
                entry = json.loads(line)
            except Exception:
                continue

            if entry.get("type") != "assistant":
                continue

            content = entry.get("message", {}).get("content", [])
            if not isinstance(content, list):
                continue

            for block in content:
                if not isinstance(block, dict):
                    continue
                if block.get("type") != "tool_use":
                    continue
                if block.get("name") != "AskUserQuestion":
                    continue

                questions = block.get("input", {}).get("questions", [])
                if not questions:
                    continue

                parts = []
                for q in questions:
                    parts.append(f"<b>{q.get('question', '')}</b>")
                    for opt in q.get("options", []):
                        label = opt.get("label", "")
                        desc = opt.get("description", "")
                        parts.append(f"  • {label}" + (f" — {desc}" if desc else ""))

                return "\n".join(parts)

        return ""
    except Exception as e:
        print(f"[telegram hook] ask_user_question read failed: {e}", file=sys.stderr)
        return ""


def handle_notification(payload: dict, token: str, chat_id: str):
    """Forward Claude's notification to Telegram, enriched with last assistant message."""
    message = payload.get("message", "")
    # Debug: log full payload keys and message
    if not message:
        return

    notification_type = payload.get("notification_type", "")

    if notification_type == "permission_prompt":
        text = f"🔐 <b>Wallet — Permiso requerido</b>\n\n{message}"
    else:
        text = f"💬 <b>Wallet — Claude necesita tu input</b>"
        generic_messages = {"claude code needs your attention", "needs your attention"}
        if message.strip().lower() in generic_messages:
            transcript_path = payload.get("transcript_path", "")
            context = get_last_ask_user_question(transcript_path)
            if not context:
                context = get_last_assistant_message(transcript_path)
            if context:
                text += f"\n\n{context}"
        else:
            text += f"\n\n{message}"

    send_telegram(token, chat_id, text, silent=False)


# ── Entrypoint ────────────────────────────────────────────────────────────────

def main():
    if len(sys.argv) < 2:
        sys.exit(0)

    event = sys.argv[1]
    try:
        payload = json.load(sys.stdin)
    except Exception:
        sys.exit(0)

    config = load_config()
    token = config.get("TELEGRAM_TOKEN", "")
    chat_id = config.get("TELEGRAM_CHAT_ID", "")

    if not token or not chat_id:
        sys.exit(0)

    if event == "stop":
        handle_stop(payload, config, token, chat_id)
    elif event == "post_tool":
        handle_post_tool(payload, token, chat_id)
    elif event == "notification":
        handle_notification(payload, token, chat_id)


if __name__ == "__main__":
    main()
