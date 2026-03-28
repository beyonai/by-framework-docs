# By-Framework Python Client Sample

这是一个使用 `uv` 进行项目管理的 Python 客户端示例，演示了如何向 `by-framework` Gateway 发送消息。

## 特性
- **uv 管理**: 使用 `pyproject.toml` 定义依赖。
- **Workspace 集成**: 自动关联主仓库中的 `by-framework` 核心库。
- **流式响应**: 内置监听逻辑，支持获取 Worker 的实时输出。

## 快速上手

### 1. 准备环境
由于该项目已集成在 `by-framework-samples` 的 workspace 中，请在根目录或本目录下执行：

```bash
uv sync
```

### 2. 配置环境变量
复制示例配置文件并根据需要修改：

```bash
cp .env.example .env
```

### 3. 运行项目

**首先确保至少有一个 Worker 已开启**，例如：
```bash
cd ../workers/langgraph-worker
uv run python main.py
```

**在本目录下运行客户端:**
```bash
uv run python main.py
```

## 开发说明
项目主要逻辑位于 `main.py` 中。您可以根据需要扩展更多指令发送或响应处理逻辑。
