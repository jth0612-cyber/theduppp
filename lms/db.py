"""SQLite 연결과 스키마. 모든 쿼리는 파라미터 바인딩(?)만 사용한다."""
import sqlite3

from flask import current_app, g

# role: teacher(강사), assistant(조교: 질문답변만), student(학생)
USERS_COLUMNS = """
    id              INTEGER PRIMARY KEY,
    role            TEXT NOT NULL CHECK (role IN ('teacher', 'assistant', 'student')),
    username        TEXT NOT NULL UNIQUE,
    nickname        TEXT,
    display_name    TEXT NOT NULL DEFAULT '',
    password_hash   TEXT NOT NULL,
    student_id      INTEGER REFERENCES students(id) ON DELETE CASCADE,
    must_change_pw  INTEGER NOT NULL DEFAULT 0,
    disabled        INTEGER NOT NULL DEFAULT 0,
    failed_attempts INTEGER NOT NULL DEFAULT 0,
    locked_until    TEXT,
    last_login_at   TEXT,
    created_at      TEXT NOT NULL DEFAULT (datetime('now', 'localtime'))
"""

# 소유자 계정이 지워져도 파일은 남는다 (학습 기록 유지. 파일 자체는 학생 영구 삭제 때 지움)
FILES_COLUMNS = """
    id            INTEGER PRIMARY KEY,
    stored_name   TEXT NOT NULL UNIQUE,
    original_name TEXT NOT NULL,
    mime          TEXT NOT NULL,
    size          INTEGER NOT NULL,
    owner_id      INTEGER REFERENCES users(id) ON DELETE SET NULL,
    created_at    TEXT NOT NULL DEFAULT (datetime('now', 'localtime'))
"""

