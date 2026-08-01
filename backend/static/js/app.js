// 易经 LLM 卜卦 — 前端逻辑（中英双语）
const $ = (id) => document.getElementById(id);

// ── 语言字典 ──
const I18N = {
  zh: {
    title: "🔮 易经卜卦",
    subtitle: "静心默念你的问题，掷六次硬币，让易经老人为你解卦",
    label_question: "你想问什么？",
    placeholder_question: "例如：今年事业运势如何？",
    btn_throw: "掷硬币",
    btn_cast: "起卦解卦",
    btn_reset: "重新起卦",
    loading: "卦象已成，易经老人正在推演…（可能需要片刻）",
    footer: "纯本地部署 · LLM 由环境变量配置 · 卦象算法零依赖",
    thrown: "已掷：{n} / 6 爻",
    moving: "动",
    error: "出错：{msg}",
    rag_note: "",
  },
  en: {
    title: "🔮 I Ching Divination",
    subtitle: "Focus on your question, toss the coins six times, and let the I Ching sage interpret",
    label_question: "What is your question?",
    placeholder_question: "e.g. How will my career be this year?",
    btn_throw: "Toss Coins",
    btn_cast: "Cast & Interpret",
    btn_reset: "Start Over",
    loading: "The hexagram is cast. The sage is interpreting… (may take a moment)",
    footer: "Runs locally · LLM configured via env vars · zero-dependency hexagram math",
    thrown: "Thrown: {n} / 6",
    moving: "M",
    error: "Error: {msg}",
    rag_note: "",
  },
};

let lang = "zh";
function t(key, vars) {
  let s = I18N[lang][key] ?? key;
  if (vars) for (const [k, v] of Object.entries(vars)) s = s.replace("{" + k + "}", v);
  return s;
}

function setLang(l) {
  lang = l;
  document.documentElement.lang = l === "zh" ? "zh-CN" : "en";
  document.querySelectorAll("[data-i18n]").forEach((el) => {
    el.textContent = t(el.dataset.i18n);
  });
  document.querySelectorAll("[data-i18n-placeholder]").forEach((el) => {
    el.placeholder = t(el.dataset.i18nPlaceholder);
  });
  document.querySelectorAll("[data-i18n-prefix]").forEach((el) => {
    const k = el.dataset.i18nPrefix;
    if (k === "thrown") el.textContent = t("thrown", { n: lines.length });
  });
  document.getElementById("btn-lang-zh").classList.toggle("active", l === "zh");
  document.getElementById("btn-lang-en").classList.toggle("active", l === "en");
}

// ── 起卦逻辑 ──
let lines = [];
const MAX_LINES = 6;

function renderLines() {
  const box = $("lines");
  box.innerHTML = "";
  lines.forEach((l) => {
    const div = document.createElement("div");
    div.className = "line" + (l.old ? " old" : " young");
    if (l.val === 0) {
      div.style.background = "transparent";
      div.style.display = "flex";
      div.style.gap = "24px";
      const a = document.createElement("div");
      a.style.cssText = "width:63px;height:16px;background:#3d3226;border-radius:3px";
      const b = a.cloneNode();
      div.appendChild(a); div.appendChild(b);
    }
    if (l.old) {
      const m = document.createElement("span");
      m.className = "mark";
      m.textContent = t("moving");
      div.appendChild(m);
    }
    box.appendChild(div);
  });
}

$("btn-throw").addEventListener("click", () => {
  if (lines.length >= MAX_LINES) return;
  const coins = [0, 1, 2].map(() => Math.random() < 0.5 ? 1 : 0);
  const s = coins.reduce((a, b) => a + b, 0);
  const type = s === 3 ? { val: 1, old: true } : s === 0 ? { val: 0, old: true } : s === 2 ? { val: 1, old: false } : { val: 0, old: false };
  lines.push({ coins, ...type });
  renderLines();
  $("coin-result").textContent = t("thrown", { n: lines.length });
  if (lines.length === MAX_LINES) {
    $("btn-throw").disabled = true;
    $("btn-cast").style.display = "block";
    $("btn-reset").style.display = "block";
  }
});

$("btn-cast").addEventListener("click", async () => {
  const question = $("question").value.trim();
  $("btn-cast").disabled = true;
  $("result").style.display = "block";
  $("loading").style.display = "block";
  $("reading").textContent = "";
  $("hexagram").textContent = "";
  try {
    const resp = await fetch("/api/iching", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        tosses: lines.map((l) => ({ coins: l.coins })),
        question,
        lang,
      }),
    });
    const data = await resp.json();
    if (!resp.ok) throw new Error(data.detail || "HTTP " + resp.status);
    const h = data.hexagram;
    let hexTxt = `${h.name}`;
    if (h.changing.length) {
      hexTxt += (lang === "zh" ? " · 变爻第" + h.changing.join("、") + "爻" : " · moving lines " + h.changing.join(","));
      if (h.changed) hexTxt += (lang === "zh" ? " → 变卦 " + h.changed : " → becomes " + h.changed);
    }
    $("hexagram").textContent = hexTxt + (data.rag_used ? " · 📚" : "");
    $("reading").textContent = data.reading;
  } catch (e) {
    $("reading").textContent = t("error", { msg: e.message });
  } finally {
    $("loading").style.display = "none";
    $("btn-cast").disabled = false;
  }
});

$("btn-reset").addEventListener("click", () => {
  lines = [];
  renderLines();
  $("btn-throw").disabled = false;
  $("btn-cast").style.display = "none";
  $("btn-reset").style.display = "none";
  $("coin-result").textContent = t("thrown", { n: 0 });
  $("result").style.display = "none";
});

setLang("zh");
