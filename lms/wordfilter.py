"""욕설·비방어 거르기. 같이 공부의 칠판·역 노트처럼 다른 학생에게 보이는 짧은 글에 쓴다.

띄어쓰기·숫자·기호를 끼워 넣거나(시1발, 시 발) 영문을 섞어도 잡히도록 글자를 정리한 뒤 낱말 목록과 비교한다.
목록에 없는 말은 못 거르므로, 선생님 화면에서 글을 지울 수 있게 함께 둔다."""
import re
import unicodedata

# 정리한 글(한글·영문 소문자만 남김) 안에 들어 있으면 막는 낱말
_BAD = """
시발 씨발 씨빨 시빨 씨바 시바 씨팔 시팔 쓰발 쒸발 씹새 씹년 씹할 십새 십쌔 ㅅㅂ ㅆㅂ ㅅㅍ ㅆㅍ
병신 븅신 빙신 ㅂㅅ 좆 좃 존나 졸라 존니 ㅈㄴ 개새 개색 개샛 개세끼 새끼 색기 쌔끼 ㅅㄲ
미친놈 미친년 미친새 미친개 미쳤냐 ㅁㅊ 지랄 ㅈㄹ 닥쳐 엿먹 엠창 느금 느그엄마 니애미 니엄마 니미럴 애미 애비
호로새 호로자식 후레자식 등신 찐따 또라이 돌아이 정신병자 한남 김치녀 된장녀 틀딱 급식충 맘충 한녀
ㄲㅈ ㄷㅊ 꺼져라 꺼지셈 죽어버려 뒤질래 디질래 자살해
fuck fuk fck shit bitch bastard asshole
"""
BAD_WORDS = sorted({w for w in _BAD.split() if w}, key=len, reverse=True)
_JUNK = re.compile(r"[^0-9a-z가-힣ㄱ-ㅎㅏ-ㅣ]")
_LEET = str.maketrans({"1": "", "0": "", "!": "", "@": "a", "$": "s", "3": "", "8": "", "*": ""})


def _clean(text):
    t = unicodedata.normalize("NFC", text or "").lower()
    t = _JUNK.sub("", t)
    return t.translate(_LEET)


def bad_word(text):
    """걸린 낱말을 돌려준다. 깨끗하면 None."""
    t = _clean(text)
    for w in BAD_WORDS:
        if w in t:
            return w
    return None