SCHEMA = """
PRAGMA foreign_keys = ON;

CREATE TABLE IF NOT EXISTS users (""" + USERS_COLUMNS + """);

CREATE TABLE IF NOT EXISTS classes (
    id          INTEGER PRIMARY KEY,
    name        TEXT NOT NULL,
    description TEXT NOT NULL DEFAULT '',
    archived    INTEGER NOT NULL DEFAULT 0,
    join_code   TEXT,
    join_open   INTEGER NOT NULL DEFAULT 1,
    created_at  TEXT NOT NULL DEFAULT (datetime('now', 'localtime'))
);

-- phone_enc / memo_enc 는 Fernet 으로 암호화된 값
CREATE TABLE IF NOT EXISTS students (
    id          INTEGER PRIMARY KEY,
    class_id    INTEGER NOT NULL REFERENCES classes(id) ON DELETE CASCADE,
    name        TEXT NOT NULL,
    student_no  TEXT NOT NULL UNIQUE,
    target      TEXT NOT NULL DEFAULT '',
    phone_enc   TEXT,
    memo_enc    TEXT,
    active      INTEGER NOT NULL DEFAULT 1,
    created_at  TEXT NOT NULL DEFAULT (datetime('now', 'localtime'))
);
CREATE INDEX IF NOT EXISTS idx_students_class ON students(class_id);
CREATE INDEX IF NOT EXISTS idx_students_name ON students(name);

CREATE TABLE IF NOT EXISTS exams (
    id          INTEGER PRIMARY KEY,
    class_id    INTEGER NOT NULL REFERENCES classes(id) ON DELETE CASCADE,
    name        TEXT NOT NULL,
    subject     TEXT NOT NULL DEFAULT '',
    exam_date   TEXT NOT NULL,
    max_score   REAL NOT NULL DEFAULT 100,
    created_at  TEXT NOT NULL DEFAULT (datetime('now', 'localtime'))
);
CREATE INDEX IF NOT EXISTS idx_exams_class ON exams(class_id);

CREATE TABLE IF NOT EXISTS scores (
    id          INTEGER PRIMARY KEY,
    exam_id     INTEGER NOT NULL REFERENCES exams(id) ON DELETE CASCADE,
    student_id  INTEGER NOT NULL REFERENCES students(id) ON DELETE CASCADE,
    score       REAL NOT NULL,
    UNIQUE (exam_id, student_id)
);
CREATE INDEX IF NOT EXISTS idx_scores_student ON scores(student_id);

-- 학습/상담 메모 (본문 암호화)
CREATE TABLE IF NOT EXISTS notes (
    id          INTEGER PRIMARY KEY,
    student_id  INTEGER NOT NULL REFERENCES students(id) ON DELETE CASCADE,
    category    TEXT NOT NULL DEFAULT '학습',
    body_enc    TEXT NOT NULL,
    created_at  TEXT NOT NULL DEFAULT (datetime('now', 'localtime'))
);
CREATE INDEX IF NOT EXISTS idx_notes_student ON notes(student_id);

CREATE TABLE IF NOT EXISTS questions (
    id          INTEGER PRIMARY KEY,
    student_id  INTEGER NOT NULL REFERENCES students(id) ON DELETE CASCADE,
    title       TEXT NOT NULL,
    body        TEXT NOT NULL,
    image_id    INTEGER REFERENCES files(id) ON DELETE SET NULL,
    qtype       TEXT NOT NULL DEFAULT '학습질문',
    status      TEXT NOT NULL DEFAULT 'open' CHECK (status IN ('open', 'answered')),
    created_at  TEXT NOT NULL DEFAULT (datetime('now', 'localtime'))
);
CREATE INDEX IF NOT EXISTS idx_questions_status ON questions(status);

CREATE TABLE IF NOT EXISTS answers (
    id           INTEGER PRIMARY KEY,
    question_id  INTEGER NOT NULL REFERENCES questions(id) ON DELETE CASCADE,
    author_id    INTEGER NOT NULL REFERENCES users(id),
    body         TEXT NOT NULL,
    created_at   TEXT NOT NULL DEFAULT (datetime('now', 'localtime'))
);

CREATE TABLE IF NOT EXISTS notices (
    id          INTEGER PRIMARY KEY,
    class_id    INTEGER NOT NULL REFERENCES classes(id) ON DELETE CASCADE,
    tag         TEXT NOT NULL DEFAULT '공지',
    textbook    TEXT NOT NULL DEFAULT '',
    title       TEXT NOT NULL,
    body        TEXT NOT NULL,
    created_at  TEXT NOT NULL DEFAULT (datetime('now', 'localtime'))
);

-- 업로드 파일은 웹 루트 밖(instance/uploads)에 무작위 이름으로 저장
CREATE TABLE IF NOT EXISTS files (""" + FILES_COLUMNS + """);

CREATE TABLE IF NOT EXISTS materials (
    id          INTEGER PRIMARY KEY,
    class_id    INTEGER NOT NULL REFERENCES classes(id) ON DELETE CASCADE,
    title       TEXT NOT NULL,
    file_id     INTEGER NOT NULL REFERENCES files(id),
    created_at  TEXT NOT NULL DEFAULT (datetime('now', 'localtime'))
);

-- 답변 뒤 학생의 추가 질문 (작성자는 질문한 학생)
CREATE TABLE IF NOT EXISTS followups (
    id          INTEGER PRIMARY KEY,
    question_id INTEGER NOT NULL REFERENCES questions(id) ON DELETE CASCADE,
    body        TEXT NOT NULL,
    image_id    INTEGER REFERENCES files(id) ON DELETE SET NULL,
    created_at  TEXT NOT NULL DEFAULT (datetime('now', 'localtime'))
);
CREATE INDEX IF NOT EXISTS idx_followups_question ON followups(question_id);

-- 강의 영상은 파일을 직접 올리지 않고 외부(유튜브 일부공개 등) 링크 + 만료일로 관리
CREATE TABLE IF NOT EXISTS videos (
    id          INTEGER PRIMARY KEY,
    class_id    INTEGER NOT NULL REFERENCES classes(id) ON DELETE CASCADE,
    title       TEXT NOT NULL,
    url         TEXT NOT NULL,
    duration    TEXT NOT NULL DEFAULT '',
    expires_on  TEXT,
    created_at  TEXT NOT NULL DEFAULT (datetime('now', 'localtime'))
);

-- 학생 접속일 (출석 관리용이 아니라 학생 본인의 학습 연속 기록용)
CREATE TABLE IF NOT EXISTS visits (
    user_id     INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    day         TEXT NOT NULL,
    PRIMARY KEY (user_id, day)
);

-- 미니게임 한 판. 정답(answer)은 서버에만 두고 채점도 서버에서 한다
CREATE TABLE IF NOT EXISTS game_rounds (
    id          INTEGER PRIMARY KEY,
    user_id     INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    game        TEXT NOT NULL,
    topic       TEXT NOT NULL DEFAULT '',
    payload     TEXT NOT NULL,
    answer      TEXT NOT NULL,
    score       INTEGER,
    total       INTEGER,
    started_at  TEXT NOT NULL,
    finished_at TEXT
);
CREATE INDEX IF NOT EXISTS idx_game_rounds_user ON game_rounds(user_id, started_at);

CREATE TABLE IF NOT EXISTS news (
    id          INTEGER PRIMARY KEY,
    title       TEXT NOT NULL,
    url         TEXT NOT NULL,
    source      TEXT NOT NULL DEFAULT '',
    summary     TEXT NOT NULL DEFAULT '',
    created_at  TEXT NOT NULL DEFAULT (datetime('now', 'localtime'))
);

-- 학생 회원가입 신청. 선생님이 승인하면 students/users 로 옮기고 이 행은 지운다
CREATE TABLE IF NOT EXISTS signup_requests (
    id            INTEGER PRIMARY KEY,
    class_id      INTEGER NOT NULL REFERENCES classes(id) ON DELETE CASCADE,
    name          TEXT NOT NULL,
    student_no    TEXT NOT NULL UNIQUE,
    password_hash TEXT NOT NULL,
    consent_at    TEXT NOT NULL,
    ip            TEXT NOT NULL DEFAULT '',
    created_at    TEXT NOT NULL DEFAULT (datetime('now', 'localtime'))
);

CREATE TABLE IF NOT EXISTS audit_log (
    id          INTEGER PRIMARY KEY,
    user_id     INTEGER,
    username    TEXT,
    action      TEXT NOT NULL,
    target      TEXT NOT NULL DEFAULT '',
    ip          TEXT NOT NULL DEFAULT '',
    created_at  TEXT NOT NULL DEFAULT (datetime('now', 'localtime'))
);
CREATE INDEX IF NOT EXISTS idx_audit_created ON audit_log(created_at);
-- ---------- 교재 분석실 ----------
-- 교재 (이용 기간이 끝나면 분석실을 볼 수 없다)
CREATE TABLE IF NOT EXISTS books (
    id          INTEGER PRIMARY KEY,
    title       TEXT NOT NULL,
    subject     TEXT NOT NULL DEFAULT '',
    expires_on  TEXT NOT NULL,
    is_free     INTEGER NOT NULL DEFAULT 0,
    notice      TEXT NOT NULL DEFAULT '',
    created_at  TEXT NOT NULL DEFAULT (datetime('now', 'localtime'))
);

-- 교재 인증 코드. max_uses 가 NULL 이면 여러 명이 쓰는 배포 코드
CREATE TABLE IF NOT EXISTS book_codes (
    id          INTEGER PRIMARY KEY,
    book_id     INTEGER NOT NULL REFERENCES books(id) ON DELETE CASCADE,
    code        TEXT NOT NULL UNIQUE,
    max_uses    INTEGER,
    uses        INTEGER NOT NULL DEFAULT 0,
    created_at  TEXT NOT NULL DEFAULT (datetime('now', 'localtime'))
);
CREATE INDEX IF NOT EXISTS idx_book_codes_book ON book_codes(book_id);

CREATE TABLE IF NOT EXISTS user_books (
    user_id       INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    book_id       INTEGER NOT NULL REFERENCES books(id) ON DELETE CASCADE,
    code_id       INTEGER REFERENCES book_codes(id) ON DELETE SET NULL,
    registered_at TEXT NOT NULL DEFAULT (datetime('now', 'localtime')),
    PRIMARY KEY (user_id, book_id)
);

-- 교재의 회차(모의고사). answer_key / points 는 JSON 배열, 서버에만 둔다
CREATE TABLE IF NOT EXISTS mocks (
    id          INTEGER PRIMARY KEY,
    book_id     INTEGER NOT NULL REFERENCES books(id) ON DELETE CASCADE,
    round_no    INTEGER NOT NULL,
    title       TEXT NOT NULL DEFAULT '',
    n_items     INTEGER NOT NULL,
    full_score  REAL NOT NULL,
    answer_key  TEXT NOT NULL,
    points      TEXT NOT NULL,
    open        INTEGER NOT NULL DEFAULT 1,
    created_at  TEXT NOT NULL DEFAULT (datetime('now', 'localtime')),
    UNIQUE (book_id, round_no)
);

-- 가채점 제출. mode: answers(답안 입력) / score(점수만 입력). 답안이 다 차야 score 가 생긴다
CREATE TABLE IF NOT EXISTS mock_entries (
    id          INTEGER PRIMARY KEY,
    mock_id     INTEGER NOT NULL REFERENCES mocks(id) ON DELETE CASCADE,
    user_id     INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    mode        TEXT NOT NULL CHECK (mode IN ('answers', 'score')),
    answers     TEXT NOT NULL DEFAULT '',
    score       REAL,
    updated_at  TEXT NOT NULL DEFAULT (datetime('now', 'localtime')),
    UNIQUE (mock_id, user_id)
);

-- ---------- 공부 도구 ----------
-- 오답 노트: 모의고사에서 틀린 문항의 복습 상태와 틀린 이유
CREATE TABLE IF NOT EXISTS wrong_notes (
    user_id     INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    mock_id     INTEGER NOT NULL REFERENCES mocks(id) ON DELETE CASCADE,
    item_no     INTEGER NOT NULL,
    reason      TEXT NOT NULL DEFAULT '',
    memo        TEXT NOT NULL DEFAULT '',
    reviewed_at TEXT,
    PRIMARY KEY (user_id, mock_id, item_no)
);

-- 개념 카드 묶음과 카드, 학생별 표시(known/unsure)
CREATE TABLE IF NOT EXISTS decks (
    id          INTEGER PRIMARY KEY,
    title       TEXT NOT NULL,
    unit        TEXT NOT NULL DEFAULT '',
    class_id    INTEGER REFERENCES classes(id) ON DELETE CASCADE,
    created_at  TEXT NOT NULL DEFAULT (datetime('now', 'localtime'))
);
CREATE TABLE IF NOT EXISTS cards (
    id          INTEGER PRIMARY KEY,
    deck_id     INTEGER NOT NULL REFERENCES decks(id) ON DELETE CASCADE,
    front       TEXT NOT NULL,
    back        TEXT NOT NULL,
    pos         INTEGER NOT NULL DEFAULT 0
);
CREATE INDEX IF NOT EXISTS idx_cards_deck ON cards(deck_id);
CREATE TABLE IF NOT EXISTS card_marks (
    user_id     INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    card_id     INTEGER NOT NULL REFERENCES cards(id) ON DELETE CASCADE,
    status      TEXT NOT NULL CHECK (status IN ('known', 'unsure')),
    updated_at  TEXT NOT NULL DEFAULT (datetime('now', 'localtime')),
    PRIMARY KEY (user_id, card_id)
);

-- 반별 주간 시간표, 사이트 설정(수능일 등)
CREATE TABLE IF NOT EXISTS timetable (
    id          INTEGER PRIMARY KEY,
    class_id    INTEGER NOT NULL REFERENCES classes(id) ON DELETE CASCADE,
    weekday     INTEGER NOT NULL CHECK (weekday BETWEEN 0 AND 6),
    starts      TEXT NOT NULL,
    ends        TEXT NOT NULL,
    title       TEXT NOT NULL,
    room        TEXT NOT NULL DEFAULT ''
);
CREATE TABLE IF NOT EXISTS settings (
    key         TEXT PRIMARY KEY,
    value       TEXT NOT NULL
);

-- 과제와 제출
CREATE TABLE IF NOT EXISTS assignments (
    id          INTEGER PRIMARY KEY,
    class_id    INTEGER NOT NULL REFERENCES classes(id) ON DELETE CASCADE,
    title       TEXT NOT NULL,
    body        TEXT NOT NULL DEFAULT '',
    due_on      TEXT,
    created_at  TEXT NOT NULL DEFAULT (datetime('now', 'localtime'))
);
CREATE TABLE IF NOT EXISTS submissions (
    id            INTEGER PRIMARY KEY,
    assignment_id INTEGER NOT NULL REFERENCES assignments(id) ON DELETE CASCADE,
    student_id    INTEGER NOT NULL REFERENCES students(id) ON DELETE CASCADE,
    file_id       INTEGER REFERENCES files(id) ON DELETE SET NULL,
    note          TEXT NOT NULL DEFAULT '',
    status        TEXT NOT NULL DEFAULT 'submitted' CHECK (status IN ('submitted', 'checked', 'redo')),
    comment       TEXT NOT NULL DEFAULT '',
    submitted_at  TEXT NOT NULL DEFAULT (datetime('now', 'localtime')),
    checked_at    TEXT,
    UNIQUE (assignment_id, student_id)
);

-- 함께 공부하는 장소(산사·노천탕·역·찻집): 지금 있는 사람, 집중 기록, 남기고 간 글
CREATE TABLE IF NOT EXISTS room_presence (
    user_id     INTEGER PRIMARY KEY REFERENCES users(id) ON DELETE CASCADE,
    place       TEXT NOT NULL,
    status      TEXT NOT NULL DEFAULT 'rest' CHECK (status IN ('focus', 'rest')),
    focus_since TEXT,
    plan_min    INTEGER NOT NULL DEFAULT 25,
    last_seen   TEXT NOT NULL DEFAULT (datetime('now', 'localtime'))
);
CREATE TABLE IF NOT EXISTS focus_logs (
    id          INTEGER PRIMARY KEY,
    user_id     INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    place       TEXT NOT NULL,
    minutes     INTEGER NOT NULL,
    ended_at    TEXT NOT NULL DEFAULT (datetime('now', 'localtime'))
);
CREATE INDEX IF NOT EXISTS idx_focus_user ON focus_logs(user_id, ended_at);
-- 학생끼리 팔로우 (닉네임으로만 보인다)
CREATE TABLE IF NOT EXISTS follows (
    follower_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    followee_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    created_at  TEXT NOT NULL DEFAULT (datetime('now', 'localtime')),
    PRIMARY KEY (follower_id, followee_id),
    CHECK (follower_id != followee_id)
);
CREATE INDEX IF NOT EXISTS idx_follows_followee ON follows(followee_id);
CREATE INDEX IF NOT EXISTS idx_focus_place ON focus_logs(place, ended_at);
CREATE TABLE IF NOT EXISTS room_notes (
    id          INTEGER PRIMARY KEY,
    place       TEXT NOT NULL,
    user_id     INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    body        TEXT NOT NULL,
    created_at  TEXT NOT NULL DEFAULT (datetime('now', 'localtime'))
);
CREATE INDEX IF NOT EXISTS idx_room_notes_place ON room_notes(place, created_at);

-- 웹 푸시 구독 (브라우저마다 하나)
CREATE TABLE IF NOT EXISTS push_subs (
    id          INTEGER PRIMARY KEY,
    user_id     INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    endpoint    TEXT NOT NULL UNIQUE,
    p256dh      TEXT NOT NULL,
    auth        TEXT NOT NULL,
    created_at  TEXT NOT NULL DEFAULT (datetime('now', 'localtime'))
);

-- 공지 좋아요 (한 사람 한 번)
CREATE TABLE IF NOT EXISTS notice_likes (
    notice_id   INTEGER NOT NULL REFERENCES notices(id) ON DELETE CASCADE,
    user_id     INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    PRIMARY KEY (notice_id, user_id)
);
"""



