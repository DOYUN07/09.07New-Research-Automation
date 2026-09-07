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

# 산업통상부형: 첨부파일 링크 텍스트가 제목 링크보다 길다 (1차 진단에서 발견된 문제)
ATTACH_TRAP = """<html><body><table><tbody>
<tr><td>71310</td>
    <td><a href="/kor/article/ATCL2826a2625/71310/view">2026년도 산업통상부-에너지공기업 기술나눔</a>
        <a href="/common/download.do?fid=99231" class="file">
          2026년도 산업통상부-에너지공기업 기술나눔 공고문.hwpx 다운로드</a></td>
    <td>산업기술시장혁신과</td><td>2026-09-07</td><td>412</td></tr>
<tr><td>71307</td>
    <td><a href="/kor/article/ATCL2826a2625/71307/view">산업융합 규제샌드박스 규제특례 승인</a>
        <a href="/common/download.do?fid=99228" class="file">
          산업융합 규제샌드박스 규제특례 승인 공고문.hwpx 다운로드</a></td>
    <td>산업융합규제샌드박스팀</td><td>2026-09-07</td><td>233</td></tr>
<tr><td>71304</td>
    <td><a href="/kor/article/ATCL2826a2625/71304/view">지역산업위기대응 이차보전 지원사업 2차 변경공고</a>
        <a href="/common/download.do?fid=99225" class="file">
          2026년도 지역산업위기대응 이차보전 지원사업 2차 변경공고.hwpx 다운로드</a></td>
    <td>지역경제정책과</td><td>2026-09-04</td><td>877</td></tr>
</tbody></table></body></html>"""

# 부산테크노파크형 2: 한 <a> 안에 제목 span이 두 개라 제목이 두 번 이어붙는다
DOUBLED_TITLE = """<html><body><table><tbody>
<tr><td>4533</td><td><a href="/view?seq=1">
      <span class="subjectWr">신중년 디지털 전환 지원사업 공고</span><span
      class="titleHover">신중년 디지털 전환 지원사업 공고</span></a></td>
    <td>2026.09.07</td></tr>
<tr><td>4532</td><td><a href="/view?seq=2">
      <span class="subjectWr">고령친화 서비스 실증 참여기업 모집</span><span
      class="titleHover">고령친화 서비스 실증 참여기업 모집</span></a></td>
    <td>2026.09.05</td></tr>
<tr><td>4531</td><td><a href="/view?seq=3">
      <span class="subjectWr">클라우드 바우처 3차 공고</span><span
      class="titleHover">클라우드 바우처 3차 공고</span></a></td>
    <td>2026.09.02</td></tr>
</tbody></table></body></html>"""

# 연구개발특구진흥재단형: 공고기간·신청기간 두 개의 기간이 한 행에 있다
# (1차 진단에서 게시일이 미래 날짜로 잡히던 문제)
TWO_PERIODS = """<html><body><table><tbody>
<tr><td>1</td><td>접수중</td>
    <td><a href="/form.tab?TSK_PBNC_ID=2026-0023">2026년 사회문제해결형 R&amp;BD 지원사업 시행 공고</a></td>
    <td>2026-08-21 ~ 2026-09-21</td><td>2026-09-10 ~ 2026-09-21</td>
    <td>김담당</td><td>521</td></tr>
<tr><td>2</td><td>접수중</td>
    <td><a href="/form.tab?TSK_PBNC_ID=2026-0024">2026년 실증화 지원 프로그램 공고</a></td>
    <td>2026-09-01 ~ 2026-10-05</td><td>2026-09-15 ~ 2026-10-05</td>
    <td>이담당</td><td>318</td></tr>
<tr><td>3</td><td>접수중</td>
    <td><a href="/form.tab?TSK_PBNC_ID=2026-0025">2026년 규제샌드박스 컨설팅 지원사업</a></td>
    <td>2026-09-03 ~ 2026-09-30</td><td>2026-09-08 ~ 2026-09-30</td>
    <td>박담당</td><td>140</td></tr>
</tbody></table></body></html>"""

