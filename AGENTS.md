# Meeting Correct - 会议实时语音事实核查助手

## 项目简介

实时从麦克风获取语音转录文本，调用 Qwen 模型检测文本中的事实陈述，并通过联网搜索验证事实真假。

## 快速开始

```bash
# 终端 1：运行主程序（ASR + 事实核查）
python main.py --demo   # 模拟模式
python main.py          # 实时模式（默认启用 VAD）

# 终端 2：运行前端服务（WebSocket 推送）
python server.py
```

访问 http://localhost:8000 查看实时结果。

## 架构设计

### 核心思路：解耦 + 异步

```
ASR 线程 → 队列 → 工作线程 → LLM API → 写文件
                                    ↓
前端页面 ← WebSocket ← 文件监控 ← fact_check_results.json
```

### 文件输出

- `transcript.txt` - 转录原文（追加写入）
- `fact_check_results.json` - 核查结果数组（JSON 格式）
- `fact_check_results.md` - 核查结果（Markdown 格式，人可读）

## 项目结构

```
meeting-correct/
├── main.py                # 主程序（ASR + 核查）
├── server.py              # 前端服务（WebSocket + 文件监控）
├── static/
│   └── index.html         # 前端页面
├── core/
│   ├── config.py          # 配置（API Key、模型名）
│   ├── asr/
│   │   ├── qwen3.py       # 阿里云实时语音识别
│   │   ├── vad.py         # 本地 VAD 语音活动检测
│   │   └── __init__.py    # ASR 模块导出
│   ├── qwen_client.py     # Qwen API 客户端（纯 LLM 调用）
│   └── fact_checker.py    # 事实核查（业务逻辑 + Prompt）
├── scripts/
│   └── download_vad_model.py  # VAD 模型下载脚本
├── models/
│   └── silero_vad.onnx    # Silero VAD 模型
├── fact_check_results.json  # 核查结果（JSON）
├── fact_check_results.md    # 核查结果（Markdown）
├── transcript.txt           # 转录原文
├── pyproject.toml         # 依赖配置
└── AGENTS.md              # 本文件
```

## 核心模块

### 1. ASR 语音识别 (core/asr/qwen3.py)

- 使用 dashscope 的 qwen3-asr-flash-realtime 模型
- 使用 sounddevice 捕获麦克风音频
- WebSocket 实时传输音频流
- **本地 VAD**：默认启用 Silero VAD 检测语音片段，仅发送有效语音到服务端

### 2. 增量事实核查 (core/fact_checker.py)

**两步处理流程**：
1. **ASR 文本修正**：修正拼音、外文、乱码等识别错误（如 "yan 唱会"→"演唱会"），保留用户原始表达（数字、时间、事实陈述不修改）
2. **事实提取**：从修正后的文本中提取需要核查的事实主张

**增量检查机制**：
- **overlap_chars=200**：每次检查向前重叠 200 字符，避免边界切分问题
- **min_new_chars=10**：累积新文本不足 10 字符时不触发检查
- **去重 + 合并**：根据 claim 内容去重，避免重复核查

### 3. Qwen 客户端 (core/qwen_client.py)

- `chat(messages, enable_search)`：通用对话接口
- `search(query)`：带联网搜索的接口
- 纯 LLM 调用封装，无业务逻辑

### 4. 前端服务 (server.py)

- 使用 FastAPI + WebSocket
- 使用 watchdog 监控文件变化
- 文件变化时自动推送到前端，无需轮询

### 5. 前端页面 (static/index.html)

- 原生 HTML + JS
- WebSocket 连接，实时接收推送
- 自动渲染核查结果

## 关键技术点

### 1. 异步架构

**主线程（ASR）**：
- 快速响应音频回调
- 只累积文本 + 写入队列
- 不阻塞

**工作线程（事实核查）**：
- 从队列消费文本
- 限流：每 3 秒最多核查 1 次
- 定期唤醒：队列空时 5 秒检查 1 次

### 2. 文件监控

使用 watchdog 库监听文件变化：

```python
class FileChangeHandler(FileSystemEventHandler):
    def on_modified(self, event):
        if event.src_path.endswith(RESULTS_JSON):
            asyncio.run_coroutine_threadsafe(push_to_clients(), _main_loop)
```

注意：watchdog 回调在独立线程执行，需要用 `asyncio.run_coroutine_threadsafe` 将任务调度到主线程的 event loop。

### 3. WebSocket 推送

- 前端连接时立即推送当前数据（刷新页面也能看到历史结果）
- 文件变化时主动推送，无需前端轮询

### 4. JSON 数据格式

fact_check_results.json 内容：

```json
[
  {
    "claim": "2024 年北京举办冬季奥运会",
    "verified": false,
    "summary": "北京并未在 2024 年举办冬季奥运会..."
  },
  {
    "claim": "中国首都是北京",
    "verified": true,
    "summary": "根据宪法，北京是中华人民共和国首都..."
  }
]
```

transcript.txt 内容（追加写入）：

```
今天天气很好
我来自北京
中国首都是北京
```

## 依赖

- dashscope
- sounddevice
- fastapi
- uvicorn
- watchdog
- requests
- openai
- websocket-client
- numpy

### 可选依赖

- sherpa-onnx（用于本地 VAD）

安装 VAD 依赖：
```bash
uv pip install sherpa-onnx
```

## 配置

编辑 `core/config.py`：

```python
QWEN_API_KEY = "sk-xxx"  # 替换为你的 API Key
QWEN_BASE_URL = "https://dashscope.aliyuncs.com/compatible-mode/v1"
FACT_CHECK_MODEL = "qwen-plus"
```
