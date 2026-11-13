"""TOPIC에 딸린 개념 게임. 판(stage)마다 서버가 정답을 갖고 채점한다.

- neutral : TOPIC 24 중화 반응 — 염기를 몇 mL 넣어야 완전히 중화되는지 맞히고 BTB 색으로 확인
- redox   : TOPIC 23 산화 환원 — 반응식에서 산화되는 물질과 환원되는 물질 고르기
- shell   : TOPIC 07 전자 배치 — 원자 번호를 보고 껍질마다 전자 수 채우기
"""
import random

_rng = random.SystemRandom()
STAGES = 6


# ---------------------------------------------------------------- 중화 반응
def _neutral_stage():
    oh_per = _rng.choice([1, 2, 3])                     # NaOH 수용액 5 mL 속 OH⁻ 수
    k = _rng.randint(2, 6)                              # 완전 중화에 필요한 5 mL 묶음 수
    acid_ml = _rng.choice([10, 20])
    pub = {"acid_ml": acid_ml, "h": oh_per * k, "unit": 5, "oh": oh_per, "max_ml": 40}
    return pub, {"ml": 5 * k}


def _neutral_check(pub, ans, pick):
    if not isinstance(pick, int) or not 0 <= pick <= pub["max_ml"] or pick % pub["unit"]:
        return None
    oh = pick // pub["unit"] * pub["oh"]
    h = pub["h"]
    water = min(h, oh)
    left = {"H⁺": h - water, "OH⁻": oh - water, "Cl⁻": h, "Na⁺": oh}
    state = "중성" if h == oh else "산성" if h > oh else "염기성"
    color = {"중성": "초록", "산성": "노랑", "염기성": "파랑"}[state]
    ok = pick == ans["ml"]
    exp = (f"H⁺ {h}개에 OH⁻ {oh}개가 들어가 물이 {water}개 생겼어요. 남은 이온으로 {state}, BTB는 {color}색. "
           f"완전 중화하려면 OH⁻도 {h}개, 즉 {ans['ml']} mL가 필요해요.")
    return ok, {"state": state, "color": color, "left": left, "water": water, "answer": ans["ml"], "explanation": exp}


# ---------------------------------------------------------------- 산화 환원
# (반응물 [(화학식, 이름)], 생성물 [(화학식, 이름)], 산화: (반응물 칸, 생성물 칸, 표시), 환원: (…), 해설)
_O_UP, _O_DOWN = "산화(산소를 얻음)", "환원(산소를 잃음)"
_E_UP, _E_DOWN = "산화(전자를 잃음)", "환원(전자를 얻음)"
REDOX = [
    ([("2CuO", "산화 구리(Ⅱ)"), ("C", "탄소")], [("2Cu", "구리"), ("CO₂", "이산화 탄소")], (1, 1, _O_UP), (0, 0, _O_DOWN),
     "탄소는 산소를 얻어 이산화 탄소가 되고, 산화 구리(Ⅱ)는 산소를 잃어 구리가 돼요."),
    ([("Fe₂O₃", "산화 철(Ⅲ)"), ("3CO", "일산화 탄소")], [("2Fe", "철"), ("3CO₂", "이산화 탄소")], (1, 1, _O_UP), (0, 0, _O_DOWN),
     "철의 제련: 일산화 탄소는 산소를 얻고, 산화 철은 산소를 잃어 철이 돼요."),
    ([("CH₄", "메테인"), ("2O₂", "산소")], [("CO₂", "이산화 탄소"), ("2H₂O", "물")], (0, 0, _O_UP), (1, 1, "환원"),
     "연소: 메테인은 산소를 얻어 산화되고, 산소는 환원돼요."),
    ([("2Mg", "마그네슘"), ("O₂", "산소")], [("2MgO", "산화 마그네슘")], (0, 0, _O_UP), (1, 0, "환원"),
     "마그네슘은 산소와 결합해 산화돼요. 산소는 환원돼요."),
    ([("4Fe", "철"), ("3O₂", "산소")], [("2Fe₂O₃", "산화 철(Ⅲ)")], (0, 0, _O_UP), (1, 0, "환원"),
     "철이 녹스는 반응이에요. 철이 산소를 얻어 산화돼요."),
    ([("Zn", "아연"), ("Cu²⁺", "구리 이온")], [("Zn²⁺", "아연 이온"), ("Cu", "구리")], (0, 0, _E_UP), (1, 1, _E_DOWN),
     "아연은 전자를 잃어 아연 이온이 되고, 구리 이온은 전자를 얻어 구리로 석출돼요."),
    ([("Cu", "구리"), ("2Ag⁺", "은 이온")], [("Cu²⁺", "구리 이온"), ("2Ag", "은")], (0, 0, _E_UP), (1, 1, _E_DOWN),
     "구리는 전자를 잃고, 은 이온은 전자를 얻어 은으로 석출돼요."),
    ([("Mg", "마그네슘"), ("2H⁺", "수소 이온")], [("Mg²⁺", "마그네슘 이온"), ("H₂", "수소")], (0, 0, _E_UP), (1, 1, _E_DOWN),
     "금속과 산의 반응: 마그네슘은 전자를 잃고, 수소 이온은 전자를 얻어 수소 기체가 돼요."),
    ([("2Na", "나트륨"), ("Cl₂", "염소")], [("2NaCl", "염화 나트륨")], (0, 0, _E_UP), (1, 0, _E_DOWN),
     "나트륨은 전자를 잃어 나트륨 이온, 염소는 전자를 얻어 염화 이온이 돼요."),
    ([("6CO₂", "이산화 탄소"), ("6H₂O", "물")], [("C₆H₁₂O₆", "포도당"), ("6O₂", "산소")], (1, 1, "산화"), (0, 0, "환원"),
     "광합성: 이산화 탄소는 환원되어 포도당이 되고, 물은 산화되어 산소가 생겨요."),
    ([("C₆H₁₂O₆", "포도당"), ("6O₂", "산소")], [("6CO₂", "이산화 탄소"), ("6H₂O", "물")], (0, 0, "산화"), (1, 1, "환원"),
     "세포호흡: 포도당은 산화되어 이산화 탄소가 되고, 산소는 환원되어 물이 돼요."),
]