def get_db():
    if "db" not in g:
        g.db = sqlite3.connect(current_app.config["DATABASE"])
        g.db.row_factory = sqlite3.Row
        g.db.execute("PRAGMA foreign_keys = ON")
    return g.db


def close_db(_exc=None):
    db = g.pop("db", None)
    if db is not None:
        db.close()


def init_db(path):
    from nickname import generate_nickname

    conn = sqlite3.connect(path)
    conn.executescript(SCHEMA)
    # 기존 DB 이전: 새로 생긴 열 추가
    _add_column(conn, "users", "nickname", "TEXT")
    _add_column(conn, "users", "display_name", "TEXT NOT NULL DEFAULT ''")
    _add_column(conn, "users", "disabled", "INTEGER NOT NULL DEFAULT 0")
    _allow_assistant_role(conn)
    _release_file_owner(conn)
    _add_column(conn, "questions", "qtype", "TEXT NOT NULL DEFAULT '학습질문'")
    _add_column(conn, "notices", "tag", "TEXT NOT NULL DEFAULT '공지'")
    _add_column(conn, "notices", "textbook", "TEXT NOT NULL DEFAULT ''")
    _add_column(conn, "classes", "join_code", "TEXT")
    _add_column(conn, "classes", "join_open", "INTEGER NOT NULL DEFAULT 1")
    # Google 계정 연결, 한 기기 로그인(학생), 공지 고정·조회수
    _add_column(conn, "users", "google_sub", "TEXT")
    _add_column(conn, "signup_requests", "google_sub", "TEXT")
    _add_column(conn, "signup_requests", "google_email", "TEXT")
    _add_column(conn, "users", "google_email", "TEXT")
    _add_column(conn, "users", "session_version", "INTEGER NOT NULL DEFAULT 0")
    conn.execute("CREATE UNIQUE INDEX IF NOT EXISTS idx_users_google_sub ON users(google_sub)")
    _add_column(conn, "notices", "pinned", "INTEGER NOT NULL DEFAULT 0")
    _add_column(conn, "notices", "views", "INTEGER NOT NULL DEFAULT 0")
    conn.execute("CREATE UNIQUE INDEX IF NOT EXISTS idx_classes_join_code ON classes(join_code)")
    # 자주 묻는 질문(FAQ)으로 고정
    _add_column(conn, "questions", "faq", "INTEGER NOT NULL DEFAULT 0")
    _add_column(conn, "timetable", "room", "TEXT NOT NULL DEFAULT ''")
    # 3D 같이 공부: 위치·자세·캐릭터 색
    _add_column(conn, "room_presence", "px", "REAL NOT NULL DEFAULT 0")
    _add_column(conn, "room_presence", "pz", "REAL NOT NULL DEFAULT 0")
    _add_column(conn, "room_presence", "ry", "REAL NOT NULL DEFAULT 0")
    _add_column(conn, "room_presence", "pose", "TEXT NOT NULL DEFAULT 'stand'")
    _add_column(conn, "room_presence", "seat", "INTEGER")
    _add_column(conn, "users", "avatar_color", "TEXT")
    code_taken = lambda c: conn.execute("SELECT 1 FROM classes WHERE join_code = ?", (c,)).fetchone() is not None
    for (cid,) in conn.execute("SELECT id FROM classes WHERE join_code IS NULL").fetchall():
        conn.execute("UPDATE classes SET join_code = ? WHERE id = ?", (new_join_code(code_taken), cid))
    # 닉네임 없는 학생 계정에 채워 넣기
    conn.execute("CREATE UNIQUE INDEX IF NOT EXISTS idx_users_nickname ON users(nickname)")
    taken = lambda nick: conn.execute("SELECT 1 FROM users WHERE nickname = ?", (nick,)).fetchone() is not None
    for (uid,) in conn.execute("SELECT id FROM users WHERE role = 'student' AND nickname IS NULL").fetchall():
        conn.execute("UPDATE users SET nickname = ? WHERE id = ?", (generate_nickname(taken), uid))
    conn.commit()
    conn.close()


