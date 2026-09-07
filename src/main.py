"""진입점.

사용법
  python -m src.main                 정상 실행 (수집 → 필터 → 메일 발송 → 이력 저장)
  python -m src.main --dry-run       메일 발송·이력 저장 없이 결과만 out/brief.html 로
  python -m src.main --diagnose      34개 기관 수집 상태 점검 리포트 (out/diagnose.md)
  python -m src.main --diagnose --all  비활성 기관까지 전부 점검
"""
from __future__ import annotations

import argparse
import sys
import time
import traceback
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

from .config import ROOT, Config, Institution, load_config, load_institutions
from .fetch import FetchError, fetch, make_session
from .filters import FilterStats, apply_filters
from .mailer import MailNotConfigured, is_configured, send
from .parse import Notice, parse
from .render import render_html, render_text
from .store import load_seen, prune, record, save_seen, seen_keys

KST = ZoneInfo("Asia/Seoul")
OUT = ROOT / "out"


def today_kst():
    return datetime.now(KST).date()


# --------------------------------------------------------------- 수집


def collect(
    institutions: list[Institution], cfg: Config
) -> tuple[dict[str, list[Notice]], list[tuple[str, str]]]:
    session = make_session(cfg)
    raw: dict[str, list[Notice]] = {}
    failed: list[tuple[str, str]] = []

    for i, inst in enumerate(institutions):
        if i:
            time.sleep(cfg.delay_between)
        try:
            text = fetch(session, inst, cfg)
            notices = parse(text, inst, today_kst())
            if not notices:
                failed.append((inst.name, "목록을 인식하지 못했습니다"))
                raw[inst.id] = []
                print(f"  [!] {inst.name}: 목록 인식 실패")
                continue
            raw[inst.id] = notices
            print(f"  [+] {inst.name}: {len(notices)}건 수집")
        except FetchError as exc:
            failed.append((inst.name, str(exc)))
            raw[inst.id] = []
            print(f"  [!] {inst.name}: {exc}")
        except Exception as exc:  # noqa: BLE001
            failed.append((inst.name, f"{type(exc).__name__}: {exc}"))
            raw[inst.id] = []
            print(f"  [!] {inst.name}: {type(exc).__name__}: {exc}")
    return raw, failed


# --------------------------------------------------------------- 정상 실행


def run(dry_run: bool = False) -> int:
    cfg = load_config()
    institutions = [x for x in load_institutions() if x.enabled and x.url]
    today = today_kst()

    print(f"== 공고 브리핑 {today} (대상 {len(institutions)}개 기관) ==")
    raw, failed = collect(institutions, cfg)

    state = load_seen()
    known = seen_keys(state) if cfg.dedupe else set()
    stats = FilterStats()

    grouped: dict[str, list[Notice]] = {}
    empty: list[str] = []
    names = {i.id: i.name for i in institutions}
    failed_ids = {n for n, _ in failed}

    for inst in institutions:
        kept = apply_filters(raw.get(inst.id, []), cfg, today, known, stats)
        grouped[inst.id] = kept
        if not kept and inst.name not in failed_ids:
            empty.append(inst.name)

    total = sum(len(v) for v in grouped.values())
    print(f"-- {stats.as_line()}")

    html_body = render_html(grouped, names, today, cfg, empty, failed)
    text_body = render_text(grouped, names, today, cfg)

    OUT.mkdir(exist_ok=True)
    (OUT / "brief.html").write_text(html_body, encoding="utf-8")
    (OUT / "brief.txt").write_text(text_body, encoding="utf-8")
    print(f"-- 결과 저장: {OUT/'brief.html'}")

    if dry_run:
        print("-- dry-run: 발송·이력 저장을 건너뜁니다")
        return 0

    if total == 0 and not cfg.send_when_empty:
        print("-- 신규 공고 0건, send_when_empty=false → 발송하지 않습니다")
        return 0

    subject = f"{cfg.subject_prefix} {today.strftime('%m월 %d일')} 신규 {total}건"
    if not is_configured():
        print(
            "-- SMTP 미설정: 메일을 보내지 않았습니다.\n"
            "   GitHub Secrets에 SMTP_USER / SMTP_PASSWORD 를 등록하면 발송이 시작됩니다.\n"
            f"   지금 결과는 {OUT/'brief.html'} 에 저장되어 있습니다."
        )
        return 0

    try:
        send(subject, html_body, text_body, cfg.recipients, cfg.sender_name)
        print(f"-- 발송 완료: {', '.join(cfg.recipients)}")
    except MailNotConfigured as exc:
        print(f"-- 발송 건너뜀: {exc}")
        return 0
    except Exception as exc:  # noqa: BLE001
        print(f"-- 발송 실패: {type(exc).__name__}: {exc}")
        return 1

    # 발송에 성공했을 때만 이력에 기록한다
    sent = [n for v in grouped.values() for n in v]
    record(state, sent, today)
    prune(state, today)
    save_seen(state)
    print(f"-- 발송 이력 {len(sent)}건 기록")
    return 0


