"""데모 사이트용 DB: 정태혁 통합과학 SEASON 1 을 N주차까지 진행한 상황 (가짜 데이터).

이 폴더의 instance/ 에 DB·비밀키·업로드 사진을 새로 만든다. 실제 운영 폴더에서 실행하지 말 것.
    python seed_demo.py            # 14주차(시즌1 끝)까지
    python seed_demo.py 4          # 4주차까지
로그인 정보: DEMO_CREDENTIALS.txt (이 파일 옆)

페르소나
- 선생님 정태혁 (teacher)        공지·회차·시험 평가·행정문의·cast
- 조교 한지수 (ta_hanjisu)        학습질문·학습상담·1:1 첨삭·시험지 첨삭·OMR·수업 기록
- 학생 8명, 반마다 1명 (PERSONAS)  중심 인물은 박서윤 (대구 토요일 A반)

진도·교재: SEASON 1 커리큘럼 (주차 = 토~금, 1주차 12.26~01.01, 14주차 03.27~04.02)
일정: 대구 토 12/26, 대치 일 12/27, 대치 목 12/31 개강 (재종 4반은 12/28 월).
N주차가 끝난 금요일을 '오늘'로 보고, 요일을 지키며 실행일 직전 금요일로 당긴다.
→ 화면의 '오늘·이번 주·최근 7일'이 채워진다.
모든 행동은 실제 화면 기능(폼 전송)으로 실행하고, 날짜만 나중에 맞춘다.
"""
import io
import os
import random
import re
import secrets
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
    14: ("6단원 + 예시문항 분석", ["과학과 미래 사회", "예시문항"]),
}
LOGIC_BUILD = {1: 1, 2: 2, 3: 3, 4: 4, 6: 5, 8: 6, 10: 7, 12: 8}     # 주차 → LOGIC BUILD 호
QUESTIONS = {  # 주차: [(제목, 내용, 조교 답변)]  · 2022 개정 통합과학 범위 안
    1: [("[LINE UP I-24-3] 흡수 스펙트럼 선의 위치", "흡수선과 방출선 위치가 같다는 게 왜인지 모르겠습니다.",
         "같은 원소는 같은 에너지 차이에서만 빛을 흡수하고 방출합니다. 그래서 흡수선과 방출선이 같은 파장에 생깁니다."),
        ("[LINE UP I-18-2] 별의 진화 순서", "적색 거성 다음 단계가 질량에 따라 갈리는 기준을 모르겠습니다.",
         "핵융합이 끝난 뒤 남은 질량이 기준입니다. 태양 정도면 백색 왜성, 훨씬 크면 초신성 폭발을 거칩니다.")],
    2: [("[Squeeze 2호-7] 샤가프 법칙 비율", "A의 비율만 주어졌을 때 G+C 비율 구하는 순서가 헷갈립니다.",
         "A=T 이므로 A+T 를 먼저 구하고, 100%에서 빼면 G+C 입니다. G=C 이므로 반으로 나누면 G 입니다."),
        ("[FRAMING I-45-3] 전사할 때 염기", "주형 가닥에서 RNA 염기를 정하는 순서가 헷갈립니다.",
         "주형 가닥 염기와 상보적인 염기를 쓰고 T 자리에 U를 씁니다. 교재 46p 표를 같이 보세요.")],
    3: [("[LOGIC BUILD 3호-5] 카탈레이스 실험", "온도를 높였을 때 기포 발생이 줄어드는 이유가 궁금합니다.",
         "카탈레이스는 단백질이라 온도가 너무 높으면 입체 구조가 변해 기능을 잃습니다."),
        ("[Squeeze 3호-11] 지구 시스템 상호작용", "화산 폭발이 기권과 수권에 주는 영향을 같이 묻는 문제가 어렵습니다.",
         "권역 하나씩 표로 적어 보세요. 화산재는 기권, 산성비는 수권으로 이어집니다.")],
    4: [("[Squeeze 4호-12] 빗면 위 물체의 가속도", "빗면 기울기가 같으면 질량이 달라도 가속도가 같다는 부분이 헷갈립니다.",
         "빗면 방향 힘이 질량에 비례하고, 가속도는 힘을 질량으로 나눈 값이라 질량이 지워집니다."),
        ("[Squeeze 4호-9] 자유 낙하 거리", "1초, 2초 동안 떨어진 거리 비가 1:4인 이유를 다시 설명해 주세요.",
         "속력이 시간에 비례해 커지므로 거리는 시간의 제곱에 비례합니다.")],
    5: [("[Squeeze 5호-6] 충격량과 충돌 시간", "충돌 시간이 길어지면 힘이 줄어드는데 충격량은 같다는 부분이 헷갈립니다.",
         "충격량은 운동량 변화량이라 처음과 나중 속도가 같으면 같습니다. 시간이 길면 같은 충격량을 작은 힘으로 받습니다."),
        ("[LINE UP I-112-4] 반도체 도핑", "p형과 n형 반도체 차이를 그림으로 정리하고 싶습니다.",
         "넣은 원소의 원자가 전자 수로 구분합니다. 3개면 p형, 5개면 n형입니다.")],
    6: [("[LOGIC BUILD 5호-8] 공유 전자쌍 수", "N₂에서 공유 전자쌍이 3개인 걸 그림으로 어떻게 세나요?",
         "원자가 전자 5개씩 그리고, 각자 8개를 채우려면 3쌍을 함께 써야 합니다."),
        ("[FRAMING I-130-2] 이온 결합 화합물 녹는점", "이온 사이 거리가 짧을수록 녹는점이 높아지는 이유가 궁금합니다.",
         "거리가 짧을수록 이온 사이 인력이 커서 떼어 내는 데 에너지가 더 듭니다.")],
    7: [("[Squeeze 7호-4] 판의 경계", "발산형 경계에서 화산 활동이 있는 이유가 궁금합니다.",
         "판이 벌어지면서 아래 맨틀이 올라와 압력이 줄고, 녹아서 마그마가 생깁니다."),
        ("[LINE UP II-30-6] 지질시대 구분", "대멸종이 지질시대 경계가 되는 이유가 무엇인가요?",
         "화석으로 보이는 생물 무리가 크게 바뀌는 지점이라 시대를 나누는 기준이 됩니다.")],
    8: [("[LOGIC BUILD 6호-3] 산화 환원 판단", "산소를 얻는 것과 전자를 잃는 것이 같은 산화라는 게 헷갈립니다.",
         "산소와 결합하면서 전자를 내주는 경우가 많아서 둘 다 산화로 봅니다. 교재 표를 기준으로 하나씩 대응시켜 보세요."),
        ("[Squeeze 8호-10] 광합성과 호흡", "광합성이 환원이고 호흡이 산화인 이유를 다시 설명해 주세요.",
         "이산화 탄소가 산소를 잃고 포도당이 되는 쪽이 환원, 포도당이 산소를 얻는 쪽이 산화입니다.")],
    9: [("[Squeeze 9호-5] 중화 반응 이온 수", "혼합 용액의 전체 이온 수가 어떻게 변하는지 그래프가 헷갈립니다.",
         "중화점 전에는 반응한 만큼 넣은 쪽 이온이 대신 들어옵니다. 이온을 하나씩 표로 세어 보세요."),
        ("[FRAMING II-22-7] 중화점 찾기", "온도가 가장 높은 지점이 중화점인 이유가 궁금합니다.",
         "중화 반응에서 열이 나오는데, 반응한 양이 가장 많은 지점에서 온도가 가장 높습니다.")],
    10: [("[LOGIC BUILD 7호-6] 중화 반응 양적 관계", "몇 mL를 넣어야 완전히 중화되는지 구하는 비례식이 헷갈립니다.",
          "H⁺ 수와 OH⁻ 수가 같아지는 부피를 찾습니다. 단위 부피당 이온 수부터 적으세요."),
         ("[Squeeze 10호-3] 에너지 출입", "흡열 반응인데 주변 온도가 내려가는 이유가 궁금합니다.",
          "반응이 주변에서 열을 가져가기 때문에 주변 온도가 내려갑니다.")],
    11: [("[Squeeze 11호-8] 생태계 평형", "먹이 그물에서 한 종이 줄면 평형이 회복되는 과정이 헷갈립니다.",
          "먹이가 줄면 포식자가 줄고, 그러면 다시 먹이가 늘어나는 순서로 회복됩니다."),
         ("[LINE UP II-70-2] 자연 선택", "변이가 먼저인지 환경 변화가 먼저인지 헷갈립니다.",
          "변이는 원래 있고, 환경이 그중 유리한 변이를 가진 개체를 더 많이 남기게 합니다.")],
    12: [("[LOGIC BUILD 8호-4] 지구 열수지", "지구가 흡수하는 에너지와 방출하는 에너지가 같은 이유가 궁금합니다.",
          "들어오는 양과 나가는 양이 같아야 평균 온도가 일정하게 유지됩니다."),
         ("[Squeeze 12호-9] 엘니뇨 때 용승", "엘니뇨 때 동태평양 용승이 약해지는 이유를 다시 설명해 주세요.",
          "무역풍이 약해져 표층 바닷물이 서쪽으로 덜 밀려나서 깊은 곳의 찬 물이 덜 올라옵니다.")],
    13: [("[Squeeze 13호-7] 렌츠 법칙 방향", "자석을 멀리할 때 유도 전류 방향 정하는 법이 헷갈립니다.",
          "코일은 변화를 방해하는 쪽으로 자기장을 만듭니다. 멀어지면 끌어당기는 방향입니다."),
         ("[FRAMING II-98-5] 발전기 에너지 전환", "발전기에서 어떤 에너지가 어떤 에너지로 바뀌는지 정리하고 싶습니다.",
          "회전하는 운동 에너지가 전자기 유도로 전기 에너지가 됩니다.")],
    14: [("[예시문항 7번] 과학 기술과 사회", "예시문항 7번 보기 ㄷ이 왜 틀렸는지 궁금합니다.",
          "보기 ㄷ은 자료에 없는 결론을 끌어냈습니다. 자료에서 확인되는 것만 고르세요."),
         ("[Squeeze 14호-2] 6단원 정리", "6단원에서 꼭 외워야 할 것만 추려 주실 수 있나요?",
          "필기노트 14호 마지막 장 정리표만 보면 충분합니다.")],
}

