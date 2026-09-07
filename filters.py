"""공고 선별 규칙.

적용 순서
  1) 제외 키워드   — 하나라도 걸리면 무조건 버림 (가장 우선)
  2) 마감 여부     — 마감일이 지났거나 상태가 '마감'이면 버림
  3) 게시일 범위   — 오늘로부터 lookback_days 이내
  4) 포함 키워드   — require_keyword 가 true 면 최소 1개 필요
  5) 중복 발송     — 이미 보낸 공고는 버림
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import date, timedelta

from .config import Config
from .parse import Notice


@dataclass
class FilterStats:
    total: int = 0
    dropped_excluded: int = 0
    dropped_expired: int = 0
    dropped_old: int = 0
    dropped_no_keyword: int = 0
    dropped_duplicate: int = 0
    kept: int = 0

    def as_line(self) -> str:
        return (
            f"수집 {self.total} → 채택 {self.kept} "
            f"(제외키워드 {self.dropped_excluded}, 마감 {self.dropped_expired}, "
            f"기간초과 {self.dropped_old}, 키워드없음 {self.dropped_no_keyword}, "
            f"중복 {self.dropped_duplicate})"
        )


def _hits(title: str, words: list[str]) -> list[str]:
    low = title.lower()
    return [w for w in words if w and w.lower() in low]


def apply_filters(
    notices: list[Notice],
    cfg: Config,
    today: date,
    seen_keys: set[str],
    stats: FilterStats,
) -> list[Notice]:
    cutoff = today - timedelta(days=cfg.lookback_days)
    kept: list[Notice] = []

    for n in notices:
        stats.total += 1

        # 1) 제외 키워드
        if _hits(n.title, cfg.exclude_keywords):
            stats.dropped_excluded += 1
            continue

        # 2) 마감
        if cfg.exclude_expired:
            if n.deadline is not None and n.deadline < today:
                stats.dropped_expired += 1
                continue
            if n.closed_flag:
                stats.dropped_expired += 1
                continue
            if n.deadline is None and cfg.unknown_deadline == "exclude":
                stats.dropped_expired += 1
                continue

        # 3) 게시일 범위
        if n.posted is not None:
            if n.posted < cutoff:
                stats.dropped_old += 1
                continue
        elif cfg.unknown_posted == "exclude":
            # 목록에 게시일이 없는 게시판은 몇 달 전 공고도 계속 후보로 남는다.
            # 그게 부담스러우면 이 설정으로 아예 버릴 수 있다.
            stats.dropped_old += 1
            continue

        # 4) 포함 키워드
        matched = _hits(n.title, cfg.include_keywords)
        if cfg.require_keyword and not matched:
            stats.dropped_no_keyword += 1
            continue
        n.matched_keywords = matched

        # 5) 중복
        if cfg.dedupe and n.key in seen_keys:
            stats.dropped_duplicate += 1
            continue

        kept.append(n)
        stats.kept += 1

    # 최신순 정렬 (게시일 미상은 뒤로)
    kept.sort(key=lambda x: (x.posted is None, -(x.posted.toordinal() if x.posted else 0)))
    return kept[: cfg.max_per_institution]
