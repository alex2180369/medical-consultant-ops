#!/usr/bin/env python3
"""Локальная служба устранения неисправностей (cron/systemd)."""

from __future__ import annotations

import json
import sys
from datetime import UTC, datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from healthcheck.checks import load_config, run_all_checks
from notifications.notifier import send_notification
from remediation.actions import remediate_from_report

LOG_PATH = Path("/var/log/medical-consultant-ops/watchdog.log")


def _log(event: dict) -> None:
    LOG_PATH.parent.mkdir(parents=True, exist_ok=True)
    with LOG_PATH.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(event, ensure_ascii=False) + "\n")


def main() -> int:
    config = load_config()
    report = run_all_checks(config)
    status = report["status"]

    if status == "ok":
        _log({"timestamp": datetime.now(UTC).isoformat(), "status": "ok"})
        return 0

    failed = ", ".join(report["failed"])
    send_notification(
        "Проблема на сервере",
        f"Статус: {status}\nОшибки: {failed}",
        priority="high",
        tags=["warning"],
    )

    actions = remediate_from_report(report, config["COMPOSE_DIR"])
    after = run_all_checks(config)

    action_text = "\n".join(
        f"- {item.action}: {'OK' if item.ok else 'FAIL'} ({item.message})"
        for item in actions
    )
    send_notification(
        "Результат автоустранения",
        f"Было: {status} ({failed})\nСтало: {after['status']}\n{action_text}",
        priority="default" if after["status"] == "ok" else "high",
        tags=["wrench"],
    )

    _log(
        {
            "timestamp": datetime.now(UTC).isoformat(),
            "before": report,
            "after": after,
            "actions": [item.__dict__ for item in actions],
        }
    )
    return 0 if after["status"] == "ok" else 1


if __name__ == "__main__":
    raise SystemExit(main())
