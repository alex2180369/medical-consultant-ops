# Состояние проекта (чекпоинт)

**Кодовое слово для продолжения:** `Привет, начинаем работу`

**Дата сохранения:** 2026-06-15

---

## Сервер

| Параметр | Значение |
|----------|----------|
| ОС | Ubuntu 26.04 LTS |
| IP | `130.49.148.74` |
| Домен | `https://помощники-консультанты.рф/` |
| Пользователь | `root` |

## Приложение

| Путь | Описание |
|------|----------|
| `/opt/medical_consultant_app/` | **Активный** Docker-стек (PostgreSQL + backend + frontend) |
| `/opt/medical_consultant_app/.env` | Секреты (AITUNNEL; Appwrite-переменные очищены) |
| `/opt/medical_consultant_app/docker-compose.yml` | Frontend `127.0.0.1:8080`, PostgreSQL `127.0.0.1:5432` |
| `/opt/medical_consultant/` | Старый стек (остановлен) |

**Образы:** локальная сборка `medical_consultant_app-backend`, `medical_consultant_app-frontend`

**GitHub:** [alex2180369/medical_consultant](https://github.com/alex2180369/medical_consultant) — PR #1 смержен, fix `@types/react` в main (`1dc1bd9`)

## Инфраструктура

- **Nginx** на хосте: HTTP→HTTPS, `/` → `:8080`, `/ops/` → `:9000`
- **SSL:** Let's Encrypt, автообновление certbot
- **DNS:** только `130.49.148.74` (запись Beget удалена)

## Ops-службы (`/opt/medical-consultant-ops/`)

| Служба | Статус |
|--------|--------|
| Мониторинг (GitHub Actions) | ✅ Работает, actions v6/v8 (Node 24) |
| Автоустранение (watchdog) | ✅ Каждые 3 мин |
| Оповещения (ntfy) | ✅ Топик `medical-consultant-ops` |
| Dozzle (логи) | ✅ `127.0.0.1:9999` |

**GitHub:** [alex2180369/medical-consultant-ops](https://github.com/alex2180369/medical-consultant-ops)

**Эндпоинты:**
- `https://помощники-консультанты.рф/ops/status`
- `https://помощники-консультанты.рф/ops/health`

**Systemd:**
- `medical-consultant-ops-api`
- `medical-consultant-watchdog.timer`

## Что НЕ трогать без необходимости

- `.env` файлы (секреты)
- Nginx-конфиг certbot (HTTP-редирект на кириллический домен)
- После изменения `.env` приложения: `docker compose up -d --force-recreate backend`

## Последний известный статус

- Сайт открывается по HTTPS ✅ (`/health` → 200)
- Новый стек запущен из `/opt/medical_consultant_app` ✅
- PostgreSQL 16 в Docker, чистая БД ✅
- AITUNNEL API-ключ в backend загружен ✅
- **Appwrite удалён с сервера (2026-06-15)** — `/opt/appwrite`, nginx `/v1/`, `/console/`, `/images/` сняты; переменные Appwrite в `.env` пустые
- **Аутентификация:** планируется собственная email/password (не Appwrite)
- После изменения `.env`: `docker compose build frontend && docker compose up -d --force-recreate`
- README полный: `/opt/medical-consultant-ops/README.md`