# ---------------------------------------------------------------- 날짜
TODAY = date.today() - timedelta(days=(date.today().weekday() - 4) % 7)   # 실행일 직전 금요일 = N주차 마지막 날
W1 = TODAY - timedelta(days=WEEKS * 7 + 4)                                # 1주차가 걸친 달력 주의 월요일 (12/21)


def day(week, weekday):
    """커리큘럼 주차(토~금) week 의 요일. weekday 0=월 … 6=일. 토·일은 그 주의 시작."""
    base = W1 + timedelta(days=(week - 1) * 7)
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


def last_id(table):
    return q(f"SELECT MAX(id) AS id FROM {table}", one=True)["id"]


DATES = []          # (table, id, {column: value}) - 마지막에 한꺼번에 날짜를 맞춘다


def at(table, row_id, **cols):
    if row_id:
        DATES.append((table, row_id, cols))


# ---------------------------------------------------------------- 선생님 · 조교
PW = {"teacher": secrets.token_urlsafe(8) + "!7", "ta": secrets.token_urlsafe(8) + "!7", "ta2": secrets.token_urlsafe(8) + "!7"}
with app.app_context():
    from security import encrypt, hash_password
    x("INSERT INTO users (role, username, display_name, password_hash) VALUES ('teacher', 'teacher', '정태혁', ?)",
      (hash_password(PW["teacher"]),))
