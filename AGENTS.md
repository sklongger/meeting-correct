# Meeting Correct - 会议实时语音事实核查助手

## 项目简介

基于 LangGraph 构建的实时语音事实核查系统，专为**创投决策会议**设计。从麦克风获取语音转录文本，检测文本中的技术/商业常识类观点论断，并通过联网搜索验证事实真假。

## 业务场景

风投机构的投资决策会议上，投资人与合伙人讨论项目时常涉及大量数据和观点。本系统帮助：

- **自动核查**：验证市场规模、技术标准、行业数据等公开信息的准确性
- **跳过不适合验证的内容**：
  - 人名、公司名相关陈述（ASR 对专有名词识别不准）
  - 非公开信息、小道消息（信任投资人专业素养）
  - 主观判断、投资建议（无需验证）

## 提取规则

| 类型 | 是否提取 | 示例 |
|------|---------|------|
| 市场规模、行业数据 | ✅ | "中国SaaS市场规模超过1000亿" |
| 技术标准、技术原理 | ✅ | "Python是最流行的AI开发语言" |
| 政策法规、行业标准 | ✅ | "GDPR要求企业保护用户数据" |
| 人名相关陈述 | ❌ | "张三即将离职" |
| 公司名相关陈述 | ❌ | "XX公司估值10亿" |
| 非公开信息 | ❌ | "他们刚拿了红杉的钱" |
| 主观判断 | ❌ | "我觉得这个项目不错" |

## 快速开始

```bash
# 安装依赖
uv sync

# 终端 1：运行主程序（ASR + 事实核查）
uv run python main.py --demo   # 模拟模式
uv run python main.py          # 实时模式

# 终端 2：运行前端服务（WebSocket 推送）
uv run python server.py
```

访问 http://localhost:8000 查看实时结果。

## 架构设计

### 核心思路：解耦 + 非阻塞 + LangGraph 子图

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                            ASR 线程（永不阻塞）                              │
│  麦克风 → VAD → ASR WebSocket → 回调 → 断句缓冲区 + 写文件                  │
└─────────────────────────────────────────────────────────────────────────────┘
                                           │
                                           ▼ 完整句子
┌─────────────────────────────────────────────────────────────────────────────┐
│                           提取线程（单任务占用）                             │
│  ┌───────────────────────────────────────────────────────────────────────┐  │
│  │                    Extract Graph（LangGraph 子图）                    │  │
│  │                                                                       │  │
│  │   文本修正 ──────► 事实提取                                           │  │
│  └───────────────────────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────────────────────┘
                                           │
                                           ▼ 待验证事实
┌─────────────────────────────────────────────────────────────────────────────┐
│                           验证线程（串行）                                   │
│  ┌───────────────────────────────────────────────────────────────────────┐  │
│  │                    Verify Graph（LangGraph 子图）                     │  │
│  │                                                                       │  │
│  │   联网搜索 ──────► LLM 验证 ──────► 结果去重合并 ──────► 写文件       │  │
│  └───────────────────────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────────────────────┘
```

### 关键设计点

1. **断句缓冲区**：累积文本直到形成完整句子（句末标点 / 长度阈值 / 超时）
2. **单任务占用**：同一时间只有一个提取任务运行，避免事实切碎
3. **验证串行**：保证结果一致性，支持合并/修改历史结果
4. **LangGraph 子图**：提取和验证各为独立子图，可单独测试

## 项目结构

```
meeting-correct/
├── main.py                    # 主入口
├── server.py                  # WebSocket 服务
├── core/
│   ├── config.py              # 配置（API Key、模型名）
│   ├── qwen_client.py         # Qwen API 客户端
│   ├── sentence_buffer.py     # 断句缓冲区
│   ├── pipeline.py            # 事实核查管道
│   └── asr/
│       ├── qwen3.py           # 阿里云实时语音识别
│       ├── vad.py             # 本地 VAD 语音活动检测
│       └── __init__.py
├── graph/
│   ├── state.py               # 状态定义
│   ├── extract_graph.py       # 提取子图
│   ├── verify_graph.py        # 验证子图
│   ├── nodes/
│   │   ├── base.py            # 基础节点类
│   │   ├── correct.py         # 文本修正节点
│   │   ├── extract.py         # 事实提取节点
│   │   ├── search.py          # 联网搜索节点
│   │   └── verify.py          # 验证节点
│   ├── prompts/
│   │   ├── correct.py         # 修正 prompt
│   │   ├── extract.py         # 提取 prompt
│   │   └── verify.py          # 验证 prompt
│   └── tests/                 # 测试文件
├── static/
│   └── index.html             # 前端页面
├── data/
│   ├── fact_check_results.json    # 核查结果（JSON）
│   ├── fact_check_results.md      # 核查结果（Markdown）
│   └── transcript.txt             # 转录原文
└── pyproject.toml             # 依赖配置
```

## LangGraph 子图

### 提取子图（Extract Graph）

```python
State: {
    text: str,
    corrected_text: str,
    facts: List[dict],
    errors: List[str]
}

Flow: 文本修正 → 事实提取
```

### 验证子图（Verify Graph）

```python
State: {
    claim: str,
    original_text: str,
    search_result: str,
    verified: bool,
    summary: str
}

Flow: 联网搜索 → LLM 验证
```

## 断句规则

SentenceBuffer 根据以下规则输出完整句子：

1. **句末标点**：以 `。！？；.!?;` 或换行结尾，且长度 >= 15
2. **最大长度**：长度 >= 500 时强制输出
3. **超时**：超过 2 秒未追加新文本，且长度 >= 7

## 结果去重

验证结果写入时自动去重：

1. **精确匹配**：claim 完全相同
2. **包含关系**：一个 claim 包含另一个
3. **字符重叠**：字符重叠率 > 80%

## 测试

```bash
# 测试断句缓冲区
uv run python graph/tests/test_sentence_buffer.py

# 测试节点（mock LLM）
uv run python graph/tests/test_nodes.py

# 测试提取子图（需要真实 LLM）
uv run python graph/tests/test_extract.py
```

## 配置

编辑 `core/config.py`：

```python
QWEN_API_KEY = "sk-xxx"  # 替换为你的 API Key
QWEN_BASE_URL = "https://dashscope.aliyuncs.com/compatible-mode/v1"
FACT_CHECK_MODEL = "qwen-plus"
```

## 依赖

- langgraph：图结构编排
- openai：LLM API 调用
- dashscope：阿里云 ASR
- sounddevice：音频采集
- fastapi + uvicorn：WebSocket 服务
- watchdog：文件监控