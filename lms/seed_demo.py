"""데모 사이트용 DB: 정태혁 통합과학 SEASON 1 을 N주차까지 진행한 상황 (가짜 데이터).

이 폴더의 instance/ 에 DB·비밀키, 업로드 사진을 새로 만든다. 실제 운영 폴더에서 실행하지 말 것.
    python seed_demo.py            # 14주차(시즌1 끝)까지
    python seed_demo.py 4          # 4주차까지
로그인 정보: DEMO_CREDENTIALS.txt (이 파일 옆)

페르소나
- 선생님 정태혁 (master)         공지, 회차, 시험 평가, 행정문의·cast
- 조교 한지수 (ta_hanjisu)        학습질문, 학습상담·1:1 첨삭, 시험지 첨삭·OMR·수업 기록
- 학생 8명, 반마다 1명 (PERSONAS)  중심 인물은 박서윤 (대구 토요일 A반)

진도, 교재: SEASON 1 커리큘럼 (주차 = 토~금, 1주차 12.26~01.01, 14주차 03.27~04.02)
시험: testfile/ 의 모의고사, 복테 파일 한 벌을 1~14회로 복제 (문항정보는 demo_items.py)
사진: make_demo.py 가 tools/demo_photos.py 를 띄워 두면 실제 교재, 시험지에 학생 필기를 얹은 사진을 쓴다
일정: 대구 토 12/26, 대치 일 12/27, 대치 목 12/31 개강 (재종 4반은 12/28 월).
N주차가 끝난 금요일을 '오늘'로 보고, 요일을 지키며 실행일 직전 금요일로 당긴다.
→ 화면의 '오늘, 이번 주, 최근 7일'이 채워진다.
모든 행동은 실제 화면 기능(폼 전송)으로 실행하고, 날짜만 나중에 맞춘다.
"""
import io
import json as _js
import os
import random
import re
import secrets
import shutil
import subprocess
import sys
from datetime import date, datetime, timedelta

BASE = os.path.dirname(os.path.abspath(__file__))
INSTANCE = os.path.join(BASE, "instance")
DB = os.path.join(INSTANCE, "lms.sqlite3")
CRED = os.path.join(BASE, "DEMO_CREDENTIALS.txt")
IMG_DIR = os.path.join(BASE, "_seed_img")
WEEKS = int(sys.argv[1]) if len(sys.argv) > 1 else 14
os.environ["LMS_DATABASE"] = DB
os.environ.setdefault("SESSION_COOKIE_SECURE", "0")
for p in (DB, DB + "-wal", DB + "-shm"):
    if os.path.exists(p):
        os.remove(p)

from app import create_app  # noqa: E402

app = create_app({"TESTING": True, "WTF_CSRF_ENABLED": False})
rng = random.Random(20261226)
FAIL = []

# ---------------------------------------------------------------- 커리큘럼 (SEASON 1)
CURRICULUM = {  # 주차: (진도, 단원 목록)
    1: ("1단원 전체 + 스펙트럼, 지구 탄생과 진화", ["원소의 생성", "스펙트럼", "지구의 탄생과 진화"]),
    2: ("샤가프 + 생명중심원리 + 지각과 생명체 구성 물질", ["샤가프 법칙", "생명중심원리", "지각과 생명체 구성 물질"]),
    3: ("카탈레이스 + 지구 시스템과 상호작용", ["카탈레이스", "지구 시스템과 상호작용"]),
    4: ("역학", ["역학"]),
    5: ("운동량 + 전기적 성질, 반도체", ["운동량", "전기적 성질과 반도체"]),
    6: ("화학 결합 (전자배치 로직 빌드)", ["화학 결합"]),
    7: ("판구조론 + 생명체 + 지질시대", ["판구조론", "지질시대와 생명체"]),
    8: ("산화환원", ["산화와 환원"]),
    9: ("중화반응 1", ["중화 반응"]),
    10: ("중화반응 2 + 에너지 출입", ["중화 반응", "에너지 출입"]),
    11: ("진화, 생물 다양성, 생태계 요소, 평형", ["진화와 생물 다양성", "생태계와 평형"]),
    12: ("열수지, 엘니뇨", ["지구 열수지", "엘니뇨"]),
    13: ("렌츠, 에너지", ["전자기 유도", "에너지 전환"]),
    14: ("감염병과 과학윤리 + 예시문항 분석", ["과학과 미래 사회", "예시문항"]),
}
WEEK_UNIT = {1: "물질과 규칙성", 2: "물질과 규칙성", 3: "시스템과 상호작용", 4: "시스템과 상호작용", 5: "시스템과 상호작용",
             6: "물질과 규칙성", 7: "시스템과 상호작용", 8: "변화와 다양성", 9: "변화와 다양성", 10: "변화와 다양성",
             11: "변화와 다양성", 12: "환경과 에너지", 13: "환경과 에너지", 14: "과학과 미래사회"}   # 학습질문 단원 (taskkit.UNITS)
def unit_of(title, w):   # 11주차는 진화(변화와 다양성)와 생태계(환경과 에너지)가 섞여 있다
    return "환경과 에너지" if "생태계" in title else WEEK_UNIT[w]