T = login("teacher", PW["teacher"])
ok("조교 추가", T.post("/t/staff", data={"display_name": "한지수", "username": "ta_hanjisu"}))
ok("조교 추가 2", T.post("/t/staff", data={"display_name": "김도윤", "username": "ta_kimdoyun"}))
with app.app_context():
    x("UPDATE users SET password_hash = ?, must_change_pw = 0 WHERE username = 'ta_hanjisu'", (hash_password(PW["ta"]),))
    x("UPDATE users SET password_hash = ?, must_change_pw = 0 WHERE username = 'ta_kimdoyun'", (hash_password(PW["ta2"]),))
TA = login("ta_hanjisu", PW["ta"])
TA2 = login("ta_kimdoyun", PW["ta2"])
ok("조교 소개", TA.post("/t/me/intro", data={"intro": "생명·화학 담당. 오답 원인부터 같이 봅니다."}))
ok("조교 소개 2", TA2.post("/t/me/intro", data={"intro": "물리·지구과학 담당. 계산 문항 풀이 순서를 잡아 드립니다."}))
TA_ID = q("SELECT id FROM users WHERE username = 'ta_hanjisu'", one=True)["id"]

# ---------------------------------------------------------------- 반 8개 (단과 4 · 재종 4)
CLASSES = [  # 이름, 구분, [(요일, 시작, 끝)]
    ("대구 토요일 A반", "단과", [(5, "10:00", "13:00")]),
    ("대구 토요일 B반", "단과", [(5, "14:00", "17:00")]),
    ("대치 일요일반", "단과", [(6, "14:00", "17:00")]),
    ("대치 목요일반", "단과", [(3, "19:00", "22:00")]),
    ("대구 재종 1반", "재종", [(0, "09:00", "11:50"), (2, "09:00", "11:50"), (4, "09:00", "11:50")]),
    ("대구 재종 2반", "재종", [(1, "13:00", "15:50"), (3, "13:00", "15:50")]),
    ("대치 재종 1반", "재종", [(0, "13:00", "15:50"), (3, "13:00", "15:50")]),
    ("대치 재종 2반", "재종", [(1, "09:00", "11:50"), (4, "09:00", "11:50")]),
]
# 학생 페르소나: 반마다 1명. weak = 약한 단원, skill = 평균 정답률, ask = 주마다 질문할 확률
PERSONAS = {
    "대구 토요일 A반": dict(name="박서윤", no="0012874416", parent="010-2817-4416", target="연세대 생명시스템", weak="생명중심원리",
                          skill=0.70, ask=0.8, note="성실형. 질문·오답 노트·시험지 첨삭을 꾸준히 씀. 화면을 가장 많이 보는 학생"),
    "대구 토요일 B반": dict(name="이도현", no="0031558207", parent="010-4120-8207", target="서울대 화학생물공학", weak="중화 반응",
                          skill=0.88, ask=0.15, note="상위권. 질문은 거의 없고 모의고사 분석·통계만 봄"),
    "대치 일요일반": dict(name="최민서", no="0045019932", parent="010-7731-9932", target="고려대 의예", weak="역학",
                        skill=0.62, ask=0.35, note="학원 여러 곳 병행. 결석이 잦고 강의 영상·수업 기록으로 따라잡음"),
    "대치 목요일반": dict(name="정하준", no="0050772641", parent="010-3392-2641", target="성균관대 화학공학", weak="산화와 환원",
                        skill=0.58, ask=0.5, note="2주차에 늦게 합류. 1주차 자료를 찾아봄", late=2),
    "대구 재종 1반": dict(name="김나연", no="kny2027", parent="010-5560-1183", target="경북대 수의예", weak="화학 결합",
                        skill=0.66, ask=0.6, note="재수생. 소도시 명상 집중 기록이 가장 길고 학습상담을 자주 씀"),
    "대구 재종 2반": dict(name="오준혁", no="ojh0412", parent="010-6014-0412", target="계명대 간호", weak="지구 열수지",
                        skill=0.45, ask=0.55, note="하위권. 오답 노트 이유 고르기와 시험지 첨삭에 기대는 편"),
    "대치 재종 1반": dict(name="윤지아", no="yja2027", parent="010-8825-3071", target="이화여대 화학생명", weak="전기적 성질과 반도체",
                        skill=0.68, ask=0.3, note="아이폰 사용. 알림·홈 화면 설치를 씀. 교재 배송·환불 행정문의"),
    "대치 재종 2반": dict(name="한승우", no="hsw2027", parent="010-2290-7764", target="한양대 기계", weak="엘니뇨",
                        skill=0.57, ask=0.25, note="게임(퀴즈) 위주. 비밀번호를 잃어버려 임시 비밀번호를 받은 적 있음"),
}
LAST = "김이박최정강조윤장임한오서신권황안송류홍전고문양손배백허남심노"
FIRST = ["민준", "서연", "도윤", "하은", "시우", "지유", "주원", "서윤", "예준", "지민", "하준", "수아", "지호", "채원", "준서",
         "다은", "건우", "예린", "현우", "소율", "우진", "지아", "선우", "윤서", "연우", "태민", "가은", "승현", "나연", "재원"]
