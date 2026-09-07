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

from . import deadline as deadline_rules
from .config import Institution

# ---------------------------------------------------------------- 날짜

_D4 = re.compile(r"(20\d{2})\s*[-./]\s*(\d{1,2})\s*[-./]\s*(\d{1,2})")
_D2 = re.compile(r"(?<!\d)(\d{2})\s*[-./]\s*(\d{1,2})\s*[-./]\s*(\d{1,2})(?!\d)")
# "2026.09.15(화) 17:00" 뒤에 붙는 요일/시각은 무시된다.

_RANGE_SEP = re.compile(r"^[\s~〜∼–—\-]*(?:부터|까지)?[\s~〜∼–—\-]*$")

# '마감 2026-12-31' 처럼 날짜 바로 앞에 붙는 마감 표시
_DEADLINE_LABEL = re.compile(
    r"(마감|종료|접수\s*마감|신청\s*마감|모집\s*마감)\s*(일시|일자|기한|일)?\s*[::]?\s*$"
)


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

    ref = today or date.today()

    # 0) '마감 2026-12-31' 처럼 앞에 마감 표시가 붙은 날짜는 게시일이 될 수 없다.
    #    (전북테크노파크처럼 목록에 마감일시만 있는 게시판 대응)
    labeled_deadline: set[int] = set()
    for k, d in enumerate(ds):
        window = text[max(0, d.start - 14) : d.start]
        if _DEADLINE_LABEL.search(window):
            labeled_deadline.add(k)

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

    # 2) 게시일: 기간·마감표시에 속하지 않은 날짜를 우선하고, 미래 날짜는 쓰지 않는다
    loose = [
        ds[k].value
        for k in range(len(ds))
        if k not in in_range and k not in labeled_deadline
    ]
    candidates = [v for v in sorted(loose) if v <= ref]
    if not candidates:
        rest = [ds[k].value for k in range(len(ds)) if k not in labeled_deadline]
        candidates = [v for v in sorted(rest) if v <= ref]
    posted = candidates[0] if candidates else None

    # 3) 마감일: 마감표시가 붙은 날짜 > 기간 종료일 > 가장 늦은 날짜 순으로 채택
    if labeled_deadline:
        deadline = max(ds[k].value for k in labeled_deadline)
    elif range_ends:
        deadline = max(range_ends)
    else:
        latest = max(d.value for d in ds)
        deadline = latest if posted is not None and latest > posted else None

    if deadline is not None and posted is not None and deadline < posted:
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
    """첨부파일 링크인지 판별한다.

    class 이름으로 판단하지 않는다 — 'download', 'dropdown', 'file-list' 같은 이름이
    본문 링크에도 흔히 붙어 있어서, class로 거르면 멀쩡한 게시판이 통째로 날아간다.
    실제로 v1.1에서 NIPA가 이 문제로 0건이 되었다.
    """
    if _FILE_EXT.search(text) or _FILE_WORDS.search(text):
        return True
    href = (a.get("href") or "") + " " + (a.get("onclick") or "")
    return bool(
        re.search(r"(fileDown|file_down|filedown|attachfile|/download|downloadFile)", href)
    )


def _anchor_title(a: Tag) -> str:
    """<a> 하나에서 제목을 뽑는다.

    한 <a> 안에 '말줄임용 span'과 '전체제목 span'이 같이 들어 있는 게시판이 있어
    통째로 텍스트를 뽑으면 제목이 두 번 나온다(부산테크노파크).
    자식 요소끼리 한쪽이 다른 쪽의 앞부분이면 긴 쪽만 쓴다.
    """
    full = clean_text(a.get_text(" "))
    attr = clean_text(a.get("title") or "")
    if len(attr) > len(full):
        full = attr

    kids = [clean_text(c.get_text(" ")) for c in a.find_all(True, recursive=False)]
    kids = [k for k in kids if len(k) >= 8]
    if len(kids) >= 2:
        for i in range(len(kids)):
            for j in range(len(kids)):
                if i == j:
                    continue
                short = kids[i].rstrip(" .…·")
                if short and kids[j].startswith(short):
                    return kids[j]
    return full


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
    """행 후보를 모은다.

    '같은 종류가 안에 또 있으면 상위 행'이라고 판단한다. 예전에는 tr 안에 li가 있어도
    상위 행으로 봤는데, 첨부파일 목록을 <ul><li>로 넣은 게시판(중소벤처기업부)의
    모든 행이 그 규칙에 걸려 통째로 사라졌다. 그래서 '같은 태그'만 본다.
    """
    rows = []
    for tag in soup.find_all(tags):
        if tag.find(tag.name):
            continue  # 같은 종류가 안에 또 있으면 상위 행이다
        if not tag.find("a"):
            continue
        rows.append(tag)
    return rows


def _signature(row: Tag) -> str:
    """행의 생김새. 부모가 달라도 같은 모양이면 한 목록으로 묶기 위한 것."""
    return row.name + "." + ".".join(sorted(row.get("class") or []))


