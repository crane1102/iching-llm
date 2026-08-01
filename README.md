# 易经 LLM 卜卦 🔮

传统易经六爻占卜 + LLM 智能解卦。抛六次硬币，让 AI 为你解读卦象。

纯本地部署，**接什么 LLM 由你决定**——任何支持 OpenAI 兼容协议的服务或本地模型都能用。

## 特性

- 🪙 **正宗六爻起卦**：三枚硬币掷六次，老阳/老阴为动爻，自动计算本卦、变卦
- 📜 **64 卦全表**：卦名、卦符、卦辞内置（零依赖）
- 📖 **内置《周易》卦爻辞全文**：解卦时自动注入本卦+变卦的卦辞、六爻爻辞、象辞（公版古籍），LLM 不再靠记忆解卦，准确率大幅提升
- 🧠 **任意 LLM 可接**：环境变量配置，本地 Ollama / Gemma / DeepSeek / OpenAI / 通义都行
- 📚 **可选 RAG 增强**：指向你的知识库目录即可自动检索相关经文，不设置则纯 LLM 解卦
- 🌐 **Web 界面**：简洁响应式，手机电脑都能用

## 快速开始

```bash
# 1. 安装依赖
pip install -r requirements.txt

# 2. 配置 LLM（环境变量，二选一）
export LLM_BASE_URL=http://localhost:11434/v1   # 本地 Ollama
export LLM_API_KEY=
export LLM_MODEL=qwen2.5:7b

# 3. 启动
cd backend
uvicorn app:app --host 0.0.0.0 --port 8088
```

打开 http://localhost:8088 ，默念问题，掷六次硬币，得到解卦。

### LLM 配置示例

| 后端 | LLM_BASE_URL | LLM_MODEL |
|---|---|---|
| 本地 Ollama | `http://localhost:11434/v1` | `qwen2.5:7b` |
| 本地 Gemma (MLX) | `http://localhost:8080/v1` | `gemma-4-26b-a4b-it` |
| DeepSeek | `https://api.deepseek.com/v1` | `deepseek-chat` |
| OpenAI | `https://api.openai.com/v1` | `gpt-4o` |
| 通义千问 | `https://dashscope.aliyuncs.com/compatible-mode/v1` | `qwen-max` |

## RAG 增强（可选）

```bash
# 把 .md/.txt 文件放进一个目录，指向它即可
export ICHING_RAG_DIR=/path/to/your/knowledge
```

解卦时若问题命中知识库内容，会自动注入相关段落作为参考。不设置则跳过，纯 LLM 解卦。

## API

- `GET /api/health` — 服务状态 + LLM/RAG 配置
- `POST /api/iching` — 解卦

```json
{
  "tosses": [{"coins": [1,1,0]}, {"coins": [0,1,1]}, {"coins": [1,1,1]}, {"coins": [0,0,0]}, {"coins": [1,0,1]}, {"coins": [0,1,0]}],
  "question": "今年事业运势如何？"
}
```

返回本卦、动爻、变卦、LLM 解卦全文。

## 项目结构

```
iching-llm/
├── backend/
│   ├── app.py            # FastAPI 主服务（LLM/RAG 均环境变量配置）
│   ├── iching_coin.py    # 64卦 + 起卦算法（零依赖，可独立使用）
│   ├── iching_texts.py   # 公版《周易》64卦卦辞爻辞全文（解卦注入用）
│   ├── static/           # Web 前端
│   └── templates/
├── requirements.txt
└── .env.example
```

## 经文来源与版权

内置的卦辞、爻辞、象辞取自通行本《周易》（周文王/周公/孔子系辞，两千年以上古籍），属于公版内容，可自由分发。卦爻辞文本与通行本逐字核对过（乾、坤、屯、蒙、需、讼、泰、否、既济、未济等卦验证一致）。

## 许可

MIT License

---

*卦象算法来自传统易经六爻起卦法，卦辞取自通行本《周易》。解卦内容由 AI 生成，仅供参考娱乐。*
