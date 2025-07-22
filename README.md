# 🚀 多功能 AI 应用系统

一个基于微服务架构的多功能 AI 应用系统，集成了多种 AI 服务提供商，提供智能对话、文档生成、图表制作、日程管理等功能。

## ✨ 特性

- 🤖 **多 AI 服务商支持**：OpenAI GPT、Anthropic Claude、Google Gemini、DeepSeek
- 🏗️ **微服务架构**：模块化设计，易于扩展和维护
- 📊 **可视化界面**：基于 React + Material-UI 的现代化前端
- 🛠️ **工具服务集成**：PPT生成、图表制作、日程提醒、API文档生成
- ⚙️ **配置管理**：统一的配置管理和状态监控
- 🔌 **RESTful API**：完整的 API 接口和文档

![仪表盘](screenshot/dashboard.png)
![PPT生成器](screenshot/ppt_generator.png)
![图表生成器](screenshot/chart_generator.png)
![设置](screenshot/setting.png)
![原神](screenshot/ppt_example.png)

## 🏛️ 系统架构

```
多功能 AI 应用系统
├── 🎨 Frontend (React + TypeScript)     - 端口 4396
├── 🔧 Backend API (FastAPI)            - 端口 8000
├── 🧠 Agent Core (AI 引擎)              - 端口 8001
└── 🛠️ Tool Services (工具服务)
    ├── 📄 PPT 生成器                    - 端口 8002
    ├── 📈 图表生成器                    - 端口 8003
    ├── 📅 日程提醒器                    - 端口 8004
    └── 📚 API文档生成器                 - 端口 8005
```

## 📋 环境要求

- **Python**: 3.9+
- **Node.js**: 16+
- **Poetry**: 包管理工具
- **npm**: Node.js 包管理器

## 🚀 快速开始

### 1. 环境检查
```bash
python check_env.py
```

### 2. 安装依赖
```bash
# Windows
install_deps.bat

# Linux/Mac
./install_deps.sh
```

### 3. 启动所有服务
```bash
# Windows
start_all.bat

# Linux/Mac
./start_all.sh
```

### 4. 访问应用
- 🎨 **前端应用**: http://localhost:4396
- 🔧 **后端 API**: http://localhost:8000/docs
- 🧠 **Agent API**: http://localhost:8001/docs

## 📁 项目结构

```
ai-app-system/
├── 📁 backend/                 # 后端 API 服务
│   ├── app/                    # 应用代码
│   ├── config.yaml            # 配置文件
│   ├── pyproject.toml         # Python 依赖
│   └── main.py                # 入口文件
├── 📁 frontend/               # 前端应用
│   ├── src/                   # 源代码
│   ├── public/                # 静态资源
│   ├── package.json           # Node.js 依赖
│   └── tsconfig.json          # TypeScript 配置
├── 📁 agent_core/             # AI Agent 核心
│   ├── core/                  # 核心逻辑
│   ├── api/                   # API 接口
│   ├── config.yaml            # Agent 配置
│   └── main.py                # 入口文件
├── 📁 tool_services/          # 工具服务
│   ├── ppt_generator_service/ # PPT 生成服务
│   ├── chart_generator_service/ # 图表生成服务
│   ├── schedule_reminder_service/ # 日程提醒服务
│   └── api_doc_generator_service/ # API文档生成服务
├── 📁 docs/                   # 文档
├── start_all.bat              # 启动脚本 (Windows)
├── stop_all.bat               # 停止脚本 (Windows)
├── install_deps.bat           # 依赖安装脚本 (Windows)
└── check_env.py               # 环境检查脚本
```

## ⚙️ 配置说明

### AI 服务配置

系统支持多种 AI 服务提供商，需要在配置文件中设置相应的 API 密钥：

```yaml
# agent_core/config.yaml
llm_configs:
  gpt:
    api_key: "your-openai-api-key"
    model: "gpt-4"
  anthropic:
    api_key: "your-anthropic-api-key"
    model: "claude-3-opus-20240229"
  gemini:
    api_key: "your-google-api-key"
    model: "gemini-2.0-flash-exp"
  deepseek:
    api_key: "your-deepseek-api-key"
    model: "deepseek-chat"
```

### 数据库配置

系统使用 SQLite 作为默认数据库，支持 PostgreSQL：

```yaml
# backend/config.yaml
database:
  url: "sqlite:///./ai_app.db"
  # 或使用 PostgreSQL
  # url: "postgresql://user:password@localhost/dbname"
```

## 🛠️ 开发指南

### 后端开发
```bash
cd backend
poetry shell
poetry install
uvicorn main:app --reload --port 8000
```

### 前端开发
```bash
cd frontend
npm install
npm start
```

### Agent 核心开发
```bash
cd agent_core
poetry shell
poetry install
python main.py
```

### 添加新的工具服务

1. 在 `tool_services/` 目录下创建新服务
2. 实现 FastAPI 应用
3. 更新启动脚本添加新服务
4. 在 Agent 核心中注册工具

## 🧪 测试

```bash
# 后端测试
cd backend
poetry run pytest

# Agent 核心测试
cd agent_core
poetry run pytest

# 前端测试
cd frontend
npm test
```

## 📊 监控和日志

- **日志目录**: 各服务的日志文件位于对应目录下
- **健康检查**: 每个服务都提供 `/health` 端点
- **配置状态**: Agent 核心提供配置状态查看功能

## 🔧 常见问题

### 服务启动失败
1. 检查端口是否被占用
2. 确认所有依赖已正确安装
3. 检查配置文件是否正确

### AI 服务连接失败
1. 验证 API 密钥是否正确
2. 检查网络连接
3. 确认配置格式正确

### 前端页面无法访问
1. 确认前端服务已启动
2. 检查端口 4396 是否可用
3. 查看浏览器控制台错误信息


## 📄 许可证

本项目采用 MIT 许可证 - 详见 [LICENSE](LICENSE) 文件

## 📞 支持

如果您遇到任何问题或有建议，请通过以下方式联系：

- 提交 [Issue](../../issues)
- 发送邮件至项目维护者
- 查看 [文档](docs/) 获取更多信息

---

⭐ 如果这个项目对您有帮助，请给我们一个星标！
