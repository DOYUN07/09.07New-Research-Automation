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


def split_period(text: str, today: date | None = None) -> tuple[date | None, date | None]:
    """행 텍스트에서 (게시일, 마감일)을 추정한다.

    한 행에 게시일·공고기간·신청기간이 뒤섞여 최대 4~5개 날짜가 나오는 사이트가 있어
    '어느 게 접수기간인지' 맞히려 들면 오히려 틀린다. 대신 단순하고 안전한 규칙을 쓴다.

      게시일 = 오늘보다 늦지 않은 날짜 중 가장 이른 것
               (미래 날짜를 게시일로 잡는 사고를 막는다)
      마감일 = 가장 늦은 날짜 (게시일보다 뒤일 때만)

    게시일이 실제보다 며칠 이르게 잡힐 수 있으나, 그 방향의 오차는
    '최근 10일' 필터에서 공고를 놓치는 쪽이 아니라 한 번 더 보는 쪽으로 작용한다.
    """
    ds = find_dates(text)
    if not ds:
        return None, None
    if len(ds) == 1:
        return ds[0].value, None

    ref = today or date.today()

    # 1) 'A ~ B' 형태로 붙어 있는 날짜쌍을 모두 찾는다 (공고기간·신청기간 등)
    in_range: set[int] = set()
    range_ends: list[date] = []
    i = 0
    while i < len(ds) - 1:
        between = text[ds[i].end : ds[i + 1].start]
        # 사이에 요일·시각 표기가 껴 있어도 기간으로 인정한다
        stripped = re.sub(r"[()월화수목금토일\d:시분초\s]", "", between)
        if (_RANGE_SEP.match(between) or stripped in ("~", "-", "–", "—", "")) and ds[
            i
        ].value <= ds[i + 1].value:
            in_range.update({i, i + 1})
            range_ends.append(ds[i + 1].value)
            i += 2
            continue
        i += 1

    # 2) 게시일: 기간에 속하지 않은 날짜를 우선하고, 미래 날짜는 쓰지 않는다
    loose = [ds[k].value for k in range(len(ds)) if k not in in_range]
    candidates = [v for v in sorted(loose) if v <= ref]
    if not candidates:
        candidates = [v for v in sorted(d.value for d in ds) if v <= ref]
    posted = candidates[0] if candidates else min(d.value for d in ds)

    # 3) 마감일: 기간의 종료일 중 가장 늦은 것, 기간이 없으면 가장 늦은 날짜
    if range_ends:
        deadline = max(range_ends)
    else:
        latest = max(d.value for d in ds)
        deadline = latest if latest > posted else None
    if deadline is not None and deadline < posted:
        deadline = None
    return posted, deadline


# ---------------------------------------------------------------- 텍스트 정리

_BADGES = re.compile(
    r"(새글|NEW|new|N\b|공지|답변|첨부파일|파일첨부|조회수|D-\d+|D\s*-\s*\d+|마감임박)"
)
_WS = re.compile(r"\s+")

# 첨부파일 링크를 제목으로 착각하지 않기 위한 판별
_FILE_EXT = re.compile(
    r"\.(hwp|hwpx|pdf|docx?|xlsx?|pptx?|zip|jpe?g|png|gif|txt|csv|gul|egg|rar|7z)\b",
    re.IGNORECASE,
)
_FILE_WORDS = re.compile(r"(다운로드|download|바로보기|미리보기|내려받기|파일받기)", re.IGNORECASE)


def clean_text(s: str) -> str:
    s = s.replace("\xa0", " ")
    s = _BADGES.sub(" ", s)
    s = _WS.sub(" ", s).strip(" \t\r\n·|/-")
    return _collapse_doubled(s)


def _collapse_doubled(s: str) -> str:
    """같은 제목이 두 번 이어붙은 경우를 되돌린다.

    한 <a> 안에 '말줄임용 span'과 '전체제목 span'이 같이 들어 있는 게시판이 있어
    텍스트를 뽑으면 제목이 그대로 두 번 나온다.
    """
    if len(s) < 12:
        return s
    n = len(s)
    if n % 2 == 0:
        half = n // 2
        if s[:half] == s[half:]:
            return s[:half].strip()
    # 사이에 공백 하나가 낀 경우
    half = (n - 1) // 2
    if n % 2 == 1 and s[:half] == s[half + 1 :] and s[half] == " ":
        return s[:half].strip()
    return s


