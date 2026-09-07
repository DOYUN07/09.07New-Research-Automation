"""게시판 목록 파서.

기관마다 HTML 구조가 달라 선택자를 일일이 지정하면 관리가 불가능하다.
그래서 기본은 '범용 파서'로 목록을 자동 인식하고,
자동 인식이 안 되는 곳만 institutions.yaml 에서 선택자를 덮어쓴다.

범용 파서의 원리
  1) 페이지 안의 모든 <tr>/<li> 중 '더 이상 중첩되지 않고 링크를 가진 것'을 후보 행으로 본다.
  2) 같은 부모를 가진 후보 행들을 하나의 그룹으로 묶는다.
  3) 그룹마다 점수를 매긴다: 날짜를 가진 행이 많을수록, 행 수가 많을수록 높다.
     (게시판 목록은 날짜가 있고, 내비게이션 메뉴는 없다)
  4) 최고점 그룹을 공고 목록으로 채택한다.
"""
from __future__ import annotations

import json
import re
from dataclasses import dataclass, field
from datetime import date
from urllib.parse import urljoin

from bs4 import BeautifulSoup, Tag

from .config import Institution

# ---------------------------------------------------------------- 날짜

_D4 = re.compile(r"(20\d{2})\s*[-./]\s*(\d{1,2})\s*[-./]\s*(\d{1,2})")
_D2 = re.compile(r"(?<!\d)(\d{2})\s*[-./]\s*(\d{1,2})\s*[-./]\s*(\d{1,2})(?!\d)")
# "2026.09.15(화) 17:00" 뒤에 붙는 요일/시각은 무시된다.

_RANGE_SEP = re.compile(r"^[\s~〜∼–—\-]*(?:부터|까지)?[\s~〜∼–—\-]*$")


@dataclass
class FoundDate:
    value: date
    start: int
    end: int


def _mk(y: int, m: int, d: int) -> date | None:
    try:
        return date(y, m, d)
    except ValueError:
        return None


def find_dates(text: str) -> list[FoundDate]:
    """텍스트에서 날짜를 등장 순서대로 모두 찾는다."""
    out: list[FoundDate] = []
    for m in _D4.finditer(text):
        v = _mk(int(m.group(1)), int(m.group(2)), int(m.group(3)))
        if v:
            out.append(FoundDate(v, m.start(), m.end()))
    if out:
        return out
    # 4자리 연도가 없을 때만 2자리 연도(26.09.07)를 시도한다
    for m in _D2.finditer(text):
        v = _mk(2000 + int(m.group(1)), int(m.group(2)), int(m.group(3)))
        if v:
            out.append(FoundDate(v, m.start(), m.end()))
    return out


def split_period(text: str) -> tuple[date | None, date | None]:
    """행 텍스트에서 (게시일, 마감일)을 추정한다.

    - 'A ~ B' 형태로 붙어 있는 두 날짜는 접수기간으로 보고 B를 마감일로 잡는다.
    - 접수기간에 속하지 않은 날짜가 있으면 그것을 게시일로 쓴다.
    - 접수기간밖에 없으면 시작일을 게시일 대용으로 쓴다.
    """
    ds = find_dates(text)
    if not ds:
        return None, None
    if len(ds) == 1:
        return ds[0].value, None

    period: tuple[int, int] | None = None
    for i in range(len(ds) - 1):
        between = text[ds[i].end : ds[i + 1].start]
        # 사이에 요일·시각 표기가 있어도 접수기간으로 인정
        cleaned = re.sub(r"[()월화수목금토일\d:시분초\s]", "", between)
        if _RANGE_SEP.match(between) or cleaned in ("~", "-", "–", "—", ""):
            if ds[i].value <= ds[i + 1].value:
                period = (i, i + 1)
                break

    if period is None:
        # 접수기간 표기가 없으면: 가장 이른 날짜를 게시일, 가장 늦은 날짜를 마감일 후보로
        vals = sorted(d.value for d in ds)
        return vals[0], (vals[-1] if vals[-1] != vals[0] else None)

    i, j = period
    deadline = ds[j].value
    others = [d.value for k, d in enumerate(ds) if k not in (i, j)]
    posted = others[0] if others else ds[i].value
    return posted, deadline


# ---------------------------------------------------------------- 텍스트 정리

_BADGES = re.compile(
    r"(새글|NEW|new|N\b|공지|답변|첨부파일|파일첨부|조회수|D-\d+|D\s*-\s*\d+|마감임박)"
)
_WS = re.compile(r"\s+")


def clean_text(s: str) -> str:
    s = s.replace("\xa0", " ")
    s = _BADGES.sub(" ", s)
    return _WS.sub(" ", s).strip(" \t\r\n·|/-")


_CLOSED_WORDS = {"마감", "종료", "접수마감", "모집마감", "완료", "접수종료"}


def looks_closed(row: Tag) -> bool:
    """상태 셀이 '마감/종료'인 행인지 확인한다."""
    for cell in row.find_all(["td", "span", "em", "strong", "div", "p"]):
        t = cell.get_text(" ", strip=True)
        if t in _CLOSED_WORDS:
            return True
    return False


# ---------------------------------------------------------------- 행 탐지


def _leaf_rows(soup: BeautifulSoup) -> list[Tag]:
    rows = []
    for tag in soup.find_all(["tr", "li"]):
        if tag.find(["tr", "li"]):
            continue  # 중첩된 상위 행은 건너뜀
        if not tag.find("a"):
            continue
        rows.append(tag)
    return rows