def _rebuild_table(conn, table, columns):
    """SQLite 는 CHECK·외래키를 바꿀 수 없으므로 표를 새로 만들어 데이터를 옮긴다."""
    conn.commit()
    conn.execute("PRAGMA foreign_keys = OFF")
    col_list = ", ".join(row[1] for row in conn.execute(f"PRAGMA table_info({table})"))
    conn.executescript(f"""
        BEGIN;
        CREATE TABLE {table}_new ({columns});
        INSERT INTO {table}_new ({col_list}) SELECT {col_list} FROM {table};
        DROP TABLE {table};
        ALTER TABLE {table}_new RENAME TO {table};
        COMMIT;
    """)
    conn.execute("PRAGMA foreign_keys = ON")


def _table_sql(conn, table):
    return conn.execute("SELECT sql FROM sqlite_master WHERE type = 'table' AND name = ?", (table,)).fetchone()[0]


def _allow_assistant_role(conn):
    """예전 DB 는 users.role 에 'assistant' 가 없다."""
    if "'assistant'" not in _table_sql(conn, "users"):
        _rebuild_table(conn, "users", USERS_COLUMNS)


def _release_file_owner(conn):
    """예전 DB 는 파일을 올린 학생의 계정을 지우려 하면 외래키 오류가 났다."""
    if "ON DELETE SET NULL" not in _table_sql(conn, "files"):
        _rebuild_table(conn, "files", FILES_COLUMNS)


