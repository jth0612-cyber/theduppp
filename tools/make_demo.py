"""NAS 데모 사이트 폴더 만들기: _deploy/demo/student-lms-demo/ (코드 사본 + 새 instance + 데모 DB).

    python tools/make_demo.py 14

- lms/ 코드만 복사한다 (.venv, instance, 테스트 산출물 제외). 실제 instance·비밀키는 쓰지 않는다.
- 사본 안에서 seed_demo.py 를 돌려 새 비밀키·DB·업로드 사진을 만든다. 사진은 testfile/ 교재·시험지로 만든다.
- 이전 데모가 있으면 DEMO_CREDENTIALS.txt 의 비밀번호를 그대로 쓴다.
- docker-compose.yml 은 컨테이너 이름 student-lms-demo, 포트 127.0.0.1:8051 로 바꾼다.
"""
import json
import os
import re
import shutil
import subprocess
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SRC = os.path.join(ROOT, "lms")
OUT = os.path.join(ROOT, "_deploy", "demo", "student-lms-demo")
PY = os.path.join(SRC, ".venv", "Scripts", "python.exe")

keep = {}                                       # 이전 데모의 비밀번호를 그대로 쓴다 (사용자가 이미 알고 있는 값)
cred = os.path.join(OUT, "DEMO_CREDENTIALS.txt")
if os.path.exists(cred):
    for line in open(cred, encoding="utf-8"):
        m = re.search(r"(\S+) / (\S+)", line)
        if m:
            u, pw = m.groups()
            keep[{"master": "teacher", "ta_hanjisu": "ta", "ta_kimdoyun": "ta2"}.get(u, u)] = pw
if os.path.exists(OUT):
    shutil.rmtree(OUT)
shutil.copytree(SRC, OUT, ignore=shutil.ignore_patterns(".venv", "instance", "__pycache__", "*.pyc", ".pytest_cache"))

# 사진: tools/demo_photos.py 를 시스템 python 으로 띄워 testfile/ 교재·시험지에 학생 필기를 얹는다
env = dict(os.environ, DEMO_SYS_PY=sys.executable, DEMO_PHOTOS=os.path.join(ROOT, "tools", "demo_photos.py"),
           DEMO_PDF=os.path.join(ROOT, "testfile"), DEMO_KEEP_PW=json.dumps(keep), PYTHONIOENCODING="utf-8")
r = subprocess.run([PY, os.path.join(OUT, "seed_demo.py")] + sys.argv[1:], cwd=OUT, env=env)
compose = os.path.join(OUT, "docker-compose.yml")
s = open(compose, encoding="utf-8").read()
s = s.replace("container_name: student-lms", "container_name: student-lms-demo").replace("127.0.0.1:8050:8000", "127.0.0.1:8051:8000")
# 실제 사이트 .env 의 공개 설정 중 화면에 보이는 것 (비밀번호 분실 문의 링크)
s = s.replace('      TZ: Asia/Seoul\n', '      TZ: Asia/Seoul\n      KAKAO_OPENCHAT_URL: "https://open.kakao.com/o/st9eKfYi"\n')
open(compose, "w", encoding="utf-8", newline="").write(s)
print("demo folder:", OUT)
sys.exit(r.returncode)
