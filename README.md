# AIExpHub — AI 模型实验结果管理平台

## 项目简介

本项目对应课程综合实践选题第 14 题，计划开发一个用于管理 AI / 机器学习实验结果的 Web 平台，逐步支持实验项目管理、实验配置与结果指标记录、多实验比较和可视化分析。

## 当前技术栈（暂定）

| 用途 | 技术 |
| --- | --- |
| 前端 | Vue 3 + Vite + TypeScript |
| UI | Element Plus |
| 图表 | ECharts |
| 后端 | Python 3.12 + FastAPI + Uvicorn |
| ORM | SQLAlchemy 2.x（当前仅建立连接与会话设施） |
| 数据库 | SQLite |
| 测试 | pytest（计划使用，当前未安装或编写） |

## 当前开发阶段

阶段 1、阶段 2、阶段 2.5 已完成。当前为阶段 3A：后端最小可运行工程 + SQLite 数据库连接。

后端提供可启动的 FastAPI 应用、SQLite 连接与会话设施，以及 `/health` 健康检查。尚未创建业务 ORM 模型或业务表，也没有项目、批次、实验、结果或比较功能；前端仍为占位目录。

已确认业务设计保留在 [需求边界](docs/requirements.md)、[领域模型](docs/domain-model.md)和[业务校验规则](docs/validation-rules.md)中，阶段安排见 [阶段开发计划](docs/development-plan.md)。

## 后端安装与启动

后端要求 Python 3.12。首次准备环境时，确认下面的 `python --version` 为 3.12；若默认 Python 版本不同，请用实际 Python 3.12 的可执行文件路径执行创建虚拟环境命令。依赖安装在后端独立虚拟环境中。

从项目根目录进入后端，以下命令适用于 Windows PowerShell：

```powershell
cd backend
python --version
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
.\.venv\Scripts\python.exe -m uvicorn app.main:app --reload
```

当前工作区已创建 Python 3.12 虚拟环境并安装依赖，可直接执行最后一条启动命令。也可先激活 `.venv`，再使用 `python -m uvicorn app.main:app --reload`。

从项目根目录启动时使用：

```powershell
.\backend\.venv\Scripts\python.exe -m uvicorn app.main:app --app-dir backend --reload
```

- 健康检查：<http://127.0.0.1:8000/health>
- Swagger 文档：<http://127.0.0.1:8000/docs>

`/health` 每次请求通过数据库会话执行 `SELECT 1`。成功返回 HTTP 200 和 `{"status":"ok","service":"AIExpHub API"}`；数据库连接失败返回 HTTP 503。按 `Ctrl+C` 停止服务。

SQLite 路径由 `app/database.py` 的实际位置计算，固定为 `backend/data/aiexphub.db`，不受启动时当前目录影响。数据库首次连接时创建文件；当前没有业务表。`.venv`、Python 缓存及数据库文件均由现有 `.gitignore` 忽略。

## 基础目录结构

```text
AIExpHub/
├── backend/
│   ├── app/
│   │   ├── __init__.py
│   │   ├── main.py          # FastAPI 应用与健康检查
│   │   └── database.py      # SQLite engine 与 SessionLocal
│   ├── data/
│   │   └── .gitkeep         # aiexphub.db 为运行时文件，不提交
│   └── requirements.txt
├── frontend/                # 前端工程预留目录
│   └── .gitkeep
├── docs/
│   ├── requirements.md      # 已确认需求、业务规则与待确认事项
│   ├── development-plan.md  # 各阶段目标、产物与验收方式
│   ├── domain-model.md      # 四个核心实体与关系
│   └── validation-rules.md  # 校验规则与预期异常语义
├── README.md
└── .gitignore
```
