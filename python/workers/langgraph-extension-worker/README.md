# LangGraph 扩展 Worker 示例

这个目录包含一个使用 `by-framework-langgraph` 扩展库构建的 Worker 示例。

## 场景说明
该 Worker 展示了如何利用通过 `by-framework` 封装的 LangGraph 能力，实现以下典型场景：
1. **远程调用**：当用户询问天气时，智能体会调用 `weather-agent`。
2. **用户交互**：当智能体需要确认信息时，会调用 `ask_user` 向前端发送表单，并等待用户回复。

## 核心特性
- **自动流式处理**：基于 `LangGraphWorker` 基类，无需手动处理 `astream` 和 `emit_chunk`。
- **状态持久化**：自动利用框架的 Checkpoint 机制，支持在 `interrupt` 后正确恢复执行。
- **工具工厂**：使用 `make_remote_agent_tool` 和 `make_ask_user_tool` 快速桥接框架原语。

## 快速开始

### 1. 安装依赖
确保你已经安装了 `by-framework` 的核心库和扩展库：

```bash
# 进入框架 libs 目录进行开发模式安装（示例）
cd ../../../by-framework-python/libs/by-framework-langgraph
pip install -e .
```

然后安装本项目依赖：
```bash
pip install -e .
```

### 2. 配置环境变量
复制 `.env.example` 并配置你的 OpenAI API Key。

```bash
cp .env.example .env
```

### 3. 运行示例
为了演示完整链路，你需要同时启动主 Worker 和模拟天气 Agent：

```bash
# 终端 1：启动主智能体
python main.py

# 终端 2：启动模拟天气智能体
python weather_agent.py
```

## 代码导读
- `main.py`: 包含 `ExtensionDemoWorker` 的实现，展示了 `remote_agent_tool` 的使用。
- `weather_agent.py`: 模拟的天气查询服务。
- `main.py`: 包含 `ExtensionDemoWorker` 的实现。请注意 `build_graph` 如何利用 `self.get_checkpointer()` 管理状态。
