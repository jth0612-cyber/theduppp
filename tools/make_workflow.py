"""역할별 전 화면 캡처(wireflow/roles3, tools/wireflow_crawl.js)로 앱 작동 흐름 캔버스를 만든다: docs/ux/workflow/index.html + img/

    python tools/make_workflow.py

단계 = (역할, 주소, 제목, 설명, 보여 줄 버튼 글자 또는 높이(px), 앞 단계 번호). 앞 단계 번호를 주면 그 카드에서 갈라져 나온다 (-1 = 새 출발점).
카드에는 버튼 글자가 있는 곳을 잘라 넣고, 누르면 화면 전체가 열린다.
"""
import json
import os
import re
import shutil

from PIL import Image

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SHOTS = os.path.join(ROOT, "wireflow", "roles3")
OUT = os.path.join(ROOT, "docs", "ux", "workflow")
BOX = json.load(open(os.path.join(SHOTS, "boxes.json"), encoding="utf-8"))
CAP = {"학생": "student", "조교": "assistant", "선생님": "teacher", "학부모": "parent"}
P = "/p/PARENT"   # 학부모 리포트 (박서윤). 비밀 링크라 따로 찍어 boxes.json 의 parent 에 넣는다
STU_DETAIL = "성적 추이 그래프, 학부모 리포트 링크와 새 링크로 바꾸기, 계정 발급, 상담 메모를 한 화면에서 봐요"

