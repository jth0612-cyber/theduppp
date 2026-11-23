"""녹화 장면으로 앱 작동 흐름 캔버스(HTML)를 만든다: docs/ux/workflow/index.html + img/

    python tools/make_workflow.py <장면 폴더>
"""
import html
import json
import os
import sys

from PIL import Image

SCENES = sys.argv[1]
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT = os.path.join(ROOT, "docs", "ux", "workflow")
os.makedirs(os.path.join(OUT, "img"), exist_ok=True)

# 흐름마다 (장면, 역할, 제목, 설명)
FLOWS = [
    ("시험 결과가 학생에게 닿기까지", "복습 테스트 10문항 · 모의고사 25문항, 채점은 OMR 엑셀 한 번", [
        ("ta_12", "조교", "회차 고르기", "복습 테스트·모의고사 1~50회. 결과가 올라온 회차에 응시 인원이 보입니다."),
        ("ta_13", "조교", "OMR 엑셀 올리기 · 시험 평가", "채점기 엑셀(정답·배점·문항정보)을 올리고 난이도·킬러 문항·총평을 적습니다."),
        ("student_10", "학생", "시험 분석", "복습 테스트 / 모의고사 탭. 내 답안, 원점수, 반 평균, 예상 등급"),
        ("student_16", "학생", "오답 분석", "고른 선지로 틀린 이유를 짚습니다 (문항정보의 보기 함정)."),
        ("student_20", "학생", "등급 기준표 · 문항 지도", "석차·백분위·점수대 분포는 학생에게 보이지 않습니다."),
        ("student_27", "학생", "오답 노트", "틀린 문항마다 이유를 고르고 다시 풀어서 맞히면 표시"),
        ("student_29", "학생", "내 성적", "득점률 그래프. 점에 마우스를 올리면 점수·반 평균"),
    ]),
    ("복습 테스트 첨삭", "1:1 관리 · 복습 테스트 회차에서만", [
        ("student_12", "학생", "시험지 사진 올리기", "풀이가 적힌 시험지를 찍어 올립니다 (6장까지)."),
        ("ta_08", "조교", "첨삭 대기 목록", "올라온 순서대로. 점수와 사진 장수가 함께 보입니다."),
        ("ta_09", "조교", "문항별 첨삭", "OMR로 틀린 문항이 미리 표시됩니다. 오답 유형·메모·코멘트를 적고 저장"),
        ("teacher_21", "학부모", "학부모 리포트에 반영", "조교 코멘트와 틀린 이유가 학부모 리포트로 나갑니다."),
    ]),
    ("Full 모의고사 피드백", "1:1 관리 · 모의고사 회차에서만", [
        ("student_22", "학생", "모의고사 탭", "25문항 50점, 시험 평가와 내 답안"),
        ("student_24", "학생", "피드백 요청", "몇 번에서 막혔는지 풀이 사진과 함께 1:1로 묻습니다."),
        ("ta_10", "조교", "피드백 대기 목록", "학생·반·회차·점수"),
        ("ta_11", "조교", "답변", "틀린 문항 요약과 학생 사진을 보고 글·사진으로 답합니다. 학생은 이어서 물을 수 있습니다."),
    ]),
    ("질문과 답변", "질답 게시판 · 학습질문은 닉네임으로 공개", [
        ("student_06", "학생", "질답 게시판", "자주 묻는 질문, 유형별 목록, 내 질문"),
        ("student_08", "학생", "질문 · 사진", "문제 사진에 직접 필기해서 올립니다. 맞혔지만 확신 없는 문항도 묻습니다."),
        ("ta_02", "조교", "질문답변 목록", "유형·대단원 칩으로 거르기, 나를 지정한 상담"),
        ("ta_06", "조교", "답변 쓰기", "사진을 보고 답하고, 좋은 질문은 자주 묻는 질문으로 고정"),
    ]),
    ("수업 · 공지 · 일정", "선생님과 조교가 올리면 그 반 학생 화면에 쌓입니다", [
        ("teacher_11", "조교", "수업 기록 올리기", "반을 골라 판서 사진과 한 줄 정리"),
        ("student_33", "학생", "수업 기록", "날짜별 판서 사진"),
        ("teacher_17", "선생님", "공지 쓰기", "공지·과제·정오, 여러 반에 같이 올리기"),
        ("student_04", "학생", "공지", "읽음 표시와 좋아요"),
        ("teacher_25", "선생님", "주요 일정", "수능 D-day와 반별 휴강 기간"),
        ("student_34", "학생", "시간표", "D-day, 휴강 3주 전부터 안내, 휴강 주는 요일 칸에 '휴강'"),
    ]),
    ("학생 관리 · 학부모", "학생 한 명의 기록을 한 화면에", [
        ("teacher_20", "선생님", "학생 상세", "성적 추이(복테/모의 탭), 학부모 리포트 링크, 계정, 메모"),
        ("teacher_21", "학부모", "학부모 리포트", "로그인 없이 링크로 열립니다. 점수·반 평균·단원·틀린 이유·코멘트·출결"),
        ("teacher_23", "선생님", "성적 리포트", "인쇄·PDF용. 복습 테스트와 모의고사 칸을 나눔"),
    ]),
    ("공부 습관", "학생이 스스로 쓰는 도구", [
        ("student_40", "학생", "소도시 명상", "집중 타이머, 최근 4주 기록"),
        ("student_39", "학생", "통과 Quiz", "TOPIC별 개념 퀴즈"),
        ("student_38", "학생", "수능 영단어", "날마다 20단어, 게임 세 가지"),
        ("student_42", "학생", "내 공부", "오늘 요약, 주간 순위, 일별 이용 시간"),
        ("teacher_27", "선생님", "소도시 명상 현황", "반별 최근 7일 집중 시간"),
    ]),
    ("반 · 계정 운영", "선생님 전용은 조교 계정 관리", [
        ("teacher_15", "선생님", "반", "단과 4반 · 재종 4반"),
        ("teacher_16", "조교", "가입 코드", "반마다 학생 개별 가입 코드, 계정 일괄 발급"),
        ("teacher_28", "선생님", "가입 승인", "코드 없이 가입한 학생 확인"),
        ("teacher_30", "선생님", "조교 계정", "조교 추가, 월별 답변·첨삭 건수"),
        ("teacher_29", "선생님", "접근 기록", "누가 어떤 학생 정보를 봤는지"),
    ]),
]

