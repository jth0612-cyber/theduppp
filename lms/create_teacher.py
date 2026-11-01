"""강사(관리자) 계정 생성: python create_teacher.py"""
import getpass
import sys

from app import create_app
from db import execute, query
from security import hash_password, password_problem


def main():
    app = create_app()
    with app.app_context():
        username = input("강사 아이디: ").strip()
        if not username:
            sys.exit("아이디를 입력하세요.")
        if query("SELECT 1 FROM users WHERE username = ?", (username,), one=True):
            sys.exit("이미 있는 아이디입니다.")
        pw = getpass.getpass("비밀번호: ")
        problem = password_problem(pw)
        if problem:
            sys.exit(problem)
        if pw != getpass.getpass("비밀번호 확인: "):
            sys.exit("비밀번호가 일치하지 않습니다.")
        execute("INSERT INTO users (role, username, password_hash) VALUES ('teacher', ?, ?)",
                (username, hash_password(pw)))
        print(f"강사 계정 '{username}' 을(를) 만들었습니다.")


if __name__ == "__main__":
    main()