def auto_detect_rows(soup: BeautifulSoup) -> list[Tag]:
    groups: dict[int, list[Tag]] = {}
    parents: dict[int, Tag] = {}
    for row in _leaf_rows(soup):
        parent = row.parent
        if parent is None:
            continue
        key = id(parent)
        groups.setdefault(key, []).append(row)
        parents[key] = parent

    best: list[Tag] = []
    best_score = -1.0
    for key, rows in groups.items():
        if len(rows) < 3:
            continue
        texts = [r.get_text(" ", strip=True) for r in rows]
        dated = sum(1 for t in texts if find_dates(t))
        avg_len = sum(len(t) for t in texts) / len(texts)

        if dated == 0:
            # 날짜가 전혀 없는 그룹은 내비게이션일 가능성이 높다.
            # 제목이 충분히 길 때만 후보로 인정한다.
            if avg_len < 15:
                continue
            score = len(rows) + avg_len / 20
        else:
            score = dated * 10 + len(rows) + avg_len / 20

        if score > best_score:
            best_score, best = score, rows
    return best


# ---------------------------------------------------------------- 항목


@dataclass
class Notice:
    institution_id: str
    institution_name: str
    title: str
    url: str
    posted: date | None = None
    deadline: date | None = None
    closed_flag: bool = False
    matched_keywords: list[str] = field(default_factory=list)

    @property
    def key(self) -> str:
        import hashlib

        basis = f"{self.institution_id}|{self.url or self.title}"
        return hashlib.sha1(basis.encode("utf-8")).hexdigest()[:16]


# ---------------------------------------------------------------- 추출


def _pick_title(row: Tag, inst: Institution) -> str:
    if inst.title_selector:
        el = row.select_one(inst.title_selector)
        if el:
            t = clean_text(el.get_text(" "))
            if t:
                return t
    best = ""
    for a in row.find_all("a"):
        t = clean_text(a.get_text(" "))
        # title 속성이 더 완전한 경우가 많다
        attr = clean_text(a.get("title") or "")
        if len(attr) > len(t):
            t = attr
        if len(t) > len(best):
            best = t
    if len(best) < 4:
        # 링크 텍스트가 아이콘뿐인 경우 — 행에서 가장 긴 셀을 제목으로
        for cell in row.find_all(["td", "div", "p", "strong"]):
            t = clean_text(cell.get_text(" "))
            if len(t) > len(best) and not find_dates(t):
                best = t
    return best


def _pick_link(row: Tag, inst: Institution) -> str:
    base = inst.base or inst.url
    anchors = row.find_all("a")

    # 1) 정상적인 href
    for a in anchors:
        href = (a.get("href") or "").strip()
        if href and not href.startswith(("javascript:", "#")):
            return urljoin(base, href)

    # 2) onclick / javascript: 안에서 식별자 추출
    if inst.link_from_onclick:
        pat = re.compile(inst.link_from_onclick)
        candidates = anchors + [row]
        for el in candidates:
            for attr in ("onclick", "href", "data-url", "data-id"):
                val = el.get(attr) or ""
                m = pat.search(val)
                if m:
                    ident = m.group(1)
                    if inst.detail_url:
                        return inst.detail_url.replace("{id}", ident)
                    return urljoin(base, ident)
    return inst.url


def _pick_dates(row: Tag, inst: Institution) -> tuple[date | None, date | None]:
    posted = deadline = None

    if inst.date_selector:
        el = row.select_one(inst.date_selector)
        if el:
            ds = find_dates(el.get_text(" "))
            if ds:
                posted = ds[0].value
    if inst.deadline_selector:
        el = row.select_one(inst.deadline_selector)
        if el:
            ds = find_dates(el.get_text(" "))
            if ds:
                deadline = ds[-1].value

    if posted is None or deadline is None:
        p, d = split_period(row.get_text(" ", strip=True))
        posted = posted or p
        deadline = deadline or d
    return posted, deadline


def parse_html(html: str, inst: Institution) -> list[Notice]:
    soup = BeautifulSoup(html, "lxml")

    if inst.row_selector:
        rows = soup.select(inst.row_selector)
    else:
        rows = auto_detect_rows(soup)

    out: list[Notice] = []
    seen_titles: set[str] = set()
    for row in rows:
        title = _pick_title(row, inst)
        if not title or len(title) < 5:
            continue
        if title in seen_titles:
            continue
        seen_titles.add(title)

        posted, deadline = _pick_dates(row, inst)
        out.append(
            Notice(
                institution_id=inst.id,
                institution_name=inst.name,
                title=title,
                url=_pick_link(row, inst),
                posted=posted,
                deadline=deadline,
                closed_flag=looks_closed(row),
            )
        )
    return out


def parse_json(text: str, inst: Institution) -> list[Notice]:
    data = json.loads(text)
    items = data.get(inst.json_items, []) if inst.json_items else data
    if not isinstance(items, list):
        return []

    out: list[Notice] = []
    for it in items:
        title = clean_text(str(it.get(inst.json_title or "title", "")))
        if not title:
            continue
        raw_date = str(it.get(inst.json_date or "date", ""))
        ds = find_dates(raw_date)
        ident = str(it.get(inst.json_id or "id", ""))
        url = inst.detail_url.replace("{id}", ident) if inst.detail_url else inst.url
        out.append(
            Notice(
                institution_id=inst.id,
                institution_name=inst.name,
                title=title,
                url=url,
                posted=ds[0].value if ds else None,
            )
        )
    return out


def parse(text: str, inst: Institution) -> list[Notice]:
    if inst.type == "json":
        return parse_json(text, inst)
    return parse_html(text, inst)
