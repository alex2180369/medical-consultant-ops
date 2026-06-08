#!/usr/bin/env python3
"""Проверка снаружи (GitHub Actions)."""

from __future__ import annotations

import json
import os
import sys
import time

import httpx


def main() -> int:
    site_url = os.environ.get("SITE_URL", "https://помощники-консультанты.рф").rstrip("/")
    ops_token = os.environ.get("OPS_TOKEN", "").strip()
    remediate_url = os.environ.get("REMEDIATE_URL", f"{site_url}/ops/remediate")

    checks = {
        "frontend": f"{site_url}/",
        "backend_health": f"{site_url}/health",
        "ops_status": f"{site_url}/ops/status",
    }

    report: dict[str, object] = {"site_url": site_url, "checks": {}, "failed": []}
    with httpx.Client(timeout=20, follow_redirects=True) as client:
        for name, url in checks.items():
            started = time.perf_counter()
            try:
                response = client.get(url)
                latency_ms = round((time.perf_counter() - started) * 1000, 1)
                ok = response.status_code < 400
                if name == "ops_status" and ok:
                    payload = response.json()
                    ok = payload.get("status") in {"ok", "degraded"}
                    if payload.get("status") == "critical":
                        ok = False
                    report["ops_payload"] = payload
                report["checks"][name] = {
                    "ok": ok,
                    "status_code": response.status_code,
                    "latency_ms": latency_ms,
                }
                if not ok:
                    report["failed"].append(name)
            except Exception as exc:  # noqa: BLE001
                report["checks"][name] = {"ok": False, "error": str(exc)}
                report["failed"].append(name)

    report["status"] = "ok" if not report["failed"] else "critical"
    print(json.dumps(report, ensure_ascii=False, indent=2))

    if report["failed"] and ops_token:
        try:
            with httpx.Client(timeout=60) as client:
                response = client.post(
                    remediate_url,
                    headers={"X-Ops-Token": ops_token},
                    params={"source": "github-actions"},
                )
                print(f"remediate_status={response.status_code}")
        except Exception as exc:  # noqa: BLE001
            print(f"remediate_error={exc}")

    return 0 if report["status"] == "ok" else 1


if __name__ == "__main__":
    raise SystemExit(main())
