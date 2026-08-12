# Odyssea IMAX watcher

Следит за появлением новых дат сеансов фильма **Odyssea** (The Odyssey,
Christopher Nolan) в формате **IMAX 70mm** в Cinema City Flora (Praha)
и шлёт уведомление в Telegram, как только они открываются.

На момент настройки (12.08.2026) сеансы открыты только до **24.08.2026** —
это уже сохранено в `state/dates.json`, чтобы первый запуск не заспамил чат.
Как только Cinema City откроет новые даты (25.08 и позже), придёт сообщение
со списком дат, временем сеансов, статусом (доступно / sold out) и прямой
ссылкой на покупку.

## Как работает

1. GitHub Actions запускает `watch_imax.py` каждые 15 минут (можно поменять
   в `.github/workflows/imax-watch.yml`).
2. Скрипт дёргает публичный JSON API cinemacity.cz (тот же, что использует
   сам сайт) — без ключей и логина:
   - `.../dates/in-cinema/1052/until/<дата>?attr=70-mm` — список дат с IMAX 70mm сеансами
   - `.../film-events/in-cinema/1052/at-date/<дата>?attr=70-mm` — сеансы на конкретную дату
3. Сравнивает с сохранённым `state/dates.json`. Если появились новые даты —
   шлёт сообщение в Telegram и коммитит обновлённый state обратно в репозиторий.

## Установка

1. Создать приватный репозиторий на GitHub, залить туда эту папку.
2. В Settings → Secrets and variables → Actions добавить (можно использовать
   те же значения, что и для бота Sparta–Slavia):
   - `TELEGRAM_BOT_TOKEN`
   - `TELEGRAM_CHAT_ID`
3. Убедиться, что у Actions есть право на запись (Settings → Actions →
   General → Workflow permissions → **Read and write permissions**) — это
   нужно, чтобы workflow мог закоммитить обновлённый `state/dates.json`.
4. Запустить вручную первый раз (Actions → Odyssea IMAX watch → Run workflow),
   чтобы проверить, что всё работает и приходит тестовое сообщение при
   ручном форс-запуске.

## Локальный запуск (проверка)

```bash
export TELEGRAM_BOT_TOKEN=...
export TELEGRAM_CHAT_ID=...
python watch_imax.py
```

## Настройки

- `LOOKAHEAD_DAYS` в `watch_imax.py` — на сколько дней вперёд проверять (по умолчанию 90).
- Частота проверки — `cron` в workflow-файле (сейчас каждые 15 минут).
- Если понадобится следить за другим фильмом/кинотеатром — поменять
  `FILM_NAME_HINT`, `CINEMA_ID` в `watch_imax.py`.
