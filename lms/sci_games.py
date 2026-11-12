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
# (반응식 조각, 반응물 후보, 산화되는 반응물, 환원되는 반응물, 해설)
REDOX = [
    ("2CuO + C → 2Cu + CO₂", ["CuO", "C"], "C", "CuO", "C는 산소를 얻어 CO₂가 되고(산화), CuO는 산소를 잃어 Cu가 돼요(환원)."),
    ("Fe₂O₃ + 3CO → 2Fe + 3CO₂", ["Fe₂O₃", "CO"], "CO", "Fe₂O₃", "철의 제련: CO는 산소를 얻고, 산화 철은 산소를 잃어 철이 돼요."),
    ("CH₄ + 2O₂ → CO₂ + 2H₂O", ["CH₄", "O₂"], "CH₄", "O₂", "연소: 메테인은 산소를 얻어 산화되고, 산소는 환원돼요."),
    ("2Mg + O₂ → 2MgO", ["Mg", "O₂"], "Mg", "O₂", "마그네슘은 산소를 얻고 전자를 잃어 산화돼요."),
    ("4Fe + 3O₂ → 2Fe₂O₃", ["Fe", "O₂"], "Fe", "O₂", "철이 녹스는 반응이에요. 철이 산소를 얻어 산화돼요."),
    ("Zn + Cu²⁺ → Zn²⁺ + Cu", ["Zn", "Cu²⁺"], "Zn", "Cu²⁺", "아연은 전자를 잃어 Zn²⁺(산화), 구리 이온은 전자를 얻어 Cu로 석출돼요(환원)."),
    ("Cu + 2Ag⁺ → Cu²⁺ + 2Ag", ["Cu", "Ag⁺"], "Cu", "Ag⁺", "구리는 전자를 잃고, 은 이온은 전자를 얻어 은으로 석출돼요."),
    ("Mg + 2H⁺ → Mg²⁺ + H₂", ["Mg", "H⁺"], "Mg", "H⁺", "금속과 산의 반응: 마그네슘이 전자를 잃고 수소 이온이 전자를 얻어 수소 기체가 돼요."),
    ("2Na + Cl₂ → 2NaCl", ["Na", "Cl₂"], "Na", "Cl₂", "나트륨은 전자를 잃어 Na⁺, 염소는 전자를 얻어 Cl⁻이 돼요."),
    ("6CO₂ + 6H₂O → C₆H₁₂O₆ + 6O₂", ["CO₂", "H₂O"], "H₂O", "CO₂", "광합성: 이산화 탄소는 환원되어 포도당이 되고, 물은 산화되어 산소가 생겨요."),
    ("C₆H₁₂O₆ + 6O₂ → 6CO₂ + 6H₂O", ["C₆H₁₂O₆", "O₂"], "C₆H₁₂O₆", "O₂", "세포호흡: 포도당은 산화되어 이산화 탄소가 되고, 산소는 환원되어 물이 돼요."),
]


def _redox_stage(used):
    eq, cands, ox, red, exp = _rng.choice([r for r in REDOX if r[0] not in used] or REDOX)
    used.add(eq)
    opts = list(cands)
    _rng.shuffle(opts)
    return {"eq": eq, "opts": opts}, {"ox": opts.index(ox), "red": opts.index(red), "exp": exp}


def _redox_check(pub, ans, pick):
    if not isinstance(pick, dict):
        return None
    ox, red = pick.get("ox"), pick.get("red")
    n = len(pub["opts"])
    if not (isinstance(ox, int) and isinstance(red, int) and 0 <= ox < n and 0 <= red < n):
        return None
    ok = ox == ans["ox"] and red == ans["red"]
    return ok, {"ox": ans["ox"], "red": ans["red"], "explanation": ans["exp"]}


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
        ion = f"원자가 전자 {val}개 → 전자를 {val}개 잃어 +{val} 양이온이 되기 쉬워요."
    else:
        ion = f"원자가 전자 {val}개 → 전자를 {8 - val}개 얻어 −{8 - val} 음이온이 되기 쉬워요." if val >= 5 else f"원자가 전자 {val}개 → 주로 전자를 공유해요."
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
