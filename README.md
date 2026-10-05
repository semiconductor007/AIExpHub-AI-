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
| 测试 | pytest + httpx / FastAPI TestClient（已建立后端验收测试） |

## 当前开发阶段

阶段 1、阶段 2、阶段 2.5、阶段 3A、阶段 3B、阶段 3C、阶段 3D、阶段 3E 已完成。当前为阶段 3F：后端 pytest 自动化验收。

后端提供 `/health` 健康检查、Project、ExperimentBatch 和 Experiment CRUD API，以及 ExperimentResult 首次录入、查询和完整更新 API、对应的 Pydantic Schema 与请求级数据库 Session。四个 ORM 模型和业务表已建立，核心 API 与数据库约束已通过 pytest 自动验收；比较、统计及前端功能尚未实现，当前没有认证或迁移工具。

已确认业务设计保留在 [需求边界](docs/requirements.md)、[领域模型](docs/domain-model.md)和[业务校验规则](docs/validation-rules.md)中，阶段安排见 [阶段开发计划](docs/development-plan.md)。

已实现接口及状态码见 [当前 API](docs/api.md)。名称 trim 后非空，列表按 id ASC 返回；PUT 完整更新 name / description，省略或传 null 的 description 会清空。输入不接受 id、created_at 或 Batch 的 project_id；删除项目或批次时保留 RESTRICT 规则，存在子记录返回 409。资源不存在返回 404，输入校验失败返回 422。

Experiment 编号在 Schema 中 trim + uppercase，应用层检查全局唯一，数据库 UNIQUE 提供第二层保护；模型名称 trim 后非空，parameters 必须为非空 JSON object、参数键不固定。Experiment PUT 完整更新编号、模型、参数和备注，省略 notes 或传 null 会清空，不允许移动所属 Batch。实验可以没有 Result，响应暂不包含结果；当前只提供批次内实验列表。

Result 通过 `/experiments/{experiment_id}/result` 访问：POST 仅首次创建，重复录入返回 409；GET / PUT 区分实验不存在与结果未录入，均返回对应 404，PUT 不执行 upsert。五项指标至少一项非 null，允许整数和浮点数，拒绝 bool、string、NaN / Infinity；前四项范围 [0, 1]，loss >= 0。PUT 完整替换指标，省略项清空，真实修改后 updated_at 刷新。没有 Result DELETE 或全局结果列表。

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

## 后端测试

在 `backend` 目录使用现有 Python 3.12 虚拟环境安装开发依赖并运行：

```powershell
.\.venv\Scripts\python.exe -m pip install -r requirements-dev.txt
.\.venv\Scripts\python.exe -m pytest -q
```

激活虚拟环境后也可使用 `pip install -r requirements-dev.txt` 和 `python -m pytest -q`，或直接 `pytest -q`。

测试通过 FastAPI TestClient 调用实际 HTTP 层，每个用例使用独立的 `tmp_path/test.db` SQLite 数据库并开启外键。Router 的 get_db 和健康检查的 Session 均指向测试数据库；TestClient 不进入生产 lifespan，测试守卫禁止生产 engine 连接或 init_db 执行。测试不会读取、清空或修改 `backend/data/aiexphub.db`。临时目录由 pytest 管理，结束后关闭会话、清空 dependency overrides 并 dispose 测试 engine。

开发依赖固定 pytest 9.1.1、httpx 0.28.1，不改变生产运行依赖。当前有 60 个用例，覆盖 Project / Batch / Experiment / Result 的核心规则和数据库第二层约束；测试文件可独立执行。现有 Starlette 1.7.0 会提示 TestClient 使用 httpx 的第三方弃用 warning，调用仍正常，未为消除 warning 升级框架或加入其他测试依赖。

## 当前数据库层

应用启动时调用 `init_db()`，先加载 `app.models` 注册模型，再执行 `Base.metadata.create_all(bind=engine)`，创建缺失的本地 SQLite 表：

