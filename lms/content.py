"""공지 분류, 외부 링크(강의 영상·뉴스) 검증 등 콘텐츠 관련 상수와 헬퍼."""
import re
from urllib.parse import urlparse

NOTICE_TAGS = ["공지", "정오", "일정", "시험", "자료"]
QUESTION_TYPES = ["학습질문", "행정문의"]
MAX_FOLLOWUPS = 2  # 답변 후 추가 질문 횟수

# 강의 영상은 이 사이트 링크만 허용 (임의 사이트로 학생을 보내지 않도록)
VIDEO_HOSTS = {"youtube.com", "www.youtube.com", "m.youtube.com", "youtu.be",
               "vimeo.com", "player.vimeo.com", "drive.google.com"}

_YT_ID = re.compile(r"^[A-Za-z0-9_-]{11}$")


def validate_https_url(url, allowed_hosts=None):
    url = (url or "").strip()
    if len(url) > 500:
        raise ValueError("주소가 너무 깁니다.")
    parsed = urlparse(url)
    if parsed.scheme != "https" or not parsed.hostname:
        raise ValueError("https:// 로 시작하는 주소를 입력하세요.")
    if allowed_hosts is not None and parsed.hostname.lower() not in allowed_hosts:
        raise ValueError("유튜브, 비메오, 구글 드라이브 링크만 등록할 수 있습니다.")
    return url


def youtube_id(url):
    parsed = urlparse(url)
    host = (parsed.hostname or "").lower()
    vid = None
    if host == "youtu.be":
        vid = parsed.path.lstrip("/").split("/")[0]
    elif host.endswith("youtube.com"):
        if parsed.path == "/watch":
            for part in parsed.query.split("&"):
                if part.startswith("v="):
                    vid = part[2:]
        elif parsed.path.startswith(("/embed/", "/shorts/", "/live/")):
            vid = parsed.path.split("/")[2]
    return vid if vid and _YT_ID.match(vid) else None


def host_of(url):
    return (urlparse(url).hostname or "").removeprefix("www.")


FILE_KINDS = {"pdf": "PDF", "ppt": "PPT", "pptx": "PPT", "docx": "DOC", "hwp": "HWP",
              "png": "IMG", "jpg": "IMG", "jpeg": "IMG"}


def file_kind(name):
    ext = name.rsplit(".", 1)[-1].lower() if "." in name else ""
    return FILE_KINDS.get(ext, "FILE")
