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

from . import archive, sheet
from .config import ROOT, Config, Institution, load_config, load_institutions
from .fetch import FetchError, fetch, make_session
from .filters import FilterStats, apply_filters
from .mailer import MailNotConfigured, is_configured, send
from .parse import Notice, parse
from .render import render_html, render_text
from .store import load_seen, prune, record, save_seen, seen_keys
from .verify import drop_expired, verify

KST = ZoneInfo("Asia/Seoul")
OUT = ROOT / "out"


def today_kst():
    return datetime.now(KST).date()


# --------------------------------------------------------------- 수집


RETRY_ROUND_WAIT = 45  # 접속 실패한 기관을 다시 시도하기 전 대기(초)


def _try_one(session, inst: Institution, cfg: Config) -> tuple[list[Notice], str | None]:
    """한 기관을 수집한다. (결과, 실패사유) 를 돌려준다."""
    try:
        text = fetch(session, inst, cfg)
        notices = parse(text, inst, today_kst())
        if not notices:
            return [], "목록을 인식하지 못했습니다"
        return notices, None
    except FetchError as exc:
        return [], str(exc)
    except Exception as exc:  # noqa: BLE001
        return [], f"{type(exc).__name__}: {exc}"


def _is_network_error(reason: str) -> bool:
    """다시 시도해볼 가치가 있는 실패인지 (일시적 차단·타임아웃 등)."""
    marks = (
        "Max retries",
        "timed out",
        "Timeout",
        "Connection",
        "ConnectionError",
        "너무 짧습니다",
        "HTTP 5",
        "HTTP 429",
        "HTTP 403",
    )
    return any(m in reason for m in marks)


def collect(
    institutions: list[Institution], cfg: Config
) -> tuple[dict[str, list[Notice]], list[tuple[str, str]]]:
    session = make_session(cfg)
    raw: dict[str, list[Notice]] = {}
    reasons: dict[str, str] = {}

    for i, inst in enumerate(institutions):
        if i:
            time.sleep(cfg.delay_between)
        notices, reason = _try_one(session, inst, cfg)
        raw[inst.id] = notices
        if reason:
            reasons[inst.id] = reason
            print(f"  [!] {inst.name}: {reason}")
        else:
            print(f"  [+] {inst.name}: {len(notices)}건 수집")

    # 재시도 라운드 — 정부 부처 사이트들이 특정 IP를 한동안 막는 일이 잦다.
    # 한 바퀴 다 돈 뒤 잠시 쉬었다가 접속 실패한 곳만 새 연결로 다시 시도한다.
    retryable = [x for x in institutions if _is_network_error(reasons.get(x.id, ""))]
    if retryable:
        print(f"-- 접속 실패 {len(retryable)}곳, {RETRY_ROUND_WAIT}초 후 재시도합니다")
        time.sleep(RETRY_ROUND_WAIT)
        session2 = make_session(cfg)
        for i, inst in enumerate(retryable):
            if i:
                time.sleep(cfg.delay_between * 2)
            notices, reason = _try_one(session2, inst, cfg)
            if not reason:
                raw[inst.id] = notices
                reasons.pop(inst.id, None)
                print(f"  [+] {inst.name}: 재시도 성공 — {len(notices)}건")
            else:
                print(f"  [!] {inst.name}: 재시도도 실패 — {reason}")

    names = {x.id: x.name for x in institutions}
    failed = [(names[k], v) for k, v in reasons.items()]
    return raw, failed


# --------------------------------------------------------------- 정상 실행


