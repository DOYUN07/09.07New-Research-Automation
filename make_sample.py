"""샘플 메일 생성 — 2026-09-07 기준 실제 공고 제목으로 메일 모양을 확인한다.

실행: python -m tests.make_sample   →  out/sample-brief.html
"""
from __future__ import annotations

from datetime import date
from pathlib import Path

from src.config import ROOT, load_config
from src.parse import Notice
from src.render import render_html, render_text

TODAY = date(2026, 9, 7)


def n(inst_id, inst_name, title, url, posted, deadline, kws):
    return Notice(
        institution_id=inst_id,
        institution_name=inst_name,
        title=title,
        url=url,
        posted=date(*posted) if posted else None,
        deadline=date(*deadline) if deadline else None,
        matched_keywords=kws,
    )


NAMES = {
    "bipa": "부산정보산업진흥원",
    "btp": "부산테크노파크",
    "gntp": "경남테크노파크",
    "gjtp": "광주테크노파크",
    "mss": "중소벤처기업부",
    "nipa": "정보통신산업진흥원(NIPA)",
    "iris": "범부처통합연구지원시스템(IRIS)",
    "khidi": "한국보건산업진흥원",
    "khidi_esenior": "고령친화산업지원센터",
    "kstartup": "K-Startup(창업진흥원)",
    "busan_pass": "부산사회서비스원",
}