LOGIC_BUILD = {1: 1, 2: 2, 3: 3, 4: 4, 6: 5, 8: 6, 10: 7, 12: 8}     # 주차 → LOGIC BUILD 호
QUESTIONS = {  # 주차: [(제목, 내용, 조교 답변, 사진)]  · 사진: ("item", 시험, 번호, 메모) 또는 ("page", 교재, 쪽, 찾을 글자, 메모)
    1: [("[LINE UP 30p] 흡수 스펙트럼 선의 위치", "흡수선과 방출선 위치가 같다는 게 왜인지 모르겠습니다.",
         "같은 원소는 같은 에너지 차이에서만 빛을 흡수하고 방출합니다. 그래서 흡수선과 방출선이 같은 파장에 생깁니다.",
         ("page", "lineup", 30, "흡수 스펙트럼", "흡수선 = 방출선 위치?")),
        ("[모의고사 1회 15번] 핵융합 전후 질량", "입자 수는 그대로인데 질량 총합이 줄어든다는 ㄱ이 이해가 안 됩니다.",
         "헬륨-3 두 개가 헬륨-4 하나와 수소 두 개가 될 때 줄어든 질량만큼 에너지가 나옵니다(질량 결손). 입자 수가 아니라 질량을 비교하세요.",
         ("item", "m", 15, "입자 수 같은데\n질량 왜 줄어?"))],
    2: [("[모의고사 2회 24번] ㉠~㉣ 염기 정하기", "표에서 ㉠이 T인 걸 어떻게 아는지 모르겠습니다.",
         "X₁과 X₂는 같은 열이 아니라 짝 염기끼리 수가 같습니다. ㉡=14, ㉣=18을 X₁의 빈칸과 맞춰 보면 ㉠-㉢, ㉡-㉣이 짝이고, T/(A+G)=4/5를 만족하는 경우는 ㉠=T(32개)뿐입니다.",
         ("item", "m", 24, "㉠이 왜 T?\n상보 관계 먼저?")),
        ("[FRAMING 77p] 전사할 때 염기", "주형 가닥에서 RNA 염기를 정하는 순서가 헷갈립니다.",
         "주형 가닥 염기와 상보적인 염기를 쓰고 T 자리에 U를 씁니다.", ("page", "framing", 77, "전사", "주형 가닥 → ?"))],
    3: [("[모의고사 3회 11번] T₂에서 효소 구조", "T₂에서 반응 속도가 0인데 단백질 구조가 같다는 ㄴ이 왜 틀렸나요?",
         "효소는 단백질이라 온도가 너무 높으면 입체 구조가 바뀌어 기능을 잃습니다. T₂에서 속도가 0인 것은 구조가 변했기 때문이라 T₁과 같지 않습니다.",
         ("item", "m", 11, "T2 구조\n같은 거 아님?")),
        ("[복테 3회 3번] 산호와 탄소 이동", "산호가 골격을 만드는 게 왜 수권에서 생물권으로 가는 이동인지 궁금합니다.",
         "바닷물(수권)에 녹은 탄소를 산호(생물권)가 몸으로 가져가니 D→C입니다. 골격이 쌓여 석회암이 되면 그때부터 지권입니다.",
         ("item", "r", 3, "D→C 맞나?"))],
    4: [("[LOGIC BUILD 14-1] 등가속도 공식 고르기", "s = v₀t + ½at²과 2as = v² − v₀² 중 어떤 걸 써야 하는지 헷갈립니다.",
         "시간이 주어지면 앞의 식, 시간이 없고 속력과 거리만 있으면 뒤의 식을 씁니다. 모르는 값이 하나만 남는 식을 고르세요.",
         ("page", "logic", 1, "공식", "언제 뭐 써??")),
        ("[복테 4회 16번] h가 45m보다 큰지", "수평으로 던진 공 그래프에서 h를 구하는 방법을 모르겠습니다.",
         "연직 방향만 보면 자유 낙하와 같습니다. 수면에 닿는 시간이 3초보다 짧으니 h = ½gt²은 45 m보다 작습니다.",
         ("item", "r", 16, "h = 1/2 g t^2 ?"))],
    5: [("[모의고사 5회 14번] t₁에서 운동량 비교", "t₁일 때 (나)가 힘이 제일 크니까 운동량도 제일 크다고 생각했습니다.",
         "운동량은 그 순간의 힘이 아니라 처음 운동량에서 t₁까지 받은 충격량(그래프 넓이)을 뺀 값입니다. (나)는 t₁ 전에 충격량을 거의 다 받아 운동량이 가장 작습니다.",
         ("item", "m", 14, "힘 크면\n운동량도 큰 거 아님?")),
        ("[LINE UP 72p] 반도체 도핑", "p형과 n형 반도체 차이를 그림으로 정리하고 싶습니다.",
         "넣은 원소의 원자가 전자 수로 구분합니다. 3개면 p형, 5개면 n형입니다.", ("page", "lineup", 72, "반도체", "p형 3족? n형 5족?"))],
    6: [("[복테 6회 11번] AB 결합에 참여한 전자 껍질", "H와 F가 결합할 때 F는 어느 껍질 전자가 참여하나요?",
         "F는 둘째 껍질(원자가 전자) 전자 하나가 H의 전자와 전자쌍을 이룹니다. 첫째 껍질 전자가 참여하는 건 H뿐이라 ㄴ은 틀립니다.",
         ("item", "r", 11, "F도 첫째 껍질?")),
        ("[FRAMING 47p] 이온 결합 화합물", "이온 사이 거리가 짧을수록 녹는점이 높아지는 이유가 궁금합니다.",
         "거리가 짧을수록 이온 사이 인력이 커서 떼어 내는 데 에너지가 더 듭니다.", ("page", "framing", 47, "이온 결합", "거리 짧으면 왜 높음?"))],
    7: [("[모의고사 7회 21번] A와 C 확장 방향", "A와 C가 둘 다 0° 왼쪽에 있어서 확장 방향이 같다고 골랐습니다.",
         "경도가 아니라 해령을 기준으로 봐야 합니다. C가 있는 위도에서는 해령이 서쪽으로 꺾여 있어 C는 해령 동쪽입니다. 그래서 A는 서쪽, C는 동쪽으로 멀어집니다.",
         ("item", "m", 21, "C도 서쪽 아님?")),
        ("[복테 7회 12번] 대멸종 직전과 직후", "㉠ 직전 대멸종과 직후 대멸종 중 어느 쪽이 더 많이 줄었는지 그래프에서 어떻게 보나요?",
         "㉠ 직전(고생대 말)에는 400 가까이에서 200 근처로 떨어집니다. ㉠ 직후(중생대 말)보다 감소 폭이 훨씬 커서 ㄷ은 틀립니다.",
         ("item", "r", 12, "직전 vs 직후??"))],
    8: [("[모의고사 8회 19번] b 구하기", "Ⅰ과 Ⅱ의 이온 수 비로 b가 3인 걸 구하는 과정이 막힙니다.",
         "넣은 B 1 g당 생기는 Bᵇ⁺를 x라 두면 Ⅰ은 4x, Ⅱ는 6x입니다. 줄어든 A⁺는 그 b배라 Ⅰ: N−4bx, Ⅱ: N−6bx입니다. 비 1:3과 1:1을 넣으면 b=3, N=24x가 나옵니다.",
         ("item", "m", 19, "b 어떻게 3?")),
        ("[복테 8회 20번] (다)에 C를 더 넣으면", "ㄷ에서 C를 0.5N개 더 넣었을 때 이온 수 계산이 헷갈립니다.",
         "앞에서 b=2, c=3, x=2가 정해집니다. 남은 A⁺ 3N개에 C 0.5N개가 반응하면 A⁺는 1.5N개 줄어 1.5N개, C³⁺는 N개에서 1.5N개가 되어 같아집니다.",
         ("item", "r", 20, "A+ 1.5N 맞나?"))],
    9: [("[모의고사 9회 25번] 최고 온도로 농도 비교", "t₁ > t₂ > t₃에서 HCl과 NaOH 농도 관계를 어떻게 세우나요?",
         "부피가 모두 40 mL라 최고 온도는 생긴 물의 양에 비례합니다. (가)가 가장 높으려면 HCl 농도가 NaOH보다 작아야 하고, (나) > (다)에서 NaOH 농도는 HCl의 2배보다 작습니다.",
         ("item", "m", 25, "온도 = 물 양?")),
        ("[복테 9회 25번] V 구하기", "Ⅰ에서 Ⅱ로 갈 때 K⁺ 수가 늘어난 걸로 V를 구하는 건가요?",
         "맞습니다. Ⅰ에서 H⁺:K⁺ = 4:2라 농도 비 HCl:KOH = 3:1이 나오고, K⁺가 3이 되도록 KOH V mL를 넣으면 V=20입니다.",
         ("item", "r", 25, "K+로 V 구하기?"))],
    10: [("[복테 10회 1번] 에너지를 흡수하면 화학 변화?", "학생 B 말이 왜 틀렸는지 예시를 알고 싶습니다.",
          "얼음이 녹을 때처럼 물리 변화도 에너지를 흡수합니다. '항상'이 틀린 말입니다.", ("item", "r", 1, "얼음 녹는 건?")),
         ("[모의고사 10회 10번] 질산 암모늄 용해", "용해도 흡열 반응이라고 볼 수 있나요? ㄷ이 왜 틀렸는지도 궁금합니다.",
          "용해되면서 주변 열을 흡수하니 흡열입니다. 용해와 응결은 물질이 바뀌지 않아 둘 다 물리 변화라 ㄷ은 틀립니다.",
          ("item", "m", 10, "용해 = 화학 변화?"))],
    11: [("[모의고사 11회 16번] 피라미드 순서", "A, B, C가 Ⅰ~Ⅲ 중 무엇인지 정하는 기준이 궁금합니다.",
          "2차 소비자가 줄어드는 중이니 Ⅰ→Ⅱ→Ⅲ 순서입니다. 1차 소비자가 늘고 생산자가 줄어 Ⅲ에서는 1차 소비자가 생산자보다 많아지니 B가 Ⅲ입니다.",
          ("item", "m", 16, "B 왜 Ⅲ?")),
         ("[복테 11회 9번] ⓐ+ⓑ 범위", "ⓑ의 최솟값을 정하는 방법을 모르겠습니다.",
          "(바) 뒤 금속 공은 2ⓑ개가 되고 (사)에서 1개 이상 빠져 22개가 남으니 2ⓑ ≥ 23, ⓑ ≥ 12입니다. ⓐ=48이라 합은 60 이상입니다.",
          ("item", "r", 9, "ⓑ 최소?"))],
    12: [("[모의고사 12회 23번] A+B+C = D+E", "ㄴ 식이 왜 성립하는지 모르겠습니다.",
          "지표에서 B+F=D, 대기에서 A+C=E+F입니다. 두 식을 더하면 F가 지워져 A+B+C=D+E가 됩니다.", ("item", "m", 23, "F는 어디로?")),
         ("[복테 12회 22번] t₁이 B인 이유", "기압 편차로 엘니뇨와 라니냐를 어떻게 구분하나요?",
          "서태평양 기압 편차가 +면 엘니뇨입니다. (가)에서 A 시기는 동태평양 수온약층이 깊어(밝은 색) 엘니뇨, B는 라니냐라 기압 편차가 −인 t₁이 B입니다.",
          ("item", "r", 22, "기압 +면 엘니뇨?"))],
    13: [("[복테 13회 13번] 코일이 자석에 작용하는 힘", "p를 지날 때와 q를 지날 때 힘 방향이 같은 이유가 궁금합니다.",
          "가까워질 때는 밀고 멀어질 때는 당깁니다. 둘 다 자석 운동을 방해해 운동 반대 방향으로 같습니다.", ("item", "r", 13, "미는 거 vs 당기는 거")),
         ("[모의고사 13회 20번] 발전기 효율", "ㄷ에서 효율을 어떻게 계산하나요?",
          "효율은 생산된 에너지를 공급된 에너지로 나눈 값입니다. 1/20, 4/80, 9/180 모두 0.05입니다.", ("item", "m", 20, "효율 = 9/180?"))],
    14: [("[모의고사 14회 7번] 스마트팜과 GMO", "GMO를 기를 때 윤리 요소를 고려해야 한다는 ㄴ이 자료 어디에 근거하나요?",
          "자료는 GMO 육성이 가능하다고만 하지만, 과학 기술을 쓸 때 윤리를 고려해야 한다는 것은 6단원 핵심 내용입니다. 마지막 문장의 경각심도 같은 뜻입니다.",
          ("item", "m", 7, "ㄴ 근거?")),
         ("[복테 14회 21번] SI 접두어 비", "㉢/㉡ 계산을 어떻게 하나요?",
          "n은 10⁻⁹, d는 10⁻¹이라 10⁻⁹ ÷ 10⁻¹ = 10⁻⁸입니다. 지수끼리 빼면 됩니다.", ("item", "r", 21, "10^-9 / 10^-1 = ?"))],
}
# 수업 기록 사진: 교재 쪽에 조교 필기, 교재에 없는 단원은 판서 노트 + 그 주 모의고사 문항 풀이
LESSONS = {
    1: [("page", "lineup", 30, "흡수 스펙트럼", "★ 흡수선 = 방출선"), ("page", "lineup", 38, "원소의 생성", "빅뱅 → H, He\n별 → 무거운 원소")],
    2: [("page", "lineup", 66, "샤가프", "A=T, G=C\n→ 비율 계산"), ("page", "lineup", 103, "전사", "주형 가닥 → RNA\nT 대신 U")],
    3: [("page", "lineup", 113, "카탈레이스", "고온 → 변성\n→ 기능 X"), ("page", "lineup", 76, "지구 시스템", "권역끼리 표로 정리")],
    4: [("page", "logic", 1, None, "기울기 = 가속도\n넓이 = 변위"), ("page", "logic", 3, None, "공식 고르기:\n모르는 값 1개")],
    5: [("page", "lineup", 98, "충격량", "충격량\n= 운동량 변화량"), ("page", "lineup", 70, "반도체", "p형 3족 / n형 5족")],
    6: [("page", "lineup", 52, "이온 결합", "금속 + 비금속\n→ 이온 결합"), ("page", "lineup", 49, "원자가 전자", "결합에 쓰는 전자")],
    7: [("page", "lineup", 84, "판의 경계", "발산 / 수렴 / 보존"), ("page", "lineup", 79, "화석", "화석 → 지질시대 구분")],
    8: [("note", "8주차 산화와 환원", ["산화: 산소를 얻음 / 전자를 잃음", "환원: 산소를 잃음 / 전자를 얻음", "!산화와 환원은 항상 동시에",
                                  "- 금속 + 금속 양이온", "  반응성 큰 금속이 전자를 줌", "- 전하량 보존:", "  줄어든 양이온 전하 = 늘어난 전하",
                                  "예) A+ 2개 → B2+ 1개", "- 광합성: CO2 환원", "- 호흡: 포도당 산화"]), ("item", "m", 19, "전하량 보존\nb = 3")],
    9: [("note", "9주차 중화 반응 1", ["중화 반응: H+ + OH- → H2O", "- 구경꾼 이온: Na+, Cl- 수 일정", "!중화점 = 온도 최고점",
                                   "  (생긴 물의 양이 최대)", "- 혼합 용액 액성: 남은 이온으로", "- 페놀프탈레인: 염기성에서 붉은색",
                                   "단위 부피당 이온 수", "  = 이온 수 ÷ 전체 부피"]), ("item", "m", 25, "물 양 ∝ 온도")],
    10: [("note", "10주차 중화 반응 2 · 에너지 출입", ["넣은 부피 - 이온 수 그래프", "- H+: 중화점까지 감소 → 0", "- OH-: 중화점 뒤부터 증가",
                                              "!산에 염기: 전체 이온 수 중화점 전 일정", "에너지 출입", "- 발열: 연소, 중화, 호흡",
                                              "- 흡열: 광합성, 질산 암모늄 용해"]), ("item", "m", 10, "용해 = 흡열\n물리 변화")],
    11: [("note", "11주차 진화, 생태계", ["변이 → 자연 선택 → 진화", "!변이는 원래 있다 (환경이 고른다)", "- 유전적 다양성 ↑ → 환경 변화에 강함",
                                     "생태계 구성 요소: 생물 / 비생물", "- 개체군 안 / 개체군 사이 / 생물↔비생물",
                                     "생태 피라미드: 위로 갈수록 에너지 ↓", "- 평형: 먹이 ↓ → 포식자 ↓ → 먹이 ↑"]), ("item", "m", 16, "Ⅰ → Ⅱ → Ⅲ")],
    12: [("note", "12주차 열수지, 엘니뇨", ["복사 평형: 흡수 = 방출", "- 태양 100 = 반사 30 + 지구 복사 70", "- 대기 재복사 → 온실 효과",
                                      "!수증기·CO2 ↑ → 지표로 오는 재복사 ↑", "엘니뇨: 무역풍 약화", "- 동태평양 수온 ↑, 용승 약화",
                                      "- 서태평양 기압 ↑", "라니냐는 반대"]), ("item", "m", 23, "E = 58")],
    13: [("note", "13주차 렌츠 법칙, 에너지", ["전자기 유도: 자기장 변화 → 유도 전류", "!렌츠 법칙: 변화를 방해하는 방향",
                                          "- 가까워질 때 밀고 멀어질 때 당김", "- 자석이 빠를수록, 감은 수가 많을수록 전류 ↑",
                                          "에너지 전환", "- 발전기: 운동 → 전기", "- 효율 = 유용한 에너지 ÷ 공급 에너지"]), ("item", "r", 13, "방해하는 방향")],
    14: [("note", "14주차 과학과 미래 사회", ["빅데이터: 수집 → 처리(오차) → 분석", "- 사물 인터넷: 사물끼리 정보 교환",
                                        "- 스마트팜, 감염병 진단 키트", "!과학 기술의 양면성", "- 윤리, 보안, 환경 문제를 함께 고려",
                                        "예시문항: 자료에 있는 것만 판단"]), ("item", "m", 7, "양면성")],
}
# Full 모의고사 피드백(1:1): 주차 → (모의고사 문항, 학생 풀이 줄, 조교 답변)
FEEDBACK_M = {
    2: (24, ["X1, X2 상보 → 같은 열 아님?", "㉡ 14, ㉣ 18", "T/(A+G) = 4/5", "㉠ = T 인지 모르겠음"],
        "X₁과 X₂는 같은 열이 아니라 짝 염기끼리 수가 같습니다. ㉡=14, ㉣=18을 X₁의 빈칸과 맞춰 보면 ㉠-㉢, ㉡-㉣이 짝이고, "
        "T/(A+G)=4/5를 만족하는 경우는 ㉠=T(32개)뿐입니다. 한 가닥이 90개라 ㄴ은 틀리고 답은 ③입니다."),
    4: (22, ["B → Ⅲ 0.1초, Ⅳ 0.2초", "0.5h = 0.1v1 + 0.05", "1.5h = 0.2v1 + 0.2", "v1 = 0.5, h = 0.2", "ㄷ v2 계산?"],
        "v₁=0.5 m/s, h=0.2 m까지 맞습니다. (라)에서 Ⅳ→Ⅴ 0.2 m를 0.05초에 지나니 Ⅳ 속력이 3.75 m/s이고, "
        "v₂² = 3.75² − 2·10·0.6이라 v₂ ≈ 1.44 m/s로 v₁의 4배(2 m/s)보다 작습니다. 답은 ⑤입니다."),
    6: (3, ["X: 돌기 1 → 전자 1개 잃음", "Y: 홈 1 → 1개 얻음", "Z: 큰 블록, 돌기 2 → Mg?", "ㄴ Y2Z? YZ2?"],
        "X=Li, Y=F, Z=Mg까지 맞습니다. Mg²⁺와 F⁻는 1:2로 결합하니 Y:Z = 2:1이라 ㄴ도 옳습니다. "
        "ㄷ은 원자가 전자 수가 Li 1, F 7이라 틀립니다. 답은 ③입니다."),
    8: (19, ["B 1g당 이온 x", "Ⅰ: 4x, Ⅱ: 6x", "A+ : N - 4bx ?", "비 1:3 → ㉠이 뭔지?"],
        "㉠을 Bᵇ⁺로 두면 Ⅰ: 4x : (N−4bx) = 1:3, Ⅱ: 6x = N−6bx가 되어 b=3, N=24x가 나옵니다. ㉠을 A⁺로 두면 식이 성립하지 않습니다. "
        "A⁺는 B 8 g에서 다 반응하니 Ⅲ에는 B가 2 g 남아 답은 ⑤입니다."),
    10: (25, ["t1 > t2 > t3", "(가) 20:20 가장 높음", "HCl 농도 < NaOH?", "ㄷ 구경꾼 이온 비교 모르겠음"],
         "부피가 모두 40 mL라 최고 온도는 생긴 물의 양에 비례합니다. HCl 농도 a, NaOH 농도 b로 두면 a < b < 2a입니다. "
         "구경꾼 이온은 (나) 30a+10b, (다) 10a+30b라 (다)가 많아 ㄷ도 옳고 답은 ⑤입니다."),
    12: (23, ["반사 4 + 26 = 30", "E = 100 - 30 - 12 = 58", "ㄴ A+B+C = D+E ?", "ㄷ 수증기 ↑ → F ↓ ?"],
         "E=58 맞습니다. 지표 B+F=D, 대기 A+C=E+F를 더하면 ㄴ이 나옵니다. 수증기가 늘면 대기 재복사 F는 늘어서 ㄷ은 틀립니다. 답은 ③입니다."),
    14: (14, ["(나) 에어백 없음 → 짧고 큼", "t1 운동량 = 힘 크기?", "ㄴ 평균 힘 (나) > (다) > (라)", "ㄷ 나일론이 더 오래"],
         "운동량은 그 순간의 힘이 아니라 t₁까지 받은 충격량(넓이)을 뺀 값이라 (나)가 가장 작습니다. 그래서 ㄱ은 틀리고, "
         "ㄴ·ㄷ은 맞아 답은 ④입니다."),
}
REVIEW_PAGE = [1, 1, 1, 1, 2, 2, 2, 2, 3, 3, 3, 3, 3, 4, 4, 4, 4, 5, 5, 5, 5, 6, 6, 6, 6]     # 복테 파일 원본 문항 → 시험지 쪽