cls = {}
for name, track, slots in CLASSES:
    ok(f"반 {name}", T.post("/t/classes", data={"name": name, "track": track, "description": f"{track} · 2028 수능 대비 SEASON 1"}))
    cid = q("SELECT id FROM classes WHERE name = ?", (name,), one=True)["id"]
    cls[name] = {"id": cid, "track": track, "slots": slots, "students": []}
    for wd, s, e in slots:
        x("INSERT INTO timetable (class_id, weekday, starts, ends, title, room) VALUES (?, ?, ?, ?, '통합과학', ?)",
          (cid, wd, s, e, name.split()[0] + " 3관"))

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
    P[name] = {"st": st, "per": PERSONAS[name], "pw": secrets.token_urlsafe(8) + "!7", "c": c}


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
OTHERS = [(st, accounts[st["id"]]) for _, st in ALL_STUDENTS if st["id"] in accounts]

# ---------------------------------------------------------------- 교재 · 인증 코드
ok("교재 복습 테스트", T.post("/t/books", data={"title": "SEASON 1 복습 테스트", "subject": "통합과학", "expires_on": "2027-11-30", "kind": "복습 테스트"}))
ok("교재 모의고사", T.post("/t/books", data={"title": "정태혁 모의고사 SEASON 1", "subject": "통합과학", "expires_on": "2027-11-30",
                                           "kind": "모의고사", "notice": "매주 1회분 + SEQUENCE 분석 교재"}))
