#!/usr/bin/env python3
"""
Cinema City IMAX watcher — следит за появлением новых дат сеансов
фильма "Odyssea" (The Odyssey, Christopher Nolan) в формате IMAX 70mm
в Cinema City Flora (Praha) и шлёт уведомление в Telegram, как только
появляются новые даты (например, после 24.08.2026).

Использует публичный (без ключа) JSON API cinemacity.cz — тот же,
что и сам сайт.
"""

import json
import os
import sys
import urllib.request
from datetime import date, timedelta
from pathlib import Path

# --- Настройки ---
TENANT_ID = "10101"          # Cinema City Česká republika
CINEMA_ID = "1052"           # Cinema City Flora (IMAX zál)
ATTR = "70-mm"                # атрибут IMAX 70mm формата
LANG = "cs_CZ"
FILM_NAME_HINT = "odyssea"    # доп. проверка по названию (на случай др. 70mm фильма)

LOOKAHEAD_DAYS = 90            # на сколько дней вперёд проверяем даты
STATE_FILE = Path(__file__).parent / "state" / "dates.json"

TELEGRAM_BOT_TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN")
TELEGRAM_CHAT_ID = os.environ.get("TELEGRAM_CHAT_ID")

BASE = f"https://www.cinemacity.cz/cz/data-api-service/v1/quickbook/{TENANT_ID}"


def http_get_json(url: str) -> dict:
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
    with urllib.request.urlopen(req, timeout=20) as resp:
        return json.loads(resp.read().decode("utf-8"))


def fetch_available_dates() -> list[str]:
    until = (date.today() + timedelta(days=LOOKAHEAD_DAYS)).isoformat()
    url = f"{BASE}/dates/in-cinema/{CINEMA_ID}/until/{until}?attr={ATTR}&lang={LANG}"
    data = http_get_json(url)
    return sorted(data.get("body", {}).get("dates", []))


def fetch_events_for_date(day: str) -> list[dict]:
    url = f"{BASE}/film-events/in-cinema/{CINEMA_ID}/at-date/{day}?attr={ATTR}&lang={LANG}"
    data = http_get_json(url)
    body = data.get("body", {})
    films = {f["id"]: f.get("name", "") for f in body.get("films", [])}
    events = []
    for ev in body.get("events", []):
        film_name = films.get(ev.get("filmId"), "")
        if FILM_NAME_HINT not in film_name.lower():
            continue
        events.append({
            "date": day,
            "time": ev.get("eventDateTime", "")[11:16],
            "auditorium": ev.get("auditorium"),
            "sold_out": ev.get("soldOut"),
            "availability": ev.get("availabilityRatio"),
            "link": ev.get("bookingRouterLaunchLink"),
        })
    return events


def load_state() -> set[str]:
    if STATE_FILE.exists():
        return set(json.loads(STATE_FILE.read_text(encoding="utf-8")))
    return set()


def save_state(dates: set[str]) -> None:
    STATE_FILE.parent.mkdir(parents=True, exist_ok=True)
    STATE_FILE.write_text(json.dumps(sorted(dates), ensure_ascii=False, indent=2), encoding="utf-8")


def send_telegram(text: str) -> None:
    if not TELEGRAM_BOT_TOKEN or not TELEGRAM_CHAT_ID:
        print("TELEGRAM_BOT_TOKEN / TELEGRAM_CHAT_ID не заданы — вывожу в лог:\n", text)
        return
    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
    payload = json.dumps({
        "chat_id": TELEGRAM_CHAT_ID,
        "text": text,
        "parse_mode": "HTML",
        "disable_web_page_preview": False,
    }).encode("utf-8")
    req = urllib.request.Request(url, data=payload, headers={"Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=20) as resp:
        resp.read()


def format_message(new_dates: list[str], events_by_date: dict[str, list[dict]]) -> str:
    lines = ["🎬 <b>Odyssea IMAX 70mm — открылись новые даты!</b>", ""]
    for d in new_dates:
        lines.append(f"📅 <b>{d}</b>")
        evs = events_by_date.get(d, [])
        if not evs:
            lines.append("  (дата открыта, сеансы ещё без деталей)")
            continue
        for ev in evs:
            status = "🔴 SOLD OUT" if ev["sold_out"] else "🟢 доступно"
            lines.append(f"  {ev['time']} — {status}")
            if ev.get("link") and not ev["sold_out"]:
                lines.append(f"  👉 {ev['link']}")
        lines.append("")
    lines.append("Сайт: https://www.cinemacity.cz/films/odyssea/7268s2r")
    return "\n".join(lines)


def main() -> None:
    current_dates = fetch_available_dates()
    known_dates = load_state()

    if not known_dates:
        # первый запуск — просто сохраняем текущее состояние, не спамим
        save_state(set(current_dates))
        print(f"Инициализировано. Известные даты: {current_dates}")
        return

    new_dates = sorted(set(current_dates) - known_dates)

    if new_dates:
        events_by_date = {d: fetch_events_for_date(d) for d in new_dates}
        msg = format_message(new_dates, events_by_date)
        send_telegram(msg)
        print("Отправлено уведомление:\n", msg)
    else:
        print(f"Новых дат нет. Текущие даты: {current_dates}")

    save_state(set(current_dates))


if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        print(f"Ошибка: {e}", file=sys.stderr)
        sys.exit(1)
