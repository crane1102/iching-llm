"""易经 LLM 卜卦 — 独立开源版

硬币起卦 + LLM 解卦（OpenAI 兼容协议，可接任意 LLM）
可选 RAG 增强：设置 ICHING_RAG_DIR 指向包含 .md/.txt 的目录即可启用

环境变量：
  LLM_BASE_URL    LLM API 地址（默认 http://localhost:8080/v1，兼容 OpenAI 协议即可）
  LLM_API_KEY     API Key（本地服务可留空）
  LLM_MODEL       模型名（默认 gemma-4-26b-a4b-it）
  ICHING_RAG_DIR   可选：知识库目录，启用 RAG 增强
"""
import os
import re
from pathlib import Path

import httpx
import uvicorn
from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from pydantic import BaseModel, Field

from iching_coin import calc, build_prompt
from iching_texts import ZHOUI, get_hex, get_hex_by_symbol_name, format_hex_text
from iching_en import get_judgment_en

BASE = Path(__file__).parent
templates = Jinja2Templates(directory=str(BASE / "templates"))

app = FastAPI(title="易经 LLM 卜卦", version="1.0.0")


class NoCacheStaticFiles(StaticFiles):
    """静态文件禁用缓存，保证前端改动即时生效"""

    async def get_response(self, path: str, scope):
        resp = await super().get_response(path, scope)
        if resp.status_code == 200:
            resp.headers["Cache-Control"] = "no-cache, no-store, must-revalidate"
        return resp


@app.middleware("http")
async def no_cache_html(request, call_next):
    resp = await call_next(request)
    if request.url.path in ("/", "/index.html"):
        resp.headers["Cache-Control"] = "no-cache, no-store, must-revalidate"
    return resp


app.mount("/static", NoCacheStaticFiles(directory=str(BASE / "static")), name="static")

# ─────────────────────────────────────────────
# LLM 配置：全部环境变量，不写死任何模型
# ─────────────────────────────────────────────
LLM_CFG = {
    "base_url": os.environ.get("LLM_BASE_URL", "http://localhost:8080/v1").rstrip("/"),
    "api_key": os.environ.get("LLM_API_KEY", ""),
    "model": os.environ.get("LLM_MODEL", "gemma-4-26b-a4b-it"),
}


async def call_llm(sys_prompt, user_msg, max_tokens=800):
    """调用 OpenAI 兼容的 chat/completions 接口"""
    headers = {"Content-Type": "application/json"}
    if LLM_CFG["api_key"]:
        headers["Authorization"] = f"Bearer {LLM_CFG['api_key']}"
    try:
        async with httpx.AsyncClient(timeout=600) as c:
            r = await c.post(f"{LLM_CFG['base_url']}/chat/completions", json={
                "model": LLM_CFG["model"],
                "messages": [{"role": "system", "content": sys_prompt},
                             {"role": "user", "content": user_msg}],
                "max_tokens": max_tokens,
                "temperature": 0.9,
            }, headers=headers)
            data = r.json()
            if "choices" in data:
                return data["choices"][0]["message"]["content"]
            return f"【LLM错误】{data.get('error', {}).get('message', '')[:60]}"
    except Exception as e:
        return f"【LLM错误】{str(e)[:80]}"


# ─────────────────────────────────────────────
# 可选 RAG：有知识库就用，没有就纯 LLM 解卦
# ─────────────────────────────────────────────
RAG_DIR = os.environ.get("ICHING_RAG_DIR", "")
RAG_INDEX = []


def load_rag():
    """加载知识库目录下的 .md/.txt 文件为可检索文本"""
    global RAG_INDEX
    if not RAG_DIR or not os.path.isdir(RAG_DIR):
        RAG_INDEX = []
        return
    RAG_INDEX = []
    for f in sorted(Path(RAG_DIR).glob("*.md")) + sorted(Path(RAG_DIR).glob("*.txt")):
        try:
            RAG_INDEX.append({"path": str(f), "text": f.read_text(encoding="utf-8")})
        except Exception:
            continue
    print(f"📚 RAG 已启用：{len(RAG_INDEX)} 个文件（{RAG_DIR}）")


def rag_search(question, top_k=2):
    """极简关键词检索（开源版不带向量库，够用且零依赖）"""
    if not RAG_INDEX:
        return []
    terms = [t for t in re.split(r"\s+", question) if len(t) >= 2]
    scored = []
    for doc in RAG_INDEX:
        score = sum(doc["text"].count(t) for t in terms)
        if score > 0:
            scored.append((score, doc))
    scored.sort(key=lambda x: -x[0])
    return [doc["text"][:800] for _, doc in scored[:top_k]]


load_rag()


