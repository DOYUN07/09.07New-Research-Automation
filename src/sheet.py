"""구글시트에서 설정 읽어오기.

인증키·서비스계정이 필요 없습니다. 시트를 '웹에 게시'하면 나오는 CSV 주소를
그냥 읽습니다. 그래서 **다른 구글 계정의 시트라도 그대로 연동됩니다.**

시트 구성 (탭 이름은 아무거나 상관없고, 주소만 맞으면 됩니다)

  키워드   | 구분   | 키워드        | 사용 |
           | 포함   | 시니어        | Y    |
           | 제외   | 채용          | Y    |

  수신자   | 이메일             | 이름   | 사용 |
           | hong@zeroweb.co.kr | 홍길동 | Y    |

  기관     | 기관명             | 주소                  | 사용 |
           | 부산테크노파크      |                       | Y    |
           | 새로운기관          | https://.../list      | Y    |

규칙
  - '사용' 칸이 N, n, 아니오, false 면 그 줄은 무시합니다. 비어 있으면 사용으로 봅니다.
  - 기관 탭에서 기존 기관은 '기관명'으로 찾아 켜고 끄기만 합니다.
    (주소·선택자 같은 세부 설정은 institutions.yaml 이 계속 관리합니다)
  - '주소'가 적힌 새 이름은 새 기관으로 추가됩니다.
  - 시트를 못 읽으면 조용히 로컬 설정을 그대로 씁니다. 브리핑은 멈추지 않습니다.
"""
from __future__ import annotations

import csv
import io
import re

import requests

from .config import Config, Institution

OFF = {"n", "no", "false", "0", "x", "아니오", "아니요", "미사용", "off", "끔"}

# 브라우저 주소창에서 복사한 편집 주소
_EDIT_URL = re.compile(r"/spreadsheets/d/(?!e/)([A-Za-z0-9_-]{20,})")
_GID = re.compile(r"[?&#]gid=(\d+)")


class SheetError(Exception):
    pass


def to_csv_url(url: str) -> str:
    """어떤 형태의 구글시트 주소든 CSV로 읽히는 주소로 바꾼다.

    브라우저에서 그냥 복사한 편집 주소
        .../spreadsheets/d/<시트ID>/edit?gid=<탭ID>#gid=<탭ID>
    는 그대로 열면 CSV가 아니라 화면(HTML)이 나온다. 그래서
        .../spreadsheets/d/<시트ID>/export?format=csv&gid=<탭ID>
    로 바꿔준다. (이 주소가 동작하려면 시트 공유가
     '링크가 있는 모든 사용자 - 뷰어' 여야 한다)

    '웹에 게시'로 받은 주소(/spreadsheets/d/e/... output=csv)는 그대로 둔다.
    """
    url = (url or "").strip()
    if not url:
        return url
    if "/spreadsheets/d/e/" in url:  # 웹에 게시된 주소
        return url
    m = _EDIT_URL.search(url)
    if not m:
        return url
    sid = m.group(1)
    g = _GID.search(url)
    gid = g.group(1) if g else "0"
    return f"https://docs.google.com/spreadsheets/d/{sid}/export?format=csv&gid={gid}"


def _get(url: str, timeout: int) -> list[dict]:
    resp = requests.get(to_csv_url(url), timeout=timeout, allow_redirects=True)
    if resp.status_code >= 400:
        raise SheetError(f"HTTP {resp.status_code} — 시트 공유 설정을 확인하세요")
    resp.encoding = "utf-8"
    text = resp.text
    if "<html" in text[:400].lower() or "accounts.google.com" in resp.url:
        raise SheetError(
            "CSV 대신 로그인 화면이 왔습니다 — 시트 공유를 "
            "'링크가 있는 모든 사용자: 뷰어'로 바꾸거나 '웹에 게시'하세요"
        )
    rows = list(csv.DictReader(io.StringIO(text)))
    if not rows:
        raise SheetError("내용이 비어 있습니다")
    return rows


def _cell(row: dict, *names: str) -> str:
    """열 이름이 조금 달라도 찾아준다 (공백·대소문자 무시)."""
    norm = {(k or "").strip().replace(" ", ""): (v or "").strip() for k, v in row.items()}
    for n in names:
        key = n.replace(" ", "")
        if key in norm:
            return norm[key]
    return ""


def _enabled(row: dict) -> bool:
    v = _cell(row, "사용", "사용여부", "활성", "enabled", "use").lower()
    return v not in OFF


# ---------------------------------------------------------------- 각 탭


def _words(rows: list[dict]) -> list[str]:
    out = []
    for r in rows:
        if not _enabled(r):
            continue
        word = _cell(r, "키워드", "단어", "keyword")
        if word:
            out.append(word)
    return out


