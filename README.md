# Medical Consultant Ops

Три службы для мониторинга, автоустранения неисправностей и оповещений.

## 1. Служба мониторинга (GitHub)

Внешний контроль каждые 5 минут через GitHub Actions.

**Проверяет:**
- фронтенд (`/`)
- backend (`/health`)
- расширенный статус (`/ops/status`) — Docker, БД, SSL, nginx, API-ключи

**Эндпоинты на сервере:**
- `GET /ops/status` — полный отчёт
- `GET /ops/health` — краткий статус

## 2. Служба устранения неисправностей

**На сервере (каждые 3 мин):** `medical-consultant-watchdog.timer`

Действия при сбоях:
- пересоздание backend
- перезапуск frontend
- `nginx reload`
- `docker compose up -d`

**По запросу:** `POST /ops/remediate` с заголовком `X-Ops-Token`

GitHub Actions при сбое автоматически вызывает remediate.

## 3. Служба оповещения

- **ntfy.sh** — push на телефон (приложение ntfy)
- **Telegram** — опционально
- **Dozzle** — просмотр логов Docker через SSH-туннель
- **local-monitor/index.html** — дашборд на локальном ПК

## Установка на сервере

```bash
cd /opt/medical-consultant-ops
sudo bash deploy/install.sh
```

## Публикация на GitHub

```bash
cd /opt/medical-consultant-ops
git init
git add .
git commit -m "Add monitoring, remediation and notification services"
gh repo create medical-consultant-ops --public --source=. --push
```

## GitHub Secrets / Variables

| Имя | Тип | Описание |
|-----|-----|----------|
| `OPS_TOKEN` | Secret | Токен из `/opt/medical-consultant-ops/.env` |
| `SITE_URL` | Variable | `https://помощники-консультанты.рф` |
| `NTFY_TOPIC` | Variable | Топик ntfy для алертов |

## Локальный монитор

```bash
# Откройте в браузере:
notifications/local-monitor/index.html
```

## Dozzle (логи)

```bash
ssh -L 9999:127.0.0.1:9999 root@130.49.148.74
# http://localhost:9999
```

## ntfy

1. Установите приложение [ntfy](https://ntfy.sh)
2. Подпишитесь на топик из `.env` (`NTFY_TOPIC`)
