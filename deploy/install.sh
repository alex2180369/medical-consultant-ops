#!/bin/bash
set -euo pipefail

OPS_DIR="/opt/medical-consultant-ops"
COMPOSE_MONITOR="$OPS_DIR/deploy/docker-compose.monitoring.yml"

echo "==> Установка Python-зависимостей"
if [ ! -d "$OPS_DIR/.venv" ]; then
  python3 -m venv "$OPS_DIR/.venv"
fi
"$OPS_DIR/.venv/bin/pip" install -q -r "$OPS_DIR/requirements.txt"
PYTHON_BIN="$OPS_DIR/.venv/bin/python"

if [ ! -f "$OPS_DIR/.env" ]; then
  echo "==> Создание .env из шаблона"
  cp "$OPS_DIR/.env.example" "$OPS_DIR/.env"
  OPS_TOKEN=$(openssl rand -hex 32)
  sed -i "s/^OPS_TOKEN=$/OPS_TOKEN=$OPS_TOKEN/" "$OPS_DIR/.env"
  echo "Сгенерирован OPS_TOKEN (сохраните для GitHub Secrets): $OPS_TOKEN"
fi

echo "==> Запуск Dozzle"
docker compose -f "$COMPOSE_MONITOR" up -d

echo "==> Установка ops-api systemd service"
cat > /etc/systemd/system/medical-consultant-ops-api.service <<EOF
[Unit]
Description=Medical Consultant Ops API
After=network-online.target docker.service

[Service]
Type=simple
WorkingDirectory=$OPS_DIR
EnvironmentFile=$OPS_DIR/.env
ExecStart=$OPS_DIR/.venv/bin/python -m uvicorn ops_api:app --host 127.0.0.1 --port 9000
Restart=always
RestartSec=5

[Install]
WantedBy=multi-user.target
EOF

systemctl daemon-reload
systemctl enable --now medical-consultant-ops-api.service

echo "==> Установка watchdog systemd timer"
cat > /etc/systemd/system/medical-consultant-watchdog.service <<EOF
[Unit]
Description=Medical Consultant watchdog remediation
After=docker.service network-online.target

[Service]
Type=oneshot
WorkingDirectory=$OPS_DIR
ExecStart=$OPS_DIR/.venv/bin/python $OPS_DIR/remediation/watchdog.py
EOF

cat > /etc/systemd/system/medical-consultant-watchdog.timer <<'EOF'
[Unit]
Description=Run Medical Consultant watchdog every 3 minutes

[Timer]
OnBootSec=2min
OnUnitActiveSec=3min
AccuracySec=30s

[Install]
WantedBy=timers.target
EOF

systemctl daemon-reload
systemctl enable --now medical-consultant-watchdog.timer

echo "==> Готово"
echo "Status:  https://помощники-консультанты.рф/ops/status"
echo "Dozzle:  ssh -L 9999:127.0.0.1:9999 root@130.49.148.74  →  http://localhost:9999"
