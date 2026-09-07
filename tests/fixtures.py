"""실제 기관 게시판 구조를 본뜬 테스트용 HTML.

2026-09-07 사전조사에서 확인한 각 사이트의 실제 마크업 패턴을 재현한 것.
네트워크 없이 파서를 검증하기 위해 사용한다.
"""

# 부산테크노파크: 표 + 접수기간 + 별도 게시일 컬럼
BTP = """<html><body>
<div id="header"><ul class="gnb"><li><a href="/a">사업안내</a></li>
<li><a href="/b">기업지원</a></li><li><a href="/c">알림마당</a></li></ul></div>
<table class="bdListTbl"><thead><tr><th>번호</th><th>사업공고명</th><th>접수기간</th>
<th>상태</th><th>작성자</th><th>게시일</th></tr></thead>
<tbody>
<tr><td>4533</td>
    <td class="subject"><a href="?mCode=MN013&amp;mode=view&amp;board_seq=9582417">
      <span class="titleHover">Age-Tech 종합지원센터 운영 사업 TRL기반 기술성장 맞춤 지원 공고</span></a></td>
    <td class="period">접수기간 : 2026.09.07 ~ 2026.09.30 <span class="dday">D-23</span></td>
    <td>접수중</td><td>기업지원단</td><td class="date">2026.09.07</td></tr>
<tr><td>4532</td>
    <td class="subject"><a href="?mCode=MN013&amp;mode=view&amp;board_seq=9582398">
      <span class="titleHover">2026년 커피산업 실무인력 양성교육(하반기) 교육생 모집공고</span></a></td>
    <td class="period">접수기간 : 2026.08.20 ~ 2026.09.01</td>
    <td>마감</td><td>인재양성실</td><td class="date">2026.08.20</td></tr>
<tr><td>4531</td>
    <td class="subject"><a href="?mCode=MN013&amp;mode=view&amp;board_seq=9582364">
      <span class="titleHover">2027년도 부산 방산 중소기업 생산성향상 지원사업 2차 공고</span></a></td>
    <td class="period">접수기간 : 2026.08.31 ~ 2026.10.15</td>
    <td>접수중</td><td>방산팀</td><td class="date">2026.08.31</td></tr>
<tr><td>4530</td>
    <td class="subject"><a href="?mCode=MN013&amp;mode=view&amp;board_seq=9582301">
      <span class="titleHover">2026년 부산테크노파크 직원 채용 공고</span></a></td>
    <td class="period">접수기간 : 2026.09.02 ~ 2026.09.20</td>
    <td>접수중</td><td>인사팀</td><td class="date">2026.09.02</td></tr>
</tbody></table></body></html>"""

# 광주테크노파크: 번호 셀이 th, 기간만 있고 게시일 컬럼 없음
GJTP = """<html><body>
<table class="list-table"><tbody>
<tr><th scope="row" class="num">1772</th>
    <td class="tal"><a href="?act=view&amp;bsnssId=2259">2026년도 지역기업 맞춤형 현장애로 해결 기술닥터 참여기업 2차 모집</a></td>
    <td class="period">2026-09-03 ~ <br>2026-09-14</td>
    <td class="respon">기업지원팀</td><td class="hits">120</td><td class="accept">접수중</td></tr>
<tr><th scope="row" class="num">1771</th>
    <td class="tal"><a href="?act=view&amp;bsnssId=2258">청년창업 거주지원시설(창업하여家) 입주자 3차 모집</a></td>
    <td class="period">2026-09-02 ~ <br>2026-09-30</td>
    <td class="respon">창업지원팀</td><td class="hits">88</td><td class="accept">접수중</td></tr>
<tr><th scope="row" class="num">1770</th>
    <td class="tal"><a href="?act=view&amp;bsnssId=2257">지역혁신 실증 프로젝트 기획 실증의제 수요조사 공고(2차)</a></td>
    <td class="period">2026-09-01 ~ <br>2026-09-05</td>
    <td class="respon">전략기획팀</td><td class="hits">45</td><td class="accept">마감</td></tr>
</tbody></table></body></html>"""