FLOWS = [
    ("시작 화면", "로그인하면 역할마다 첫 화면이 달라요", [
        ("학생", "/s/", "학생 홈", "알림(최근 7일 답변과 첨삭), 공지, 질답 게시판 최근 글, 질문하기 바로가기", None, None),
        ("학생", "/s/books/buy", "교재 구매", "교재마다 판매처로 가요. 구매, 배송, 환불은 판매처에서 해요", None, 0),
        ("학생", "/password", "내 계정", "비밀번호를 바꿔요. 10자 이상, 영문, 숫자, 특수문자 중 2종류 이상", None, 0),
        ("선생님", "/t/", "대시보드", "답변 대기 질문, 피드백 대기, 첨삭 대기 수와 최근 회차의 응시 인원, 평균", None, -1),
        ("조교", "/t/questions", "조교 첫 화면은 질문답변", "조교는 답변 대기 질문 목록에서 시작해요. 메뉴는 선생님과 같고 조교 계정 관리만 없어요.", None, 3),
    ]),
    ("시험 결과 올리기", "조교나 실장이 채점기 OMR 엑셀을 올리면 학생 화면과 학부모 리포트에 바로 반영돼요. 손으로 입력하는 단계는 없어요.", [
        ("조교", "/t/books", "복테/모의고사", "복습 테스트 1~50회, 모의고사 1~50회와 회차마다 응시 인원. 회차는 시즌과 상관없이 이어져요.", None, None),
        ("조교", "/t/books/3", "교재(회차 묶음) 관리", "회차를 더하고 닫고 지워요. '열림' 회차 중 OMR 결과나 시험 분석이 있는 회차만 학생에게 보여요.", "회차 추가", 0),
        ("조교", "/t/mocks/64", "회차의 시험 분석", "난이도, 주요 문항, 총평, 해설 영상 주소. 학생 화면에는 난이도와 주요 문항만 보이고 총평과 영상은 접혀 있어요.", "저장", 0),
        ("조교", "/t/mocks/64", "회차에 OMR 엑셀 올리기", "정답, 배점, 문항정보가 든 채점기 엑셀을 올려요. 정답 칸 *는 모두 정답, -는 정답 없음. 복테는 10문항 10점, 모의고사는 25문항 50점이에요.", "올리기", 2),
        ("조교", "/t/mocks/64", "회차의 학부모 문자", "올린 결과로 반별 학부모 문자 문안을 만들어요(점수, 반 평균, 공부할 문항).", "학부모 문자", 3),
    ]),
    ("학생이 결과 보기", "시험 분석, 오답 노트, 내 성적 모두 복습 테스트와 모의고사 탭이 따로 있어요", [
        ("학생", "/s/analysis", "시험 분석", "새 답변이나 첨삭이 있는 회차가 먼저 열려요. 회차 칸에서 고르면 바로 바뀌어요.", None, None),
        ("학생", "/s/analysis?kind=review", "시험 분석의 복습 테스트 탭", "10문항 10점. 난이도와 주요 문항, 내 답안, 원점수, 반 평균, 예상 등급. 석차, 백분위, 점수대 분포는 학생에게 보이지 않아요. 범례와 산출 방식은 제목 옆 물음표에 있어요.", None, 0),
        ("학생", "/s/analysis?kind=mock", "시험 분석의 모의고사 탭", "25문항 50점. 고른 선지로 본 틀린 이유, 등급 기준표, 문항 지도(파랑이 진할수록 많이 틀린 문항)", None, 0),
        ("학생", "/s/wrong?kind=review", "오답 노트의 복습 테스트", "틀린 문항마다 이유를 고르고, 다시 풀어 맞히면 체크해요. 고르는 즉시 저장돼요. 이유는 학생, 조교, 자동 순으로 하나만 대표로 남아요.", None, 1),
        ("학생", "/s/wrong?kind=mock", "오답 노트의 모의고사", "회차를 고르거나 전체 회차를 봐요. 위에 이유별 문항 수와 비율이 있어요.", None, 2),
        ("학생", "/s/scores?kind=review", "내 성적의 복습 테스트", "득점률 그래프. 점에 마우스를 올리면 점수와 반 평균이 보여요.", None, 3),
        ("학생", "/s/scores?kind=mock", "내 성적의 모의고사", "회차별 원점수와 반 평균", None, 4),
        ("학생", "/s/wrong?kind=mock&view=open", "오답 노트의 복습 전만", "아직 다시 풀지 않은 문항만 남겨요.", None, 4),
        ("학생", "/s/report", "성적 리포트", "인쇄하거나 PDF로 저장해요. 복습 테스트와 모의고사 칸이 나뉘어 있어요.", None, 5),
    ]),
    ("복습 테스트 첨삭", "1:1 관리, 복습 테스트 회차에서만", [
        ("학생", "/s/analysis?kind=review", "시험지 사진 올리기", "풀이가 적힌 시험지를 찍어 올려요(6장까지). 시험지 제출, 선생님 검사, 문항별 첨삭 순서로 진행돼요.", "다시 올리기", None),
        ("조교", "/t/papers", "첨삭 대기", "올라온 순서대로 점수, 사진 장수, 제출 시각을 보여 줘요.", None, 0),
        ("조교", "/t/papers/15", "문항별 첨삭", "OMR로 틀린 문항이 미리 표시돼요. 문항마다 반 오답률, 오답 유형, 메모를 적고 저장하면 다음 시험지로 넘어가요.", "첨삭 저장", 1),
        ("조교", "/t/papers?status=done", "첨삭 완료", "끝난 첨삭 목록. 다시 열어 고칠 수 있어요.", None, 2),
        ("학생", "/s/feedback", "1:1 관리", "복테 첨삭과 모의고사 피드백을 회차별로 모아 봐요. 누르면 그 회차 분석으로 가요.", None, 2),
        ("학부모", P + "?kind=review", "학부모 리포트에 반영", "조교가 고른 틀린 이유와 코멘트가 학부모 리포트로 나가요.", None, 2),
    ]),
    ("Full 모의고사 피드백", "1:1 관리, 모의고사 회차에서만", [
        ("학생", "/s/analysis?kind=mock", "피드백 요청", "어느 문항에서 막혔는지 풀이 사진과 함께 1:1로 물어요.", 2900, None),
        ("조교", "/t/feedback", "피드백 대기", "학생, 반, 회차, 점수, 요청 시각을 보여 줘요.", None, 0),
        ("조교", "/t/feedback/14", "답변", "틀린 문항 요약(배점, 정답, 고른 답)과 학생 사진을 보고 글과 사진으로 답해요. 학생은 이어서 물을 수 있어요.", "답변 보내기", 1),
        ("조교", "/t/feedback?status=done", "답변 완료", "답한 요청 목록", None, 2),
        ("학생", "/s/feedback", "1:1 관리에서 확인", "답변이 오면 홈의 알림과 1:1 관리에 떠요.", None, 2),
    ]),
    ("질문과 답변", "질답 게시판. 학습질문은 닉네임으로 공개되고 행정문의는 비공개예요", [
        ("학생", "/s/questions", "질답 게시판", "이번 주 많이 본 질문, 선생님이 고른 자주 묻는 질문, 유형별 목록이 있어요.", None, None),
        ("학생", "/s/questions", "질문 쓰기", "유형을 칩으로 고르면 칸 안 안내가 그 유형에 맞게 바뀌어요. 학습질문은 문제 사진이 필요해요.", None, 0),
        ("학생", "/s/questions?view=mine", "내 질문", "내가 쓴 질문만 모아 봐요.", None, 0),
        ("학생", "/s/questions?view=mine&status=open", "내 질문의 답변 대기", "", None, 2),
        ("학생", "/s/questions?view=mine&status=answered", "내 질문의 답변 완료", "", None, 2),
        ("학생", "/s/questions/93", "질문 상세", "답변을 보고 이어서 물을 수 있어요(질문은 3번까지).", None, 3),
        ("조교", "/t/questions", "질문답변", "유형과 단원 칩으로 걸러요. 답변 대기, 답변 완료, 전체, 자주 묻는 질문 탭", None, -1),
        ("조교", "/t/questions?status=answered", "답변 완료", "", None, 6),
        ("조교", "/t/questions/93", "답변 쓰기", "답변을 올리면 다음 대기 질문으로 넘어가요. 좋은 질문은 자주 묻는 질문으로 고정해요.", "답변 등록", 6),
    ]),
    ("공지와 cast", "반 공지는 그 반 학생에게, cast는 모든 학생에게 가요", [
        ("조교", "/t/classes/1?tab=notices", "반 공지 쓰기", "말머리(공지, 정오, 일정, 시험, 자료), 맨 위 고정, 다른 반에도 올리기. '정오'는 학생 정오표 탭에 교재별로 모여요.", "등록", None),
        ("학생", "/s/notices", "공지", "말머리 탭, 검색, 읽음 수와 공감 수", None, 0),
        ("학생", "/s/notices/137", "공지 읽기", "열면 읽음으로 세요. 공감을 누를 수 있어요.", None, 1),
        ("선생님", "/cast/new", "cast 새 글", "제목, 유튜브 주소, 편지나 안내 본문, 맨 위 고정", "올리기", -1),
        ("선생님", "/cast/3", "cast 글", "", None, 3),
        ("선생님", "/cast/3/edit", "글 고치기", "고쳐서 저장하거나 글을 지워요.", None, 4),
        ("학생", "/cast", "학생 cast", "모든 반 학생이 봐요.", None, 4),
    ]),
    ("수업 자료와 일정", "선생님이나 조교가 반을 골라 올리면 그 반 학생 화면에 쌓여요", [
        ("조교", "/t/lessons", "수업 기록 올리기", "반, 날짜, 주제, 노트 사진 10장까지. 사진이 없으면 한 줄 정리를 꼭 적어요.", "올리기", None),
        ("학생", "/s/lessons", "수업 기록", "주차별 판서와 노트 사진", None, 0),
        ("조교", "/t/classes/1?tab=materials", "반 자료실", "PDF, PPT, DOCX, HWP, 이미지를 20MB까지 올려요.", "올리기", -1),
        ("학생", "/s/materials", "자료실", "", None, 2),
        ("조교", "/t/classes/1?tab=videos", "강의 영상 등록", "유튜브 '일부 공개'나 구글 드라이브 링크. 만료일이 지나면 학생 화면에서 숨겨져요.", "등록", -1),
        ("학생", "/s/videos", "강의 영상", "", None, 4),
        ("조교", "/t/timetable", "주요 일정", "수능 D-day, 반별 휴강 기간(시작, 끝, 사유)", "넣기", -1),
        ("학생", "/s/timetable", "시간표", "D-day가 보이고, 휴강은 3주 전부터 위에 안내돼요. 휴강 주에는 요일 칸에 '휴강'이 떠요.", None, 6),
        ("조교", "/t/link", "조교 시스템 연동", "시트의 🌐앱_ 표를 받아 학생코드별로 성적, 오답, 리포트, 과제, 출결을 반영해요. 이름, 연락처, 학교는 저장하지 않아요.", "반영하기", -1),
        ("학생", "/s/attendance", "출결", "출석, 지각, 조퇴, 결석과 도착 시각", None, 8),
    ]),
    ("학생 관리와 학부모", "학생 한 명의 기록을 한 화면에서 봐요", [
        ("조교", "/t/students", "학생 검색", "단과와 재종, 이름, 아이디, 반, 목표로 찾아요.", None, None),
        ("조교", "/t/students/10?kind=review", "학생 상세의 복습 테스트 탭", STU_DETAIL, None, 0),
        ("조교", "/t/students/10?kind=mock", "학생 상세의 모의고사 탭", STU_DETAIL, None, 0),
        ("조교", "/t/students/10/report", "성적 리포트", "인쇄하거나 PDF로 저장해요.", None, 1),
        ("학부모", P + "?kind=review", "학부모 리포트의 복습 테스트", "로그인 없이 링크로 열어요. 점수, 반 평균, 지난 회차 대비 변화, 약한 단원, 틀린 이유, 코멘트, 출결", None, 1),
        ("학부모", P + "?kind=mock", "학부모 리포트의 모의고사", "", None, 2),
    ]),
    ("수업 일정, 교재 배부, 출석", "진도 그룹은 단과와 재종 따로, 한 주차는 토요일부터 금요일까지. 교재는 주차에 배정하고 수업마다 넣고 빼요", [
        ("조교", "/t/classes/1?tab=times", "반 수업 시간", "요일, 교시, 시작과 끝, 관, 교실. 주차마다 이 시간에 수업 칸이 생겨요. 단과는 3시간 30분 1회, 재종은 100분 여러 번", None, None),
        ("조교", "/t/schedule", "진도 그룹", "진도를 같이 나가는 반 묶음. 단과와 재종은 따로, 한 반은 그룹 하나에만 들어가요. 다른 그룹의 진도를 주차 번호대로 가져올 수 있어요.", None, 0),
        ("조교", "/t/schedule/*", "주차 × 수업 표", "줄은 주차(토~금), 열은 반 수업 시간(토요일반이 먼저). 칸마다 출석/명단과 교재, 오른쪽 끝은 교재별 배부 수", None, 1),
        ("조교", "/t/schedule/edit", "주차 고치기", "날짜(설 연휴 뒤 7주차), 진도, 복테와 모의고사 회차, 배부 교재를 바꿔요. '휴강 주로'를 누르면 뒤 주차 진도가 한 주씩 밀려요(단과 중간고사, 기말고사).", None, 2),
        ("조교", "/t/schedule/*?view=cal", "달력", "주차 한 줄을 토~금 칸으로 펼쳐 날짜별 수업과 출석 수를 봐요.", None, 2),
        ("조교", "/t/schedule/sessions/*", "수업 칸의 교재 넣고 빼기", "주차 교재를 이 수업만 빼거나 더 넣어요(예: Sequence가 아직 안 들어오면 다음 주에 같이 배부). 배부 수는 출석(지각, 조퇴 포함) 수예요.", 520, 2),
        ("조교", "/t/schedule/sessions/*", "수업 칸의 출석", "출석, 지각, 조퇴, 결석, 다른 반. 조교 시스템(시트) 출결이 들어오면 자동으로 채우고, 손으로 고친 칸은 그대로 둬요. 리클래스 학생은 아이디로 넣어요.", 1150, 5),
        ("조교", "/t/handouts", "배부 교재", "라인업, 프레이밍, 로직빌드, 스퀴즈, 시퀀스, 필기노트. 복테와 모의고사 회차와는 따로예요.", None, -1),
    ]),
    ("반과 계정", "반을 만들고 가입 코드를 나눠 주면 학생이 직접 가입해요", [
        ("조교", "/t/classes", "반 관리", "단과와 재종 반, 학생 수, 복테와 모의고사 평균 득점률, 새 반 만들기, 보관된 반", "만들기", None),
        ("조교", "/t/classes/1?tab=students", "반의 학생과 가입 코드", "학생마다 다른 가입 코드(한 번만 써요). 행정 시스템 코드를 붙여 넣거나 CSV로 받아요.", "등록", 0),
        ("조교", "/t/signups", "가입 승인", "코드 없이 들어온 신청. 미리 등록한 명단과 아이디가 같으면 승인할 때 이어 줘요.", None, 1),
        ("선생님", "/t/staff", "조교 계정", "선생님만 써요. 조교 추가(임시 비밀번호는 한 번만 보여요), 비밀번호 초기화, 사용 중지, 월별 답변 수 엑셀", None, -1),
        ("선생님", "/t/audit", "접근 기록", "로그인, 학생 정보 열람과 수정, 다운로드, 내보내기 기록", None, 3),
    ]),
    ("소도시 명상", "집중 타이머. 5분 이상 집중한 시간만 기록돼요", [
        ("학생", "/s/rooms", "장소 고르기", "오늘, 이번 주, 최근 4주 기록과 장소마다 이번 주 터줏대감", None, None),
        ("학생", "/s/rooms/sento", "노천탕", "자리에 앉으면 집중이 시작돼요. 지금 같이 있는 사람 수가 보여요.", None, 0),
        ("학생", "/s/rooms/eki", "바닷가 역", "3분마다 열차가 지나가고 역 노트가 있어요.", None, 0),
        ("학생", "/s/rooms/kissa", "골목 찻집", "늘 비가 오는 저녁 찻집", None, 0),
        ("학생", "/s/rooms/rank", "터줏대감 순위", "장소별 이번 주, 이번 달, 전체 순위", None, 0),
        ("학생", "/s/my", "내 공부", "오늘 공부 시간, 주간 순위(명상과 퀴즈), 최근 7일 이용 시간", None, 1),
        ("선생님", "/t/rooms", "소도시 명상 현황", "지금 있는 학생과 최근 7일 집중 시간 순위", None, -1),
    ]),
    ("수능 영단어", "평가원 빈출 단어를 하루 20개씩", [
        ("학생", "/s/games/", "수능 영단어", "누적 단어, 복습 단어, 게임 세 가지", None, None),
        ("학생", "/s/games/vocab", "오늘의 20단어", "카드를 눌러 뜻을 확인해요. 틀린 단어는 복습으로 가요.", None, 0),
        ("학생", "/s/games/vocab/review", "영단어 복습", "", None, 0),
        ("학생", "/s/games/vocab/match", "짝 맞추기", "5쌍씩 4판. 뜻 칸에 짝 없는 뜻이 하나 섞여 있어요.", None, 0),
        ("학생", "/s/games/speed/vocab_speed", "스피드 O/X", "60초 동안 ←는 O, →는 X", None, 0),
    ]),
    ("통과 Quiz", "TOPIC 01~34, 개념 문장 900여 개, 한 판 10문제", [
        ("학생", "/s/games/sci", "통과 Quiz", "TOPIC별 점수. 게임이 있는 TOPIC은 목록에 함께 있어요.", None, None),
        ("학생", "/s/games/mixed", "섞어 풀기", "O/X, ㄱㄴㄷ, 4지선다, 분류, 순서, 계산", None, 0),
        ("학생", "/s/games/speed/sci_speed", "O/X 스피드", "60초 동안 개념 문장을 O/X로 풀어요.", None, 0),
        ("학생", "/s/games/quiz", "TOPIC 퀴즈", "처음 보는 문제와 전에 틀린 문제가 먼저 나와요.", None, 0),
        ("학생", "/s/games/play/shell", "전자 배치 (TOPIC 07)", "", None, 0),
        ("학생", "/s/games/dna", "염기 짝 맞추기", "DNA 짝 맞추기와 RNA 전사, 난이도 셋", None, 4),
        ("학생", "/s/games/chargaff", "샤가프 법칙", "A=T, G=C, 전사된 RNA 문제 포함 5문제", None, 4),
        ("학생", "/s/games/play/redox", "산화 환원 (TOPIC 23)", "", None, 4),
        ("학생", "/s/games/play/neutral", "중화 반응 (TOPIC 24)", "", None, 4),
    ]),
]