def clean_reading(text):
    """去掉 LLM 输出中的 Markdown 痕迹"""
    if not text:
        return text
    s = text
    s = re.sub(r"```[\s\S]*?```", "", s)
    s = re.sub(r"\*\*(.+?)\*\*", r"\1", s)
    s = re.sub(r"\*(.+?)\*", r"\1", s)
    s = re.sub(r"__([^_]+)__", r"\1", s)
    s = re.sub(r"_([^_]+)_", r"\1", s)
    s = re.sub(r"^#{1,6}\s*", "", s, flags=re.M)
    s = re.sub(r"^\s*\d+[.)、]\s*[-*+·]?\s*", "", s, flags=re.M)
    s = re.sub(r"^\s*[-*+·]\s+", "", s, flags=re.M)
    s = re.sub(r"^\s*>\s?", "", s, flags=re.M)
    s = re.sub(r"^[-=*_]{3,}\s*$", "", s, flags=re.M)
    s = re.sub(r"[ \t\u3000]{2,}", " ", s)
    s = re.sub(r"\n{3,}", "\n\n", s)
    return s.strip()


# ─────────────────────────────────────────────
# API
# ─────────────────────────────────────────────
class IChingRequest(BaseModel):
    tosses: list = Field(...)
    question: str = Field("", max_length=200)
    lang: str = Field("zh", max_length=5)


@app.get("/", response_class=HTMLResponse)
async def index(request: Request):
    return templates.TemplateResponse(request=request, name="index.html")


@app.get("/api/health")
async def health():
    """健康检查：返回 LLM 配置状态"""
    rag_on = len(RAG_INDEX) > 0
    return {
        "status": "ok",
        "llm": {"model": LLM_CFG["model"], "base_url": LLM_CFG["base_url"]},
        "rag": {"enabled": rag_on, "files": len(RAG_INDEX)},
    }


@app.post("/api/iching")
async def get_iching(data: IChingRequest):
    """掷卦 + LLM 解卦（支持 zh/en 双语）"""
    hex_data = calc(data.tosses)
    question = data.question or ""
    is_en = data.lang == "en"

    # RAG 增强（可选，中文知识库对英文问题意义不大）
    rag_ctx = ""
    if question and RAG_INDEX and not is_en:
        snippets = rag_search(question)
        if snippets:
            rag_ctx = "\n\n以下为知识库中与问题相关的参考资料：\n" + "\n".join(
                f"- {s}" for s in snippets)

    # 注入本卦+变卦的卦爻辞原文（中/英）
    hex_doc = get_hex(hex_data["num"])
    if is_en and hex_doc:
        j_en, img_en = get_judgment_en(hex_data["num"])
        hex_text = f"Hexagram {hex_data['num']}: {hex_doc['name']} (symbol {hex_doc['symbol']})\nJudgment: {j_en}\nImage: {img_en}"
    else:
        hex_text = format_hex_text(hex_doc, yang=hex_data.get("lines")) if hex_doc else ""

    changed_text = ""
    if hex_data.get("changed"):
        changed_doc = get_hex_by_symbol_name(hex_data["changed"])
        if changed_doc:
            if is_en:
                j_en2, img_en2 = get_judgment_en(changed_doc["n"])
                changed_text = f"\n\n[Becoming Hexagram {changed_doc['n']}: {changed_doc['name']}] Judgment: {j_en2}"
            else:
                changed_text = f"\n\n【变卦参考】{format_hex_text(changed_doc, yang=hex_data.get('changed_lines'))}"

    if is_en:
        sys_prompt = "You are the I Ching Sage, fluent in the Book of Changes, giving accurate and vivid interpretations. Answer in natural paragraphs in English."
        moving = f"moving lines: {','.join(str(i) for i in hex_data['changing'])}" if hex_data["changing"] else "no moving lines (static hexagram)"
        sym = hex_doc["symbol"] if hex_doc else ""
        prompt = f"""The inquirer cast the hexagram {hex_data['name']} (symbol {sym}).
{moving}{f', becomes {hex_data["changed"]}' if hex_data.get('changed') else ''}
Question: {question or 'No question asked — please give a general reading of this hexagram.'}

[Hexagram text]
{hex_text}{changed_text}

Interpret this hexagram for the inquirer's question, within 400 words, in natural paragraphs. No markdown symbols."""
    else:
        sys_prompt = "你是易经老人，精通六十四卦，解卦准确而生动，回答用自然段落。" + rag_ctx
        prompt = f"""求问者掷六爻得【{hex_data['name']}】卦，请依真实卦象解答。
{hex_data['meaning']}
变爻：第{','.join(str(i) for i in hex_data['changing'])}爻{'，变卦：' + hex_data['changed'] if hex_data.get('changed') else ''}
问题：{question or '（未提问，请泛论此卦含义）'}

【本卦经文】
{hex_text}{changed_text}

请结合经文原文解答求问者的问题，400字以内，用自然段落输出，禁止任何 Markdown 符号。"""

    reading = await call_llm(sys_prompt, prompt, max_tokens=800)

    return {
        "status": "ok",
        "hexagram": hex_data,
        "reading": clean_reading(reading),
        "rag_used": bool(rag_ctx),
    }


if __name__ == "__main__":
    print(f"🔮 易经 LLM 卜卦 v1.0.0")
    print(f"📡 LLM: {LLM_CFG['model']} @ {LLM_CFG['base_url']}")
    print(f"📚 RAG: {'启用 (' + str(len(RAG_INDEX)) + ' 文件)' if RAG_INDEX else '未启用（设置 ICHING_RAG_DIR 可开启）'}")
    uvicorn.run("app:app", host="0.0.0.0", port=8088)