used = sorted({s for _, _, steps in FLOWS for s, *_ in steps})
for s in used:
    im = Image.open(os.path.join(SCENES, s + ".jpg")).convert("RGB")
    im = im.crop((0, 0, im.width, im.height - 86))                 # 아래 자막 띠는 잘라 낸다 (카드에 설명이 있음)
    im.save(os.path.join(OUT, "img", s + ".jpg"), quality=80, optimize=True)

data = [{"title": t, "sub": sub, "steps": [{"img": f"img/{s}.jpg", "role": r, "title": tt, "desc": d} for s, r, tt, d in steps]}
        for t, sub, steps in FLOWS]
tpl = open(os.path.join(ROOT, "tools", "workflow_template.html"), encoding="utf-8").read()
page = tpl.replace("/*DATA*/null", json.dumps(data, ensure_ascii=False))
open(os.path.join(OUT, "artifact.html"), "w", encoding="utf-8").write(page)          # 아티팩트용 (머리는 게시할 때 붙는다)
HEAD = ('<!doctype html>\n<html lang="ko"><head><meta charset="utf-8">'
        '<meta name="viewport" content="width=device-width, initial-scale=1, viewport-fit=cover">\n')
open(os.path.join(OUT, "index.html"), "w", encoding="utf-8").write(HEAD + page + "\n</html>\n")   # PC에서 바로 여는 파일
print("scenes", len(used), "->", OUT)