- `projects`
- `experiment_batches`
- `experiments`
- `experiment_results`

当前开发阶段采用 `create_all` 初始化，重复启动不会重复创建已有表，但它不会迁移或修改已有表结构。后续需要正式迁移能力时再讨论 Alembic，本阶段未引入。

每个新数据库连接通过 engine 的 `connect` 事件执行 `PRAGMA foreign_keys=ON`。Project → Batch、Batch → Experiment 使用 RESTRICT；Experiment → Result 使用 CASCADE。ORM 双向关系使用 `back_populates`，父端设置 `passive_deletes="all"`，由数据库处理删除，避免 ORM 将子记录外键改为 NULL；实验结果关系为可选单条结果。

实验编号全局 UNIQUE，结果的 `experiment_id` UNIQUE。结果表的六个命名 CHECK 保证四项 [0, 1] 指标、非负 loss 和至少一项指标非 NULL。创建时间使用系统 UTC 时间，结果的 `updated_at` 在 ORM 更新时刷新；原生 SQL 更新不会触发 ORM 的 onupdate。

数据库提供第二层完整性保护，Project 与 Batch 名称、Experiment 编号与模型名称、非空 JSON object 和结果指标的输入校验已在 Schema 实现。422 错误回显中的非有限值转为文本，避免响应序列化失败；非法指标不会保存。没有添加 SQLite JSON 扩展 CHECK。参数列使用 `JSON(none_as_null=True)`，使 Python None 作为 SQL NULL 接受 NOT NULL 约束检查。

已实际验证外键开启、两级 RESTRICT、两项 UNIQUE、指标范围、全空结果拒绝、合法边界及结果 CASCADE。临时验证数据已回滚，当前四张业务表均为空，数据库文件不提交。

阶段 3C 已通过真实 Uvicorn HTTP 调用验证项目和批次的创建、查询、修改、删除、404 / 409 / 422、空列表、名称 trim、列表顺序、只读字段拒绝和数据库提交失败处理。

阶段 3D 已通过 A–X 真实 HTTP 验证，包括实验 CRUD、编号规范化、跨项目全局唯一、PUT 排除自身、参数校验与 Batch RESTRICT 回归。另验证了数据库 UNIQUE、提交时唯一冲突和其他 IntegrityError 的回滚；HTTP 验证数据与临时触发器已清理，四张表记录数均为 0，服务已停止。

阶段 3E 已通过 A–AA 真实 HTTP 验证：结果首次录入、查询、完整更新、数值边界、bool / string / 非有限值拒绝、更新时间和 Experiment 删除 CASCADE 均正常。NaN、Infinity、-Infinity 实测均返回 422；另确认 UNIQUE / CHECK 及提交失败回滚有效。临时数据与触发器已清理，四张表记录数均为 0，服务已停止。

## 基础目录结构

```text
AIExpHub/
├── backend/
│   ├── app/
│   │   ├── __init__.py
│   │   ├── main.py          # 初始化、Router 注册与健康检查
│   │   ├── database.py      # Base、连接、get_db 与 init_db
│   │   ├── models.py        # 四个业务 ORM 模型与数据库约束
│   │   ├── schemas.py       # Project、Batch、Experiment 与 Result Schema
│   │   └── routers/
│   │       ├── __init__.py
│   │       ├── projects.py
│   │       ├── batches.py
│   │       ├── experiments.py
│   │       └── results.py
│   ├── data/
│   │   └── .gitkeep         # aiexphub.db 为运行时文件，不提交
│   ├── tests/
│   │   ├── conftest.py
│   │   ├── test_health.py
│   │   ├── test_projects.py
│   │   ├── test_batches.py
│   │   ├── test_experiments.py
│   │   ├── test_results.py
│   │   └── test_database_constraints.py
│   ├── pytest.ini
│   ├── requirements-dev.txt
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