# ---------------------------------------------------------------- 날짜
TODAY = date.today() - timedelta(days=(date.today().weekday() - 4) % 7)   # 실행일 직전 금요일 = N주차 마지막 날
BREAK_AFTER = 6                                                           # 커리큘럼: 6주차(02.05) 뒤 한 주 설 연휴, 7주차는 02.13부터
GAP = 7 if WEEKS > BREAK_AFTER else 0
W1 = TODAY - timedelta(days=WEEKS * 7 + 4 + GAP)                          # 1주차가 걸친 달력 주의 월요일 (12/21)


def day(week, weekday):
    """커리큘럼 주차(토~금) week 의 요일. weekday 0=월 … 6=일. 토·일은 그 주의 시작. 7주차부터는 설 연휴 한 주 뒤."""
    base = W1 + timedelta(days=(week - 1) * 7 + (7 if week > BREAK_AFTER else 0))
    return base + timedelta(days=weekday if weekday >= 5 else weekday + 7)


def sess(c, k):
    """그 반의 k번째 수업 날 (첫 요일 기준). 재종은 12/28(월)부터라 k주차 안에 든다."""
    return day(k, c["slots"][0][0])


def ts(d, hh=10, mm=0):
    return datetime(d.year, d.month, d.day, hh, mm).strftime("%Y-%m-%d %H:%M:%S")


# ---------------------------------------------------------------- 도우미
def q(sql, args=(), one=False):
    with app.app_context():
        from db import query
        return query(sql, args, one=one)


def x(sql, args=()):
    with app.app_context():
        from db import execute
        return execute(sql, args)


def ok(label, r, expect=(200, 302)):
    if r.status_code not in expect:
        FAIL.append(f"{label}: {r.status_code}")
    return r


_ip = [0]


def client():
    """가상 사용자마다 다른 IP (가입·로그인 시도 제한은 IP 단위)."""
    _ip[0] += 1
    c = app.test_client()
    c.environ_base["REMOTE_ADDR"] = f"10.27.{_ip[0] // 250}.{_ip[0] % 250 + 1}"
    return c


def login(user, pw):
    c = client()
    ok(f"login {user}", c.post("/login", data={"username": user, "password": pw}), (302,))
    return c


def img(name):
    p = os.path.join(IMG_DIR, name)
    if os.path.exists(p):
        return (io.BytesIO(open(p, "rb").read()), name)
    png = (b"\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x01\x00\x00\x00\x01\x08\x06\x00\x00\x00\x1f\x15\xc4\x89"
           b"\x00\x00\x00\rIDATx\x9cc\xf8\x0f\x00\x00\x01\x01\x00\x05\x18\xd8N\x00\x00\x00\x00IEND\xaeB`\x82")
    return (io.BytesIO(png), name)


SHOTS = os.path.join(BASE, "_shots")
os.makedirs(SHOTS, exist_ok=True)
_ph = None
if all(os.environ.get(k) for k in ("DEMO_SYS_PY", "DEMO_PHOTOS", "DEMO_PDF")):
    _ph = subprocess.Popen([os.environ["DEMO_SYS_PY"], "-X", "utf8", os.environ["DEMO_PHOTOS"], "serve", os.environ["DEMO_PDF"]],
                           stdin=subprocess.PIPE, stdout=subprocess.PIPE, text=True, encoding="utf-8")
_shot_n = [0]


def shot(**req):
    """사진 요청 → [(파일, 이름)]. 사진 도구가 없으면 빈 PNG 하나."""
    if _ph is None:
        return [img("photo.png")]
    _shot_n[0] += 1
    req.setdefault("seed", _shot_n[0])
    req["out"] = os.path.join(SHOTS, f"{_shot_n[0]:04d}.jpg")
    _ph.stdin.write(_js.dumps(req, ensure_ascii=False) + "\n")
    _ph.stdin.flush()
    res = _js.loads(_ph.stdout.readline())
    if not res["files"]:
        FAIL.append(f"사진 {req['op']}: {res.get('error')}")
        return [img("photo.png")]
    return [(io.BytesIO(open(f, "rb").read()), f"IMG_{20270100 + _shot_n[0]:08d}_{k}.jpg") for k, f in enumerate(res["files"])]


def last_id(table):
    return q(f"SELECT MAX(id) AS id FROM {table}", one=True)["id"]


DATES = []          # (table, id, {column: value}) - 마지막에 한꺼번에 날짜를 맞춘다


def at(table, row_id, **cols):
    if row_id:
        DATES.append((table, row_id, cols))


# ---------------------------------------------------------------- 선생님 · 조교
KEEP = _js.loads(os.environ.get("DEMO_KEEP_PW") or "{}")   # 다시 만들 때 이전 데모 비밀번호 유지 (make_demo.py)
PW = {k: KEEP.get(k) or secrets.token_urlsafe(8) + "!7" for k in ("teacher", "ta", "ta2")}
with app.app_context():
    from security import encrypt, hash_password
    x("INSERT INTO users (role, username, display_name, password_hash) VALUES ('teacher', 'master', '정태혁', ?)",
      (hash_password(PW["teacher"]),))
T = login("master", PW["teacher"])
ok("조교 추가", T.post("/t/staff", data={"display_name": "한지수", "username": "ta_hanjisu"}))
ok("조교 추가 2", T.post("/t/staff", data={"display_name": "김도윤", "username": "ta_kimdoyun"}))
with app.app_context():
    x("UPDATE users SET password_hash = ?, must_change_pw = 0 WHERE username = 'ta_hanjisu'", (hash_password(PW["ta"]),))
    x("UPDATE users SET password_hash = ?, must_change_pw = 0 WHERE username = 'ta_kimdoyun'", (hash_password(PW["ta2"]),))
TA = login("ta_hanjisu", PW["ta"])
TA2 = login("ta_kimdoyun", PW["ta2"])
ok("조교 소개", TA.post("/t/me/intro", data={"intro": "생명과 화학 담당이에요. 오답 원인부터 같이 봐요."}))
ok("조교 소개 2", TA2.post("/t/me/intro", data={"intro": "물리와 지구과학 담당이에요. 계산 문항 풀이 순서를 잡아 드려요."}))
TA_ID = q("SELECT id FROM users WHERE username = 'ta_hanjisu'", one=True)["id"]