def _add_column(conn, table, column, ddl):
    cols = {row[1] for row in conn.execute(f"PRAGMA table_info({table})")}
    if column not in cols:
        conn.execute(f"ALTER TABLE {table} ADD COLUMN {column} {ddl}")


# 헷갈리는 글자(0/O, 1/I/L)를 뺀 대문자·숫자 8자리 → 약 1조 가지
_JOIN_ALPHABET = "ABCDEFGHJKMNPQRSTUVWXYZ23456789"


def new_join_code(is_taken):
    import secrets
    while True:
        code = "".join(secrets.choice(_JOIN_ALPHABET) for _ in range(8))
        if not is_taken(code):
            return code


def join_code_taken(code):
    return query("SELECT 1 FROM classes WHERE join_code = ?", (code,), one=True) is not None


def nickname_taken(nick):
    return query("SELECT 1 FROM users WHERE nickname = ?", (nick,), one=True) is not None


def query(sql, args=(), one=False):
    cur = get_db().execute(sql, args)
    rows = cur.fetchall()
    cur.close()
    return (rows[0] if rows else None) if one else rows


def execute(sql, args=()):
    db = get_db()
    cur = db.execute(sql, args)
    db.commit()
    return cur.lastrowid


def get_setting(key, default=""):
    row = query("SELECT value FROM settings WHERE key = ?", (key,), one=True)
    return row["value"] if row else default


def set_setting(key, value):
    execute("INSERT INTO settings (key, value) VALUES (?, ?) ON CONFLICT(key) DO UPDATE SET value = excluded.value",
            (key, value))
