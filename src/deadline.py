"""마감일 판정.

문제
  진단에서 34개 기관 중 20곳이 '마감일 파싱 0/N' 이었다. 목록 화면에 등록일만
  있고 접수기간이 없는 게시판이 많기 때문이다. 그런 공고는 마감 여부를 판단할
  근거가 없어 전부 통과했고, 결과적으로 이미 끝난 공고가 메일에 섞였다.

해결 — 세 군데를 순서대로 본다
  1) 목록 행     : 접수기간 컬럼 (기존)
  2) 공고 제목   : "(~9.16.(수) 까지)" 처럼 제목에 박아둔 마감일
  3) 상세 페이지 : 1·2에서 못 찾은 것만 실제로 열어서 접수기간을 읽는다

'상시모집·예산 소진 시까지' 처럼 마감일이 없는 게 정상인 공고는 따로 표시한다.
"""
from __future__ import annotations

import re
from datetime import date

# ---------------------------------------------------------------- 상시 모집

ALWAYS_OPEN = re.compile(
    r"(상시\s*모집|상시\s*접수|수시\s*모집|수시\s*접수|연중\s*수시|연중\s*상시"
    r"|예산\s*소진\s*시|소진\s*시\s*까지|선착순\s*마감|모집\s*시\s*까지)"
)

# ---------------------------------------------------------------- 마감 상태

CLOSED_PHRASE = re.compile(
    r"(접수\s*마감|모집\s*마감|신청\s*마감|접수\s*종료|모집\s*종료|공고\s*종료"
    r"|마감\s*되었|종료\s*되었|마감\s*됨|종료\s*됨)"
)
# '마감임박', '마감일', '마감기한' 은 마감된 게 아니다
NOT_CLOSED = re.compile(r"(마감\s*임박|마감\s*일|마감\s*기한|마감\s*예정|마감\s*안내)")

# ---------------------------------------------------------------- 날짜

_FULL = re.compile(
    r"(20\d{2})\s*[.\-/년]\s*(\d{1,2})\s*[.\-/월]\s*(\d{1,2})\s*[.일]?"
)
# 연도 없는 날짜: "9.16", "9월 16일"
_PARTIAL = re.compile(r"(?<!\d)(\d{1,2})\s*[.\-/월]\s*(\d{1,2})\s*[.일]?(?!\d)")

# 마감을 가리키는 말 (이 뒤에 오는 날짜가 마감일)
_DUE_LABEL = re.compile(
    r"(접수\s*마감|신청\s*마감|모집\s*마감|마감\s*일시|마감\s*일자|마감\s*기한|마감일|마감)"
)
# 기간을 가리키는 말 (이 뒤의 'A ~ B' 에서 B가 마감일)
_PERIOD_LABEL = re.compile(r"(접수\s*기간|신청\s*기간|모집\s*기간|공모\s*기간|사업\s*기간|공고\s*기간)")

_RANGE = re.compile(r"[~〜∼–—]|부터")


def _mk(y: int, m: int, d: int) -> date | None:
    try:
        return date(y, m, d)
    except ValueError:
        return None


def _full_dates(text: str) -> list[tuple[date, int, int]]:
    out = []
    for m in _FULL.finditer(text):
        v = _mk(int(m.group(1)), int(m.group(2)), int(m.group(3)))
        if v:
            out.append((v, m.start(), m.end()))
    return out


def _resolve_partial(
    mm: int, dd: int, ref: date, anchor_is_posted: bool = False
) -> date | None:
    """연도 없는 '9.16' 을 실제 날짜로 바꾼다.

    기준일이 무엇이냐에 따라 규칙이 다르다.

    ① 기준일이 게시일일 때 (anchor_is_posted=True)
       **마감일은 게시일보다 앞설 수 없다.** 1월 5일에 올린 공고의 '~12.20' 이
       작년 12월일 리는 없다. 그래서 게시일 이후 중 가장 이른 해를 고른다.
         게시일 1/5,  '12.20' → 2026-12-20 (같은 해 연말, 장기 사업)
         게시일 4/2,  '4.24'  → 2026-04-24
         게시일 12/28,'1.15'  → 2027-01-15 (해를 넘김)

    ② 기준일이 오늘일 때 (게시일을 모르는 게시판)
       공고가 언제 올라온 건지 알 수 없으므로 **오늘과 가장 가까운 해**를 고른다.
         오늘 9/7, '4.24' → 2026-04-24 (넉 달 전 마감)
         오늘 9/7, '9.16' → 2026-09-16 (아흐레 뒤)
       예전에는 '과거면 내년'으로 봐서 9월에 본 '4.24' 를 2027년으로 오판했고,
       이미 끝난 공고가 메일에 그대로 나갔다.
    """
    cands = [v for y in (ref.year - 1, ref.year, ref.year + 1) if (v := _mk(y, mm, dd))]
    if not cands:
        return None

    if anchor_is_posted:
        # 게시일 이후(당일 포함) 중 가장 이른 것. 없으면 가장 늦은 것으로 물러선다.
        after = [v for v in cands if v >= ref]
        return min(after) if after else max(cands)

    return min(cands, key=lambda v: (abs((v - ref).days), -v.toordinal()))