# ---------------------------------------------------------------- 반 8개 (단과 4 · 재종 4)
CLASSES = [  # 이름, 구분, [(요일, 시작, 끝, 교시, 관, 교실)]  단과 3시간 30분 1회 · 재종 100분 여러 번
    ("대구 토요일 A반", "단과", [(5, "10:00", "13:30", "", "대구관", "301")]),
    ("대구 토요일 B반", "단과", [(5, "14:30", "18:00", "", "대구관", "301")]),
    ("대치 일요일반", "단과", [(6, "14:00", "17:30", "", "대치 M3관", "101")]),
    ("대치 목요일반", "단과", [(3, "18:30", "22:00", "", "대치 M3관", "101")]),
    ("대치 재종 3반", "재종", [(0, "10:30", "12:10", "2교시", "대치 N관", "L102"), (2, "10:30", "12:10", "2교시", "대치 N관", "L102"),
                            (4, "10:30", "12:10", "2교시", "대치 N관", "L102")]),
    ("대치 재종 4반", "재종", [(1, "13:20", "15:00", "3교시", "대치 N관", "L102"), (3, "13:20", "15:00", "3교시", "대치 N관", "L102")]),
    ("대치 재종 1반", "재종", [(0, "13:20", "15:00", "3교시", "대치 W관", "801"), (3, "15:20", "17:00", "4교시", "대치 W관", "801")]),
    ("대치 재종 2반", "재종", [(1, "08:30", "10:10", "1교시", "대치 W관", "801"), (4, "08:30", "10:10", "1교시", "대치 W관", "801")]),
]
# 학생 페르소나: 반마다 1명. weak = 약한 단원, skill = 평균 정답률, ask = 주마다 질문할 확률
PERSONAS = {
    "대구 토요일 A반": dict(name="박서윤", no="0012874416", parent="010-2817-4416", target="연세대 생명시스템", weak="생명중심원리",
                          skill=0.70, ask=0.8, note="성실형. 질문, 오답 노트, 시험지 첨삭을 꾸준히 씀. 화면을 가장 많이 보는 학생"),
    "대구 토요일 B반": dict(name="이도현", no="0031558207", parent="010-4120-8207", target="서울대 화학생물공학", weak="중화 반응",
                          skill=0.88, ask=0.15, note="상위권. 질문은 거의 없고 모의고사 분석, 통계만 봄"),
    "대치 일요일반": dict(name="최민서", no="0045019932", parent="010-7731-9932", target="고려대 의예", weak="역학",
                        skill=0.62, ask=0.35, note="학원 여러 곳 병행. 결석이 잦고 강의 영상, 수업 기록으로 따라잡음"),
    "대치 목요일반": dict(name="정하준", no="0050772641", parent="010-3392-2641", target="성균관대 화학공학", weak="산화와 환원",
                        skill=0.58, ask=0.5, note="2주차에 늦게 합류. 1주차 자료를 찾아봄", late=2),
    "대치 재종 3반": dict(name="김나연", no="kny2027", parent="010-5560-1183", target="경북대 수의예", weak="화학 결합",
                        skill=0.66, ask=0.6, note="재수생. 소도시 명상 집중 기록이 가장 길고 학습상담을 자주 씀"),
    "대치 재종 4반": dict(name="오준혁", no="ojh0412", parent="010-6014-0412", target="계명대 간호", weak="지구 열수지",
                        skill=0.45, ask=0.55, note="하위권. 오답 노트 이유 고르기와 시험지 첨삭에 기대는 편"),
    "대치 재종 1반": dict(name="윤지아", no="yja2027", parent="010-8825-3071", target="이화여대 화학생명", weak="전기적 성질과 반도체",
                        skill=0.68, ask=0.3, note="아이폰 사용. 알림, 홈 화면 설치를 씀. 교재 배송, 환불 행정문의"),
    "대치 재종 2반": dict(name="한승우", no="hsw2027", parent="010-2290-7764", target="한양대 기계", weak="엘니뇨",
                        skill=0.57, ask=0.25, note="게임(퀴즈) 위주. 비밀번호를 잃어버려 임시 비밀번호를 받은 적 있음"),
}
LAST = "김이박최정강조윤장임한오서신권황안송류홍전고문양손배백허남심노"
FIRST = ["민준", "서연", "도윤", "하은", "시우", "지유", "주원", "서윤", "예준", "지민", "하준", "수아", "지호", "채원", "준서",
         "다은", "건우", "예린", "현우", "소율", "우진", "지아", "선우", "윤서", "연우", "태민", "가은", "승현", "나연", "재원"]
cls = {}
for name, track, slots in CLASSES:
    ok(f"반 {name}", T.post("/t/classes", data={"name": name, "track": track, "description": f"2028 수능 대비 SEASON 1"}))
    cid = q("SELECT id FROM classes WHERE name = ?", (name,), one=True)["id"]
    cls[name] = {"id": cid, "track": track, "slots": slots, "students": []}
    for wd, s, e, per_, hall, room in slots:
        x("INSERT INTO timetable (class_id, weekday, starts, ends, title, period, hall, room) VALUES (?, ?, ?, ?, '통합과학', ?, ?, ?)",
          (cid, wd, s, e, per_, hall, room))

n = 0
with app.app_context():
    from security import encrypt
    for ci, (name, c) in enumerate(cls.items()):
        per = PERSONAS[name]
        size = 26 if c["track"] == "단과" else 22
        for i in range(size):
            n += 1
            if i == 0:
                sname, parent, no, target = per["name"], per["parent"], per["no"], per["target"]
            else:
                sname, parent = rng.choice(LAST) + rng.choice(FIRST), f"010-{rng.randint(2000, 9899)}-{n:04d}"
                no = f"00{rng.randint(10000000, 99999999)}" if c["track"] == "단과" else f"s27{n:04d}"
                target = rng.choice(["", "서울대 생명과학", "연세대 생명시스템", "고려대 의예", "한양대 화공", "경북대 의예"])
            sid = x("INSERT INTO students (class_id, name, student_no, parent_phone_enc, target) VALUES (?, ?, ?, ?, ?)",
                    (c["id"], sname, no, encrypt(parent), target))
            c["students"].append({"id": sid, "name": sname, "no": no, "parent8": parent.replace("-", "")[-8:]})
        for k in range(size + 4):
            x("INSERT INTO student_codes (class_id, code) VALUES (?, ?)", (c["id"], f"{27 + ci}{k:04d}"))

ALL_STUDENTS = [(c_name, st) for c_name, c in cls.items() for st in c["students"]]
SKILL = {st["id"]: rng.uniform(0.4, 0.95) for _, st in ALL_STUDENTS}
WEAK = {}
P = {}                                            # 반 이름 → 페르소나 실행 정보
for name, c in cls.items():
    st = c["students"][0]
    SKILL[st["id"]] = PERSONAS[name]["skill"]
    WEAK[st["id"]] = PERSONAS[name]["weak"]
    P[name] = {"st": st, "per": PERSONAS[name], "pw": KEEP.get(st["no"]) or secrets.token_urlsafe(8) + "!7", "c": c}


def signup(c, st, pw, when):
    code = q("SELECT code FROM student_codes WHERE class_id = ? AND student_id IS NULL ORDER BY id LIMIT 1", (c["id"],), one=True)["code"]
    r = client().post("/signup", data={"track": c["track"], "code": code, "name": st["name"], "student_no": st["no"],
                                       "password": pw, "confirm": pw, "consent": "1"})
    ok(f"가입 {st['name']}", r, (302,))
    u = q("SELECT id FROM users WHERE username = ?", (st["no"],), one=True)
    if u:
        at("users", u["id"], created_at=ts(when, 9, rng.randint(0, 59)))
        x("UPDATE student_codes SET used_at = ? WHERE student_id = ?", (ts(when, 9, 30), st["id"]))
    return u["id"] if u else None


accounts = {}
for name, p in P.items():
    p["uid"] = signup(p["c"], p["st"], p["pw"], sess(p["c"], p["per"].get("late", 1)))
    p["S"] = login(p["st"]["no"], p["pw"])
for name, c in cls.items():
    for st in c["students"][1:8]:
        pw = secrets.token_urlsafe(10) + "!1"
        accounts[st["id"]] = (st["no"], pw, signup(c, st, pw, sess(c, 1)))
SEO = P["대구 토요일 A반"]
STUDY = {"대구 토요일 A반": ("개념 다지기형", "해설 참고형"), "대구 토요일 B반": ("심화 도전형", ""), "대치 일요일반": ("벼락치기형", "미이행형"),
         "대치 목요일반": ("미이행형", "개념 다지기형"), "대치 재종 3반": ("안정형", ""), "대치 재종 4반": ("불안, 과소확신형", "해설 참고형"),
         "대치 재종 1반": ("마무리 다듬기형", ""), "대치 재종 2반": ("양치기형", "")}
TYPE_POOL = ["안정형"] * 8 + ["개념 다지기형"] * 5 + ["마무리 다듬기형"] * 5 + ["심화 도전형"] * 5 + ["양치기형"] * 5 +             ["벼락치기형"] * 4 + ["해설 참고형"] * 5 + ["불안, 과소확신형"] * 5 + ["미이행형"] * 4
PRACTICE = {"개념 다지기형": "필기노트 복습 후 같은 단원 기출 10문항", "심화 도전형": "LOGIC BUILD 킬러 1문항 끝까지 혼자 풀기",
            "벼락치기형": "수업 다음 날 30분 복습 고정", "미이행형": "과제 1개만 정해 끝까지", "안정형": "지금 순서 유지, 오답 이유 고르기",
            "불안, 과소확신형": "맞힌 문항도 근거 한 줄 쓰기", "마무리 다듬기형": "시간 재고 모의고사 1회", "양치기형": "푼 문항 중 3개만 다시 풀기",
            "해설 참고형": "해설 보기 전 5분 더 고민"}
with app.app_context():
    from db import get_db
    import json as _json
    db_ = get_db()
    for name, c in cls.items():
        for st in c["students"]:
            code = q("SELECT code FROM student_codes WHERE student_id = ?", (st["id"],), one=True)
            if not code:
                continue
            main, sub = STUDY[name] if st is c["students"][0] else (rng.choice(TYPE_POOL), "")
            data = {"학생코드": code["code"], "이름": st["name"], "진단일": day(1, 6).isoformat(), "공부유형": main, "보조유형": sub,
                    "판정": "확정", "설명": f"1주차 공부 유형 자가진단 결과 {main}", "이번주실천": PRACTICE[main]}
            db_.execute("INSERT INTO sys_rows (tbl, code, data) VALUES ('공부유형', ?, ?)", (code["code"], _json.dumps(data, ensure_ascii=False)))
    db_.execute("INSERT INTO sys_sync (tbl, n_rows, synced_at, source) VALUES ('공부유형', ?, ?, 'csv')",
                (sum(len(c["students"]) for c in cls.values()), ts(day(1, 6), 21)))
    db_.commit()
OTHERS = [(st, accounts[st["id"]]) for _, st in ALL_STUDENTS if st["id"] in accounts]

