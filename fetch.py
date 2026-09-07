"""HTTP 수집 — 재시도, 인코딩 추정, SSL 예외 처리."""
from __future__ import annotations

import time
import urllib3

import requests

from .config import Config, Institution

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)


class FetchError(Exception):
    pass


def make_session(cfg: Config) -> requests.Session:
    s = requests.Session()
    s.headers.update(
        {
            "User-Agent": cfg.user_agent,
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
            "Accept-Language": "ko-KR,ko;q=0.9,en;q=0.8",
            "Connection": "close",
        }
    )
    return s


def fetch(session: requests.Session, inst: Institution, cfg: Config) -> str:
    """기관 목록 페이지 HTML(또는 JSON 문자열)을 가져온다."""
    if not inst.url:
        raise FetchError("URL이 설정되지 않았습니다")

    last_err: Exception | None = None
    for attempt in range(cfg.retries + 1):
        try:
            resp = session.get(
                inst.url,
                timeout=cfg.timeout,
                verify=inst.verify_ssl,
                headers={"Referer": inst.base or inst.url},
                allow_redirects=True,
            )
            if resp.status_code >= 400:
                raise FetchError(f"HTTP {resp.status_code}")

            if inst.encoding:
                resp.encoding = inst.encoding
            elif not resp.encoding or resp.encoding.lower() in ("iso-8859-1", "ascii"):
                resp.encoding = resp.apparent_encoding or "utf-8"

            text = resp.text
            if len(text) < 500:
                raise FetchError(f"응답이 너무 짧습니다 ({len(text)}바이트) — 차단 페이지일 수 있음")
            return text
        except Exception as exc:  # noqa: BLE001
            last_err = exc
            if attempt < cfg.retries:
                time.sleep(1.5 * (attempt + 1))

    raise FetchError(str(last_err))