def apply_keyword_tab(cfg: Config, url: str, timeout: int, kind: str) -> str:
    """포함 탭 또는 제외 탭 하나를 읽는다. kind 는 'include' / 'exclude'."""
    words = _words(_get(url, timeout))
    if not words:
        raise SheetError("쓸 수 있는 키워드가 없습니다")
    if kind == "include":
        cfg.include_keywords = words
    else:
        cfg.exclude_keywords = words
    return f"{len(words)}개"


def apply_keywords(cfg: Config, url: str, timeout: int) -> str:
    """포함·제외가 '구분' 칸으로 한 탭에 섞여 있는 형태 (예전 방식, 계속 지원)."""
    rows = _get(url, timeout)
    inc: list[str] = []
    exc: list[str] = []
    for r in rows:
        if not _enabled(r):
            continue
        word = _cell(r, "키워드", "단어", "keyword")
        if not word:
            continue
        kind = _cell(r, "구분", "유형", "종류", "type")
        (exc if "제외" in kind or kind.lower() in ("exclude", "x") else inc).append(word)
    if not inc and not exc:
        raise SheetError("쓸 수 있는 키워드가 없습니다")
    if inc:
        cfg.include_keywords = inc
    if exc:
        cfg.exclude_keywords = exc
    return f"포함 {len(inc)}개 / 제외 {len(exc)}개"


def apply_recipients(cfg: Config, url: str, timeout: int) -> str:
    rows = _get(url, timeout)
    people = []
    for r in rows:
        if not _enabled(r):
            continue
        mail = _cell(r, "이메일", "메일", "메일주소", "email", "주소")
        if "@" in mail and "." in mail.split("@")[-1]:
            people.append(mail)
    if not people:
        raise SheetError("쓸 수 있는 이메일 주소가 없습니다")
    cfg.recipients = people
    return f"{len(people)}명"


def apply_institutions(
    institutions: list[Institution], url: str, timeout: int
) -> tuple[list[Institution], str]:
    rows = _get(url, timeout)
    by_name = {i.name.strip(): i for i in institutions}
    on = off = added = 0

    for r in rows:
        name = _cell(r, "기관명", "기관", "이름", "name")
        if not name:
            continue
        use = _enabled(r)
        found = by_name.get(name.strip())
        if found is not None:
            if found.enabled != use:
                found.enabled = use
                on += 1 if use else 0
                off += 0 if use else 1
            continue
        # 시트에만 있는 새 기관 — 주소가 있어야 추가한다
        addr = _cell(r, "주소", "URL", "url", "링크", "게시판주소")
        if use and addr.startswith("http"):
            institutions.append(
                Institution(
                    id="sheet_" + str(abs(hash(name)) % 10**8),
                    name=name.strip(),
                    url=addr,
                    base=addr,
                    enabled=True,
                    status="check",
                    notes="구글시트에서 추가됨",
                )
            )
            added += 1

    return institutions, f"켬 {on} / 끔 {off} / 추가 {added}"


# ---------------------------------------------------------------- 진입점


def apply_all(
    cfg: Config, institutions: list[Institution]
) -> tuple[list[Institution], list[str]]:
    """시트 설정을 적용하고, 무슨 일이 있었는지 사람이 읽을 수 있는 줄로 돌려준다."""
    log: list[str] = []
    sheet = cfg.sheet or {}
    if not sheet.get("enabled"):
        return institutions, log

    timeout = int(sheet.get("timeout", 20))
    jobs = [
        (
            "포함 키워드",
            sheet.get("include_keywords_url"),
            lambda u: apply_keyword_tab(cfg, u, timeout, "include"),
        ),
        (
            "제외 키워드",
            sheet.get("exclude_keywords_url"),
            lambda u: apply_keyword_tab(cfg, u, timeout, "exclude"),
        ),
        # 포함·제외를 한 탭에 '구분' 칸으로 넣은 예전 방식도 계속 지원한다
        ("키워드", sheet.get("keywords_url"), lambda u: apply_keywords(cfg, u, timeout)),
        ("수신자", sheet.get("recipients_url"), lambda u: apply_recipients(cfg, u, timeout)),
    ]
    for label, url, fn in jobs:
        if not url:
            continue
        try:
            log.append(f"구글시트 {label}: {fn(url)}")
        except Exception as exc:  # noqa: BLE001
            log.append(f"구글시트 {label} 읽기 실패 ({exc}) — 저장소 설정을 씁니다")

    url = sheet.get("institutions_url")
    if url:
        try:
            institutions, msg = apply_institutions(institutions, url, timeout)
            log.append(f"구글시트 기관: {msg}")
        except Exception as exc:  # noqa: BLE001
            log.append(f"구글시트 기관 읽기 실패 ({exc}) — 저장소 설정을 씁니다")

    return institutions, log
