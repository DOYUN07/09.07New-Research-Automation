"""마감일 확인 — 상세 페이지를 열어 실제 접수기간을 읽는다.

왜 필요한가
  게시판 목록에 마감일이 없는 기관이 20곳 넘는다. 그 공고들은 마감 여부를
  판단할 근거가 없어 전부 통과했고, 이미 끝난 공고가 메일에 섞였다.

무엇을 하는가
  키워드·기간 필터를 통과했지만 마감일을 모르는 공고만 골라
  상세 페이지를 한 번씩 열어 접수기간을 읽는다.

왜 필터 뒤에 하는가
  수집 단계에서 전부 열면 하루 400건이 넘는다. 필터를 통과한 것만 열면
  보통 10~40건이라 실행 시간이 1~2분 늘어나는 선에서 끝난다.
"""
from __future__ import annotations

import time
from dataclasses import dataclass
from datetime import date

import requests

from . import deadline as deadline_rules
from .config import Config
from .parse import Notice


@dataclass
class VerifyStats:
    checked: int = 0
    found: int = 0
    always_open: int = 0
    closed: int = 0
    failed: int = 0
    skipped: int = 0

    def as_line(self) -> str:
        return (
            f"마감일 확인 {self.checked}건 → 찾음 {self.found}, 상시 {self.always_open}, "
            f"마감확인 {self.closed}, 실패 {self.failed}"
            + (f", 한도초과로 건너뜀 {self.skipped}" if self.skipped else "")
        )


def _fetch(session: requests.Session, url: str, timeout: int) -> str | None:
    try:
        r = session.get(url, timeout=timeout, allow_redirects=True, verify=False)
        if r.status_code >= 400:
            return None
        if not r.encoding or r.encoding.lower() in ("iso-8859-1", "ascii"):
            r.encoding = r.apparent_encoding or "utf-8"
        return r.text if len(r.text) > 300 else None
    except Exception:  # noqa: BLE001
        return None


def verify(
    notices: list[Notice],
    cfg: Config,
    today: date,
    session: requests.Session,
) -> tuple[list[Notice], VerifyStats]:
    """마감일을 모르는 공고의 상세 페이지를 열어 채운다. 목록을 그대로 돌려준다."""
    stats = VerifyStats()
    if not cfg.verify_deadline:
        return notices, stats

    targets = [
        n
        for n in notices
        if n.deadline is None and n.note != "상시" and n.url and n.url.startswith("http")
    ]
    limit = cfg.verify_max
    if len(targets) > limit:
        stats.skipped = len(targets) - limit
        targets = targets[:limit]

    for i, n in enumerate(targets):
        if i:
            time.sleep(cfg.verify_delay)
        stats.checked += 1
        html = _fetch(session, n.url, cfg.verify_timeout)
        if html is None:
            stats.failed += 1
            continue

        # 게시일을 알면 그걸 기준으로 연도를 정한다 (마감일은 게시일보다 앞설 수 없다)
        dl, note, closed = deadline_rules.from_detail_html(
            html, n.posted or today, anchor_is_posted=n.posted is not None
        )
        if closed:
            n.closed_flag = True
            stats.closed += 1
        if dl:
            n.deadline = dl
            n.deadline_source = "상세"
            stats.found += 1
        elif note == "상시":
            n.note = "상시"
            stats.always_open += 1

    return notices, stats


def drop_expired(
    notices: list[Notice], cfg: Config, today: date
) -> tuple[list[Notice], int]:
    """마감이 확인된 공고를 걷어낸다. (남은 목록, 걷어낸 수)"""
    if not cfg.exclude_expired:
        return notices, 0
    kept = []
    dropped = 0
    for n in notices:
        if n.closed_flag:
            dropped += 1
            continue
        if n.deadline is not None and n.deadline < today:
            dropped += 1
            continue
        if n.deadline is None and n.note != "상시" and cfg.unknown_deadline == "exclude":
            dropped += 1
            continue
        kept.append(n)
    return kept, dropped
