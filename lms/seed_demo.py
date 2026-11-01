"""체험용 데모 DB 생성 (실제 데이터와 분리된 instance/demo.sqlite3 사용).

    python seed_demo.py
    set LMS_DATABASE=instance\\demo.sqlite3 && python app.py   (Windows cmd)

모든 학생 이름과 점수는 무작위로 만든 가짜 데이터입니다.
"""
import os
import random
import secrets

BASE = os.path.dirname(os.path.abspath(__file__))
DEMO_DB = os.path.join(BASE, "instance", "demo.sqlite3")
CRED_FILE = os.path.join(BASE, "instance", "DEMO_CREDENTIALS.txt")
os.environ["LMS_DATABASE"] = DEMO_DB

from app import create_app  # noqa: E402
from db import execute, get_db, nickname_taken  # noqa: E402
from nickname import generate_nickname  # noqa: E402
from security import encrypt, hash_password  # noqa: E402

LAST = "김이박최정강조윤장임한오서신권황안송류홍"
FIRST = ["민수", "서연", "지훈", "하은", "도윤", "지우", "예준", "수아", "시우", "지민", "현우", "채원", "준서", "다은", "건우", "유진"]


def main():
    if os.path.exists(DEMO_DB):
        os.remove(DEMO_DB)
    app = create_app()
    random.seed(7)
    with app.app_context():
        teacher_pw = "Demo-" + secrets.token_urlsafe(9)
        execute("INSERT INTO users (role, username, password_hash) VALUES ('teacher', 'demo', ?)",
                (hash_password(teacher_pw),))
        ta_pw = "Assist-" + secrets.token_urlsafe(9)
        execute("""INSERT INTO users (role, username, display_name, password_hash)
                   VALUES ('assistant', 'ta_demo', '김조교', ?)""", (hash_password(ta_pw),))
        student_pw = "Stud-" + secrets.token_urlsafe(9)
        db = get_db()
        no = 1000
        for cname in ["A반", "B반", "C반", "K반"]:
            cid = db.execute("INSERT INTO classes (name, description) VALUES (?, ?)",
                             (cname, "통합과학 · 데모")).lastrowid
            sids = []
            for _ in range(60):
                no += 1
                sid = db.execute("""INSERT INTO students (class_id, name, student_no, target, phone_enc)
                                    VALUES (?, ?, ?, ?, ?)""",
                                 (cid, random.choice(LAST) + random.choice(FIRST), f"D{no}",
                                  random.choice(["서울대", "연세대 의예", "고려대", "카이스트", ""]),
                                  encrypt(f"010-0000-{no:04d}"))).lastrowid
                sids.append(sid)
            for week in range(1, 7):
                eid = db.execute("""INSERT INTO exams (class_id, name, subject, exam_date, max_score)
                                    VALUES (?, ?, '통합과학', ?, 100)""",
                                 (cid, f"{week}주차 주간테스트", f"2026-09-{week * 4:02d}")).lastrowid
                for sid in sids:
                    db.execute("INSERT INTO scores (exam_id, student_id, score) VALUES (?, ?, ?)",
                               (eid, sid, max(0, min(100, round(random.gauss(68 + week * 2, 14))))))
            db.execute("INSERT INTO notices (class_id, title, body) VALUES (?, '이번 주 과제', '1단원 기출 20문항 풀어오기')", (cid,))
            db.execute("""INSERT INTO notices (class_id, tag, textbook, title, body)
                          VALUES (?, '정오', '개념서 1권', '42p 3번 보기 정오', '③ 보기의 \"공유 결합\"을 \"이온 결합\"으로 고칩니다.')""", (cid,))
            db.execute("""INSERT INTO videos (class_id, title, url, duration, expires_on)
                          VALUES (?, '원소의 생성 (3주차)', 'https://drive.google.com/file/d/demo/view', '71:11', '2026-12-31')""", (cid,))
        db.execute("""INSERT INTO news (title, url, source, summary) VALUES
                      ('2028 교과전형 과목 이수 조건 정리', 'https://news.example.com/2028', '교육신문',
                       '의약학 계열 지원 시 과학 과목 이수 조건을 미리 확인하세요.')""")
        db.execute("""INSERT INTO users (role, username, nickname, password_hash, student_id)
                      VALUES ('student', 'D1001', ?, ?, 1)""",
                   (generate_nickname(nickname_taken), hash_password(student_pw)))
        # 다른 학생들의 공개 질문 (게시판 체험용)
        samples = [("극한 문제 질문", "0/0 꼴에서 막혔어요"), ("치환적분 범위", "치환하면 적분 구간도 바꾸나요?"),
                   ("수열 귀납법", "n=k+1 단계가 이해가 안 돼요"), ("삼각함수 그래프", "주기 구하는 법 알려주세요"),
                   ("확률 독립", "독립과 배반의 차이가 헷갈려요")]
        for i, (title, body) in enumerate(samples):
            sid = 1 + i * 37
            if i:
                db.execute("""INSERT INTO users (role, username, nickname, password_hash, student_id)
                              SELECT 'student', student_no, ?, ?, id FROM students WHERE id = ?""",
                           (generate_nickname(nickname_taken), hash_password(secrets.token_urlsafe(16)), sid))
            qid = db.execute("INSERT INTO questions (student_id, title, body) VALUES (?, ?, ?)",
                             (sid, title, body)).lastrowid
            if i % 2:
                db.execute("INSERT INTO answers (question_id, author_id, body) VALUES (?, 1, '교재 3단원 예제를 다시 보세요.')", (qid,))
                db.execute("UPDATE questions SET status = 'answered' WHERE id = ?", (qid,))
        db.commit()
    with open(CRED_FILE, "w", encoding="utf-8") as fh:
        fh.write(f"데모 강사: demo / {teacher_pw}\n데모 조교: ta_demo / {ta_pw}\n데모 학생: D1001 / {student_pw}\n")
    print(f"데모 DB 생성 완료: {DEMO_DB}\n로그인 정보: {CRED_FILE}")


if __name__ == "__main__":
    main()