GROUPED = {
    "bipa": [
        n("bipa", NAMES["bipa"],
          "2026년 AX 에이지테크 시장확산 지원사업 모집 공고",
          "https://bipa.kr/board/business/view?seq=85330",
          (2026, 9, 1), (2026, 9, 19), ["에이지테크", "AX"]),
        n("bipa", NAMES["bipa"],
          "2026 해양문화도시 기반의 에이지테크 실증거점 조성 사업 「CES 2027 통합 부산관」 참가기업 모집 공고",
          "https://bipa.kr/board/business/view?seq=85329",
          (2026, 9, 1), (2026, 9, 22), ["에이지테크", "실증"]),
    ],
    "btp": [
        n("btp", NAMES["btp"],
          "Age-Tech 종합지원센터 운영 사업 TRL기반 기술성장 맞춤 지원 공고",
          "https://www.btp.or.kr/kor/CMS/Board/Board.do?mCode=MN013&mode=view&board_seq=9582417",
          (2026, 9, 7), (2026, 9, 30), ["Age-Tech"]),
        n("btp", NAMES["btp"],
          "2027년도 부산 방산 중소기업 생산성향상 지원사업 2차 공고",
          "https://www.btp.or.kr/kor/CMS/Board/Board.do?mCode=MN013&mode=view&board_seq=9582364",
          (2026, 8, 31), (2026, 10, 15), []),
    ],
    "gntp": [
        n("gntp", NAMES["gntp"],
          "아태 AI 특화지구(AHAP) 조성 사업 사전 컨소시엄 모집 공고",
          "https://www.gntp.or.kr/biz/applyInfo/3840",
          (2026, 9, 5), (2026, 9, 19), ["AI"]),
        n("gntp", NAMES["gntp"],
          "경상남도 제조 스타트업 홍보·마케팅 지원 프로그램 수혜기업 모집공고",
          "https://www.gntp.or.kr/biz/applyInfo/3838",
          (2026, 9, 3), (2026, 9, 24), ["홍보", "마케팅"]),
    ],
    "gjtp": [
        n("gjtp", NAMES["gjtp"],
          "2026년도 지역기업 맞춤형 현장애로 해결 기술닥터 참여기업 2차 모집",
          "https://www.gjtp.or.kr/home/business.cs?act=view&bsnssId=2259",
          (2026, 9, 3), (2026, 9, 14), []),
    ],
    "mss": [
        n("mss", NAMES["mss"],
          "2026년 중소기업 스마트서비스 지원사업 참여기업 모집 공고(A/S지원)",
          "https://www.mss.go.kr/site/smba/ex/bbs/View.do?cbIdx=310&bcIdx=1071012&parentSeq=1071012",
          (2026, 9, 7), (2026, 10, 6), ["스마트"]),
        n("mss", NAMES["mss"],
          "『중소기업 AX 우수사례 공모전』참가기업 모집 공고",
          "https://www.mss.go.kr/site/smba/ex/bbs/View.do?cbIdx=310&bcIdx=1070845&parentSeq=1070845",
          (2026, 9, 1), (2026, 9, 30), ["AX"]),
    ],
    "nipa": [
        n("nipa", NAMES["nipa"],
          "2026년 아태 AI 특화지구(AHAP) 조성 사업 공고",
          "https://www.nipa.kr/home/2-2/16921",
          (2026, 9, 3), (2026, 9, 24), ["AI"]),
    ],
    "iris": [
        n("iris", NAMES["iris"],
          "2026년도 산업기술R&D연구기획사업 신규지원대상 연구개발과제 공고",
          "https://www.iris.go.kr/contents/retrieveBsnsAncmView.do?ancmId=023977&ancmPrg=ancmIng",
          (2026, 9, 7), None, []),
    ],
    "khidi": [
        n("khidi", NAMES["khidi"],
          "2026년 GHKOL 국제의료사업 실무특화 컨설팅 사업 공고 (~9.16.(수) 까지)",
          "https://www.khidi.or.kr/board/view?menuId=MENU01108&linkId=48949455",
          (2026, 9, 3), (2026, 9, 16), ["헬스케어"]),
    ],
    "khidi_esenior": [
        n("khidi_esenior", NAMES["khidi_esenior"],
          "[공고] 2026년 1차 고령친화우수제품 지정 공고",
          "https://www.khidi.or.kr/board/view?menuId=MENU00325&linkId=48948098",
          None, None, ["고령"]),
    ],
    "kstartup": [
        n("kstartup", NAMES["kstartup"],
          "2026년 인천국제공항공사 상생형 창업·벤처기업 지원사업 모집공고",
          "https://www.k-startup.go.kr/web/contents/bizpbanc-ongoing.do?schM=view&pbancSn=179111&page=1",
          (2026, 9, 4), (2026, 9, 15), []),
    ],
    "busan_pass": [
        n("busan_pass", NAMES["busan_pass"],
          "부산형 통합돌봄「부산, 함께돌봄」우수사례 공모 계획",
          "https://busan.pass.or.kr/SW_bbs/notice/view.php?zipEncode=BBB222",
          (2026, 9, 2), None, ["돌봄"]),
    ],
}

EMPTY = [
    "산업통상부", "보건복지부", "농림축산식품부", "한국지능정보사회진흥원(NIA)",
    "연구개발특구진흥재단", "한국사회보장정보원", "중앙사회서비스원",
    "전남정보문화산업진흥원", "전남바이오진흥원", "광주정보문화산업진흥원",
    "저출산고령사회위원회", "부산시민운동지원센터", "부산경제진흥원",
]

FAILED = [
    ("한국사회적기업진흥원", "HTTP 400 — 서버가 봇 요청을 차단"),
    ("전북테크노파크", "연결 시간 초과"),
]


def main() -> int:
    cfg = load_config()
    html = render_html(GROUPED, NAMES, TODAY, cfg, EMPTY, FAILED)
    text = render_text(GROUPED, NAMES, TODAY, cfg)

    out = ROOT / "out"
    out.mkdir(exist_ok=True)
    (out / "sample-brief.html").write_text(html, encoding="utf-8")
    (out / "sample-brief.txt").write_text(text, encoding="utf-8")

    total = sum(len(v) for v in GROUPED.values())
    print(f"샘플 생성 완료: {total}건 / {len(GROUPED)}개 기관")
    print(f"  {out/'sample-brief.html'}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
