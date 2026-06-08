"""Служба оповещения о событиях мониторинга."""

from __future__ import annotations

import os
from pathlib import Path
from typing import Any

import httpx
from dotenv import load_dotenv


def _load_env() -> None:
    load_dotenv(Path(__file__).resolve().parents[1] / ".env")


def send_notification(
    title: str,
    message: str,
    *,
    priority: str = "default",
    tags: list[str] | None = None,
) -> dict[str, Any]:
    """Отправить уведомление через ntfy и/или Telegram."""
    _load_env()
    results: dict[str, Any] = {}

    ntfy_topic = os.environ.get("NTFY_TOPIC", "").strip()
    if ntfy_topic:
        results["ntfy"] = _send_ntfy(title, message, priority=priority, tags=tags)

    telegram_token = os.environ.get("TELEGRAM_BOT_TOKEN", "").strip()
    telegram_chat = os.environ.get("TELEGRAM_CHAT_ID", "").strip()
    if telegram_token and telegram_chat:
        results["telegram"] = _send_telegram(
            telegram_token, telegram_chat, f"*{title}*\n{message}"
        )

    return results


def _send_ntfy(
    title: str,
    message: str,
    *,
    priority: str,
    tags: list[str] | None,
) -> dict[str, Any]:
    topic = os.environ["NTFY_TOPIC"]
    server = os.environ.get("NTFY_SERVER", "https://ntfy.sh").rstrip("/")
    headers = {
        "Title": title,
        "Priority": priority,
        "Tags": ",".join(tags or ["medical", "server"]),
    }
    try:
        response = httpx.post(
            f"{server}/{topic}",
            content=message.encode("utf-8"),
            headers=headers,
            timeout=15,
        )
        return {"ok": response.status_code < 400, "status_code": response.status_code}
    except Exception as exc:  # noqa: BLE001
        return {"ok": False, "error": str(exc)}


def _send_telegram(token: str, chat_id: str, text: str) -> dict[str, Any]:
    try:
        response = httpx.post(
            f"https://api.telegram.org/bot{token}/sendMessage",
            json={"chat_id": chat_id, "text": text, "parse_mode": "Markdown"},
            timeout=15,
        )
        data = response.json()
        return {"ok": data.get("ok", False), "response": data}
    except Exception as exc:  # noqa: BLE001
        return {"ok": False, "error": str(exc)}