# ---------------------------------------------------------------- 교재
# 앱이 미리 만들어 둔 '복습 테스트'·'모의고사' 1~50회에 결과를 올린다 (실제 운영 방식)
BOOK_R = q("SELECT id FROM books WHERE title = '복습 테스트' AND is_practice = 0", one=True)["id"]
BOOK_M = q("SELECT id FROM books WHERE title = '모의고사' AND is_practice = 0", one=True)["id"]



# ---------------------------------------------------------------- OMR (복습 테스트 · 모의고사)
import demo_items as DI  # noqa: E402

EXAMS = {"r": DI.REVIEW, "m": DI.MOCK}                 # 복습 테스트 · 모의고사 (같은 파일을 1~14회로)
NEAR = {k: DI.near_wrong(v) for k, v in EXAMS.items()}
PHOTO_EXAM = {"r": "rev", "m": "mock"}
R_NEW = {src: i + 1 for i, src in enumerate(DI.REVIEW_SRC)}   # 복테 파일 원본 번호 → 복테 1~10번


def pdf_no(kind, no):
    """OMR 번호 → 시험지 파일의 문항 번호 (사진용)."""
    return DI.REVIEW_SRC[no - 1] if kind == "r" else no


def _renumber(entries):
    """질문·수업 기록 데이터는 복테 파일 원본 번호로 적어 두었다 → 복테 1~10번으로 바꾸고, 고르지 않은 문항은 뺀다."""
    out = []
    for e in entries:
        is_q = len(e) == 4 and isinstance(e[3], tuple)          # 질문 (제목, 내용, 답변, 사진) / 수업 기록은 사진 하나
        src = e[3] if is_q else e
        if src[0] != "item" or src[1] != "r":
            out.append(e)
            continue
        if src[2] not in R_NEW:
            continue
        new = (src[0], src[1], R_NEW[src[2]], *src[3:])
        if is_q:
            out.append((re.sub(r"(\[복테 \d+회 )\d+(번\])", lambda m: f"{m.group(1)}{R_NEW[src[2]]}{m.group(2)}", e[0]), e[1], e[2], new))
        else:
            out.append(new)
    return out


QUESTIONS = {w: _renumber(v) for w, v in QUESTIONS.items()}
CURATED = {x[0] for v in QUESTIONS.values() for x in v}        # 미리 쓴 질문 (추가 질문은 이것에만 붙인다)
LESSONS = {w: _renumber(v) for w, v in LESSONS.items()}
KILLER = {"r": ", ".join(str(R_NEW[n]) for n in (20, 23, 25)), "m": "19, 22, 24"}
LEVEL_DROP = {"상": 0.2, "중": 0.05, "하": -0.12}


def omr_workbook(kind, absent):
    from openpyxl import Workbook
    its = EXAMS[kind]
    wb = Workbook()
    ws = wb.active
    ws.title = "OMR"
    ws.append(["이름", "수험번호", "반"] + list(range(1, len(its) + 1)))
    ws.append(["정답", "", ""] + [it[0] for it in its])
    ws.append(["배점", "", ""] + [it[1] for it in its])
    for c_name, st in ALL_STUDENTS:
        if st["id"] in absent:
            continue
        row = []
        for i, it in enumerate(its):
            k = it[0]
            if k in ("*", "-"):                               # 보기가 없는 문항: 아무거나 마킹
                row.append(rng.randint(1, 5))
                continue
            pr = SKILL[st["id"]] - LEVEL_DROP[it[5]] - (0.35 if WEAK.get(st["id"]) == it[2] else 0)
            if rng.random() < pr:
                row.append(k)
            elif rng.random() < 0.03:
                row.append(None)                              # 무응답
            elif NEAR[kind][i] and rng.random() < 0.75:      # 보기 하나만 다른 선지를 많이 고른다
                row.append(rng.choice(NEAR[kind][i]))
            else:
                row.append(rng.choice([v for v in range(1, 6) if v != k]))
        ws.append([st["name"], st["parent8"], c_name] + row)
    info = wb.create_sheet("문항정보")
    info.append(["문항번호", "정답", "배점", "단원", "핵심개념", "요구역량", "난이도", "문항형식", "선지구성", "보기함정", "선지분석"])
    for r in DI.info_rows(its):
        info.append(r)
    buf = io.BytesIO()
    wb.save(buf)
    return buf.getvalue()


def make_round(kind, rnd, when, week):
    book = BOOK_R if kind == "r" else BOOK_M
    mid = q("SELECT id FROM mocks WHERE book_id = ? AND round_no = ?", (book, rnd), one=True)["id"]
    absent = {st["id"] for _, st in ALL_STUDENTS if rng.random() < 0.06}
    absent.discard(SEO["st"]["id"])
    if rng.random() < 0.3:
        absent.add(P["대치 일요일반"]["st"]["id"])                   # 최민서는 가끔 결석
    if rnd < P["대치 목요일반"]["per"]["late"]:
        absent.add(P["대치 목요일반"]["st"]["id"])                   # 정하준은 2주차부터
    data = omr_workbook(kind, absent)
    ok(f"OMR {kind}-{rnd}", (TA if rnd % 2 else TA2).post(f"/t/mocks/{mid}/omr", data={"file": (io.BytesIO(data), f"{rnd}회_채점.xlsx")},
                                                          content_type="multipart/form-data"))
    ok(f"시험 평가 {kind}-{rnd}", T.post(f"/t/mocks/{mid}/review", data={
        "level": str(rng.choice([3, 3, 4])), "time": rng.choice(["적당", "빠듯"]), "killer": KILLER[kind], "video": "",
        "review": f"{CURRICULUM[week][0]} 주간. 킬러 문항 {KILLER[kind]}번은 조건 독해, 계산형입니다. 오답이 몰린 문항은 다음 수업 앞 10분에 다시 봅니다."}))
    x("UPDATE mocks SET exam_date = ? WHERE id = ?", (when.isoformat(), mid))
    at("mocks", mid, created_at=ts(when - timedelta(days=1), 20), review_at=ts(when + timedelta(days=1), 22))
    at("omr_uploads", last_id("omr_uploads"), created_at=ts(when + timedelta(days=1), 21))
    for r in q("SELECT id FROM mock_entries WHERE mock_id = ?", (mid,)):
        at("mock_entries", r["id"], updated_at=ts(when + timedelta(days=1), 21))
    for r in q("SELECT id FROM exam_results WHERE mock_id = ?", (mid,)):
        at("exam_results", r["id"], updated_at=ts(when + timedelta(days=1), 21))
    return mid


def my_answers(kind, w, uid):
    e = q("SELECT answers FROM mock_entries WHERE mock_id = ? AND user_id = ?", (MOCK[(kind, w)], uid), one=True) if uid else None
    return (e["answers"] or "") if e else ""


def wrong_why(kind, no, pick):
    """고른 선지로 틀린 이유 (유형, 설명): 정답과 다른 보기의 함정."""
    ans, _, _, _, _, _, opts, bogi = EXAMS[kind][no - 1]
    if opts and ans not in ("*", "-"):
        g = opts.split("|")
        diff = [lab for lab in "ㄱㄴㄷ" if (lab in g[pick - 1]) != (lab in g[ans - 1])]
        if diff:
            t = bogi["ㄱㄴㄷ".index(diff[0])]
            return t[2], f"보기 {diff[0]}: {t[1]}"
    elif not opts and pick in bogi:
        return bogi[pick][1], bogi[pick][0]
    return "조건 독해", "조건을 놓침"


def item_photo_req(kind, no, who, uid, w, note, unsure=None):
    """질문 사진: 그 학생이 OMR에 고른 선지에 동그라미, 보기마다 자기 판단(O/X), 헷갈린 보기에 ?
    unsure: 맞혔지만 확신이 없던 보기 (정답에 동그라미, 그 보기에만 ?)"""
    ans, opts = EXAMS[kind][no - 1][0], EXAMS[kind][no - 1][6]
    if unsure and opts:
        right = opts.split("|")[ans - 1]
        think = {lab: (None if lab == unsure else lab in right) for lab in "ㄱㄴㄷ"}
        return shot(op="item", exam=PHOTO_EXAM[kind], no=pdf_no(kind, no), who=who, pick=ans, think=think, note=note)
    a = my_answers(kind, w, uid)
    pick = int(a[no - 1]) if len(a) >= no and a[no - 1] in "12345" and a[no - 1] != str(ans) else None
    if pick is None:
        pick = rng.choice(NEAR[kind][no - 1] or [v for v in range(1, 6) if v != ans])
    think = {}
    if opts:
        g = opts.split("|")
        for lab in "ㄱㄴㄷ":
            mine, right = lab in g[pick - 1], lab in g[ans - 1]
            think[lab] = None if mine != right and rng.random() < 0.6 else mine
    return shot(op="item", exam=PHOTO_EXAM[kind], no=pdf_no(kind, no), who=who, pick=pick, think=think, note=note)


BIG_UNIT = {"측정 표준": "과학의 기초", "화학 결합": "물질과 규칙성", "원소의 생성": "물질과 규칙성", "지구의 탄생과 진화": "물질과 규칙성",
            "샤가프 법칙": "물질과 규칙성", "생명중심원리": "물질과 규칙성", "전기적 성질과 반도체": "물질과 규칙성",
            "역학": "시스템과 상호작용", "운동량": "시스템과 상호작용", "지구 시스템과 상호작용": "시스템과 상호작용", "판구조론": "시스템과 상호작용",
            "카탈레이스": "시스템과 상호작용", "세포막과 물질 이동": "시스템과 상호작용",
            "산화와 환원": "변화와 다양성", "중화 반응": "변화와 다양성", "에너지 출입": "변화와 다양성", "지질시대와 생명체": "변화와 다양성",
            "진화와 생물 다양성": "변화와 다양성", "생태계와 평형": "환경과 에너지", "지구 열수지": "환경과 에너지", "엘니뇨": "환경과 에너지",
            "전자기 유도": "환경과 에너지", "에너지 전환": "환경과 에너지", "과학과 미래 사회": "과학과 미래사회"}
ASKED = set()


def unsure_question(w, uid):
    """맞혔지만 확신 없이 푼 문항: 그 학생이 맞힌 합답형 문항에서 감으로 판단한 보기 하나의 근거를 묻는다."""
    for kind in rng.sample(["r", "m"], 2):
        a = my_answers(kind, w, uid)
        its = EXAMS[kind]
        right = [i + 1 for i, it in enumerate(its) if it[6] and it[0] not in ("*", "-") and i < len(a) and a[i] == str(it[0])
                 and it[5] != "하" and f"{kind}{w}-{i + 1}" not in ASKED]                 # 쉬운 문항은 묻지 않는다
        if not right:
            continue
        no = rng.choice(right)
        ASKED.add(f"{kind}{w}-{no}")
        ans, _, unit, concept, _, _, opts, bogi = its[no - 1]
        lab = rng.choice("ㄱㄴㄷ")
        t, why, _ = bogi["ㄱㄴㄷ".index(lab)]
        title = f"[{'복테' if kind == 'r' else '모의고사'} {w}회 {no}번] {concept} (맞혔지만 확신 없음)"
        body = rng.choice([f"맞히긴 했는데 보기 {lab}은 감으로 골랐습니다. {'왜 옳은지' if t else '왜 틀린지'} 근거를 알고 싶습니다.",
                           f"{ans}번으로 맞혔지만 보기 {lab} 판단에 확신이 없었습니다. 어떻게 확인하면 되나요?",
                           f"시간이 없어 보기 {lab}을 대충 넘기고 맞혔습니다. 정확한 근거가 궁금합니다."])
        reply = (f"판단은 맞았습니다. 보기 {lab}은 {'옳은' if t else '틀린'} 진술입니다. "
                 f"'{why}' 쪽으로 헷갈리기 쉬운 보기라 근거를 한 줄로 적어 두세요. {concept}에서 같은 형태가 자주 나옵니다.")
        return title, body, reply, ("item", kind, no, f"보기 {lab} 맞나?", lab), BIG_UNIT.get(unit, WEEK_UNIT[w])
    return None