# 전북테크노파크형: 목록에 게시일 없이 '마감 2026-12-31 18:00'만 있다
# (2차 진단에서 마감일시가 게시일로 잡히던 문제)
DEADLINE_ONLY = """<html><body><ul class="biz-list">
<li><span class="state">접수중</span>
    <a href="https://www.jbtp.or.kr/board/view.jbtp?dataSid=19770">
      2026년 산업기술단지 거점기능강화사업 기업애로해결 컨설팅 수요조사 공고</a>
    <span class="due">마감 2026-12-31 18:00</span></li>
<li><span class="state">접수중</span>
    <a href="https://www.jbtp.or.kr/board/view.jbtp?dataSid=19843">
      2026년 전북형 스마트 제조혁신 프로젝트 사업 추가모집 공고</a>
    <span class="due">마감 2026-12-31 18:00</span></li>
<li><span class="state">접수중</span>
    <a href="https://www.jbtp.or.kr/board/view.jbtp?dataSid=20611">
      2026년도 오픈랩 활용 기술지원 프로그램 참여기업 모집공고</a>
    <span class="due">마감 2026-09-30 17:00</span></li>
</ul></body></html>"""

# 부산테크노파크형 3: 두 span의 내용이 완전히 같지는 않다
# (한쪽은 '재공고' 라벨이 붙고, 다른 쪽은 말줄임표로 잘려 있음)
PARTIAL_DOUBLE = """<html><body><table><tbody>
<tr><td>4530</td><td><a href="/view?seq=1">
      <span class="titleHover">기업성장기반 글로벌 하이메디 허브 특구 상생협력사업 기업지원모집 공고(4차) 재공고</span><span
      class="subjectWr">기업성장기반 글로벌 하이메디 허브 특구 상생협...</span></a></td>
    <td>2026.09.07</td></tr>
<tr><td>4529</td><td><a href="/view?seq=2">
      <span class="titleHover">글로벌시장 대응 AI기반 공조부품 성능평가 인프라 고도화사업 지원사업 2차 공고 연장</span><span
      class="subjectWr">글로벌시장 대응 AI기반 공조부품 성능평가 인프...</span></a></td>
    <td>2026.09.05</td></tr>
<tr><td>4528</td><td><a href="/view?seq=3">
      <span class="titleHover">시니어 돌봄로봇 실증 참여기업 모집 공고</span><span
      class="subjectWr">시니어 돌봄로봇 실증 참여기업 모집 공고</span></a></td>
    <td>2026.09.02</td></tr>
</tbody></table></body></html>"""

# 게시판이 <header> 안에 들어 있는 사이트 — 정리 단계가 목록을 지워버리면 안 된다
# (v1.1에서 NIPA가 0건이 된 유형의 회귀 방지)
INSIDE_HEADER = """<html><body><header id="wrap">
<table><tbody>
<tr><td>1</td><td><a href="/home/2-2/16921" class="down-link">
      2026년 아태 AI 특화지구(AHAP) 조성 사업 공고</a></td><td>2026-09-03</td></tr>
<tr><td>2</td><td><a href="/home/2-2/16900" class="down-link">
      2026년 KoVAC XR 쇼룸 입주기업 2차 모집</a></td><td>2026-08-18</td></tr>
<tr><td>3</td><td><a href="/home/2-2/16880" class="down-link">
      2026년 클라우드 바우처 지원사업 3차 공고</a></td><td>2026-08-11</td></tr>
</tbody></table></header></body></html>"""