def _best_group(rows_all: list[Tag]) -> list[Tag]:
    """행들을 묶는 방법 두 가지를 모두 시도해 점수가 높은 쪽을 고른다.

    1) 같은 부모를 가진 형제끼리  — 표준적인 게시판
    2) 태그+class 가 같은 것끼리 — 행마다 감싸는 div가 따로 있어 형제가 아닌 게시판
       (부산시민운동지원센터: div.table_td > div.table_td_line 구조)
    """
    groups: dict[str, list[Tag]] = {}
    for row in rows_all:
        if row.parent is not None:
            groups.setdefault(f"p{id(row.parent)}", []).append(row)
        sig = _signature(row)
        if sig.count(".") > 0 and len(sig) > len(row.name) + 1:
            groups.setdefault(f"c{sig}", []).append(row)

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
    note: str = ""  # '상시' 등
    deadline_source: str = "목록"  # 목록 / 제목 / 상세

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
    anchors = row.find_all("a")

    # 1차: 첨부파일 링크를 뺀 나머지에서 고른다
    cands = [t for a in anchors if (t := _anchor_title(a)) and not _is_file_anchor(a, t)]
    best = _cleanest(cands)

    # 2차 안전장치: 전부 걸러졌다면 필터 없이 다시 고른다.
    # 판별이 과하게 걸려 제목을 통째로 잃는 사고를 막는다.
    if len(best) < 4:
        best = _cleanest([_anchor_title(a) for a in anchors])

    if len(best) < 4:
        # 링크 텍스트가 아이콘뿐인 경우 — 행에서 가장 긴 셀을 제목으로
        for cell in row.find_all(["td", "div", "p", "strong"]):
            t = clean_text(cell.get_text(" "))
            if len(t) > len(best) and not find_dates(t):
                best = t
    return best


# 제목 뒤에 딸려오는 목록 메타데이터 라벨 — 여기서부터는 제목이 아니다
_META_LABEL = re.compile(
    r"\s+(담당부서|담당자|담당팀|공고번호|공고일자|신청기간|접수기간|모집기간|사업기간"
    r"|등록일자?|작성일자?|게시일자?|조회수?|첨부파일)\s"
)


def _cut_meta(title: str) -> str:
    """'…모집 공고 담당부서 OO과 공고번호 제2026-540호' 같은 꼬리를 잘라낸다.

    모바일용 <a>가 제목과 상세정보를 통째로 감싸는 게시판(중소벤처기업부)이 있어,
    그대로 두면 제목이 한 줄을 넘긴다.
    """
    if len(title) < 15:
        return title
    m = _META_LABEL.search(title)
    if m and m.start() >= 10:
        return title[: m.start()].strip()
    return title


def _cleanest(cands: list[str]) -> str:
    """여러 후보 제목 중 가장 적절한 하나를 고른다.

    A가 B의 앞부분이고 A가 말줄임(...)으로 끝나지 않는다면,
    B는 A 뒤에 메타데이터가 붙은 것이므로 A를 쓴다.
    반대로 A가 말줄임으로 끝나면 잘린 것이므로 긴 B를 쓴다.
    """
    cands = [_cut_meta(c) for c in cands if c]
    if not cands:
        return ""
    kept = []
    for b in cands:
        shadowed = any(
            a != b
            and not a.rstrip().endswith(("...", "…"))
            and b.startswith(a)
            and len(b) > len(a) + 4
            for a in cands
        )
        if not shadowed:
            kept.append(b)
    pool = kept or cands
    return max(pool, key=len)


def _pick_link(row: Tag, inst: Institution) -> str:
    base = inst.base or inst.url
    anchors = row.find_all("a")

    # 1) 정상적인 href (첨부파일 링크는 건너뛴다)
    usable = [
        a
        for a in anchors
        if (a.get("href") or "").strip()
        and not (a.get("href") or "").strip().startswith(("javascript:", "#", "mailto:"))
    ]
    for a in usable:
        if _is_file_anchor(a, clean_text(a.get_text(" "))):
            continue
        return urljoin(base, a["href"].strip())
    # 전부 첨부파일로 판정됐다면 판별이 과한 것이므로 첫 번째를 쓴다
    if usable:
        return urljoin(base, usable[0]["href"].strip())

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
    """정리된 문서로 먼저 시도하고, 결과가 0건이면 원본으로 다시 시도한다.

    nav/header 안에 게시판을 넣어둔 사이트가 있어서, 정리 단계가 오히려
    멀쩡한 목록을 지워버리는 경우가 있다. 그래서 되돌아갈 길을 남겨둔다.
    """
    for strip_chrome in (True, False):
        rows = _rows_of(html, inst, strip_chrome)
        out = _rows_to_notices(rows, inst, today)
        if out:
            return out
    return []


def _rows_of(html: str, inst: Institution, strip_chrome: bool) -> list[Tag]:
    soup = BeautifulSoup(html, "lxml")
    if strip_chrome:
        # 본문과 무관한 영역을 걷어내 메뉴를 목록으로 오인하는 것을 줄인다
        for tag in soup.find_all(["script", "style", "nav", "header", "footer", "select"]):
            tag.decompose()
    else:
        for tag in soup.find_all(["script", "style"]):
            tag.decompose()

    if inst.row_selector:
        return soup.select(inst.row_selector)
    return auto_detect_rows(soup)


def _rows_to_notices(
    rows: list[Tag], inst: Institution, today: date | None
) -> list[Notice]:
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
        # 연도 없는 날짜('4.24')를 해석할 기준일. 게시일을 알면 그쪽이 훨씬 정확하다.
        ref = posted or today or date.today()
        note = ""
        source = "목록" if deadline else ""

        # 목록에 마감일이 없으면 제목에서 찾아본다.
        # "(~9.16.(수) 까지)" 처럼 제목에 박아두는 게시판이 많다.
        if deadline is None:
            deadline, note = deadline_rules.from_text(
                title, ref, anchor_is_posted=posted is not None
            )
            if deadline:
                source = "제목"

        row_text = row.get_text(" ", strip=True)
        closed = looks_closed(row) or deadline_rules.is_closed(row_text)

        out.append(
            Notice(
                institution_id=inst.id,
                institution_name=inst.name,
                title=title,
                url=_pick_link(row, inst),
                posted=posted,
                deadline=deadline,
                closed_flag=closed,
                note=note,
                deadline_source=source,
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
