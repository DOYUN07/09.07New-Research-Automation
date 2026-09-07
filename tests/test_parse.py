"""파서 검증 — 네트워크 없이 저장된 마크업으로 확인한다.

실행: python -m tests.test_parse
"""
from __future__ import annotations

import sys
from datetime import date

from src.config import Institution, load_config
from src.filters import FilterStats, apply_filters
from src.parse import parse
from tests import fixtures

TODAY = date(2026, 9, 7)
FAILS: list[str] = []


def check(label: str, got, want) -> None:
    if got != want:
        FAILS.append(f"{label}\n    기대: {want!r}\n    실제: {got!r}")
        print(f"  ✗ {label}: {got!r} != {want!r}")
    else:
        print(f"  ✓ {label}")


def inst(**kw) -> Institution:
    kw.setdefault("id", "t")
    kw.setdefault("name", "테스트")
    kw.setdefault("url", "https://example.com/list")
    kw.setdefault("base", "https://example.com")
    return Institution(**kw)


def P(html: str, institution: Institution):
    """기준일을 2026-09-07로 고정해서 파싱한다 (미래 날짜 판정이 결과에 영향을 주므로)."""
    return parse(html, institution, TODAY)


def main() -> int:
    print("\n[1] 부산테크노파크형 — 접수기간과 게시일이 따로 있는 표")
    r = P(fixtures.BTP, inst(id="btp", base="https://www.btp.or.kr/kor/CMS/Board/Board.do"))
    check("행 수", len(r), 4)
    check("제목", r[0].title, "Age-Tech 종합지원센터 운영 사업 TRL기반 기술성장 맞춤 지원 공고")
    check("게시일", r[0].posted, date(2026, 9, 7))
    check("마감일", r[0].deadline, date(2026, 9, 30))
    check("링크 절대경로", r[0].url.startswith("https://www.btp.or.kr/"), True)
    check("마감 상태 인식", r[1].closed_flag, True)

    print("\n[2] 광주테크노파크형 — 기간만 있고 게시일 컬럼 없음, 번호가 th")
    r = P(fixtures.GJTP, inst(id="gjtp", base="https://www.gjtp.or.kr/home/business.cs"))
    check("행 수", len(r), 3)
    check("게시일=기간 시작", r[0].posted, date(2026, 9, 3))
    check("마감일=기간 끝", r[0].deadline, date(2026, 9, 14))

    print("\n[3] 농림축산식품부형 — 날짜가 dd.date 안")
    r = P(fixtures.MAFRA, inst(id="mafra", base="https://www.mafra.go.kr"))
    check("행 수", len(r), 3)
    check("제목에서 '새글' 제거", r[0].title, "스마트농업 클라우드 실증 지원사업 공고")
    check("게시일", r[0].posted, date(2026, 9, 4))

    print("\n[4] IRIS형 — ul/li 구조 + onclick 링크")
    r = P(
        fixtures.IRIS,
        inst(
            id="iris",
            base="https://www.iris.go.kr",
            row_selector="ul.dbody > li",
            link_from_onclick=r"_view\('(\d+)'",
            detail_url="https://www.iris.go.kr/contents/retrieveBsnsAncmView.do?ancmId={id}&ancmPrg=ancmIng",
        ),
    )
    check("행 수", len(r), 3)
    check("게시일", r[0].posted, date(2026, 9, 7))
    check(
        "onclick에서 상세 URL 조립",
        r[0].url,
        "https://www.iris.go.kr/contents/retrieveBsnsAncmView.do?ancmId=023977&ancmPrg=ancmIng",
    )

    print("\n[4-b] IRIS형 — 선택자 없이 자동 인식되는지")
    r_auto = P(
        fixtures.IRIS,
        inst(
            id="iris",
            base="https://www.iris.go.kr",
            link_from_onclick=r"_view\('(\d+)'",
            detail_url="https://www.iris.go.kr/x?ancmId={id}",
        ),
    )
    check("자동 인식 행 수", len(r_auto), 3)

    print("\n[5] 중소벤처기업부형 — onclick doBbsFView + 중첩 div 안의 신청기간")
    r = P(
        fixtures.MSS,
        inst(
            id="mss",
            base="https://www.mss.go.kr",
            link_from_onclick=r"doBbsFView\('\d+','(\d+)'",
            detail_url="https://www.mss.go.kr/site/smba/ex/bbs/View.do?cbIdx=310&bcIdx={id}&parentSeq={id}",
        ),
    )
    check("행 수", len(r), 3)
    check("게시일", r[0].posted, date(2026, 9, 7))
    check("마감일=신청기간 종료", r[0].deadline, date(2026, 10, 6))
    check("상세 URL bcIdx", "bcIdx=1071012" in r[0].url, True)

    print("\n[6] 부산사회서비스원형 — 2자리 연도(26.09.05)")
    r = P(fixtures.BUSAN_PASS, inst(id="bp", base="https://busan.pass.or.kr/SW_bbs/notice/"))
    check("행 수", len(r), 3)
    check("2자리 연도 해석", r[0].posted, date(2026, 9, 5))

    print("\n[7] K-Startup형 — 카드형 목록 + go_view(id)")
    r = P(
        fixtures.KSTARTUP,
        inst(
            id="ks",
            base="https://www.k-startup.go.kr",
            link_from_onclick=r"go_view\((\d+)\)",
            detail_url="https://www.k-startup.go.kr/web/contents/bizpbanc-ongoing.do?schM=view&pbancSn={id}&page=1",
        ),
    )
    check("행 수", len(r), 3)
    check("게시일", r[0].posted, date(2026, 9, 4))
    check("마감일", r[0].deadline, date(2026, 9, 15))
    check("상세 URL", "pbancSn=179111" in r[0].url, True)

    print("\n[8] 게시일이 아예 없는 게시판")
    r = P(fixtures.NO_DATE, inst(id="nd", base="https://www.khidi.or.kr"))
    check("행 수", len(r), 3)
    check("게시일 None", r[0].posted, None)
    check("제목", r[0].title, "[공고] 2026년 1차 고령친화우수제품 지정 공고")

    # -------------------------------- 1차 실전 진단(2026-09-07)에서 발견된 문제들
    print("\n[A] 첨부파일 링크를 제목으로 착각하지 않는지 (산업통상부에서 발생)")
    r = P(fixtures.ATTACH_TRAP, inst(id="motir", base="https://www.motir.go.kr"))
    check("행 수", len(r), 3)
    check("제목이 파일명이 아님", r[0].title, "2026년도 산업통상부-에너지공기업 기술나눔")
    check("'.hwpx' 미포함", ".hwpx" in r[0].title, False)
    check("'다운로드' 미포함", "다운로드" in r[0].title, False)
    check("링크가 첨부파일이 아님", "download" in r[0].url, False)
    check("링크가 본문", "/71310/view" in r[0].url, True)

    print("\n[B] 제목이 두 번 이어붙는 현상 (부산테크노파크에서 발생)")
    r = P(fixtures.DOUBLED_TITLE, inst(id="dbl", base="https://example.com"))
    check("행 수", len(r), 3)
    check("제목 1회만", r[0].title, "신중년 디지털 전환 지원사업 공고")
    check("제목 1회만 (2)", r[1].title, "고령친화 서비스 실증 참여기업 모집")

    print("\n[C] 한 행에 기간이 두 개일 때 게시일이 미래로 잡히지 않는지 (연구개발특구진흥재단)")
    r = P(fixtures.TWO_PERIODS, inst(id="innopolis", base="https://pms.innopolis.or.kr"))
    check("행 수", len(r), 3)
    check("게시일=공고기간 시작", r[0].posted, date(2026, 8, 21))
    check("게시일이 오늘 이전", r[0].posted <= TODAY, True)
    check("마감일=가장 늦은 종료일", r[0].deadline, date(2026, 9, 21))
    check("2행 게시일", r[1].posted, date(2026, 9, 1))
    check("2행 마감일", r[1].deadline, date(2026, 10, 5))

    # ---------------------------------------------------------------- 필터
    print("\n[9] 필터 규칙")
    cfg = load_config()
    cfg.include_keywords = ["Age-Tech", "지원사업", "고령", "AX", "실증", "돌봄", "클라우드"]
    cfg.exclude_keywords = ["채용", "포상", "구제역", "퇴직공무원"]
    cfg.lookback_days = 10
    cfg.max_per_institution = 10

    parsed = P(fixtures.BTP, inst(id="btp", base="https://www.btp.or.kr/"))
    st = FilterStats()
    kept = apply_filters(parsed, cfg, TODAY, set(), st)
    titles = [n.title for n in kept]
    check("채용 공고 제외", any("채용" in t for t in titles), False)
    check("마감된 공고 제외", any("커피산업" in t for t in titles), False)
    check("Age-Tech 공고 채택", any("Age-Tech" in t for t in titles), True)

    print("\n[9-b] 게시일 10일 초과 공고 제외")
    parsed = P(fixtures.BUSAN_PASS, inst(id="bp", base="https://busan.pass.or.kr/"))
    cfg.include_keywords = ["사회서비스", "돌봄"]
    cfg.exclude_keywords = []
    st = FilterStats()
    kept = apply_filters(parsed, cfg, TODAY, set(), st)
    check("07.29 공고 제외됨", any("역량강화" in n.title for n in kept), False)
    check("09.05 / 09.02 공고 채택", len(kept), 2)

    print("\n[9-c] 중복 발송 방지")
    st = FilterStats()
    already = {kept[0].key}
    kept2 = apply_filters(
        P(fixtures.BUSAN_PASS, inst(id="bp", base="https://busan.pass.or.kr/")),
        cfg,
        TODAY,
        already,
        st,
    )
    check("이미 보낸 공고 제외", len(kept2), 1)
    check("중복 카운트", st.dropped_duplicate, 1)

    print("\n[9-d] 마감일 미상 공고는 '확인필요'로 포함")
    cfg.include_keywords = ["고령", "에이지테크", "지정"]
    st = FilterStats()
    kept3 = apply_filters(
        P(fixtures.NO_DATE, inst(id="nd", base="https://www.khidi.or.kr")),
        cfg,
        TODAY,
        set(),
        st,
    )
    check("마감일 미상도 채택됨", len(kept3) >= 2, True)
    check("마감일 None", kept3[0].deadline, None)

    print("\n[9-e] unknown_deadline: exclude 로 바꾸면 제외")
    cfg.unknown_deadline = "exclude"
    st = FilterStats()
    kept4 = apply_filters(
        P(fixtures.NO_DATE, inst(id="nd", base="https://www.khidi.or.kr")),
        cfg,
        TODAY,
        set(),
        st,
    )
    check("전부 제외", len(kept4), 0)

    print()
    if FAILS:
        print(f"실패 {len(FAILS)}건")
        for f in FAILS:
            print("  - " + f)
        return 1
    print("모든 검증 통과")
    return 0


if __name__ == "__main__":
    sys.exit(main())