def auto_question(w, uid):
    """준비한 질문이 다 나간 주: 그 학생이 실제로 틀린 합답형 문항에서, 고른 답과 정답이 갈린 보기를 묻는다.
    10번에 4번쯤은 맞혔지만 확신이 없던 문항을 묻는다."""
    if rng.random() < 0.4:
        q_ = unsure_question(w, uid)
        if q_:
            return q_
    for kind in rng.sample(["r", "m"], 2):
        a = my_answers(kind, w, uid)
        its = EXAMS[kind]
        wrong = [i + 1 for i, it in enumerate(its) if it[6] and it[0] not in ("*", "-") and i < len(a) and a[i] in "12345" and a[i] != str(it[0])]
        wrong = [n for n in wrong if f"{kind}{w}-{n}" not in ASKED]
        if not wrong:
            continue
        no = rng.choice(wrong)
        ASKED.add(f"{kind}{w}-{no}")
        pick = int(a[no - 1])
        ans, _, unit, concept, _, _, opts, bogi = its[no - 1]
        g = opts.split("|")
        lab = next(x for x in "ㄱㄴㄷ" if (x in g[pick - 1]) != (x in g[ans - 1]))
        t, why, _ = bogi["ㄱㄴㄷ".index(lab)]
        title = f"[{'복테' if kind == 'r' else '모의고사'} {w}회 {no}번] {concept}"
        body = rng.choice([f"보기 {lab}이 왜 {'맞는' if t else '틀린'} 건지 모르겠습니다.",
                           f"{pick}번을 골랐는데 보기 {lab} 판단이 헷갈립니다.",
                           f"보기 {lab}을 {'틀렸다고' if t else '맞다고'} 봤는데 어디서 잘못 생각했는지 궁금합니다."])
        reply = (f"보기 {lab}은 {'옳은' if t else '틀린'} 진술입니다. 이 보기에서 많이 하는 실수가 '{why}'입니다. "
                 f"{pick}번과 정답 {ans}번은 보기 {lab} 하나로 갈리니 {concept} 부분을 필기노트에서 다시 확인하세요.")
        return title, body, reply, ("item", kind, no, f"보기 {lab} ?"), BIG_UNIT.get(unit, WEEK_UNIT[w])
    return None


def pick_question(w, uid):
    """같은 질문을 여러 명이 똑같이 올리지 않게: 준비한 질문은 한 번씩, 그다음은 그 학생 오답에서."""
    pool = [x for x in QUESTIONS[w] if x[0] not in ASKED]
    if pool:
        x = rng.choice(pool)
        ASKED.add(x[0])
        return (*x, unit_of(x[0], w))
    return auto_question(w, uid)


def question_photo(src, who, uid, w):
    if src[0] == "item":
        return item_photo_req(src[1], src[2], who, uid, w, src[3], src[4] if len(src) > 4 else None)
    _, key, page, find, note = src
    return shot(op="page", key=key, page=page, find=find, who=who, note=note)


def ask(cl, title, body, qtype, when, image=None, assignee=None, unit=""):
    data = {"title": title, "body": body, "qtype": qtype, "unit": unit}
    if image:
        data["image"] = image
    if assignee:
        data["assignee"] = str(assignee)
    ok(f"질문 {title}", cl.post("/s/questions", data=data, content_type="multipart/form-data"))
    qid = last_id("questions")
    at("questions", qid, created_at=ts(when, rng.randint(19, 23), rng.randint(0, 59)))
    return qid


def answer(cl, qid, body, when):
    ok(f"답변 {qid}", cl.post(f"/t/questions/{qid}", data={"body": body}))
    at("answers", last_id("answers"), created_at=ts(when, rng.randint(9, 23), rng.randint(0, 59)))


_lesson_cache = {}


def lesson_photos(w, track):
    """그 주 판서 사진 (조교마다 한 벌 만들어 반마다 같이 올린다)."""
    if (w, track) not in _lesson_cache:
        who = "한지수" if track == "단과" else "김도윤"
        out = []
        for src in LESSONS[w]:
            if src[0] == "page":
                f = shot(op="page", key=src[1], page=src[2], find=src[3], who=who, note=src[4], pen="blue")
            elif src[0] == "note":
                f = shot(op="note", title=src[1], lines=src[2], who=who, pen="blue")
            else:
                its = EXAMS[src[1]][src[2] - 1]
                think = {lab: lab in its[6].split("|")[its[0] - 1] for lab in "ㄱㄴㄷ"} if its[6] else {}
                f = shot(op="item", exam=PHOTO_EXAM[src[1]], no=pdf_no(src[1], src[2]), who=who, pick=its[0], think=think, note=src[3], pen="blue")
            out += [(fh.getvalue(), n) for fh, n in f]
        _lesson_cache[(w, track)] = out
    return _lesson_cache[(w, track)]


# ---------------------------------------------------------------- 시즌 시작 전 설정
MOCK = {}
CAST_VIDEO = "https://youtu.be/WEdAfYkqiZ8"         # 태혁쌤 영상 (cast·강의 영상 데모용)
ok("D-day", T.post("/t/timetable", data={"exam_day": "2027-11-18", "exam_label": "수능"}))
for name, c in cls.items():
    ok(f"개강 공지 {name}", T.post(f"/t/classes/{c['id']}/notices", data={
        "tag": "공지", "pinned": "1", "title": "SEASON 1 개강 안내",
        "body": "교재: LINE UP 개념서 · FRAMING 문제편 및 해설편 · LOGIC BUILD 필기노트, 정태혁 모의고사\n"
                "질문: 질문 게시판에 [교재-페이지-번호] 형식으로 / 행정: 질문 게시판 행정문의"}))
    at("notices", last_id("notices"), created_at=ts(sess(c, 1) - timedelta(days=2), 21))
for name, p in P.items():
    for wd, s_, e_, *_ in p["c"]["slots"]:
        p["S"].post("/s/timetable", data={"weekday": str(wd), "starts": s_, "ends": e_, "title": "통합과학", "room": "", "tone": "1"})
    p["S"].post("/s/timetable", data={"weekday": str(rng.choice([0, 1, 2])), "starts": "19:00", "ends": "21:00", "title": "자습", "room": "", "tone": "2"})