def from_text(
    text: str, ref: date, window: int = 40, anchor_is_posted: bool = False
) -> tuple[date | None, str]:
    """텍스트에서 (마감일, 비고) 를 찾는다. 비고는 '' 또는 '상시'.

    ref 는 연도 없는 날짜를 해석할 기준일.
    anchor_is_posted 는 그 기준일이 게시일인지 여부 (규칙이 달라진다).
    """
    if not text:
        return None, ""
    t = re.sub(r"\s+", " ", text)

    if ALWAYS_OPEN.search(t):
        return None, "상시"

    # 1) '마감' 표시 바로 뒤의 날짜
    for m in _DUE_LABEL.finditer(t):
        seg = t[m.end() : m.end() + window]
        fd = _full_dates(seg)
        if fd:
            return fd[0][0], ""
        pm = _PARTIAL.search(seg)
        if pm:
            v = _resolve_partial(int(pm.group(1)), int(pm.group(2)), ref, anchor_is_posted)
            if v:
                return v, ""

    # 2) '접수기간' 표시 뒤의 'A ~ B' 에서 B
    for m in _PERIOD_LABEL.finditer(t):
        seg = t[m.end() : m.end() + window * 2]
        fd = _full_dates(seg)
        if len(fd) >= 2:
            return max(x[0] for x in fd), ""
        if len(fd) == 1 and _RANGE.search(seg[: fd[0][1]]):
            return fd[0][0], ""

    # 3) '~ 날짜 까지' 형태 (라벨 없이 제목에 박아둔 경우)
    for m in re.finditer(r"[~〜∼]\s*", t):
        seg = t[m.end() : m.end() + window]
        if "까지" not in seg and not seg[:1].isdigit():
            continue
        fd = _full_dates(seg)
        if fd:
            return fd[0][0], ""
        pm = _PARTIAL.search(seg)
        if pm:
            v = _resolve_partial(int(pm.group(1)), int(pm.group(2)), ref, anchor_is_posted)
            if v:
                return v, ""

    # 4) '날짜 까지'
    for m in re.finditer(r"까지", t):
        seg = t[max(0, m.start() - window) : m.start()]
        fd = _full_dates(seg)
        if fd:
            return fd[-1][0], ""
        pms = list(_PARTIAL.finditer(seg))
        if pms:
            v = _resolve_partial(
                int(pms[-1].group(1)), int(pms[-1].group(2)), ref, anchor_is_posted
            )
            if v:
                return v, ""

    return None, ""


def is_closed(text: str) -> bool:
    """'접수마감', '모집 종료' 같은 말이 있으면 끝난 공고로 본다."""
    if not text:
        return False
    t = re.sub(r"\s+", " ", text)
    if NOT_CLOSED.search(t):
        # '마감임박' 등이 섞여 있으면 그 부분을 빼고 다시 본다
        t = NOT_CLOSED.sub(" ", t)
    return bool(CLOSED_PHRASE.search(t))


def from_detail_html(
    html: str, ref: date, anchor_is_posted: bool = False
) -> tuple[date | None, str, bool]:
    """상세 페이지 HTML에서 (마감일, 비고, 마감여부) 를 뽑는다."""
    from bs4 import BeautifulSoup

    soup = BeautifulSoup(html, "lxml")
    for tag in soup.find_all(["script", "style", "nav", "footer"]):
        tag.decompose()
    text = soup.get_text(" ", strip=True)
    # 상세 페이지는 길다. 접수 관련 정보는 보통 앞쪽에 있다.
    head = text[:6000]
    dl, note = from_text(head, ref, anchor_is_posted=anchor_is_posted)
    return dl, note, is_closed(head)
