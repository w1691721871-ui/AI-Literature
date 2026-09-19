# AI 科研文献分析助手

一个面向校招作品展示的个人实践项目。用户上传一篇可提取文本的科研论文 PDF，输入分析任务后，系统通过一个简单、可解释的 Agent 流程生成结构化分析，并支持围绕当前论文进行多轮追问。

> 这是一个单 Agent MVP。项目不包含 RAG、向量数据库、多 Agent、Redis、用户登录或持久化存储。

## 项目介绍

科研论文中的研究问题、方法、结果与局限性通常分散在不同章节，快速建立整体理解需要较多时间。本项目将 PDF 文本提取、任务识别和大模型调用组合为一个清晰流程，帮助用户得到初步的结构化论文解读。

项目重点是实践 FastAPI、PDF 处理、百炼 OpenAI 兼容接口、简单 Agent 编排与 Vue 页面交互，而非替代严谨的人工学术评审。

## 产品解决的问题

- 将可复制文本的 PDF 论文内容提取为可分析文本。
- 根据用户关注点，选择摘要、研究方法、创新点、结论、局限性或整体分析等处理模板。
- 用固定 JSON 数据结构返回结果，便于页面展示。
- 在同一篇论文的上下文中支持最近几轮连续追问。

## 核心功能

- PDF 上传、格式校验与文本提取。
- 任务识别与单 Agent 分析流程。
- 阿里云百炼 Qwen 的 OpenAI 兼容 Chat Completions 调用。
- 固定结构化分析结果：
  - `title`
  - `research_topic`
  - `research_question`
  - `methodology`
  - `key_findings`
  - `innovation_points`
  - `limitations`
  - `keywords`
- 当前论文的多轮追问：服务端为每篇论文保留最近 3 轮问答。
- Vue 3 前端：上传状态、Agent 阶段指引、结构化结果、对话追问、超时与错误提示。

## 技术架构

```text
用户
  → Vue 3（浏览器 CDN）
  → FastAPI
  → PDF 解析（pypdf）
  → PaperAnalysisAgent
  → Qwen（阿里云百炼 OpenAI 兼容接口）
  → 结构化结果
  → Vue 3 展示
```

## Agent 执行流程

```text
用户上传 PDF 并输入任务
        ↓
校验文件与任务
        ↓
提取 PDF 文本
        ↓
识别任务类型并选择提示词模板
        ↓
调用 Qwen 生成 JSON 结果
        ↓
后端清理 Markdown JSON、解析并校验字段
        ↓
返回结构化分析结果和 paper_id
        ↓
用户基于 paper_id 继续追问（携带最近 3 轮历史）
```

前端展示的 Agent 阶段是请求生命周期指引，不是服务端实时流式事件。

## 项目目录

```text
.
├── app/
│   ├── agent/
│   │   └── paper_agent.py       # 任务识别、分析编排、论文与问答上下文
│   ├── services/
│   │   ├── pdf_service.py       # PDF 校验与文本提取
│   │   └── llm_service.py       # 百炼兼容调用、JSON 清理与校验
│   └── main.py                  # FastAPI 接口、CORS 与错误映射
├── frontend/
│   ├── index.html               # Vue 页面入口
│   ├── app.js                   # 页面状态与 HTTP 请求
│   └── styles.css               # 响应式页面样式
├── .env.example                 # 环境变量模板
├── .gitignore                   # 忽略 .env、虚拟环境与本地文件
├── requirements.txt
└── README.md
```

## 本地运行方法

### 1. 创建虚拟环境并安装依赖

```powershell
py -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
Copy-Item .env.example .env
```

### 2. 配置环境变量

编辑项目根目录 `.env`。该文件已被 `.gitignore` 忽略，不应提交到 Git。

```env
DASHSCOPE_API_KEY=your_api_key_here
LLM_BASE_URL=https://dashscope.aliyuncs.com/compatible-mode/v1
LLM_MODEL=qwen-plus
```

不要将真实 API Key 写入 `.env.example`、Python 代码、前端代码或 Git 仓库。

### 3. 启动后端

```powershell
.\.venv\Scripts\python.exe -m uvicorn app.main:app --host 127.0.0.1 --port 8000
```

健康检查地址：`http://127.0.0.1:8000/health`

### 4. 启动前端

另开一个终端，在项目根目录执行：

