"""데모 폴더(_deploy/demo/student-lms-demo)를 이 PC에서 띄운다: http://127.0.0.1:5060"""
import os
import sys

HERE = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "_deploy", "demo", "student-lms-demo")
os.environ["SESSION_COOKIE_SECURE"] = "0"
sys.path.insert(0, HERE)
os.chdir(HERE)
from app import create_app  # noqa: E402

create_app().run(host="127.0.0.1", port=5060, debug=False, threaded=True)
