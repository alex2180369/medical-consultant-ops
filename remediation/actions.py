"""Действия службы устранения неисправностей."""

from __future__ import annotations

import subprocess
from dataclasses import dataclass
from typing import Any


@dataclass
class ActionResult:
    """Результат remedial-действия."""

    action: str
    ok: bool
    message: str


def _run(command: list[str], *, cwd: str | None = None, timeout: int = 120) -> ActionResult:
    action = command[0] if command else "unknown"
    try:
        result = subprocess.run(
            command,
            cwd=cwd,
            capture_output=True,
            text=True,
            timeout=timeout,
            check=True,
        )
        output = (result.stdout or result.stderr or "ok").strip()
        return ActionResult(action=" ".join(command[:3]), ok=True, message=output[:500])
    except Exception as exc:  # noqa: BLE001
        return ActionResult(action=" ".join(command[:3]), ok=False, message=str(exc))


def reload_nginx() -> ActionResult:
    return _run(["systemctl", "reload", "nginx"])


def restart_backend(compose_dir: str) -> ActionResult:
    return _run(
        ["docker", "compose", "restart", "backend"],
        cwd=compose_dir,
    )


def restart_frontend(compose_dir: str) -> ActionResult:
    return _run(
        ["docker", "compose", "restart", "frontend"],
        cwd=compose_dir,
    )


def recreate_backend(compose_dir: str) -> ActionResult:
    return _run(
        ["docker", "compose", "up", "-d", "--force-recreate", "backend"],
        cwd=compose_dir,
        timeout=180,
    )


def restart_all(compose_dir: str) -> ActionResult:
    return _run(
        ["docker", "compose", "up", "-d"],
        cwd=compose_dir,
        timeout=180,
    )


def remediate_from_report(report: dict[str, Any], compose_dir: str) -> list[ActionResult]:
    """Выбрать и выполнить действия по результатам health-check."""
    failed = set(report.get("failed", []))
    actions: list[ActionResult] = []

    if "docker_medical_consultant_backend" in failed or "backend_local" in failed:
        actions.append(recreate_backend(compose_dir))
    if "docker_medical_consultant_frontend" in failed or "frontend_local" in failed:
        actions.append(restart_frontend(compose_dir))
    if {"frontend_public", "backend_public"} & failed and "nginx" not in failed:
        actions.append(reload_nginx())
    if {"frontend_public", "backend_public", "frontend_local", "backend_local"} & failed:
        actions.append(restart_all(compose_dir))

    if not actions:
        actions.append(ActionResult("noop", True, "Автоматические действия не требуются"))

    return actions