# ---------------------------------------------------------------- 주차별 진행
for w in range(1, WEEKS + 1):
    topic, units = CURRICULUM[w]
    lb = f" · LOGIC BUILD {LOGIC_BUILD[w]}호" if w in LOGIC_BUILD else ""
    last_week = w == WEEKS
    MOCK[("r", w)] = make_round("r", w, day(w, 5), w)
    MOCK[("m", w)] = make_round("m", w, day(w, 6), w)
    for name, c in cls.items():
        d = sess(c, w)
        ok(f"과제 공지 {name} {w}", T.post(f"/t/classes/{c['id']}/notices", data={
            "tag": "과제", "title": f"{w}주차 과제", "body": f"FRAMING {topic} 범위{lb} · 필기노트 복습 / 오답 노트에서 틀린 이유 고르기"}))
        at("notices", last_id("notices"), created_at=ts(d, 22))
        pics = lesson_photos(w, c["track"])
        ok(f"수업 기록 {name} {w}", (TA if c["track"] == "단과" else TA2).post("/t/lessons", data={
            "class_id": str(c["id"]), "day": d.isoformat(), "title": f"{w}주차 {topic}", "body": f"{w}주차 판서 / 다음 시간 복습 테스트 범위",
            "image": [(io.BytesIO(b), n) for b, n in (pics if c["track"] == "단과" else pics[:1])]}, content_type="multipart/form-data"))
        at("lessons", last_id("lessons"), created_at=ts(d, 23))
        # 매주 시험은 복습 테스트(OMR)로만 올린다 (반 '시험·성적'에 따로 넣지 않는다)
        if w in (2, 6, 10):
            ok("정오", T.post(f"/t/classes/{c['id']}/notices", data={"tag": "정오", "textbook": "LINE UP 개념서", "title": f"LINE UP {w * 9}p 정오",
                                                                    "body": f"예제 {w % 3 + 1}번 보기 ㄴ의 단위를 'mL'에서 'L'로 고칩니다."}))
            at("notices", last_id("notices"), created_at=ts(day(w, 2), 18))
        if w in (4, 8, 12):
            ok("영상", T.post(f"/t/classes/{c['id']}/videos", data={"title": f"{w}주차 {topic} 보충", "url": CAST_VIDEO,
                                                                   "duration": "42:10", "expires_on": (TODAY + timedelta(days=60)).isoformat()}))
            at("videos", last_id("videos"), created_at=ts(day(w, 1), 21))
    if w in (3, 7, 11):
        ok(f"cast {w}", T.post("/cast/new", data={"title": f"{w}주차를 마치며", "body": f"{topic}까지 왔습니다. 오답 노트 이유 고르기를 빠뜨리지 마세요.", "video_url": CAST_VIDEO}))
        at("casts", last_id("casts"), created_at=ts(day(w, 6), 23), updated_at=ts(day(w, 6), 23))
    if w == 2:
        ok("자료", T.post(f"/t/classes/{SEO['c']['id']}/materials", data={"title": "필기노트 2호 보충: 생명중심원리 정리",
                                                                          "file": (io.BytesIO(b"%PDF-1.4 demo"), "note02-extra.pdf")}, content_type="multipart/form-data"))
        at("materials", last_id("materials"), created_at=ts(day(2, 1), 20))
    # 페르소나 학생의 한 주
    for name, p in P.items():
        if w < p["per"].get("late", 1):
            continue
        S, per = p["S"], p["per"]
        for r in q("SELECT id FROM notices WHERE class_id = ? ORDER BY id DESC LIMIT 2", (p["c"]["id"],)):
            S.get(f"/s/notices/{r['id']}")
        picked = pick_question(w, p["uid"]) if rng.random() < per["ask"] else None
        if picked:
            title, body, ans, src, unit = picked
            qid = ask(S, title, body, "학습질문", day(w, rng.choice([0, 1, 2])), unit=unit,
                      image=question_photo(src, p["st"]["name"], p["uid"], w))
            if not (last_week and name in ("대구 토요일 A반", "대치 재종 3반")):      # 이 둘은 오늘 조교가 답할 질문
                answer(TA if rng.random() < 0.6 else TA2, qid, ans, day(w, 3))
                if title in CURATED and rng.random() < 0.3:
                    ok("추가 질문", S.post(f"/s/questions/{qid}/followup", data={"body": "그럼 반대 경우에는 어떻게 되나요?"}))
                    at("followups", last_id("followups"), created_at=ts(day(w, 3), 22))
                    answer(TA, qid, "반대 경우는 조건만 뒤집어 같은 순서로 따라가면 됩니다. 보기마다 무엇이 바뀌는지 표로 적어 보세요.", day(w, 4))
        if (name == "대치 재종 3반" and w % 3 == 0) or (name == "대구 토요일 A반" and w in (3, 9)):
            qid = ask(S, f"{w}주차 공부 계획 상담", "복테 점수가 몇 주째 비슷합니다. 평일에 무엇을 먼저 해야 할지 모르겠습니다.", "학습상담",
                      day(w, 1), assignee=TA_ID)
            answer(TA, qid, f"평일 3일만 정해서 오답 노트 → 같은 단원 기출 10문항 순서로 돌려 보세요. {per['weak']} 문항이 계속 틀려서 그 부분부터 하면 됩니다.", day(w, 2))
            ok("상담 평점", S.post(f"/s/questions/{qid}/rate", data={"rating": str(rng.choice([4, 5, 5]))}))
        if name == "대치 재종 1반" and w in (1, 5):
            qid = ask(S, "교재 배송 문의" if w == 1 else "교재 환불 문의",
                      "FRAMING 해설편 2권이 아직 안 왔습니다." if w == 1 else "FRAMING 해설편이 두 권 왔습니다. 한 권 환불되나요?", "행정문의", day(w, 2))
            answer(T, qid, "이번 주 금요일에 발송됩니다." if w == 1 else "다음 수업 때 행정실에 반납하면 처리됩니다.", day(w, 3))
        if (name in ("대구 토요일 A반", "대치 재종 4반") and w % 2 == 0) or (name == "대치 재종 2반" and w == 6):   # Full 모의고사 피드백 (한승우는 악필)
            a_m = my_answers("m", w, p["uid"])                # Full 모의고사 피드백: 그 학생이 실제로 틀린 문항으로 묻는다
            sw = next((k for k in [w] + sorted(FEEDBACK_M) if len(a_m) >= FEEDBACK_M[k][0] and a_m[FEEDBACK_M[k][0] - 1] != str(DI.MOCK[FEEDBACK_M[k][0] - 1][0])), w)
            sno, slines, sreply = FEEDBACK_M[sw]
            ok("모의고사 피드백 요청", S.post(f"/s/analysis/{MOCK[('m', w)]}/feedback", data={"body": f"{sno}번 풀이에서 어디가 잘못됐는지 봐 주세요.",
                                                                                         "image": shot(op="solve", exam="mock", no=sno, who=p["st"]["name"], lines=slines)},
                                    content_type="multipart/form-data"))
            tid = last_id("feedback_threads")
            at("feedback_msgs", last_id("feedback_msgs"), created_at=ts(day(w, 6), 21))
            if last_week:
                at("feedback_threads", tid, created_at=ts(day(w, 6), 21), updated_at=ts(day(w, 6), 21))
            else:
                ok("모의고사 피드백 답변", TA.post(f"/t/feedback/{tid}", data={"body": sreply}))
                at("feedback_msgs", last_id("feedback_msgs"), created_at=ts(day(w, 0) + timedelta(days=7), 21))
                at("feedback_threads", tid, created_at=ts(day(w, 6), 21), updated_at=ts(day(w, 0) + timedelta(days=7), 21))
        took = q("SELECT 1 FROM mock_entries WHERE mock_id = ? AND user_id = ?", (MOCK[("r", w)], p["uid"]), one=True)
        if took and name in ("대구 토요일 A반", "대치 재종 4반") and (w % 2 == 1 or last_week):  # 시험지 첨삭 (응시한 회차만)
            a = my_answers("r", w, p["uid"])
            keys = [str(it[0]) for it in DI.REVIEW]
            wrong = [i + 1 for i, k in enumerate(keys) if k not in ("*", "-") and (i >= len(a) or a[i] != k)]   # 보기 없는 6번은 첨삭 대상에서 뺀다
            pages = sorted({REVIEW_PAGE[pdf_no("r", n) - 1] - 1 for n in wrong})[:3] or [0]
            ok("시험지 제출", S.post(f"/s/analysis/{MOCK[('r', w)]}/paper", data={
                "note": f"{', '.join(map(str, wrong[:3]))}번 풀이 봐 주세요." if wrong else "검토 부탁드립니다.",
                "image": shot(op="paper", exam="rev", answers=a, key=keys, nos=DI.REVIEW_SRC, who=p["st"]["name"], pages=pages)}, content_type="multipart/form-data"))
            pid = last_id("exam_papers")
            if last_week:
                at("exam_papers", pid, submitted_at=ts(day(w, 6), 19))
            else:
                marks = {}
                for n in wrong[:3]:
                    if n <= len(a) and a[n - 1] in "12345":
                        tp, why = wrong_why("r", n, int(a[n - 1]))
                        marks[f"r{n}"], marks[f"m{n}"] = tp, why
                ok("시험지 첨삭", TA.post(f"/t/papers/{pid}", data={**marks, "comment": f"{per['weak']}만 다시 잡으면 됩니다. 풀이 순서는 좋습니다."}))
                at("exam_papers", pid, submitted_at=ts(day(w, 6), 19), reviewed_at=ts(day(w, 0) + timedelta(days=7), 14))
        if rng.random() < (0.9 if name in ("대구 토요일 A반", "대치 재종 4반") else 0.4):   # 오답 노트
            for kind in ("r", "m"):
                mid = MOCK[(kind, w)]
                e = q("SELECT answers FROM mock_entries WHERE mock_id = ? AND user_id = ?", (mid, p["uid"]), one=True)
                key = [str(v) for v in _js.loads(q("SELECT answer_key FROM mocks WHERE id = ?", (mid,), one=True)["answer_key"])]
                picks = e["answers"] if e else ""
                for i, k in enumerate(key):
                    if k not in ("*", "-") and i < len(picks) and picks[i] in "12345" and picks[i] != k and rng.random() < 0.7:
                        tp = wrong_why(kind, i + 1, int(picks[i]))[0] if rng.random() < 0.6 else rng.choice(["개념 부족", "조건 독해", "계산 실수", "찍음"])
                        S.post(f"/s/wrong/{mid}/{i + 1}", data={"reason": tp, "memo": "", "reviewed": "" if last_week else "1"})
        if name in ("대치 재종 2반", "대구 토요일 B반") or rng.random() < 0.3:         # 퀴즈
            st_ = S.post("/s/games/quiz/start", json={"topic": f"{min(34, w * 2):02d}"}).get_json(silent=True) or {}
            if st_.get("round_id"):
                S.post(f"/s/games/quiz/{st_['round_id']}/submit", json={"answers": [rng.randint(0, 3) for _ in st_.get("questions", [])]})
                when = day(w, rng.randint(0, 4))
                at("game_rounds", st_["round_id"], started_at=ts(when, 22), finished_at=ts(when, 22, 10))
    for st, (user, pw, uid) in rng.sample(OTHERS, 3):                               # 다른 학생들 공개 질문
        picked = pick_question(w, uid)
        if not picked:
            continue
        title, body, ans, src, unit = picked
        qid = ask(login(user, pw), title, body, "학습질문", day(w, rng.randint(0, 6)), unit=unit,
                  image=question_photo(src, st["name"], uid, w))
        if not last_week or rng.random() < 0.5:
            answer(TA2 if rng.random() < 0.5 else TA, qid, ans, day(w, 4))
    if w == 2:
        faq = q("SELECT id FROM questions WHERE title LIKE '%염기 정하기%' ORDER BY id LIMIT 1", one=True)
        if faq:
            ok("자주 묻는 질문", TA.post(f"/t/questions/{faq['id']}/faq"))

# 출결 (조교 시스템 '출결' 표 형식): 수업마다 출석·지각·결석. 최민서는 결석이 잦다
with app.app_context():
    from db import get_db
    import json as _json
    db_ = get_db()
    n_att = 0
    for name, c in cls.items():
        for st in c["students"]:
            code = q("SELECT code FROM student_codes WHERE student_id = ?", (st["id"],), one=True)
            if not code:
                continue
            miss = 0.3 if st is P["대치 일요일반"]["st"] else 0.05
            start = P["대치 목요일반"]["per"]["late"] if st is P["대치 목요일반"]["st"] else 1
            for k in range(start, WEEKS + 1):
                r = rng.random()
                status = "결석" if r < miss else ("지각" if r < miss + 0.07 else "출석")
                hh, mm = map(int, c["slots"][0][1].split(":"))
                arrived = "" if status == "결석" else f"{hh if status == '출석' else hh:02d}:{(mm + (rng.randint(5, 25) if status == '지각' else -rng.randint(0, 10))) % 60:02d}"
                db_.execute("INSERT INTO sys_rows (tbl, code, data) VALUES ('출결', ?, ?)",
                            (code["code"], _json.dumps({"학생코드": code["code"], "날짜": sess(c, k).isoformat(), "출결": status, "도착시각": arrived}, ensure_ascii=False)))
                n_att += 1
    db_.execute("INSERT INTO sys_sync (tbl, n_rows, synced_at, source) VALUES ('출결', ?, ?, 'csv')", (n_att, ts(TODAY, 22)))
    # 과제 (조교 시스템 '과제' 표): 주차마다 주간지 과제. 마지막 두 주는 아직 안 낸 학생이 있다 → 앱 홈 '남은 과제'
    n_task = 0
    for name, c in cls.items():
        for st in c["students"]:
            code = q("SELECT code FROM student_codes WHERE student_id = ?", (st["id"],), one=True)
            if not code:
                continue
            for k in range(1, WEEKS + 1):
                due = sess(c, k) + timedelta(days=6)
                late = k >= WEEKS - 1 and rng.random() < (0.7 if st is P["대구 토요일 A반"]["st"] else 0.3)
                done = not late and rng.random() > 0.08
                right = rng.randint(9, 20) if done else ""
                db_.execute("INSERT INTO sys_rows (tbl, code, data) VALUES ('과제', ?, ?)", (code["code"], _json.dumps(
                    {"학생코드": code["code"], "날짜": due.isoformat(), "교재": f"Squeeze {k}호", "범위": CURRICULUM[k][0],
                     "제출": "O" if done else "", "맞은수": right, "문항수": 20 if done else ""}, ensure_ascii=False)))
                n_task += 1
    db_.execute("INSERT INTO sys_sync (tbl, n_rows, synced_at, source) VALUES ('과제', ?, ?, 'csv')", (n_task, ts(TODAY, 22)))
    db_.commit()

# 한승우: 비밀번호 분실 → 조교가 임시 비밀번호 발급 → 직접 바꿈
han = P["대치 재종 2반"]
if WEEKS >= 6:
    r = ok("임시 비밀번호 발급", TA.post(f"/t/students/{han['st']['id']}/account"))
    m = re.search(r'class="secret">\s*([^<\s]{8,})\s*<', r.get_data(as_text=True))
    if m:
        cl = login(han["st"]["no"], m.group(1))
        ok("비밀번호 변경", cl.post("/password", data={"current": m.group(1), "new": han["pw"], "confirm": han["pw"]}))
    else:
        FAIL.append("임시 비밀번호 화면에서 값을 못 찾음")