# 중소벤처기업부형: 행(tr) 안에 첨부파일 <ul><li> 가 들어 있고,
# 모바일용 <a> 가 제목 + 상세정보를 통째로 감싼다 (3차 진단에서 0건이던 원인)
ROW_WITH_LI = """<html><body><div class="board_list"><table><tbody>
<tr onclick="doBbsFView('310','1071012','16010100','1071012');"
    title="2026년 중소기업 스마트서비스 지원사업 참여기업 모집 공고(A/S지원)">
  <td>2192</td>
  <td class="subject">
    <a class="pc-detail" href="#view">2026년 중소기업 스마트서비스 지원사업 참여기업 모집 공고(A/S지원)</a>
    <a class="mo-detail" href="#view">2026년 중소기업 스마트서비스 지원사업 참여기업 모집 공고(A/S지원)
       담당부서 중소기업인공지능확산추진단 공고번호 제2026-540호 신청기간 2026-09-07 ~ 2026-10-06</a>
    <div class="tableInfoBox">
      <dl><dt>담당부서</dt><dd>중소기업인공지능확산추진단</dd></dl>
      <dl><dt>신청기간</dt><dd>2026-09-07 ~ 2026-10-06</dd></dl>
    </div>
  </td>
  <td class="attached-files">
    <ul><li><a class="attach-file" href="#">붙임1_공고문.hwp</a></li>
        <li><a class="attach-file" href="#">붙임2_신청서.hwp</a></li></ul>
  </td>
  <td>2026-09-07</td></tr>
<tr onclick="doBbsFView('310','1070845','16010100','1070845');">
  <td>2191</td>
  <td class="subject">
    <a class="pc-detail" href="#view">『중소기업 AX 우수사례 공모전』참가기업 모집 공고</a>
    <div class="tableInfoBox"><dl><dt>신청기간</dt><dd>2026-09-01 ~ 2026-09-21</dd></dl></div>
  </td>
  <td class="attached-files"><ul><li><a class="attach-file" href="#">공고문.pdf</a></li></ul></td>
  <td>2026-09-01</td></tr>
<tr onclick="doBbsFView('310','1070800','16010100','1070800');">
  <td>2190</td>
  <td class="subject">
    <a class="pc-detail" href="#view">2026년 스마트공장 클라우드 전환 지원사업 공고</a>
    <div class="tableInfoBox"><dl><dt>신청기간</dt><dd>2026-08-28 ~ 2026-09-30</dd></dl></div>
  </td>
  <td class="attached-files"><ul><li><a class="attach-file" href="#">신청서.hwp</a></li></ul></td>
  <td>2026-08-28</td></tr>
</tbody></table></div></body></html>"""

# 부산시민운동지원센터형: 행마다 감싸는 div가 따로 있어 형제가 아니다
# (div.table_td > div.table_td_line — 3차 진단에서 0건이던 원인)
WRAPPED_ROWS = """<html><body><div class="table_default type">
<div class="table_th"><p class="list_num">번호</p><p class="list_subj">제목</p>
  <p class="list_date">작성일</p></div>
<div class="table_td"><div class="table_td_line">
  <p class="list_num">884</p><p class="list_num"><b>네트워크 협력강화</b></p>
  <p class="list_subj"><a href="./view?scti=0&amp;no=2904">
    <span>[활동가커뮤니티지원사업] 든든 커뮤니티 큰모임 (9/12)</span></a></p>
  <p class="list_date">2026-09-02</p></div></div>
<div class="table_td"><div class="table_td_line">
  <p class="list_num">883</p><p class="list_num"><b>시민운동 성장지원</b></p>
  <p class="list_subj"><a href="./view?scti=0&amp;no=2903">
    <span>[교육훈련지원사업] 똑똑 활동에 힘이 필요한 순간</span></a></p>
  <p class="list_date">2026-09-02</p></div></div>
<div class="table_td"><div class="table_td_line">
  <p class="list_num">882</p><p class="list_num"><b>공론장</b></p>
  <p class="list_subj"><a href="./view?scti=0&amp;no=2901">
    <span>[이음] 정책숙의 공론장 지원사업 이음 참여 단체 모집</span></a></p>
  <p class="list_date">2026-08-28</p></div></div>
</div></body></html>"""

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