BOOK_R = q("SELECT id FROM books WHERE title = 'SEASON 1 복습 테스트'", one=True)["id"]
BOOK_M = q("SELECT id FROM books WHERE title = '정태혁 모의고사 SEASON 1'", one=True)["id"]
ok("교재 코드", T.post(f"/t/books/{BOOK_M}/codes", data={"kind": "single", "count": "40"}))
for name, p in P.items():
    code = q("SELECT code FROM book_codes WHERE book_id = ? AND uses = 0 ORDER BY id LIMIT 1", (BOOK_M,), one=True)["code"]
    ok(f"교재 등록 {p['st']['name']}", p["S"].post("/s/books/register", data={"code": code}))


# ---------------------------------------------------------------- OMR (복습 테스트 · 모의고사)
def omr_workbook(n_items, key, pts, units, absent):
    from openpyxl import Workbook
    wb = Workbook()
    ws = wb.active
    ws.title = "OMR"
    ws.append(["이름", "수험번호", "반"] + list(range(1, n_items + 1)))
    ws.append(["정답", "", ""] + key)
    ws.append(["배점", "", ""] + pts)
    for c_name, st in ALL_STUDENTS:
        if st["id"] in absent:
            continue
        row = []
        for i, k in enumerate(key):
            pr = SKILL[st["id"]] - (0.25 if i >= n_items * 2 // 3 else 0)
            if WEAK.get(st["id"]) == units[i]:
                pr -= 0.4
            row.append(k if rng.random() < pr else rng.choice([v for v in range(1, 6) if v != k]))
        ws.append([st["name"], st["parent8"], c_name] + row)
    info = wb.create_sheet("문항정보")
    info.append(["문항번호", "정답", "배점", "단원", "핵심개념", "문항형식", "선지구성", "보기함정", "선지분석"])
    for i in range(n_items):
        w1, w2 = (key[i] % 5) + 1, ((key[i] + 1) % 5) + 1
        info.append([i + 1, key[i], pts[i], units[i], "", "일반", "", "",
                     f"{w1}번: 정의를 반대로 기억함(개념 부족) / {w2}번: 조건 하나를 놓침(조건 독해)"])
    buf = io.BytesIO()
    wb.save(buf)
    return buf.getvalue()


def make_round(book, rnd, n_items, full, when, weeks):
    key = [rng.randint(1, 5) for _ in range(n_items)]
    pts = [full // n_items] * n_items
    pool = [u for w in weeks for u in CURRICULUM[w][1]]
    units = [pool[(i * 3 + rnd) % len(pool)] for i in range(n_items)]
    ok(f"회차 {book}-{rnd}", T.post(f"/t/books/{book}/mocks", data={"round_no": str(rnd), "n_items": str(n_items),
                                                                    "full_score": str(full), "answer_key": "".join(map(str, key))}))
    mid = q("SELECT id FROM mocks WHERE book_id = ? AND round_no = ?", (book, rnd), one=True)["id"]
    absent = {st["id"] for _, st in ALL_STUDENTS if rng.random() < 0.06}
    absent.discard(SEO["st"]["id"])
    if rng.random() < 0.3:
        absent.add(P["대치 일요일반"]["st"]["id"])                   # 최민서는 가끔 결석
    if rnd < P["대치 목요일반"]["per"]["late"]:
        absent.add(P["대치 목요일반"]["st"]["id"])                   # 정하준은 2주차부터
    data = omr_workbook(n_items, key, pts, units, absent)
    ok(f"OMR {book}-{rnd}", (TA if rnd % 2 else TA2).post(f"/t/mocks/{mid}/omr", data={"file": (io.BytesIO(data), f"{rnd}회_채점.xlsx")},
                                                          content_type="multipart/form-data"))
    ok(f"시험 평가 {book}-{rnd}", T.post(f"/t/mocks/{mid}/review", data={
        "level": str(rng.choice([2, 3, 3, 4])), "time": rng.choice(["충분", "적당", "빠듯"]),
        "killer": f"{n_items - 2}, {n_items}", "video": "",
        "review": f"{CURRICULUM[weeks[-1]][0]} 범위. 킬러 문항은 자료 해석형입니다. 오답이 몰린 문항은 다음 수업 앞 10분에 다시 봅니다."}))
    x("UPDATE mocks SET exam_date = ? WHERE id = ?", (when.isoformat(), mid))
    at("mocks", mid, created_at=ts(when - timedelta(days=1), 20), review_at=ts(when + timedelta(days=1), 22))
    at("omr_uploads", last_id("omr_uploads"), created_at=ts(when + timedelta(days=1), 21))
    for r in q("SELECT id FROM mock_entries WHERE mock_id = ?", (mid,)):
        at("mock_entries", r["id"], updated_at=ts(when + timedelta(days=1), 21))
    for r in q("SELECT id FROM exam_results WHERE mock_id = ?", (mid,)):
        at("exam_results", r["id"], updated_at=ts(when + timedelta(days=1), 21))
    return mid


def ask(cl, title, body, qtype, when, image=True, assignee=None):
    data = {"title": title, "body": body, "qtype": qtype}
    if image:
        data["image"] = [img("question.png")]
    if assignee:
        data["assignee"] = str(assignee)
    ok(f"질문 {title}", cl.post("/s/questions", data=data, content_type="multipart/form-data"))
    qid = last_id("questions")
    at("questions", qid, created_at=ts(when, rng.randint(19, 23), rng.randint(0, 59)))
    return qid


def answer(cl, qid, body, when):
    ok(f"답변 {qid}", cl.post(f"/t/questions/{qid}", data={"body": body}))
    at("answers", last_id("answers"), created_at=ts(when, rng.randint(9, 23), rng.randint(0, 59)))


# ---------------------------------------------------------------- 시즌 시작 전 설정
MOCK = {}
ok("D-day", T.post("/t/timetable", data={"exam_day": "2027-11-18", "exam_label": "수능"}))
for name, c in cls.items():
    ok(f"개강 공지 {name}", T.post(f"/t/classes/{c['id']}/notices", data={
        "tag": "공지", "pinned": "1", "title": "SEASON 1 개강 안내",
        "body": "교재: LINE UP 개념서 2권 · FRAMING 문항편 2권 및 해설편 2권 · 매주 Squeeze · LOGIC BUILD · 필기노트 · 정태혁 모의고사 1회분\n"
                "질문: 질문 게시판에 [교재-페이지-번호] 형식으로 / 행정: 질문 게시판 행정문의"}))
    at("notices", last_id("notices"), created_at=ts(sess(c, 1) - timedelta(days=2), 21))
for name, p in P.items():
    for wd, s_, e_ in p["c"]["slots"]:
        p["S"].post("/s/timetable", data={"weekday": str(wd), "starts": s_, "ends": e_, "title": "통합과학", "room": "", "tone": "1"})
    p["S"].post("/s/timetable", data={"weekday": str(rng.choice([0, 1, 2])), "starts": "19:00", "ends": "21:00", "title": "자습", "room": "", "tone": "2"})

# ---------------------------------------------------------------- 주차별 진행
for w in range(1, WEEKS + 1):
    topic, units = CURRICULUM[w]
    lb = f" · LOGIC BUILD {LOGIC_BUILD[w]}호" if w in LOGIC_BUILD else ""
    last_week = w == WEEKS
    for name, c in cls.items():
        d = sess(c, w)
        ok(f"과제 공지 {name} {w}", T.post(f"/t/classes/{c['id']}/notices", data={
            "tag": "과제", "title": f"{w}주차 과제", "body": f"Squeeze {w}호{lb} · 필기노트 {w}호 복습 / 오답 노트에서 틀린 이유 고르기"}))
        at("notices", last_id("notices"), created_at=ts(d, 22))
        k = (w - 1) % 4 + 1
        ok(f"수업 기록 {name} {w}", (TA if c["track"] == "단과" else TA2).post("/t/lessons", data={
            "class_id": str(c["id"]), "day": d.isoformat(), "title": f"{w}주차 {topic}", "body": f"필기노트 {w}호 판서 / 다음 시간 복습 테스트 범위",
            "image": [img(f"lesson{k}_1.png"), img(f"lesson{k}_2.png")]}, content_type="multipart/form-data"))
        at("lessons", last_id("lessons"), created_at=ts(d, 23))
        r = T.post(f"/t/classes/{c['id']}/exams", data={"name": f"{w}주차 주간 테스트", "subject": "통합과학",
                                                        "exam_date": d.isoformat(), "max_score": "50"})
        ok(f"주간테스트 {name} {w}", r, (302,))
        eid = int(r.headers["Location"].rstrip("/").rsplit("/", 1)[-1])
        ok(f"점수 {name} {w}", T.post(f"/t/exams/{eid}", data={
            f"score_{st['id']}": str(max(8, min(50, round(rng.gauss(26 + SKILL[st['id']] * 20, 4))))) for st in c["students"] if rng.random() > 0.05}))
        if w in (2, 6, 10):
            ok("정오", T.post(f"/t/classes/{c['id']}/notices", data={"tag": "정오", "textbook": "LINE UP 개념서", "title": f"LINE UP {w * 9}p 정오",
                                                                    "body": f"예제 {w % 3 + 1}번 보기 ㄴ의 단위를 'mL'에서 'L'로 고칩니다."}))
            at("notices", last_id("notices"), created_at=ts(day(w, 2), 18))
        if w in (4, 8, 12):
            ok("영상", T.post(f"/t/classes/{c['id']}/videos", data={"title": f"{w}주차 {topic} 보충", "url": "https://youtu.be/dQw4w9WgXcQ",
                                                                   "duration": "42:10", "expires_on": (TODAY + timedelta(days=60)).isoformat()}))
            at("videos", last_id("videos"), created_at=ts(day(w, 1), 21))
    MOCK[("r", w)] = make_round(BOOK_R, w, 20, 40, day(w, 5), [w])
    MOCK[("m", w)] = make_round(BOOK_M, w, 25, 50, day(w, 6), list(range(max(1, w - 2), w + 1)))
    if w in (3, 7, 11):
        ok(f"cast {w}", T.post("/cast/new", data={"title": f"{w}주차를 마치며", "body": f"{topic}까지 왔습니다. 오답 노트 이유 고르기를 빠뜨리지 마세요.", "video_url": ""}))
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
        if rng.random() < per["ask"]:
            title, body, ans = QUESTIONS[w][rng.randint(0, 1)]
            qid = ask(S, title, body, "학습질문", day(w, rng.choice([0, 1, 2])))
            if not (last_week and name in ("대구 토요일 A반", "대구 재종 1반")):      # 이 둘은 오늘 조교가 답할 질문
                answer(TA if rng.random() < 0.6 else TA2, qid, ans, day(w, 3))
                if rng.random() < 0.3:
                    ok("추가 질문", S.post(f"/s/questions/{qid}/followup", data={"body": "그럼 반대 경우에는 어떻게 되나요?"}))
                    at("followups", last_id("followups"), created_at=ts(day(w, 3), 22))
                    answer(TA, qid, "반대 경우는 조건만 뒤집어 같은 순서로 따라가면 됩니다. 교재 해당 쪽 예제 2번이 그 경우입니다.", day(w, 4))
        if (name == "대구 재종 1반" and w % 3 == 0) or (name == "대구 토요일 A반" and w in (3, 9)):
            qid = ask(S, f"{w}주차 공부 계획 상담", "복테 점수가 몇 주째 비슷합니다. 평일에 무엇을 먼저 해야 할지 모르겠습니다.", "학습상담",
                      day(w, 1), image=False, assignee=TA_ID)
            answer(TA, qid, f"평일 3일만 정해서 오답 노트 → 같은 단원 기출 10문항 순서로 돌려 보세요. {per['weak']} 문항이 계속 틀려서 그 부분부터 하면 됩니다.", day(w, 2))
            ok("상담 평점", S.post(f"/s/questions/{qid}/rate", data={"rating": str(rng.choice([4, 5, 5]))}))
        if name == "대치 재종 1반" and w in (1, 5):
            qid = ask(S, "교재 배송 문의" if w == 1 else "교재 환불 문의",
                      "FRAMING 해설편 2권이 아직 안 왔습니다." if w == 1 else "Squeeze 5호가 두 권 왔습니다. 한 권 환불되나요?", "행정문의", day(w, 2), image=False)
            answer(T, qid, "이번 주 금요일에 발송됩니다." if w == 1 else "다음 수업 때 행정실에 반납하면 처리됩니다.", day(w, 3))
        if name in ("대구 토요일 A반", "대구 재종 2반") and w % 2 == 0:            # 1:1 첨삭
            ok("1:1 첨삭 요청", S.post(f"/s/analysis/{MOCK[('r', w)]}/feedback", data={"body": "틀린 문항 풀이에서 어디가 잘못됐는지 봐 주세요.",
                                                                                      "image": [img("solve.png")]}, content_type="multipart/form-data"))
            tid = last_id("feedback_threads")
            at("feedback_msgs", last_id("feedback_msgs"), created_at=ts(day(w, 6), 21))
            if last_week:
                at("feedback_threads", tid, created_at=ts(day(w, 6), 21), updated_at=ts(day(w, 6), 21))
            else:
                ok("1:1 첨삭 답변", TA.post(f"/t/feedback/{tid}", data={"body": f"세 번째 줄에서 조건을 놓쳤습니다. {per['weak']} 개념 정의부터 다시 쓰고 같은 순서로 풀면 정답이 나옵니다."}))
                at("feedback_msgs", last_id("feedback_msgs"), created_at=ts(day(w, 0) + timedelta(days=7), 21))
                at("feedback_threads", tid, created_at=ts(day(w, 6), 21), updated_at=ts(day(w, 0) + timedelta(days=7), 21))
        took = q("SELECT 1 FROM mock_entries WHERE mock_id = ? AND user_id = ?", (MOCK[("r", w)], p["uid"]), one=True)
        if took and name in ("대구 토요일 A반", "대구 재종 2반") and (w % 2 == 1 or last_week):  # 시험지 첨삭 (응시한 회차만)
            ok("시험지 제출", S.post(f"/s/analysis/{MOCK[('r', w)]}/paper", data={"note": "틀린 문항 풀이 봐 주세요.", "image": [img("paper1.png"), img("paper2.png")]},
                                   content_type="multipart/form-data"))
            pid = last_id("exam_papers")
            if last_week:
                at("exam_papers", pid, submitted_at=ts(day(w, 6), 19))
            else:
                ok("시험지 첨삭", TA.post(f"/t/papers/{pid}", data={"r5": "개념 부족", "m5": "정의를 반대로 씀", "r12": "조건 독해", "m12": "보기 ㄷ 조건을 읽지 않음",
                                                                   "comment": f"{per['weak']}만 다시 잡으면 됩니다. 풀이 순서는 좋습니다."}))
                at("exam_papers", pid, submitted_at=ts(day(w, 6), 19), reviewed_at=ts(day(w, 0) + timedelta(days=7), 14))
        if rng.random() < (0.9 if name in ("대구 토요일 A반", "대구 재종 2반") else 0.4):   # 오답 노트
            for kind in ("r", "m"):
                mid = MOCK[(kind, w)]
                e = q("SELECT answers FROM mock_entries WHERE mock_id = ? AND user_id = ?", (mid, p["uid"]), one=True)
                key = [int(v) for v in re.findall(r"\d", q("SELECT answer_key FROM mocks WHERE id = ?", (mid,), one=True)["answer_key"])]
                picks = e["answers"] if e else ""
                for i, k in enumerate(key):
                    if i < len(picks) and picks[i] != str(k) and rng.random() < 0.7:
                        S.post(f"/s/wrong/{mid}/{i + 1}", data={"reason": rng.choice(["개념 부족", "조건 독해", "계산 실수"]),
                                                               "memo": "", "reviewed": "" if last_week else "1"})
        if name in ("대치 재종 2반", "대구 토요일 B반") or rng.random() < 0.3:         # 퀴즈
            st_ = S.post("/s/games/quiz/start", json={"topic": f"{min(34, w * 2):02d}"}).get_json(silent=True) or {}
            if st_.get("round_id"):
                S.post(f"/s/games/quiz/{st_['round_id']}/submit", json={"answers": [rng.randint(0, 3) for _ in st_.get("questions", [])]})
                when = day(w, rng.randint(0, 4))
                at("game_rounds", st_["round_id"], started_at=ts(when, 22), finished_at=ts(when, 22, 10))
    for st, (user, pw, uid) in rng.sample(OTHERS, 3):                               # 다른 학생들 공개 질문
        title, body, ans = QUESTIONS[w][rng.randint(0, 1)]
        qid = ask(login(user, pw), title, body, "학습질문", day(w, rng.randint(0, 6)))
        if not last_week or rng.random() < 0.5:
            answer(TA2 if rng.random() < 0.5 else TA, qid, ans, day(w, 4))
    if w == 2:
        faq = q("SELECT id FROM questions WHERE title LIKE '%샤가프 법칙 비율%' ORDER BY id LIMIT 1", one=True)
        if faq:
            ok("자주 묻는 질문", TA.post(f"/t/questions/{faq['id']}/faq"))

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
FOCUS = {"대구 재종 1반": 0.85, "대구 토요일 A반": 0.55, "대구 재종 2반": 0.4}
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

# ---------------------------------------------------------------- 날짜 맞추기
with app.app_context():
    for table, row_id, cols in DATES:
        sets = ", ".join(f"{k} = ?" for k in cols)
        x(f"UPDATE {table} SET {sets} WHERE id = ?", (*cols.values(), row_id))
    x("UPDATE users SET last_login_at = ?", (ts(TODAY - timedelta(days=1), 22),))
    x("UPDATE notice_reads SET read_at = (SELECT created_at FROM notices WHERE notices.id = notice_reads.notice_id)")
    x("DELETE FROM audit_log")

with open(CRED, "w", encoding="utf-8") as fh:
    fh.write(f"데모 로그인 (가짜 데이터) · SEASON 1 {WEEKS}주차까지 · 오늘 = {TODAY} (금)\n\n")
    fh.write(f"선생님 정태혁   teacher / {PW['teacher']}\n")
    fh.write(f"조교 한지수     ta_hanjisu / {PW['ta']}\n")
    fh.write(f"조교 김도윤     ta_kimdoyun / {PW['ta2']}\n\n")
    for name, p in P.items():
        fh.write(f"학생 {p['st']['name']} ({name})  {p['st']['no']} / {p['pw']}   {p['per']['note']}\n")
print("weeks", WEEKS, "students", len(ALL_STUDENTS), "accounts", len(accounts) + len(P), "fail", len(FAIL))
for f in FAIL[:40]:
    print("  FAIL", f)
sys.exit(1 if FAIL else 0)