def _redox_stage(used):
    k = _rng.choice([i for i in range(len(REDOX)) if i not in used] or list(range(len(REDOX))))
    used.add(k)
    left, right, ox, red, exp = REDOX[k]
    return ({"left": [list(x) for x in left], "right": [list(x) for x in right]},
            {"ox": ox[0], "red": red[0], "ox_to": ox[1], "red_to": red[1], "ox_lab": ox[2], "red_lab": red[2], "exp": exp})


def _redox_check(pub, ans, pick):
    if not isinstance(pick, dict):
        return None
    ox, red = pick.get("ox"), pick.get("red")
    n = len(pub["left"])
    if not (isinstance(ox, int) and isinstance(red, int) and 0 <= ox < n and 0 <= red < n):
        return None
    ok = ox == ans["ox"] and red == ans["red"]
    return ok, {k: ans[k] for k in ("ox", "red", "ox_to", "red_to", "ox_lab", "red_lab")} | {"explanation": ans["exp"]}


# ---------------------------------------------------------------- 전자 배치
ATOMS = [(3, "리튬"), (4, "베릴륨"), (5, "붕소"), (6, "탄소"), (7, "질소"), (8, "산소"), (9, "플루오린"), (10, "네온"),
         (11, "나트륨"), (12, "마그네슘"), (13, "알루미늄"), (14, "규소"), (15, "인"), (16, "황"), (17, "염소"), (18, "아르곤"),
         (19, "칼륨"), (20, "칼슘")]


def shells_of(z):
    out, left = [], z
    for cap in (2, 8, 8, 2):
        if left <= 0:
            break
        out.append(min(cap, left))
        left -= cap
    return out


def _shell_stage(used):
    z, name = _rng.choice([a for a in ATOMS if a[0] not in used] or ATOMS)
    used.add(z)
    return {"z": z, "name": name, "shells": 4}, {"shells": shells_of(z)}


def _shell_check(pub, ans, pick):
    if not isinstance(pick, list) or len(pick) > 4 or not all(isinstance(x, int) and 0 <= x <= 8 for x in pick):
        return None
    mine = list(pick)
    while mine and mine[-1] == 0:
        mine.pop()
    right = ans["shells"]
    ok = mine == right
    val = right[-1]
    if val == 8 or (pub["z"] == 2):
        ion = "바깥 껍질이 다 차 있어 이온이 되지 않아요 (18족)."
    elif val <= 3:
        ion = f"전자를 {val}개 잃어 +{val} 양이온이 되기 쉬워요."
    else:
        ion = f"전자를 {8 - val}개 얻어 −{8 - val} 음이온이 되기 쉬워요." if val >= 5 else "주로 전자를 공유해 결합해요."
    exp = f"{pub['name']}(전자 {pub['z']}개): " + ", ".join(map(str, right)) + f". {len(right)}주기, 원자가 전자 {val}개. " + ion
    return ok, {"shells": right, "explanation": exp}


# ---------------------------------------------------------------- 묶음
GAMES = {
    "neutral": {"title": "중화 반응", "topic": "24", "ico": "pH",
                "intro": "묽은 염산에 수산화 나트륨 수용액을 5 mL씩 넣어요. 완전히 중화되는 양을 맞히세요.",
                "desc": "완전 중화되는 양 맞히기"},
    "redox": {"title": "산화 환원", "topic": "23", "ico": "e⁻",
              "intro": "반응식에서 산화되는 물질과 환원되는 물질을 고르세요.", "desc": "산화·환원되는 물질 고르기"},
    "shell": {"title": "전자 배치", "topic": "07", "ico": "2·8",
              "intro": "원자 번호를 보고 안쪽 껍질부터 전자를 채우세요. 2, 8, 8 순서예요.", "desc": "껍질마다 전자 채우기"},
}


def make_round(game):
    used = set()
    stages = []
    for _ in range(STAGES):
        if game == "neutral":
            stages.append(_neutral_stage())
        elif game == "redox":
            stages.append(_redox_stage(used))
        else:
            stages.append(_shell_stage(used))
    return [p for p, _ in stages], [a for _, a in stages]


def check(game, pub, ans, pick):
    return {"neutral": _neutral_check, "redox": _redox_check, "shell": _shell_check}[game](pub, ans, pick)
