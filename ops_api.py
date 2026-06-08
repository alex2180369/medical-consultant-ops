"""HTTP API: health-check, remediation, notifications."""

from __future__ import annotations

import os
from pathlib import Path
from typing import Any

from dotenv import load_dotenv
from fastapi import FastAPI, Header, HTTPException
from fastapi.middleware.cors import CORSMiddleware

from healthcheck.checks import load_config, run_all_checks
from notifications.notifier import send_notification
from remediation.actions import remediate_from_report

load_dotenv(Path(__file__).resolve().parent / ".env")

app = FastAPI(title="Medical Consultant Ops", version="1.0.0")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["GET", "POST"],
    allow_headers=["*"],
)


def _verify_token(token: str | None) -> None:
    expected = os.environ.get("OPS_TOKEN", "").strip()
    if not expected or token != expected:
        raise HTTPException(status_code=401, detail="Неверный токен")


@app.get("/ops/status")
def status() -> dict[str, Any]:
    """Публичный расширенный health-check."""
    return run_all_checks(load_config())


@app.get("/ops/health")
def health() -> dict[str, str]:
    """Короткий ping для GitHub Actions."""
    report = run_all_checks(load_config())
    return {"status": report["status"]}


@app.post("/ops/remediate")
def remediate(
    x_ops_token: str | None = Header(default=None),
    source: str = "manual",
) -> dict[str, Any]:
    """Запустить устранение неисправностей."""
    _verify_token(x_ops_token)
    config = load_config()
    before = run_all_checks(config)
    actions = remediate_from_report(before, config["COMPOSE_DIR"])
    after = run_all_checks(config)

    message = (
        f"Источник: {source}\n"
        f"Было: {before['status']} ({', '.join(before['failed']) or 'нет ошибок'})\n"
        f"Стало: {after['status']} ({', '.join(after['failed']) or 'нет ошибок'})"
    )
    send_notification("Автоустранение неисправности", message, priority="high", tags=["wrench"])

    return {
        "before": before,
        "after": after,
        "actions": [action.__dict__ for action in actions],
    }


@app.post("/ops/notify")
def notify(
    payload: dict[str, str],
    x_ops_token: str | None = Header(default=None),
) -> dict[str, Any]:
    """Отправить тестовое уведомление."""
    _verify_token(x_ops_token)
    title = payload.get("title", "Medical Consultant Ops")
    message = payload.get("message", "Тестовое сообщение")
    return send_notification(title, message)
