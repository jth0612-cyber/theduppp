// 회원가입: 틀린 칸은 그 칸 바로 아래에 알려 주고(인라인 에러), 비밀번호는 강도 막대로 보여 준다.
(function () {
  const form = document.querySelector("[data-signup]");
  if (!form) return;
  const $ = (n) => form.querySelector(`[name="${n}"]`);
  const errEl = (n) => form.querySelector(`[data-err="${n}"]`);
  const NAME = /^[가-힣A-Za-z ]{2,20}$/, ID = /^[A-Za-z0-9-]{3,30}$/;

  function show(n, msg) {
    const el = errEl(n), input = $(n);
    if (!el || !input) return;
    el.textContent = msg || ""; el.hidden = !msg;
    if (msg) input.setAttribute("aria-invalid", "true"); else input.removeAttribute("aria-invalid");
  }
  function kinds(pw) { return [/[A-Za-z가-힣]/.test(pw), /\d/.test(pw), /[^A-Za-z0-9가-힣]/.test(pw)].filter(Boolean).length; }

  const check = {
    code: (v) => (v.replace(/[\s-]/g, "").length < 6 ? "선생님께 받은 개인 코드를 입력해 주세요." : ""),
    name: (v) => (NAME.test(v.trim()) ? "" : "이름은 한글 또는 영문 2~20자로 입력하세요."),
    student_no: (v) => ($("student_no").hasAttribute("data-card")
      ? (/^[0-9A-Fa-f]{4,20}$/.test(v.replace(/[\s:-]/g, "")) ? "" : "카드 번호는 카드에 적힌 숫자(또는 영문 A~F 섞인 번호) 4~20자예요.")
      : (ID.test(v.trim()) ? "" : "아이디는 영문·숫자·- 로 3~30자입니다.")),
    password: (v) => (v.length < 10 ? "비밀번호는 10자 이상이어야 합니다." : kinds(v) < 2 ? "영문·숫자·특수문자 중 2종류 이상 섞어 주세요." : ""),
    confirm: (v) => (v && v === $("password").value ? "" : "비밀번호가 서로 일치하지 않습니다."),
    consent: () => ($("consent").checked ? "" : "개인정보 수집·이용에 동의해야 가입할 수 있어요."),
  };
  const touched = new Set();

  // 칸을 벗어날 때 확인, 이미 틀렸던 칸은 고치는 즉시 다시 확인
  Object.keys(check).forEach((n) => {
    const input = $(n); if (!input) return;
    input.addEventListener("blur", () => { if (input.value || n === "consent") { touched.add(n); show(n, check[n](input.value)); } });
    input.addEventListener(n === "consent" ? "change" : "input", () => {
      if (touched.has(n) || input.getAttribute("aria-invalid")) show(n, check[n](input.value));
      if (n === "password" && touched.has("confirm")) show("confirm", check.confirm($("confirm").value));
    });
  });

  // 비밀번호 강도: 약해요(빨강) · 보통이에요(노랑, 가입 가능) · 안전해요(초록)
  const pw = $("password"), meter = form.querySelector("[data-pw-meter]"), hint = form.querySelector("[data-pw-hint]");
  const HINT = hint.textContent;
  pw.addEventListener("input", () => {
    const v = pw.value;
    if (!v) { meter.hidden = true; hint.textContent = HINT; hint.className = "field-hint"; return; }
    const k = kinds(v), lvl = v.length < 10 || k < 2 ? 1 : (v.length >= 12 && k === 3) || v.length >= 16 ? 3 : 2;
    meter.hidden = false; meter.dataset.lvl = lvl;
    hint.textContent = lvl === 1 ? (v.length < 10 ? `약해요 · ${10 - v.length}자 더 써 주세요` : "약해요 · 숫자나 특수문자를 섞어 주세요")
      : lvl === 2 ? "보통이에요 · 특수문자를 섞으면 더 안전해요" : "안전해요";
    hint.className = "field-hint pw-" + lvl;
  });

  // 가입하기: 틀린 칸이 있으면 보내지 않고 첫 번째 틀린 칸으로
  form.addEventListener("submit", (e) => {
    let first = null;
    Object.keys(check).forEach((n) => { const msg = check[n]($(n).value); touched.add(n); show(n, msg); if (msg && !first) first = $(n); });
    if (first) { e.preventDefault(); first.focus(); }
  });
})();