```powershell
py -m http.server 5173 --directory frontend
```

浏览器打开：`http://127.0.0.1:5173`

前端使用 Vue 3 CDN，首次访问需要网络连接。

## 百炼 API 配置

项目通过 OpenAI Python SDK 访问百炼的 OpenAI 兼容接口：

- API Key 环境变量：`DASHSCOPE_API_KEY`
- Base URL：`https://dashscope.aliyuncs.com/compatible-mode/v1`
- 默认模型：`qwen-plus`

请在百炼控制台确认该 API Key 对目标模型具有调用权限，并检查免费额度是否可用。

## 使用方法

1. 启动前端和后端。
2. 在页面左侧上传一篇包含可复制文字的 PDF。
3. 修改或保留默认分析任务。
4. 点击“开始分析”，等待右侧返回结构化结果。
5. 在下方输入问题，例如“这个研究方法有什么优势？”。
6. 点击“发送”，系统会结合当前论文和最近几轮问答回答问题。

主要接口：

- `GET /health`：健康检查。
- `POST /agent/analyze-paper`：接收 `file` 与 `task`，返回分析结果与 `paper_id`。
- `POST /agent/papers/{paper_id}/questions`：接收 `question`，返回追问回答。

## 异常处理

- 空文件、非 PDF、损坏 PDF、无可提取文本：返回中文说明。
- 提取文本过长：返回 413，提示上传更短论文。
- 空任务、无法识别的任务、空追问、追问过长：返回中文说明。
- 模型额度不足、鉴权/权限、限流、网络、超时与服务异常：返回不含密钥的中文提示。
- 模型空结果、JSON 代码块、JSON 格式异常或字段缺失：后端清理/校验，失败时安全返回错误。
- 前端对无文件、重复点击、后端不可用、网络失败和 90 秒超时提供提示。

后端日志保留 PDF 解析和模型调用的技术错误信息，但会对 API Key 与 Authorization 内容脱敏。

## 测试记录

以下为本地开发环境的基础测试记录：

| 场景 | 方式 | 结果 |
|---|---|---|
| PDF 正常上传与论文分析 | 本地测试 PDF + 当前百炼配置 | 通过，HTTP 200 |
| 结构化结果字段 | 检查 8 个固定字段 | 通过 |
| 论文追问 | 使用分析返回的 `paper_id` 继续提问 | 通过，HTTP 200 |
| 空问题 | 接口自动化测试 | 通过，HTTP 400 |
| 未上传 PDF | 接口自动化测试 | 通过，HTTP 422 |
| 无法解析的 PDF | 接口自动化测试 | 通过，HTTP 400 |
| LLM 调用失败 | 受控模拟服务层错误 | 通过，HTTP 502 |
| JSON 解析异常 | 受控输入非法 JSON | 通过，返回中文错误 |
| 超长文本 | 受控模拟提取文本超过限制 | 通过，HTTP 413 |
| 前端静态访问 | `http://127.0.0.1:5173` | 通过，HTTP 200 |
| 后端健康检查 | `/health` | 通过，`{"status":"ok"}` |

## 当前限制

- 仅支持能够通过 pypdf 提取文字的 PDF；扫描件或图片型 PDF 没有 OCR。
- 当前论文和最近问答仅保存在内存中，FastAPI 重启后会清空。
- 论文内容发送给模型前最多截取前 20,000 个字符，超出部分不会参与本次模型分析。
- Agent 是固定模板与关键词识别的单 Agent 流程，不是自主规划系统。
- 前端页面不保存跨浏览器会话的聊天记录。
- 模型效果、可用额度与响应速度受百炼账户、模型权限和网络环境影响。

## 后续可以优化的方向

- 为扫描型 PDF 增加 OCR 能力。
- 使用持久化存储保存论文与会话上下文。
- 为更长论文设计分段摘要或检索方案。
- 为前端增加可展开的 Agent 执行详情与更细的结果展示。
- 在保留现有 API 的前提下，将 Vue CDN 页面迁移为更完整的工程化前端。
- 增加正式的自动化测试文件与持续集成流程。

## 安全说明

- `.env` 已被 `.gitignore` 忽略。
- 不要提交真实 API Key、Authorization 信息、未授权论文内容或个人信息。
- 提交前请检查 `git status`，确认暂存区没有敏感文件。