CARD_W, FULL_W = 1320, 1920          # 캡처는 2배율(2560px). 카드는 440px 칸에 3배, 전체 화면은 1920px
if os.path.isdir(os.path.join(OUT, "img")):
    shutil.rmtree(os.path.join(OUT, "img"))
os.makedirs(os.path.join(OUT, "img"))
made, data, miss = {}, [], []
for t, sub, steps in FLOWS:
    out = []
    for k, (role, path, title, desc, focus, frm) in enumerate(steps):
        pages = BOX[CAP[role]]
        if "*" in path:                                    # 번호가 들어간 주소는 찍힌 것 중 첫 번째 (예: /t/schedule/sessions/*)
            rx = re.escape(path).replace(r"\*", r"[^/?]+")
            path = next(k for k in pages if re.fullmatch(rx, k))
        info = pages[path]
        full = Image.open(os.path.join(SHOTS, info["name"] + ".jpg")).convert("RGB")
        W, H = full.size
        top = 0
        if isinstance(focus, int):         # 버튼이 링크가 아니면 잘라 낼 높이(px)를 바로 준다
            top = min(H - W * 714 // 1280, round(focus * W / info["W"]))   # 높이는 화면(CSS) px
        elif focus:
            hit = [b for b in info["links"] + info["forms"] if b["text"].startswith(focus) and b["box"][0] > 18]
            if hit:
                top = max(0, min(H - W * 714 // 1280, int(hit[0]["box"][1] / 100 * H) - 220))
            else:
                miss.append((path, focus))
        key = f'{info["name"]}_{top}'
        if key not in made:
            full.crop((0, top, W, top + W * 714 // 1280)).resize((CARD_W, CARD_W * 714 // 1280), Image.LANCZOS).save(
                os.path.join(OUT, "img", key + ".webp"), quality=82, method=6)
            fp = os.path.join(OUT, "img", info["name"] + "_full.webp")
            if not os.path.exists(fp):
                full.resize((FULL_W, round(H * FULL_W / W)), Image.LANCZOS).save(fp, quality=80, method=6)
            made[key] = 1
        out.append({"img": f"img/{key}.webp", "full": f'img/{info["name"]}_full.webp', "role": role, "title": title,
                    "desc": desc, "from": frm})
    data.append({"title": t, "sub": sub, "steps": out})

tpl = open(os.path.join(ROOT, "tools", "workflow_template.html"), encoding="utf-8").read()
page = tpl.replace("/*DATA*/null", json.dumps(data, ensure_ascii=False))
open(os.path.join(OUT, "artifact.html"), "w", encoding="utf-8").write(page)          # 아티팩트용 (머리는 게시할 때 붙는다)
HEAD = ('<!doctype html>\n<html lang="ko"><head><meta charset="utf-8">'
        '<meta name="viewport" content="width=device-width, initial-scale=1, viewport-fit=cover">\n')
open(os.path.join(OUT, "index.html"), "w", encoding="utf-8").write(HEAD + page + "\n</html>\n")   # PC에서 바로 여는 파일
print("flows", len(data), "cards", sum(len(f["steps"]) for f in data), "images", len(os.listdir(os.path.join(OUT, "img"))))
print("focus not found:", miss)