# 농림축산식품부: 날짜가 td가 아니라 dd.date 안에 있음
MAFRA = """<html><body><div class="list"><table><tbody>
<tr><td>578966</td><td><p><a href="/bbs/home/791/578966/artclView.do">
      스마트농업 클라우드 실증 지원사업 공고<span class="new">새글</span></a></p>
      <dl><dd class="date">2026.09.04</dd><dd class="name">농업금융정책과</dd></dl></td></tr>
<tr><td>578959</td><td><p><a href="/bbs/home/791/578959/artclView.do">
      2026년 하반기 퇴직공무원(일반직) 포상 후보자 공개검증</a></p>
      <dl><dd class="date">2026.09.04</dd><dd class="name">운영지원과</dd></dl></td></tr>
<tr><td>578879</td><td><p><a href="/bbs/home/791/578879/artclView.do">
      SAT1형 구제역 백신접종 명령 취소 공고</a></p>
      <dl><dd class="date">2026.08.27</dd><dd class="name">방역정책과</dd></dl></td></tr>
</tbody></table></div></body></html>"""

# IRIS: 표가 아니라 ul/li, 링크는 onclick
IRIS = """<html><body><div class="board"><ul class="dbody">
<li><span class="inst_title">산업통상부 &gt; 한국산업기술기획평가원</span>
    <strong class="title"><a href="javascript:;"
      onclick="f_bsnsAncmBtinSituListForm_view('023977','ancmIng')">
      2026년도 디지털 전환 실증 지원사업 신규지원대상 과제 공고</a></strong>
    <span class="ancmDe">공고일자 :2026-09-07</span>
    <span class="rcveSttSeNmLst">접수중</span><span class="d_day">D-14</span></li>
<li><span class="inst_title">과학기술정보통신부 &gt; 정보통신기획평가원</span>
    <strong class="title"><a href="javascript:;"
      onclick="f_bsnsAncmBtinSituListForm_view('023640','ancmIng')">
      양자정보과학 인적기반조성사업 신규과제 공모</a></strong>
    <span class="ancmDe">공고일자 :2026-08-31</span>
    <span class="rcveSttSeNmLst">접수중</span></li>
<li><span class="inst_title">해양수산부 &gt; 해양수산과학기술진흥원</span>
    <strong class="title"><a href="javascript:;"
      onclick="f_bsnsAncmBtinSituListForm_view('023757','ancmIng')">
      연안하구 인간-자연시스템 관리기술 개발 사업 재공고</a></strong>
    <span class="ancmDe">공고일자 :2026-08-26</span>
    <span class="rcveSttSeNmLst">접수중</span></li>
</ul></div></body></html>"""

# 중소벤처기업부: onclick doBbsFView + 신청기간이 중첩 div 안에
MSS = """<html><body><div class="board_list"><table><tbody>
<tr><td>1071012</td>
  <td class="subject"><a href="#view" class="pc-detail"
      onclick="doBbsFView('310','1071012','16010100','1071012')">
      2026년 중소기업 스마트서비스 지원사업 참여기업 모집 공고(A/S지원)</a>
    <div class="tableInfoBox"><dl><dt>담당부서</dt><dd>스마트제조혁신기획단</dd></dl>
      <dl><dt>공고번호</dt><dd>제2026-512호</dd></dl>
      <dl><dt>신청기간</dt><dd>2026-09-07 ~ 2026-10-06</dd></dl></div></td>
  <td class="file">첨부파일</td><td>2026-09-07</td><td>331</td></tr>
<tr><td>1070968</td>
  <td class="subject"><a href="#view" class="pc-detail"
      onclick="doBbsFView('310','1070968','16010100','1070968')">
      「2026년 스마트제조혁신 유공」 포상 후보자 모집 공고</a>
    <div class="tableInfoBox"><dl><dt>담당부서</dt><dd>제조혁신과</dd></dl>
      <dl><dt>신청기간</dt><dd>2026-09-04 ~ 2026-09-26</dd></dl></div></td>
  <td class="file">첨부파일</td><td>2026-09-04</td><td>210</td></tr>
<tr><td>1070845</td>
  <td class="subject"><a href="#view" class="pc-detail"
      onclick="doBbsFView('310','1070845','16010100','1070845')">
      『중소기업 AX 우수사례 공모전』참가기업 모집 공고</a>
    <div class="tableInfoBox"><dl><dt>담당부서</dt><dd>디지털혁신과</dd></dl>
      <dl><dt>신청기간</dt><dd>2026-09-01 ~ 2026-09-30</dd></dl></div></td>
  <td class="file">첨부파일</td><td>2026-09-01</td><td>640</td></tr>
</tbody></table></div></body></html>"""

