"""이미 보낸 공고 기록 — 같은 공고를 두 번 보내지 않기 위한 것."""
from __future__ import annotations

import json
from datetime import date, datetime, timedelta
from pathlib import Path

from .config import ROOT
from .parse import Notice

STATE_PATH = ROOT / "state" / "seen.json"
KEEP_DAYS = 180


def load_seen(path: Path | None = None) -> dict:
    p = path or STATE_PATH
    if not p.exists():
        return {"items": {}}
    try:
        with p.open(encoding="utf-8") as fh:
            data = json.load(fh)
        data.setdefault("items", {})
        return data
    except (json.JSONDecodeError, OSError):
        return {"items": {}}


def seen_keys(data: dict) -> set[str]:
    return set(data.get("items", {}).keys())


def record(data: dict, notices: list[Notice], today: date) -> dict:
    items = data.setdefault("items", {})
    stamp = today.isoformat()
    for n in notices:
        items[n.key] = {
            "sent": stamp,
            "inst": n.institution_id,
            "title": n.title[:140],
        }
    return data


def prune(data: dict, today: date) -> dict:
    cutoff = today - timedelta(days=KEEP_DAYS)
    items = data.get("items", {})
    for key in list(items.keys()):
        raw = items[key].get("sent", "")
        try:
            if datetime.strptime(raw, "%Y-%m-%d").date() < cutoff:
                del items[key]
        except ValueError:
            continue
    return data


def save_seen(data: dict, path: Path | None = None) -> None:
    p = path or STATE_PATH
    p.parent.mkdir(parents=True, exist_ok=True)
    with p.open("w", encoding="utf-8") as fh:
        json.dump(data, fh, ensure_ascii=False, indent=1, sort_keys=True)
