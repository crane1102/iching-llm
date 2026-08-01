// 易经 LLM 卜卦 — 前端逻辑
const $ = (id) => document.getElementById(id);

let lines = [];          // 已掷爻：[{coins:[..], type:'young_yang'|'old_yang'|...}]
const MAX_LINES = 6;

function lineType(coins) {
  const s = coins.reduce((a, b) => a + b, 0);
  if (s === 3) return { val: 1, old: true, label: "老阳 ⚊" };
  if (s === 0) return { val: 0, old: true, label: "老阴 ⚋" };
  if (s === 2) return { val: 1, old: false, label: "少阳 ⚊" };
  return { val: 0, old: false, label: "少阴 ⚋" };
}

function renderLines() {
  const box = $("lines");
  box.innerHTML = "";
  lines.forEach((l) => {
    const div = document.createElement("div");
    div.className = "line" + (l.old ? " old" : " young");
    if (l.val === 0) {
      // 阴爻：两段
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
      m.textContent = "动";
      div.appendChild(m);
    }
    box.appendChild(div);
  });
}

$("btn-throw").addEventListener("click", () => {
  if (lines.length >= MAX_LINES) return;
  const coins = [0, 1, 2].map(() => Math.random() < 0.5 ? 1 : 0);
  lines.push({ coins, ...lineType(coins) });
  renderLines();
  $("coin-result").textContent = `已掷：${lines.length} / 6 爻`;
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
      body: JSON.stringify({ tosses: lines.map((l) => ({ coins: l.coins })), question }),
    });
    const data = await resp.json();
    if (!resp.ok) throw new Error(data.detail || "HTTP " + resp.status);
    const h = data.hexagram;
    let hexTxt = `${h.name}`;
    if (h.changing.length) {
      hexTxt += ` · 变爻第${h.changing.join("、")}爻`;
      if (h.changed) hexTxt += ` → 变卦 ${h.changed}`;
    }
    $("hexagram").textContent = hexTxt + (data.rag_used ? " · 📚" : "");
    $("reading").textContent = data.reading;
  } catch (e) {
    $("reading").textContent = "出错：" + e.message;
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
  $("coin-result").textContent = "已掷：0 / 6 爻";
  $("result").style.display = "none";
});
