"""메일 본문 생성 (HTML + 텍스트)."""
from __future__ import annotations

import html
from datetime import date

from .config import Config
from .parse import Notice

FONT = "'Malgun Gothic','맑은 고딕',Apple SD Gothic Neo,-apple-system,sans-serif"


def _fmt(d: date | None, fallback: str = "—") -> str:
    return d.strftime("%m.%d") if d else fallback


def _dday(deadline: date | None, today: date) -> str:
    if deadline is None:
        return ""
    n = (deadline - today).days
    if n < 0:
        return "마감"
    if n == 0:
        return "오늘 마감"
    return f"D-{n}"


def _esc(s: str) -> str:
    return html.escape(s, quote=True)


def render_html(
    grouped: dict[str, list[Notice]],
    names: dict[str, str],
    today: date,
    cfg: Config,
    empty_institutions: list[str],
    failed: list[tuple[str, str]],
    source_notes: list[str] | None = None,
) -> str:
    total = sum(len(v) for v in grouped.values())

    rows: list[str] = []
    for inst_id, notices in grouped.items():
        if not notices:
            continue
        rows.append(
            f'<tr><td colspan="2" style="padding:22px 0 8px;border-bottom:2px solid #111;'
            f'font:600 15px {FONT};color:#111;">{_esc(names.get(inst_id, inst_id))}'
            f'<span style="font-weight:400;color:#888;font-size:12px;"> · {len(notices)}건</span></td></tr>'
        )
        for n in notices:
            flags = []
            if n.note == "상시":
                flags.append(
                    '<span style="display:inline-block;padding:1px 6px;margin-left:6px;'
                    'border:1px solid #555;color:#444;border-radius:3px;'
                    'font-size:11px;vertical-align:middle;">상시모집</span>'
                )
            elif n.deadline is None:
                flags.append(
                    '<span style="display:inline-block;padding:1px 6px;margin-left:6px;'
                    'border:1px solid #b45309;color:#b45309;border-radius:3px;'
                    'font-size:11px;vertical-align:middle;">마감일 확인필요</span>'
                )
            if n.posted is None:
                flags.append(
                    '<span style="display:inline-block;padding:1px 6px;margin-left:6px;'
                    'border:1px solid #999;color:#777;border-radius:3px;'
                    'font-size:11px;vertical-align:middle;">게시일 미확인</span>'
                )
            dd = _dday(n.deadline, today)
            dd_html = (
                f'<span style="color:#b91c1c;font-weight:600;"> {dd}</span>' if dd else ""
            )
            kw = ", ".join(n.matched_keywords[:4])
            kw_html = (
                f'<div style="font-size:11px;color:#999;margin-top:3px;">키워드: {_esc(kw)}</div>'
                if kw
                else ""
            )
            rows.append(
                f"""<tr>
<td style="padding:11px 12px 11px 0;border-bottom:1px solid #eee;vertical-align:top;
    font:400 12px {FONT};color:#888;white-space:nowrap;width:86px;">
  {_fmt(n.posted, '—')} 게시
</td>
<td style="padding:11px 0;border-bottom:1px solid #eee;vertical-align:top;font:400 14px {FONT};">
  <a href="{_esc(n.url)}" style="color:#111;text-decoration:none;font-weight:500;">{_esc(n.title)}</a>{''.join(flags)}
  <div style="font-size:12px;color:#666;margin-top:4px;">
    마감 {_fmt(n.deadline, '상시' if n.note == '상시' else '미표기')}{dd_html}
  </div>
  {kw_html}
</td></tr>"""
            )

    if total == 0:
        rows.append(
            f'<tr><td colspan="2" style="padding:36px 0;text-align:center;'
            f'font:400 14px {FONT};color:#888;">조건에 맞는 신규 공고가 없습니다.</td></tr>'
        )

    # 하단 점검 요약
    notes: list[str] = []
    if empty_institutions:
        notes.append(
            "<b>신규 공고 없음</b> ("
            + str(len(empty_institutions))
            + "곳): "
            + _esc(", ".join(empty_institutions))
        )
    if failed:
        items = "; ".join(f"{_esc(n)} — {_esc(e)}" for n, e in failed)
        notes.append(f'<b style="color:#b91c1c;">수집 실패</b> ({len(failed)}곳): {items}')
    for line in source_notes or []:
        notes.append(_esc(line))

    notes_html = ""
    if notes:
        body = "".join(
            f'<div style="margin-bottom:7px;">{x}</div>' for x in notes
        )
        notes_html = (
            f'<div style="margin-top:30px;padding:14px 16px;background:#fafafa;'
            f'border:1px solid #eee;font:400 12px {FONT};color:#666;line-height:1.6;">{body}</div>'
        )

    return f"""<!doctype html>
<html><body style="margin:0;padding:0;background:#f4f4f5;">
<table role="presentation" width="100%" cellpadding="0" cellspacing="0" style="background:#f4f4f5;padding:24px 12px;">
<tr><td align="center">
<table role="presentation" width="100%" cellpadding="0" cellspacing="0"
       style="max-width:660px;background:#fff;border:1px solid #e5e5e5;padding:28px 30px 32px;">
  <tr><td>
    <div style="font:600 19px {FONT};color:#111;">지원사업 공고 브리핑</div>
    <div style="font:400 13px {FONT};color:#888;margin-top:5px;">
      {today.strftime('%Y년 %m월 %d일')} · 최근 {cfg.lookback_days}일 게시 · 신규 <b style="color:#111;">{total}</b>건
    </div>
  </td></tr>
  <tr><td>
    <table role="presentation" width="100%" cellpadding="0" cellspacing="0">{''.join(rows)}</table>
    {notes_html}
    <div style="margin-top:24px;font:400 11px {FONT};color:#aaa;line-height:1.6;">
      마감된 공고는 제외했습니다. 마감일이 표기되지 않은 공고는 '마감일 확인필요'로 표시했습니다.<br>
      키워드·수신자·기관 목록은 GitHub 저장소의 config.yaml / institutions.yaml 에서 수정할 수 있습니다.
    </div>
  </td></tr>
</table>
</td></tr></table>
</body></html>"""


def render_text(
    grouped: dict[str, list[Notice]],
    names: dict[str, str],
    today: date,
    cfg: Config,
) -> str:
    total = sum(len(v) for v in grouped.values())
    lines = [
        f"지원사업 공고 브리핑 — {today.strftime('%Y-%m-%d')}",
        f"최근 {cfg.lookback_days}일 게시 · 신규 {total}건",
        "",
    ]
    for inst_id, notices in grouped.items():
        if not notices:
            continue
        lines.append(f"[{names.get(inst_id, inst_id)}]")
        for n in notices:
            dl = _fmt(n.deadline, "마감일 확인필요")
            lines.append(f"  · {n.title}")
            lines.append(f"    게시 {_fmt(n.posted, '미확인')} / 마감 {dl}")
            lines.append(f"    {n.url}")
        lines.append("")
    if total == 0:
        lines.append("조건에 맞는 신규 공고가 없습니다.")
    return "\n".join(lines)
