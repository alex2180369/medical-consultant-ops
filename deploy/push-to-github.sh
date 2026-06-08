#!/bin/bash
set -euo pipefail

REPO="${1:-alex2180369/medical-consultant-ops}"
OPS_DIR="/opt/medical-consultant-ops"

cd "$OPS_DIR"

if ! gh auth status >/dev/null 2>&1; then
  echo "Сначала выполните: gh auth login"
  exit 1
fi

gh repo create "${REPO#*/}" --public --source=. --remote=origin --push 2>/dev/null || {
  git remote remove origin 2>/dev/null || true
  git remote add origin "https://github.com/$REPO.git"
  git push -u origin main
}

echo ""
echo "Репозиторий: https://github.com/$REPO"
echo ""
echo "Добавьте в GitHub → Settings → Secrets and variables → Actions:"
echo "  Secret OPS_TOKEN = значение из /opt/medical-consultant-ops/.env"
echo "  Variable SITE_URL = https://помощники-консультанты.рф"
echo "  Variable NTFY_TOPIC = medical-consultant-ops"
