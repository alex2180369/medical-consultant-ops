# Состояние проекта (чекпоинт)

**Кодовое слово для продолжения:** `Привет, начинаем работу`

**Дата сохранения:** 2026-06-08

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
| `/opt/medical_consultant/` | Docker-приложение (frontend + backend) |
| `/opt/medical_consultant/.env` | Секреты приложения (API-ключи заполнены) |
| `/opt/medical_consultant/docker-compose.yml` | Frontend на `127.0.0.1:8080` |

**Образы:** `alex2180369/medical_consultant:frontend`, `:backend`

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

- Сайт открывается по HTTPS ✅
- API-ключи в backend загружены ✅
- GitHub Actions Health Monitor проходит без предупреждений ✅
- README полный: `/opt/medical-consultant-ops/README.md`