# --------------------------------------------------------------- 진단


def diagnose(include_disabled: bool = False, dump: bool = False) -> int:
    cfg = load_config()
    all_inst = load_institutions()
    targets = [x for x in all_inst if (x.enabled or include_disabled) and x.url]
    today = today_kst()

    dump_dir = OUT / "html"
    if dump:
        dump_dir.mkdir(parents=True, exist_ok=True)

    session = make_session(cfg)
    lines = [
        f"# 기관별 수집 진단 — {today}",
        "",
        f"대상 {len(targets)}곳 / 전체 {len(all_inst)}곳",
        "",
        "| 기관 | 상태 | 수집 | 최신 게시일 | 비고 |",
        "|---|---|---|---|---|",
    ]
    detail: list[str] = []
    ok = 0

    for i, inst in enumerate(targets):
        if i:
            time.sleep(cfg.delay_between)
        try:
            text = fetch(session, inst, cfg)
            notices = parse(text, inst, today_kst())
            if not notices:
                lines.append(f"| {inst.name} | ⚠️ | 0건 | — | 목록 인식 실패 |")
                if dump:
                    # 목록을 못 읽은 기관의 원본 HTML을 남겨 원인을 볼 수 있게 한다
                    (dump_dir / f"{inst.id}.html").write_text(text, encoding="utf-8")
                continue
            ok += 1
            dated = [n for n in notices if n.posted]
            newest = max((n.posted for n in dated), default=None)
            with_dl = sum(1 for n in notices if n.deadline)
            lines.append(
                f"| {inst.name} | ✅ | {len(notices)}건 | "
                f"{newest or '날짜 미인식'} | 마감일 파싱 {with_dl}/{len(notices)} |"
            )
            detail.append(f"\n### {inst.name}\n")
            detail.append(f"`{inst.url}`\n")
            for n in notices[:3]:
                detail.append(
                    f"- {n.title}\n"
                    f"  - 게시 `{n.posted}` / 마감 `{n.deadline}`\n"
                    f"  - {n.url}\n"
                )
        except Exception as exc:  # noqa: BLE001
            msg = str(exc).replace("|", "/")[:110]
            lines.append(f"| {inst.name} | ❌ | — | — | {msg} |")

    lines.append("")
    lines.append(f"**정상 {ok}곳 / 점검 {len(targets)}곳**")
    lines.append("")
    lines.append("---")
    lines.append("")
    lines.append("## 기관별 샘플 (상위 3건)")
    lines.extend(detail)

    OUT.mkdir(exist_ok=True)
    report = "\n".join(lines)
    (OUT / "diagnose.md").write_text(report, encoding="utf-8")
    print(report)
    return 0


# --------------------------------------------------------------- CLI


def main() -> int:
    ap = argparse.ArgumentParser(description="지원사업 공고 브리핑")
    ap.add_argument("--dry-run", action="store_true", help="발송·이력 저장 없이 결과만 생성")
    ap.add_argument("--diagnose", action="store_true", help="기관별 수집 상태 점검")
    ap.add_argument("--all", action="store_true", help="진단 시 비활성 기관도 포함")
    ap.add_argument(
        "--dump",
        action="store_true",
        help="진단 시 목록 인식에 실패한 기관의 원본 HTML을 out/html/ 에 저장",
    )
    args = ap.parse_args()

    try:
        if args.diagnose:
            return diagnose(include_disabled=args.all, dump=args.dump)
        return run(dry_run=args.dry_run)
    except Exception:  # noqa: BLE001
        traceback.print_exc()
        return 1


if __name__ == "__main__":
    sys.exit(main())