# 부산사회서비스원: 2자리 연도(26.08.05)
BUSAN_PASS = """<html><body><table><tbody>
<tr><td>412</td><td><a href="view.php?zipEncode=AAA111">
    (AI활용 분야) 2026년 사회서비스 제공기관 집합컨설팅 신청안내</a></td>
    <td>운영지원팀</td><td>26.09.05</td><td>77</td></tr>
<tr><td>411</td><td><a href="view.php?zipEncode=BBB222">
    부산형 통합돌봄「부산, 함께돌봄」우수사례 공모 계획</a></td>
    <td>정책연구실</td><td>26.09.02</td><td>153</td></tr>
<tr><td>410</td><td><a href="view.php?zipEncode=CCC333">
    2026년 사회서비스 종사자 역량강화 교육 안내</a></td>
    <td>교육팀</td><td>26.07.29</td><td>91</td></tr>
</tbody></table></body></html>"""

# K-Startup: 카드형 div/li, 링크는 go_view(id)
KSTARTUP = """<html><body><div class="bizpbanc-list"><ul>
<li><div class="tit"><a href="javascript:go_view(179111)">
      2026년 인천국제공항공사 상생형 창업·벤처기업 지원사업 모집공고</a></div>
    <div class="list_info"><span>등록일자 2026-09-04</span><span class="dday">D-8</span>
    <span>마감일자 2026-09-15</span></div></li>
<li><div class="tit"><a href="javascript:go_view(179126)">
      2026년 웰컴 투 팁스 3차 참가기업 모집 (동남권)</a></div>
    <div class="list_info"><span>등록일자 2026-09-03</span><span class="dday">D-3</span>
    <span>마감일자 2026-09-10</span></div></li>
<li><div class="tit"><a href="javascript:go_view(179110)">
      2026년 한국공항공사 상생형 창업·벤처 기업지원 프로그램 참여기업 모집</a></div>
    <div class="list_info"><span>등록일자 2026-09-01</span>
    <span>마감일자 2026-09-05</span></div></li>
</ul></div></body></html>"""

# 게시일 컬럼이 아예 없는 게시판 (고령친화산업지원센터 센터공지 형태)
NO_DATE = """<html><body><table class="tstyle_list"><tbody>
<tr><td class="num">15</td><td class="ellipsis">
    <a href="/board/view?menuId=MENU00325&amp;linkId=48948098">[공고] 2026년 1차 고령친화우수제품 지정 공고</a></td>
    <td>320</td><td>첨부</td></tr>
<tr><td class="num">14</td><td class="ellipsis">
    <a href="/board/view?menuId=MENU00325&amp;linkId=48948012">고령친화산업 실태조사 참여기업 모집 안내</a></td>
    <td>211</td><td>첨부</td></tr>
<tr><td class="num">13</td><td class="ellipsis">
    <a href="/board/view?menuId=MENU00325&amp;linkId=48947980">에이지테크 수요기업 매칭 상담회 개최</a></td>
    <td>187</td><td>첨부</td></tr>
</tbody></table></body></html>"""