def run(dry_run: bool = False) -> int:
    cfg = load_config()
    all_inst = load_institutions()

    # 구글시트가 연결돼 있으면 키워드·수신자·기관을 시트 값으로 덮어쓴다.
    # 시트를 못 읽어도 저장소 설정으로 그대로 진행한다.
    all_inst, sheet_log = sheet.apply_all(cfg, all_inst)
    for line in sheet_log:
        print(f"-- {line}")

    institutions = [x for x in all_inst if x.enabled and x.url]
    today = today_kst()

    # 수신자를 어디서 읽었고 누구에게 갈 것인지 먼저 찍는다.
    # 'config.yaml 에 추가했는데 메일이 안 온다'의 원인이 대부분 여기 있다.
    print(f"== 공고 브리핑 {today} (대상 {len(institutions)}개 기관) ==")
    print(f"-- 수신자 출처: {cfg.recipients_source}")
    if cfg.recipients:
        for m in cfg.recipients:
            print(f"     → {m}")
    else:
        print("     → (없음) 받는 사람이 지정되지 않았습니다")
    bad = [m for m in cfg.recipients if "@" not in m or "." not in m.rsplit("@", 1)[-1]]
    if bad:
        print(f"   [!] 주소 형식이 이상합니다 (오타 확인): {', '.join(bad)}")
    raw, failed = collect(institutions, cfg)

    state = load_seen()
    known = seen_keys(state) if cfg.dedupe else set()
    stats = FilterStats()

    grouped: dict[str, list[Notice]] = {}
    empty: list[str] = []
    names = {i.id: i.name for i in institutions}
    failed_ids = {n for n, _ in failed}

    for inst in institutions:
        grouped[inst.id] = apply_filters(raw.get(inst.id, []), cfg, today, known, stats)

    print(f"-- {stats.as_line()}")

    # 마감일 확인 — 여기까지 살아남았지만 마감일을 모르는 공고만 상세 페이지를 열어본다.
    # 게시판 목록에 마감일이 없는 기관이 많아, 이 단계가 없으면 끝난 공고가 그대로 나간다.
    survivors = [n for v in grouped.values() for n in v]
    survivors, vstats = verify(survivors, cfg, today, make_session(cfg))
    if vstats.checked or vstats.skipped:
        print(f"-- {vstats.as_line()}")

    expired_total = 0
    for inst in institutions:
        grouped[inst.id], dropped = drop_expired(grouped[inst.id], cfg, today)
        expired_total += dropped
        if not grouped[inst.id] and inst.name not in failed_ids:
            empty.append(inst.name)
    if expired_total:
        print(f"-- 마감 확인되어 제외: {expired_total}건")

    total = sum(len(v) for v in grouped.values())

    html_body = render_html(grouped, names, today, cfg, empty, failed, sheet_log)
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

    # ---- 누적 기록 준비 (발송 성공 후에만 저장한다) ----
    sent = [n for v in grouped.values() for n in v]
    arch_rows = archive.load_rows()
    arch_rows, arch_added = archive.add(arch_rows, sent, today)

    attach: list[Path] = []
    xlsx_for_repo = False
    if cfg.archive_enabled:
        # 보기용 엑셀은 매번 out/ 에 만들어 Artifacts로 확인할 수 있게 한다
        made = archive.build_xlsx(arch_rows, OUT / archive.ARCHIVE_XLSX.name)
        if made is None:
            print("-- openpyxl 이 없어 엑셀 누적본을 만들지 못했습니다")
        else:
            print(f"-- 누적 {len(arch_rows)}건 (오늘 +{arch_added}) → {made}")
            # 지정한 요일에만 저장소에 커밋하고 메일에도 첨부한다
            if today.weekday() == cfg.archive_attach_weekday:
                attach.append(made)
                xlsx_for_repo = True

    subject = f"{cfg.subject_prefix} {today.strftime('%m월 %d일')} 신규 {total}건"
    if not is_configured():
        print(
            "-- SMTP 미설정: 메일을 보내지 않았습니다.\n"
            "   GitHub Secrets에 SMTP_USER / SMTP_PASSWORD 를 등록하면 발송이 시작됩니다.\n"
            f"   지금 결과는 {OUT/'brief.html'} 에 저장되어 있습니다."
        )
        return 0

    try:
        send(
            subject,
            html_body,
            text_body,
            cfg.recipients,
            cfg.sender_name,
            attachments=attach,
        )
        note = f" (누적본 첨부: {attach[0].name})" if attach else ""
        print(f"-- 발송 완료: {', '.join(cfg.recipients)}{note}")
    except MailNotConfigured as exc:
        print(f"-- 발송 건너뜀: {exc}")
        return 0
    except Exception as exc:  # noqa: BLE001
        print(f"-- 발송 실패: {type(exc).__name__}: {exc}")
        return 1

    # 발송에 성공했을 때만 이력과 누적 기록을 저장한다
    record(state, sent, today)
    prune(state, today)
    save_seen(state)
    print(f"-- 발송 이력 {len(sent)}건 기록")

    if cfg.archive_enabled:
        archive.save_csv(arch_rows)
        print(f"-- 누적 CSV 저장: {archive.ARCHIVE_CSV} ({len(arch_rows)}건)")
        if xlsx_for_repo:
            archive.build_xlsx(arch_rows, archive.ARCHIVE_XLSX)
            print(f"-- 누적 엑셀 갱신: {archive.ARCHIVE_XLSX.name}")
    return 0