def _is_file_anchor(a: Tag, text: str) -> bool:
    href = (a.get("href") or "") + " " + (a.get("onclick") or "")
    if _FILE_EXT.search(text) or _FILE_WORDS.search(text):
        return True
    if re.search(r"(download|fileDown|file_down|attachfile|/file/)", href, re.IGNORECASE):
        return True
    cls = " ".join(a.get("class") or [])
    return bool(re.search(r"(file|down|attach)", cls, re.IGNORECASE))


_CLOSED_WORDS = {"마감", "종료", "접수마감", "모집마감", "완료", "접수종료"}


def looks_closed(row: Tag) -> bool:
    """상태 셀이 '마감/종료'인 행인지 확인한다."""
    for cell in row.find_all(["td", "span", "em", "strong", "div", "p"]):
        t = cell.get_text(" ", strip=True)
        if t in _CLOSED_WORDS:
            return True
    return False


# ---------------------------------------------------------------- 행 탐지


def _leaf_rows(soup: BeautifulSoup, tags: list[str]) -> list[Tag]:
    rows = []
    for tag in soup.find_all(tags):
        if tag.find(tags):
            continue  # 중첩된 상위 행은 건너뜀
        if not tag.find("a"):
            continue
        rows.append(tag)
    return rows


def _best_group(rows_all: list[Tag]) -> list[Tag]:
    groups: dict[int, list[Tag]] = {}
    for row in rows_all:
        parent = row.parent
        if parent is None:
            continue
        groups.setdefault(id(parent), []).append(row)

    best: list[Tag] = []
    best_score = -1.0
    for rows in groups.values():
        if len(rows) < 3:
            continue
        texts = [r.get_text(" ", strip=True) for r in rows]
        dated = sum(1 for t in texts if find_dates(t))
        avg_len = sum(len(t) for t in texts) / len(texts)

        if dated == 0:
            # 날짜가 전혀 없는 그룹은 내비게이션 메뉴일 가능성이 높다.
            # 제목이 충분히 길 때만 후보로 인정한다.
            if avg_len < 15:
                continue
            score = len(rows) + avg_len / 20
        else:
            score = dated * 10 + len(rows) + avg_len / 20

        if score > best_score:
            best_score, best = score, rows
    return best


def auto_detect_rows(soup: BeautifulSoup) -> list[Tag]:
    """1차로 표(tr)·목록(li) 구조를 찾고, 실패하면 div 카드형까지 넓혀 다시 찾는다."""
    best = _best_group(_leaf_rows(soup, ["tr", "li"]))
    if best:
        return best
    return _best_group(_leaf_rows(soup, ["tr", "li", "div", "dl", "article"]))


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
        # title 속성이 더 완전한 경우가 많다 (목록에서 말줄임된 제목의 원본)
        attr = clean_text(a.get("title") or "")
        if len(attr) > len(t):
            t = attr
        if not t:
            continue
        if _is_file_anchor(a, t):
            continue  # 첨부파일 링크는 제목이 아니다
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

    # 1) 정상적인 href (첨부파일 링크는 건너뛴다)
    for a in anchors:
        href = (a.get("href") or "").strip()
        if not href or href.startswith(("javascript:", "#", "mailto:")):
            continue
        if _is_file_anchor(a, clean_text(a.get_text(" "))):
            continue
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


def _pick_dates(
    row: Tag, inst: Institution, today: date | None = None
) -> tuple[date | None, date | None]:
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
        p, d = split_period(row.get_text(" ", strip=True), today)
        posted = posted or p
        deadline = deadline or d
    return posted, deadline


def parse_html(html: str, inst: Institution, today: date | None = None) -> list[Notice]:
    soup = BeautifulSoup(html, "lxml")

    # 본문과 무관한 영역은 미리 걷어낸다 (메뉴를 목록으로 오인하는 것을 줄임)
    for tag in soup.find_all(["script", "style", "nav", "header", "footer", "select"]):
        tag.decompose()

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

        posted, deadline = _pick_dates(row, inst, today)
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


def parse(text: str, inst: Institution, today: date | None = None) -> list[Notice]:
    if inst.type == "json":
        return parse_json(text, inst)
    return parse_html(text, inst, today)
