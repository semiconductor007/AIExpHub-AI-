# AIExpHub — AI 模型实验结果管理平台

## 项目简介

本项目对应课程综合实践选题第 14 题，计划开发一个用于管理 AI / 机器学习实验结果的 Web 平台，逐步支持实验项目管理、实验配置与结果指标记录、多实验比较和可视化分析。

## 当前技术栈（暂定）

| 用途 | 技术 |
| --- | --- |
| 前端 | Vue 3 + Vite + TypeScript |
| UI | Element Plus |
| 图表 | ECharts |
| 后端 | Python 3.12 + FastAPI + Uvicorn + Pydantic v2 |
| ORM | SQLAlchemy 2.x（已建立四个业务模型与数据库约束） |
| 数据库 | SQLite |
| 测试 | pytest（计划使用，当前未安装或编写） |

## 当前开发阶段

阶段 1、阶段 2、阶段 2.5、阶段 3A、阶段 3B 已完成。当前为阶段 3C：Project + ExperimentBatch 基础 API。

后端提供 `/health` 健康检查、Project 和 ExperimentBatch CRUD API、对应的 Pydantic Schema 与请求级数据库 Session。四个 ORM 模型和业务表已建立；Experiment、ExperimentResult、比较、统计及前端功能尚未实现。当前没有 pytest、认证或迁移工具。

已确认业务设计保留在 [需求边界](docs/requirements.md)、[领域模型](docs/domain-model.md)和[业务校验规则](docs/validation-rules.md)中，阶段安排见 [阶段开发计划](docs/development-plan.md)。

已实现接口及状态码见 [当前 API](docs/api.md)。名称 trim 后非空，列表按 id ASC 返回；PUT 完整更新 name / description，省略或传 null 的 description 会清空。输入不接受 id、created_at 或 Batch 的 project_id；删除项目或批次时保留 RESTRICT 规则，存在子记录返回 409。资源不存在返回 404，输入校验失败返回 422。

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

SQLite 路径由 `app/database.py` 的实际位置计算，固定为 `backend/data/aiexphub.db`，不受启动时当前目录影响。`.venv`、Python 缓存及数据库文件均由现有 `.gitignore` 忽略。

## 当前数据库层

应用启动时调用 `init_db()`，先加载 `app.models` 注册模型，再执行 `Base.metadata.create_all(bind=engine)`，创建缺失的本地 SQLite 表：

- `projects`
- `experiment_batches`
- `experiments`
- `experiment_results`

当前开发阶段采用 `create_all` 初始化，重复启动不会重复创建已有表，但它不会迁移或修改已有表结构。后续需要正式迁移能力时再讨论 Alembic，本阶段未引入。

每个新数据库连接通过 engine 的 `connect` 事件执行 `PRAGMA foreign_keys=ON`。Project → Batch、Batch → Experiment 使用 RESTRICT；Experiment → Result 使用 CASCADE。ORM 双向关系使用 `back_populates`，父端设置 `passive_deletes="all"`，由数据库处理删除，避免 ORM 将子记录外键改为 NULL；实验结果关系为可选单条结果。

实验编号全局 UNIQUE，结果的 `experiment_id` UNIQUE。结果表的六个命名 CHECK 保证四项 [0, 1] 指标、非负 loss 和至少一项指标非 NULL。创建时间使用系统 UTC 时间，结果的 `updated_at` 在 ORM 更新时刷新；原生 SQL 更新不会触发 ORM 的 onupdate。

数据库提供第二层完整性保护，Project 与 Batch 名称的非空白校验已在 Schema 实现。实验编号 trim + uppercase、非空 JSON object，以及指标布尔值、NaN / Infinity 等输入校验留待后续应用层；没有添加 SQLite JSON 扩展 CHECK。参数列使用 `JSON(none_as_null=True)`，使 Python None 作为 SQL NULL 接受 NOT NULL 约束检查。

已实际验证外键开启、两级 RESTRICT、两项 UNIQUE、指标范围、全空结果拒绝、合法边界及结果 CASCADE。临时验证数据已回滚，当前四张业务表均为空，数据库文件不提交。

本阶段另已通过真实 Uvicorn HTTP 调用验证项目和批次的创建、查询、修改、删除、404 / 409 / 422、空列表、名称 trim、列表顺序、只读字段拒绝和数据库提交失败处理。HTTP 验证数据已清理，四张表记录数均为 0。

## 基础目录结构

```text
AIExpHub/
├── backend/
│   ├── app/
│   │   ├── __init__.py
│   │   ├── main.py          # 初始化、Router 注册与健康检查
│   │   ├── database.py      # Base、连接、get_db 与 init_db
│   │   ├── models.py        # 四个业务 ORM 模型与数据库约束
│   │   ├── schemas.py       # Project 与 Batch 输入输出 Schema
│   │   └── routers/
│   │       ├── __init__.py
│   │       ├── projects.py
│   │       └── batches.py
│   ├── data/
│   │   └── .gitkeep         # aiexphub.db 为运行时文件，不提交
│   └── requirements.txt
├── frontend/                # 前端工程预留目录
│   └── .gitkeep
├── docs/
│   ├── requirements.md      # 已确认需求、业务规则与待确认事项
│   ├── development-plan.md  # 各阶段目标、产物与验收方式
│   ├── domain-model.md      # 四个核心实体与关系
│   ├── validation-rules.md  # 校验规则与预期异常语义
│   └── api.md               # 已实现 API 的路径与状态码
├── README.md
└── .gitignore
```