# --------------------------------------------------------------- 진단


def diagnose(include_disabled: bool = False, dump: bool = False) -> int:
    cfg = load_config()
    all_inst = load_institutions()
    all_inst, sheet_log = sheet.apply_all(cfg, all_inst)
    for line in sheet_log:
        print(f"-- {line}")
    targets = [x for x in all_inst if (x.enabled or include_disabled) and x.url]
    today = today_kst()

    dump_dir = OUT / "html"
    if dump:
        dump_dir.mkdir(parents=True, exist_ok=True)

    session = make_session(cfg)
    results: dict[str, list[Notice]] = {}
    reasons: dict[str, str] = {}

    def attempt(sess, inst: Institution) -> None:
        """수집을 시도하고, 목록 인식에 실패하면 원본 HTML을 남긴다."""
        try:
            text = fetch(sess, inst, cfg)
        except Exception as exc:  # noqa: BLE001
            results[inst.id] = []
            reasons[inst.id] = f"{exc}"
            return
        notices = parse(text, inst, today)
        results[inst.id] = notices
        if notices:
            reasons.pop(inst.id, None)
        else:
            reasons[inst.id] = "목록을 인식하지 못했습니다"
            if dump:
                (dump_dir / f"{inst.id}.html").write_text(text, encoding="utf-8")

    for i, inst in enumerate(targets):
        if i:
            time.sleep(cfg.delay_between)
        attempt(session, inst)
        state = reasons.get(inst.id)
        print(f"  [{'!' if state else '+'}] {inst.name}: {state or str(len(results[inst.id])) + '건'}")

    # 재시도 라운드 — 정부 부처 사이트가 특정 IP를 한동안 막는 일이 잦아
    # 접속 실패한 곳만 잠시 쉰 뒤 새 연결로 한 번 더 시도한다.
    retryable = [x for x in targets if _is_network_error(reasons.get(x.id, ""))]
    if retryable:
        print(f"-- 접속 실패 {len(retryable)}곳, {RETRY_ROUND_WAIT}초 후 재시도합니다")
        time.sleep(RETRY_ROUND_WAIT)
        session2 = make_session(cfg)
        for i, inst in enumerate(retryable):
            if i:
                time.sleep(cfg.delay_between * 2)
            attempt(session2, inst)
            print(f"  [재시도] {inst.name}: {reasons.get(inst.id) or str(len(results[inst.id])) + '건'}")

    lines = [
        f"# 기관별 수집 진단 — {today}",
        "",
        f"대상 {len(targets)}곳 / 전체 {len(all_inst)}곳",
        "",
        *([f"> {x}" for x in sheet_log] + [""] if sheet_log else []),
        "| 기관 | 상태 | 수집 | 최신 게시일 | 비고 |",
        "|---|---|---|---|---|",
    ]
    detail: list[str] = []
    ok = 0

    for inst in targets:
        notices = results.get(inst.id, [])
        reason = reasons.get(inst.id)
        if reason and "인식하지" in reason:
            lines.append(f"| {inst.name} | ⚠️ | 0건 | — | 목록 인식 실패 |")
            continue
        if reason:
            lines.append(
                f"| {inst.name} | ❌ | — | — | {reason.replace('|', '/')[:110]} |"
            )
            continue
        ok += 1
        newest = max((n.posted for n in notices if n.posted), default=None)
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