ok("학부모 리포트 링크", T.post(f"/t/students/{SEO['st']['id']}/parent-link"))
ok("학생 메모", TA.post(f"/t/mocks/{MOCK[('r', WEEKS)]}/note/{SEO['st']['id']}", data={"note": f"{SEO['per']['weak']} 연속 오답. 다음 주 상담 예정."}))
first_notice = q("SELECT id FROM notices WHERE class_id = ? ORDER BY id LIMIT 1", (SEO["c"]["id"],), one=True)["id"]
SEO["S"].post(f"/s/notices/{first_notice}/like")

# ---------------------------------------------------------------- 소도시 명상 집중 기록 · 접속 기록
FOCUS = {"대치 재종 3반": 0.85, "대구 토요일 A반": 0.55, "대치 재종 4반": 0.4}
with app.app_context():
    users = [(p["uid"], FOCUS.get(name, 0.25)) for name, p in P.items()] + [(a[2], 0.2) for a in accounts.values() if a[2]]
    for uid, rate in [(u, r) for u, r in users if u]:
        for back in range(1, WEEKS * 7):
            d = TODAY - timedelta(days=back)
            if rng.random() < rate:
                x("INSERT INTO focus_logs (user_id, place, minutes, ended_at) VALUES (?, ?, ?, ?)",
                  (uid, rng.choice(["sento", "kissa", "eki"]), rng.choice([25, 30, 45, 50, 60, 80]), ts(d, rng.randint(19, 23), rng.randint(0, 59))))
            if rng.random() < rate + 0.2:
                x("INSERT OR IGNORE INTO visits (user_id, day) VALUES (?, ?)", (uid, d.isoformat()))

if _ph:
    _ph.stdin.close()
    _ph.wait()
shutil.rmtree(SHOTS, ignore_errors=True)

# ---------------------------------------------------------------- 문항 그림 (시험 분석에서 번호를 누르면 문항, 그 위에 필기해서 질문)
# 데모 시험지 PDF 를 tools/split_items.py 로 잘라(시스템 python + pymupdf) 매 회차에 같은 그림을 올린다
if app.config["ITEMS_ENABLED"] and all(os.environ.get(k) for k in ("DEMO_SYS_PY", "DEMO_PHOTOS", "DEMO_PDF")):
    import tempfile
    _tools = os.path.dirname(os.environ["DEMO_PHOTOS"])
    _idir = tempfile.mkdtemp(prefix="demo-items-")
    for kind, pdf, pick in (("m", "모의고사 데모.pdf", None), ("r", "복테 데모.pdf", DI.REVIEW_SRC)):
        out = os.path.join(_idir, kind)
        cmd = [os.environ["DEMO_SYS_PY"], "-X", "utf8", os.path.join(_tools, "split_items.py"), os.path.join(os.environ["DEMO_PDF"], pdf), out]
        subprocess.run(cmd + (["--pick", ",".join(map(str, pick))] if pick else []), check=True, capture_output=True)
        files = sorted(os.listdir(out))
        blobs = [(f, open(os.path.join(out, f), "rb").read()) for f in files]
        for w in range(1, WEEKS + 1):
            ok(f"문항 그림 {kind}{w}", T.post(f"/t/mocks/{MOCK[(kind, w)]}/items", data={"image": [(io.BytesIO(b), f) for f, b in blobs]},
                                         content_type="multipart/form-data"))
    shutil.rmtree(_idir, ignore_errors=True)

# ---------------------------------------------------------------- 수업 일정: 진도 그룹 2개(단과·재종) · 배부 교재 · 출석
# 커리큘럼(SEASON 1, 14주): 1주차 개념서 2권 + 기출문제집 문항편·해설편 각 2권, 매주 주간지·모의고사+분석서·필기노트, 고난도 TOPIC 8권
PLAN_WEEKS = WEEKS
HANDOUT_LIST = (("라인업", ["LINE UP 통합과학I", "LINE UP 통합과학II"]),
                ("프레이밍", ["FRAMING 통합과학I 문항편", "FRAMING 통합과학II 문항편", "FRAMING 통합과학I 해설편", "FRAMING 통합과학II 해설편"]),
                ("스퀴즈", [f"Squeeze {k}호" for k in range(1, 15)]),
                ("로직빌드", [f"LOGIC BUILD {k}호" for k in range(1, 9)]),
                ("시퀀스", [f"Sequence {k}회" for k in range(1, 15)]),
                ("기타", [f"정태혁 모의고사 {k}회" for k in range(1, 15)]),
                ("필기노트", [f"필기노트 {k}호" for k in range(1, 15)]))
for kind, titles in HANDOUT_LIST:
    ok(f"배부 교재 {kind}", T.post("/t/handouts", data={"kind": kind, "title": ", ".join(titles)}))
HID = {r["title"]: r["id"] for r in q("SELECT id, title FROM handouts")}


def week_handouts_of(k):
    hs = [f"Squeeze {k}호", f"정태혁 모의고사 {k}회", f"Sequence {k}회", f"필기노트 {k}호"]
    if k == 1:
        hs += HANDOUT_LIST[0][1] + HANDOUT_LIST[1][1]
    if k in LOGIC_BUILD:
        hs.append(f"LOGIC BUILD {LOGIC_BUILD[k]}호")
    return hs


for gname, track in (("2028 단과 SEASON 1", "단과"), ("2028 재종 SEASON 1", "재종")):
    ok(f"진도 그룹 {gname}", T.post("/t/schedule", data={"name": gname, "track": track, "first": day(1, 5).isoformat(), "weeks": str(PLAN_WEEKS),
                                                     "class_id": [str(c["id"]) for c in cls.values() if c["track"] == track]}))
    gid = q("SELECT id FROM course_groups WHERE name = ?", (gname,), one=True)["id"]
    for w in q("SELECT id, week_no FROM group_weeks WHERE group_id = ? ORDER BY week_no", (gid,)):
        k = w["week_no"]
        # 7주차부터는 설 연휴 한 주 뒤: 주차 날짜를 직접 바꾼다 (화면의 '고치기'와 같은 길)
        note = "개강, 교재 일괄 배부" if k == 1 else "설 연휴 뒤" if k == BREAK_AFTER + 1 else ""
        ok(f"{gname} {k}주차", T.post(f"/t/schedule/weeks/{w['id']}", data={
            "action": "save", "starts": day(k, 5).isoformat(), "ends": (day(k, 5) + timedelta(days=6)).isoformat(),
            "topic": CURRICULUM[k][0], "review_round": str(k), "mock_round": str(k), "note": note,
            "handout_id": [str(HID[h]) for h in week_handouts_of(k)]}))
# 지난 수업 칸 출석: 대부분 출석, 가끔 지각·결석 (최민서는 결석이 잦다)
by_id = {st["id"]: (c_name, st) for c_name, st in ALL_STUDENTS}
for s in q("""SELECT s.id, s.class_id, s.day FROM sessions s JOIN group_weeks w ON w.id = s.week_id
              WHERE s.day <= ? AND w.off = 0""", (TODAY.isoformat(),)):
    for st in q("SELECT id FROM students WHERE class_id = ? AND active = 1", (s["class_id"],)):
        miss = 0.3 if st["id"] == P["대치 일요일반"]["st"]["id"] else 0.04
        r = rng.random()
        state = "결석" if r < miss else "지각" if r < miss + 0.05 else "출석"
        x("INSERT OR IGNORE INTO session_students (session_id, student_id, state) VALUES (?, ?, ?)", (s["id"], st["id"], state))   # 시트 출결로 채운 칸은 그대로
# 마지막 주: 대구 토요일 B반 학생 한 명이 A반 수업을 들음 / 13주차 대치 목요일반은 Sequence 미입고로 빼고 14주차에 같이 배부
a_cls, b_cls = cls["대구 토요일 A반"]["id"], cls["대구 토요일 B반"]["id"]
dan = q("SELECT id FROM course_groups WHERE track = '단과'", one=True)["id"]
wk = {r["week_no"]: r["id"] for r in q("SELECT id, week_no FROM group_weeks WHERE group_id = ?", (dan,))}
sa = q("SELECT id FROM sessions WHERE week_id = ? AND class_id = ?", (wk[WEEKS], a_cls), one=True)["id"]
sb = q("SELECT id FROM sessions WHERE week_id = ? AND class_id = ?", (wk[WEEKS], b_cls), one=True)["id"]
mover = cls["대구 토요일 B반"]["students"][3]
x("INSERT OR REPLACE INTO session_students (session_id, student_id, state, guest) VALUES (?, ?, '출석', 1)", (sa, mover["id"]))
x("UPDATE session_students SET state = '다른 반' WHERE session_id = ? AND student_id = ?", (sb, mover["id"]))
x("UPDATE sessions SET note = '대구 토요일 B반 1명 A반 수업 수강 (학교 일정)' WHERE id = ?", (sa,))
if WEEKS >= 2:
    thu = cls["대치 목요일반"]["id"]
    s13 = q("SELECT id FROM sessions WHERE week_id = ? AND class_id = ?", (wk[WEEKS - 1], thu), one=True)["id"]
    s14 = q("SELECT id FROM sessions WHERE week_id = ? AND class_id = ?", (wk[WEEKS], thu), one=True)["id"]
    x("INSERT INTO session_handouts (session_id, handout_id, mode) VALUES (?, ?, 'drop')", (s13, HID[f"Sequence {WEEKS - 1}회"]))
    x("UPDATE sessions SET note = 'Sequence 미입고, 다음 주 배부' WHERE id = ?", (s13,))
    x("INSERT INTO session_handouts (session_id, handout_id, mode) VALUES (?, ?, 'add')", (s14, HID[f"Sequence {WEEKS - 1}회"]))

# ---------------------------------------------------------------- 날짜 맞추기
with app.app_context():
    for table, row_id, cols in DATES:
        sets = ", ".join(f"{k} = ?" for k in cols)
        x(f"UPDATE {table} SET {sets} WHERE id = ?", (*cols.values(), row_id))
    x("UPDATE users SET last_login_at = ?", (ts(TODAY - timedelta(days=1), 22),))
    x("UPDATE notice_reads SET read_at = (SELECT created_at FROM notices WHERE notices.id = notice_reads.notice_id)")
    x("DELETE FROM audit_log")

with open(CRED, "w", encoding="utf-8") as fh:
    fh.write(f"데모 로그인 (가짜 데이터) · SEASON 1 {WEEKS}주차까지, 오늘 = {TODAY} (금)\n\n")
    fh.write(f"선생님 정태혁   master / {PW['teacher']}\n")
    fh.write(f"조교 한지수     ta_hanjisu / {PW['ta']}\n")
    fh.write(f"조교 김도윤     ta_kimdoyun / {PW['ta2']}\n\n")
    for name, p in P.items():
        fh.write(f"학생 {p['st']['name']} ({name})  {p['st']['no']} / {p['pw']}   {p['per']['note']}\n")
print("weeks", WEEKS, "students", len(ALL_STUDENTS), "accounts", len(accounts) + len(P), "fail", len(FAIL))
for f in FAIL[:40]:
    print("  FAIL", f)
sys.exit(1 if FAIL else 0)
