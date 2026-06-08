"""Проверки состояния всех критических компонентов."""

from __future__ import annotations

import os
import shutil
import sqlite3
import subprocess
import time
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import httpx


@dataclass
class CheckResult:
    """Результат одной проверки."""

    name: str
    ok: bool
    message: str
    details: dict[str, Any] | None = None


def _http_check(url: str, timeout: float = 10.0) -> tuple[bool, str, dict[str, Any]]:
    started = time.perf_counter()
    try:
        with httpx.Client(timeout=timeout, follow_redirects=True) as client:
            response = client.get(url)
        latency_ms = round((time.perf_counter() - started) * 1000, 1)
        ok = response.status_code < 400
        return ok, f"HTTP {response.status_code}", {
            "status_code": response.status_code,
            "latency_ms": latency_ms,
        }
    except Exception as exc:  # noqa: BLE001
        return False, str(exc), {"latency_ms": None}


def check_frontend_public(site_url: str) -> CheckResult:
    ok, message, details = _http_check(site_url)
    return CheckResult("frontend_public", ok, message, details)


def check_backend_public(site_url: str) -> CheckResult:
    ok, message, details = _http_check(f"{site_url.rstrip('/')}/health")
    return CheckResult("backend_public", ok, message, details)


def check_frontend_local(url: str) -> CheckResult:
    ok, message, details = _http_check(url)
    return CheckResult("frontend_local", ok, message, details)


def check_backend_local(url: str) -> CheckResult:
    ok, message, details = _http_check(url)
    return CheckResult("backend_local", ok, message, details)


def check_database(data_dir: str) -> CheckResult:
    db_path = Path(data_dir) / "medical_consultant.sqlite3"
    if not db_path.exists():
        return CheckResult("database", False, "Файл БД не найден")
    try:
        size = db_path.stat().st_size
        with sqlite3.connect(f"file:{db_path}?mode=ro", uri=True) as conn:
            conn.execute("SELECT 1").fetchone()
        return CheckResult(
            "database",
            True,
            "SQLite доступна",
            {"path": str(db_path), "size_bytes": size},
        )
    except Exception as exc:  # noqa: BLE001
        return CheckResult("database", False, str(exc))


def check_docker_container(name: str) -> CheckResult:
    try:
        result = subprocess.run(
            [
                "docker",
                "inspect",
                name,
                "--format",
                "{{.State.Status}}|{{if .State.Health}}{{.State.Health.Status}}{{else}}none{{end}}",
            ],
            capture_output=True,
            text=True,
            timeout=10,
            check=True,
        )
        status, health = result.stdout.strip().split("|", 1)
        ok = status == "running" and health in {"healthy", "none"}
        return CheckResult(
            f"docker_{name}",
            ok,
            f"status={status}, health={health}",
            {"status": status, "health": health},
        )
    except Exception as exc:  # noqa: BLE001
        return CheckResult(f"docker_{name}", False, str(exc))


def check_nginx() -> CheckResult:
    try:
        subprocess.run(["systemctl", "is-active", "nginx"], check=True, capture_output=True)
        return CheckResult("nginx", True, "active")
    except Exception as exc:  # noqa: BLE001
        return CheckResult("nginx", False, str(exc))


def check_ssl_cert(cert_path: str, warn_days: int = 14) -> CheckResult:
    path = Path(cert_path)
    if not path.exists():
        return CheckResult("ssl_cert", False, "Сертификат не найден")
    try:
        result = subprocess.run(
            ["openssl", "x509", "-enddate", "-noout", "-in", str(path)],
            capture_output=True,
            text=True,
            check=True,
        )
        end_raw = result.stdout.strip().removeprefix("notAfter=")
        expire_at = datetime.strptime(end_raw, "%b %d %H:%M:%S %Y %Z").replace(tzinfo=UTC)
        days_left = (expire_at - datetime.now(UTC)).days
        ok = days_left > warn_days
        return CheckResult(
            "ssl_cert",
            ok,
            f"Осталось {days_left} дн.",
            {"days_left": days_left, "expires": expire_at.isoformat()},
        )
    except Exception as exc:  # noqa: BLE001
        return CheckResult("ssl_cert", False, str(exc))


def check_disk(path: str = "/", warn_percent: int = 90) -> CheckResult:
    usage = shutil.disk_usage(path)
    used_percent = round(usage.used / usage.total * 100, 1)
    ok = used_percent < warn_percent
    return CheckResult(
        "disk",
        ok,
        f"Занято {used_percent}%",
        {
            "used_percent": used_percent,
            "free_gb": round(usage.free / 1024**3, 2),
        },
    )


def check_api_keys(env_path: str) -> CheckResult:
    path = Path(env_path)
    if not path.exists():
        return CheckResult("api_keys", False, ".env не найден")
    values: dict[str, str] = {}
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        values[key.strip()] = value.strip()
    aitunnel = bool(values.get("AITUNNEL_API_KEY"))
    proxyapi = bool(values.get("PROXYAPI_API_KEY"))
    ok = aitunnel and proxyapi
    return CheckResult(
        "api_keys",
        ok,
        "Ключи настроены" if ok else "Отсутствуют API-ключи",
        {"aitunnel": aitunnel, "proxyapi": proxyapi},
    )


def run_all_checks(config: dict[str, str]) -> dict[str, Any]:
    """Запустить все проверки и вернуть сводный отчёт."""
    site_url = config["SITE_URL"]
    checks = [
        check_frontend_public(site_url),
        check_backend_public(site_url),
        check_frontend_local(config["FRONTEND_LOCAL"]),
        check_backend_local(config["BACKEND_HEALTH_LOCAL"]),
        check_database(config["DATA_DIR"]),
        check_docker_container("medical_consultant_backend"),
        check_docker_container("medical_consultant_frontend"),
        check_nginx(),
        check_ssl_cert(config["SSL_CERT_PATH"]),
        check_disk(),
        check_api_keys(str(Path(config["COMPOSE_DIR"]) / ".env")),
    ]
    failed = [item.name for item in checks if not item.ok]
    if not failed:
        status = "ok"
    elif any(name.endswith("_public") or name.startswith("docker_") for name in failed):
        status = "critical"
    else:
        status = "degraded"

    return {
        "status": status,
        "timestamp": datetime.now(UTC).isoformat(),
        "site_url": site_url,
        "failed": failed,
        "checks": {
            item.name: {
                "ok": item.ok,
                "message": item.message,
                "details": item.details or {},
            }
            for item in checks
        },
    }


def load_config() -> dict[str, str]:
    """Загрузить конфигурацию из окружения."""
    from dotenv import load_dotenv

    load_dotenv(Path(__file__).resolve().parents[1] / ".env")
    return {
        "SITE_URL": os.environ.get("SITE_URL", "https://помощники-консультанты.рф"),
        "FRONTEND_LOCAL": os.environ.get("FRONTEND_LOCAL", "http://127.0.0.1:8080"),
        "BACKEND_HEALTH_LOCAL": os.environ.get(
            "BACKEND_HEALTH_LOCAL", "http://127.0.0.1:8080/health"
        ),
        "DATA_DIR": os.environ.get("DATA_DIR", "/opt/medical_consultant/data"),
        "SSL_CERT_PATH": os.environ.get(
            "SSL_CERT_PATH",
            "/etc/letsencrypt/live/xn----8sbwajchcjfcbbgf7bsco4ipcr.xn--p1ai/fullchain.pem",
        ),
        "COMPOSE_DIR": os.environ.get("COMPOSE_DIR", "/opt/medical_consultant"),
    }
