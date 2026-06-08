# Medical Consultant Ops

Система мониторинга, автоустранения неисправностей и оповещений для проекта **Медицинский консультант**.

Сайт: [https://помощники-консультанты.рф/](https://помощники-консультанты.рф/)  
Сервер: `130.49.148.74`  
Приложение: `/opt/medical_consultant`  
Ops-службы: `/opt/medical-consultant-ops`

---

## Содержание

1. [Архитектура](#архитектура)
2. [Служба мониторинга](#1-служба-мониторинга)
3. [Служба устранения неисправностей](#2-служба-устранения-неисправностей)
4. [Служба оповещения](#3-служба-оповещения)
5. [Структура проекта](#структура-проекта)
6. [Установка на сервере](#установка-на-сервере)
7. [Конфигурация (.env)](#конфигурация-env)
8. [Публикация на GitHub](#публикация-на-github)
9. [Локальный монитор на ПК](#локальный-монитор-на-пк)
10. [Просмотр логов (Dozzle)](#просмотр-логов-dozzle)
11. [Полезные команды](#полезные-команды)
12. [Устранение неполадок](#устранение-неполадок)

---

## Архитектура

```
┌─────────────────────┐         каждые 5 мин
│   GitHub Actions    │ ─────────────────────────► https://помощники-консультанты.рф
│  (внешний контроль) │         /ops/status, /health
└─────────┬───────────┘
          │ при сбое
          ▼
┌─────────────────────┐         POST /ops/remediate
│  Ops API (systemd)  │ ◄────────────────────────── GitHub Actions
│  порт 127.0.0.1:9000│
└─────────┬───────────┘
          │
          ▼
┌─────────────────────┐         каждые 3 мин
│ Watchdog (systemd)  │ ──────► docker restart / nginx reload
└─────────┬───────────┘
          │
          ▼
┌─────────────────────┐
│  ntfy / Telegram    │ ──────► push-уведомления на телефон
└─────────────────────┘
```

**Nginx** проксирует:
- `/` → Docker frontend (`127.0.0.1:8080`)
- `/ops/` → Ops API (`127.0.0.1:9000`)

---

## 1. Служба мониторинга

Внешний контроль с **GitHub Actions** — проверка каждые **5 минут** независимо от сервера.

### Публичные эндпоинты

| Метод | URL | Описание |
|-------|-----|----------|
| `GET` | `/ops/status` | Полный отчёт о состоянии всех систем |
| `GET` | `/ops/health` | Краткий статус: `ok`, `degraded`, `critical` |

Пример: [https://помощники-консультанты.рф/ops/status](https://помощники-консультанты.рф/ops/status)

### Что проверяется

| Проверка | Описание |
|----------|----------|
| `frontend_public` | Главная страница по HTTPS |
| `backend_public` | `/health` по HTTPS |
| `frontend_local` | Frontend на `127.0.0.1:8080` |
| `backend_local` | Backend health через nginx |
| `database` | SQLite-файл существует и читается |
| `docker_medical_consultant_backend` | Контейнер backend запущен и healthy |
| `docker_medical_consultant_frontend` | Контейнер frontend запущен |
| `nginx` | Служба nginx активна |
| `ssl_cert` | SSL-сертификат, срок действия > 14 дней |
| `disk` | Свободное место на диске < 90% |
| `api_keys` | `AITUNNEL_API_KEY` и `PROXYAPI_API_KEY` заполнены |

### Статусы

| Статус | Значение |
|--------|----------|
| `ok` | Всё работает |
| `degraded` | Некритичные проблемы (SSL скоро истечёт, диск заполняется) |
| `critical` | Сайт или контейнеры недоступны |

### GitHub Actions

Файл: `.github/workflows/health-monitor.yml`

При сбое автоматически:
1. Запускает `healthcheck/check_remote.py`
2. Вызывает `/ops/remediate` на сервере
3. Отправляет уведомление в ntfy
4. Создаёт GitHub Issue с меткой `incident`

---

## 2. Служба устранения неисправностей

### Локальный watchdog (systemd timer)

- **Служба:** `medical-consultant-watchdog.service`
- **Таймер:** `medical-consultant-watchdog.timer` — каждые **3 минуты**
- **Лог:** `/var/log/medical-consultant-ops/watchdog.log`

### Действия при сбоях

| Проблема | Действие |
|----------|----------|
| Backend недоступен | `docker compose up -d --force-recreate backend` |
| Frontend недоступен | `docker compose restart frontend` |
| Публичный сайт не отвечает | `systemctl reload nginx` |
| Множественные сбои | `docker compose up -d` |

### Ручной запуск устранения

```bash
curl -X POST "https://помощники-консультанты.рф/ops/remediate" \
  -H "X-Ops-Token: ВАШ_OPS_TOKEN"
```

Токен хранится в `/opt/medical-consultant-ops/.env` → `OPS_TOKEN`.

---

## 3. Служба оповещения

### ntfy.sh (основной канал)

1. Установите приложение [ntfy](https://ntfy.sh) на телефон
2. Подпишитесь на топик: **`medical-consultant-ops`**
3. Готово — уведомления приходят автоматически

События:
- сбой на сервере
- результат автоустранения
- сбой проверки с GitHub Actions

### Telegram (опционально)

Заполните в `.env`:
```
TELEGRAM_BOT_TOKEN=...
TELEGRAM_CHAT_ID=...
```

### Dozzle — просмотр логов Docker

На сервере запущен контейнер `medical_consultant_dozzle` на `127.0.0.1:9999`.

С локального ПК:

```bash
ssh -L 9999:127.0.0.1:9999 root@130.49.148.74
```

Откройте в браузере: [http://localhost:9999](http://localhost:9999)

### Локальный дашборд

Файл `notifications/local-monitor/index.html` — веб-панель для браузера на вашем компьютере. Показывает статус всех проверок, обновляется каждую минуту.

---

## Структура проекта

```
medical-consultant-ops/
├── .github/workflows/
│   └── health-monitor.yml      # GitHub Actions: внешний мониторинг
├── healthcheck/
│   ├── checks.py               # Все проверки состояния
│   └── check_remote.py         # Скрипт для GitHub Actions
├── remediation/
│   ├── actions.py              # Действия автоустранения
│   └── watchdog.py             # Локальный watchdog (cron/systemd)
├── notifications/
│   ├── notifier.py             # Отправка в ntfy / Telegram
│   └── local-monitor/
│       └── index.html          # Дашборд для локального ПК
├── deploy/
│   ├── install.sh              # Установка на сервер
│   ├── push-to-github.sh       # Публикация на GitHub
│   └── docker-compose.monitoring.yml  # Dozzle
├── ops_api.py                  # HTTP API (status, remediate, notify)
├── requirements.txt
├── .env.example
└── README.md
```

---

## Установка на сервере

### Первичная установка

```bash
cd /opt/medical-consultant-ops
sudo bash deploy/install.sh
```

Скрипт:
1. Создаёт Python venv и устанавливает зависимости
2. Генерирует `.env` и `OPS_TOKEN` (если файла нет)
3. Запускает Dozzle
4. Устанавливает `medical-consultant-ops-api` (systemd)
5. Устанавливает `medical-consultant-watchdog` (systemd timer)

### Systemd-службы

| Служба | Назначение |
|--------|------------|
| `medical-consultant-ops-api` | HTTP API мониторинга (`127.0.0.1:9000`) |
| `medical-consultant-watchdog.timer` | Автоустранение каждые 3 мин |

### Nginx

В `/etc/nginx/sites-available/medical_consultant` добавлен блок:

```nginx
location /ops/ {
    proxy_pass http://127.0.0.1:9000;
    ...
}
```

---

## Конфигурация (.env)

Скопируйте шаблон:

```bash
cp .env.example .env
```

| Переменная | Описание |
|------------|----------|
| `SITE_URL` | Публичный URL сайта |
| `OPS_TOKEN` | Токен для `/ops/remediate` и `/ops/notify` |
| `NTFY_TOPIC` | Топик ntfy для уведомлений |
| `NTFY_SERVER` | Сервер ntfy (по умолчанию `https://ntfy.sh`) |
| `TELEGRAM_BOT_TOKEN` | Токен Telegram-бота (опционально) |
| `TELEGRAM_CHAT_ID` | ID чата Telegram (опционально) |
| `COMPOSE_DIR` | Путь к docker-compose приложения |
| `DATA_DIR` | Путь к данным (SQLite) |
| `SSL_CERT_PATH` | Путь к SSL-сертификату |
| `FRONTEND_LOCAL` | Локальный URL frontend |
| `BACKEND_HEALTH_LOCAL` | Локальный URL backend health |

Генерация токена:

```bash
openssl rand -hex 32
```

> **Важно:** `.env` не коммитится в git (см. `.gitignore`). Секреты храните только на сервере.

---

## Публикация на GitHub

### 1. Авторизация

```bash
gh auth login
```

### 2. Публикация репозитория

```bash
bash /opt/medical-consultant-ops/deploy/push-to-github.sh alex2180369/medical-consultant-ops
```

### 3. Настройка GitHub Actions

В репозитории: **Settings → Secrets and variables → Actions**

**Secrets:**

| Имя | Значение |
|-----|----------|
| `OPS_TOKEN` | Из `/opt/medical-consultant-ops/.env` |

**Variables:**

| Имя | Значение |
|-----|----------|
| `SITE_URL` | `https://помощники-консультанты.рф` |
| `NTFY_TOPIC` | `medical-consultant-ops` |
| `REMEDIATE_URL` | `https://помощники-консультанты.рф/ops/remediate` |

### 4. Проверка

В репозитории: **Actions → Health Monitor → Run workflow**

---

## Локальный монитор на ПК

1. Скопируйте файл на компьютер:

```bash
scp root@130.49.148.74:/opt/medical-consultant-ops/notifications/local-monitor/index.html ~/Desktop/
```

2. Откройте `index.html` в браузере
3. URL по умолчанию: `https://помощники-консультанты.рф/ops/status`
4. Статус обновляется автоматически каждые 60 секунд

---

## Просмотр логов (Dozzle)

```bash
# Терминал 1: SSH-туннель
ssh -L 9999:127.0.0.1:9999 root@130.49.148.74

# Браузер
http://localhost:9999
```

Доступные контейнеры:
- `medical_consultant_frontend`
- `medical_consultant_backend`
- `medical_consultant_dozzle`

---

## Полезные команды

```bash
# Статус всех систем
curl -s https://помощники-консультанты.рф/ops/status | python3 -m json.tool

# Краткий health-check
curl -s https://помощники-консультанты.рф/ops/health

# Статус ops-служб
systemctl status medical-consultant-ops-api
systemctl status medical-consultant-watchdog.timer

# Ручной запуск watchdog
systemctl start medical-consultant-watchdog.service

# Лог watchdog
tail -f /var/log/medical-consultant-ops/watchdog.log

# Тестовое уведомление
curl -X POST "https://помощники-консультанты.рф/ops/notify" \
  -H "X-Ops-Token: ВАШ_OPS_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"title":"Тест","message":"Проверка оповещений"}'

# Перезапуск ops-api
systemctl restart medical-consultant-ops-api

# Переустановка
bash /opt/medical-consultant-ops/deploy/install.sh
```

---

## Устранение неполадок

### Сайт не открывается

```bash
# Проверить контейнеры
docker ps -a

# Проверить nginx
systemctl status nginx
nginx -t

# Проверить ops
curl -s https://помощники-консультанты.рф/ops/status
```

### Ops API не отвечает

```bash
systemctl restart medical-consultant-ops-api
journalctl -u medical-consultant-ops-api -n 50
curl -s http://127.0.0.1:9000/ops/health
```

### Watchdog не запускается

```bash
systemctl daemon-reload
systemctl enable --now medical-consultant-watchdog.timer
journalctl -u medical-consultant-watchdog -n 20
```

### GitHub Actions падает

1. Проверьте Secret `OPS_TOKEN` в GitHub
2. Убедитесь, что `/ops/status` доступен извне
3. Проверьте DNS: домен должен указывать только на `130.49.148.74`

### Не приходят уведомления ntfy

1. Проверьте подписку на топик `medical-consultant-ops` в приложении
2. Проверьте `NTFY_TOPIC` в `.env`
3. Тест: см. команду «Тестовое уведомление» выше

### После изменения .env приложения

```bash
cd /opt/medical_consultant
docker compose up -d --force-recreate backend
```

> `docker compose restart` не перечитывает `.env` — нужен `--force-recreate`.

---

## Связанные пути на сервере

| Путь | Описание |
|------|----------|
| `/opt/medical_consultant/` | Основное приложение (docker-compose) |
| `/opt/medical-consultant-ops/` | Службы мониторинга |
| `/opt/medical_consultant/.env` | Секреты приложения |
| `/opt/medical-consultant-ops/.env` | Секреты ops-служб |
| `/var/log/medical-consultant-ops/` | Логи watchdog |

---

## Лицензия

Проект для личного использования. Репозиторий: `alex2180369/medical-consultant-ops`
