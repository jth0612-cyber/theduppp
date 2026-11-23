"""데모 폴더(_deploy/demo/student-lms-demo)를 이 PC에서 띄운다: http://127.0.0.1:5077"""
import os
import re
import sys

HERE = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "_deploy", "demo", "student-lms-demo")
os.environ["SESSION_COOKIE_SECURE"] = "0"
# NAS 데모와 같은 공개 설정 (로그인 화면의 오픈채팅 안내 등): docker-compose.yml 의 environment 값을 그대로 쓴다
compose = open(os.path.join(HERE, "docker-compose.yml"), encoding="utf-8").read()
for k, v in re.findall(r'^\s+(KAKAO_OPENCHAT_URL):\s*"?([^"\r\n]+)"?', compose, re.M):
    os.environ.setdefault(k, v.strip())
sys.path.insert(0, HERE)
os.chdir(HERE)
from app import create_app  # noqa: E402

create_app().run(host="127.0.0.1", port=5077, debug=False, threaded=True)
