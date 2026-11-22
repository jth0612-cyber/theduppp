"""NAS 데모 사이트 폴더 만들기: _deploy/demo/student-lms-demo/ (코드 사본 + 새 instance + 데모 DB).

    python tools/make_demo.py 14

- lms/ 코드만 복사한다 (.venv, instance, 테스트 산출물 제외). 실제 instance·비밀키는 쓰지 않는다.
- 사본 안에서 seed_demo.py 를 돌려 새 비밀키·DB·업로드 사진을 만든다.
- docker-compose.yml 은 컨테이너 이름 student-lms-demo, 포트 127.0.0.1:8051 로 바꾼다.
"""
import os
import shutil
import subprocess
import sys

from PIL import Image, ImageDraw, ImageFont

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SRC = os.path.join(ROOT, "lms")
OUT = os.path.join(ROOT, "_deploy", "demo", "student-lms-demo")
PY = os.path.join(SRC, ".venv", "Scripts", "python.exe")

if os.path.exists(OUT):
    shutil.rmtree(OUT)
shutil.copytree(SRC, OUT, ignore=shutil.ignore_patterns(".venv", "instance", "__pycache__", "*.pyc", ".pytest_cache"))

# 사진 자리: 수업 노트·문제·풀이·시험지 (흰 종이 + 글자)
imgs = os.path.join(OUT, "_seed_img")
os.makedirs(imgs)
font = ImageFont.truetype("C:/Windows/Fonts/malgun.ttf", 34)
small = ImageFont.truetype("C:/Windows/Fonts/malgun.ttf", 24)
pages = {f"lesson{w}_{k}.png": (f"{w}주차 판서 {k}", "TOPIC 정리 · 예제 풀이") for w in range(1, 5) for k in (1, 2)}
pages.update({"question.png": ("LINE UP 문제 사진", "보기 ㄱ·ㄴ·ㄷ"), "solve.png": ("내 풀이", "전자 배치 그림 · 공유 전자쌍"),
              "paper1.png": ("복습 테스트 시험지 1쪽", "1~10번"), "paper2.png": ("복습 테스트 시험지 2쪽", "11~20번")})
for name, (title, sub) in pages.items():
    im = Image.new("RGB", (900, 1200), "#fbfaf6")
    d = ImageDraw.Draw(im)
    for y in range(160, 1200, 48):
        d.line([(60, y), (840, y)], fill="#e3e0d6", width=1)
    d.text((60, 60), title, fill="#1a1a1a", font=font)
    d.text((60, 120), sub, fill="#767676", font=small)
    im.save(os.path.join(imgs, name))

r = subprocess.run([PY, os.path.join(OUT, "seed_demo.py")] + sys.argv[1:], cwd=OUT)
shutil.rmtree(imgs)
compose = os.path.join(OUT, "docker-compose.yml")
s = open(compose, encoding="utf-8").read()
s = s.replace("container_name: student-lms", "container_name: student-lms-demo").replace("127.0.0.1:8050:8000", "127.0.0.1:8051:8000")
open(compose, "w", encoding="utf-8", newline="").write(s)
print("demo folder:", OUT)
sys.exit(r.returncode)
