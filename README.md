# AIExpHub — AI 模型实验结果管理平台

## 项目简介

本项目对应课程综合实践选题第 14 题，计划开发一个用于管理 AI / 机器学习实验结果的 Web 平台，逐步支持实验项目管理、实验配置与结果指标记录、多实验比较和可视化分析。

## 当前技术栈（暂定）

| 用途 | 技术 |
| --- | --- |
| 前端 | Vue 3 + Vite + TypeScript，Vue Router，Axios（基础工程已初始化） |
| UI | Element Plus（当前全量注册） |
| 图表 | ECharts（计划采用，尚未安装） |
| 后端 | Python 3.12 + FastAPI + Uvicorn + Pydantic v2 |
| ORM | SQLAlchemy 2.x（已建立四个业务模型与数据库约束） |
| 数据库 | SQLite |
| 测试 | pytest + httpx / FastAPI TestClient（已建立后端验收测试） |

## 当前开发阶段

阶段 1 至阶段 4D 已完成。当前为阶段 4E：实验比较前端页面（表格版），已完成并验收。完成本阶段后停止，等待下一阶段指令。

后端提供 `/health` 健康检查、Project、ExperimentBatch 和 Experiment CRUD API，以及 ExperimentResult 首次录入、查询和完整更新 API、多实验比较 API、对应的 Pydantic Schema 与请求级数据库 Session。四个 ORM 模型和业务表已建立，核心 API、数据库约束及比较规则已通过 pytest 自动验收。前端已实现首页健康状态、Project / Batch 管理、Experiment / Result 管理和 Experiment Compare 表格页面；ECharts、Dashboard / Statistics 和 AI 分析尚未实现，当前没有认证或迁移工具。

已确认业务设计保留在 [需求边界](docs/requirements.md)、[领域模型](docs/domain-model.md)和[业务校验规则](docs/validation-rules.md)中，阶段安排见 [阶段开发计划](docs/development-plan.md)。

已实现接口及状态码见 [当前 API](docs/api.md)。名称 trim 后非空，列表按 id ASC 返回；PUT 完整更新 name / description，省略或传 null 的 description 会清空。输入不接受 id、created_at 或 Batch 的 project_id；删除项目或批次时保留 RESTRICT 规则，存在子记录返回 409。资源不存在返回 404，输入校验失败返回 422。

Experiment 编号在 Schema 中 trim + uppercase，应用层检查全局唯一，数据库 UNIQUE 提供第二层保护；模型名称 trim 后非空，parameters 必须为非空 JSON object、参数键不固定。Experiment PUT 完整更新编号、模型、参数和备注，省略 notes 或传 null 会清空，不允许移动所属 Batch。实验可以没有 Result，响应暂不包含结果；当前只提供批次内实验列表。

Result 通过 `/experiments/{experiment_id}/result` 访问：POST 仅首次创建，重复录入返回 409；GET / PUT 区分实验不存在与结果未录入，均返回对应 404，PUT 不执行 upsert。五项指标至少一项非 null，允许整数和浮点数，拒绝 bool、string、NaN / Infinity；前四项范围 [0, 1]，loss >= 0。PUT 完整替换指标，省略项清空，真实修改后 updated_at 刷新。没有 Result DELETE 或全局结果列表。

`POST /experiments/compare` 接收至少两个不同的严格正整数 ID，允许跨项目、批次和模型，按输入顺序返回实验。缺失结果或指标保持 null；accuracy / precision / recall / f1 取最大，loss 取最小，并列最优全部返回，全空指标没有最佳实验。每次只读查询最新 Result，不保存或缓存比较结果；请求非法返回 422，实验不存在返回包含缺失 ID 的 404。详细结构见 [当前 API](docs/api.md)。

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

## 前端安装与启动

工程使用官方 create-vite 的 vue-ts 模板初始化，直接位于 `frontend/`。本工作区验证环境为 Node v24.15.0、npm 11.12.1；所选 Vite 8 要求 Node 20.19+ 或 22.12+，参见 [Vite 官方初始化说明](https://vite.dev/guide/)。无需安装全局前端工具。

先在一个终端按上文启动 FastAPI（`127.0.0.1:8000`），再在另一个终端从项目根目录执行：

```powershell
cd frontend
npm install
npm run dev
```

按 Vite 输出的实际地址访问，默认是 `http://localhost:5173`。本阶段实际联调使用 `http://127.0.0.1:5173`。保留并提交 package-lock.json；需要严格按锁文件重新安装时可使用 `npm ci`。

Vue Router 当前提供 `/` 首页、`/projects` 项目管理、`/experiments` 实验管理和 `/compare` 实验比较。顶部导航标记当前页面，点击 AIExpHub 可回首页。首页加载自动检测后端，显示连接中、服务正常和服务名称，或后端服务不可用；“重新检测”可在后端停止、恢复后更新状态，检测过程中禁用重复点击。

项目管理采用上下两张卡片：项目列表支持新建、编辑、删除和查看批次；批次列表只加载当前选中项目的数据，未选择时不请求批次 API。两类名称提交前 trim 并校验非空，允许同名；创建和完整更新只提交 name / description，空说明传 null。保存后刷新列表，当前选中项目的名称和说明同步更新；删除前确认，成功后刷新，删除选中项目时清空选择与批次。

API 文件复用统一 client，批次创建与列表使用 `/projects/{id}/batches`，编辑、删除使用 `/batches/{id}`，不移动所属项目。errors.ts 解析后端 detail 字符串、422 数组及网络错误；项目存在批次、批次存在实验的 409 显示中文提示，不自动删除子资源。加载、提交和删除有独立状态防止重复操作；切换项目时忽略旧批次请求。日期使用原生 Intl.DateTimeFormat，后端无偏移的 UTC 时间按 UTC 解析，失败时显示原始值，不增加日期依赖。

实验管理使用项目→批次→实验的选择流程，切换父资源清空下级选择和结果；各层请求计数器阻止过期响应覆盖新选择。项目管理的批次行可通过“管理实验”携带 projectId / batchId 跳转；仅在 ID 合法、项目存在且批次归属匹配时自动选择，否则回退手动选择。列表只请求当前批次的实验，不逐条请求 Result；用户查看结果或创建后自动选中新实验时才加载对应结果。

实验表单对编号 trim + uppercase、模型名称 trim 后检查非空；多行参数使用 JSON.parse 校验为非空对象，允许自由键和嵌套对象。PUT 完整提交四个可编辑字段，空备注传 null，不发送 batch_id。结果未录入的特定 404 显示空状态；首次录入 POST、已有结果 PUT，共用五指标表单。空输入传 null，有限数值须满足范围，至少一项非空且 0 合法；保存后重新 GET 最新结果和更新时间。null 显示 `-`，0 显示 `0`，不转换百分比或固定小数位。删除实验需确认已有结果也将删除，使用已有后端 CASCADE，不提供 Result DELETE。

实验比较分为候选实验、已选实验与比较结果三个区域。候选按项目→批次加载，已选项可跨项目 / 批次保留，以 ID 去重并按加入顺序排列；项目和批次名称作为加入时的本地展示元数据，不写入 localStorage。至少两项才可比较，每次只调用一次 `POST /experiments/compare`，结果表保持响应顺序，名称缺失或关联不符时回退为 Project #ID / Batch #ID，不额外查询名称或结果。无 Result 的实验保留且明确标识，缺失指标显示 `-`、0 显示 `0`；最佳标签、并列摘要和方向完全使用后端 best_by_metric，不在前端重算。添加、移除或清空选择会清空旧比较结果，请求期间禁用选择修改；重新比较重新读取当前 Result。失效实验的 404 和比较 422 显示中文，错误时保留选择供手动修正；此页面不修改实验或结果，不保存比较历史。

所有 API 调用通过统一 Axios client（baseURL=`/api`，timeout=10000ms），HealthResponse 和 getHealth() 有明确类型。Vite 开发代理将 `/api` 请求转发至 `http://127.0.0.1:8000` 并移除前缀，例如 `/api/health` → `/health`，参见 [Vite proxy 文档](https://vite.dev/config/server-options.html#server-proxy)。浏览器始终请求前端同源路径，后端没有添加 CORS，未加入认证拦截器、重试或缓存；部署配置留待后续确定。

```powershell
npm run build
npm run preview
```

build 执行 `vue-tsc -b && vite build`，先类型检查，再生成 `frontend/dist/`。Element Plus 按本阶段要求全量注册，构建有大于 500 kB 的 JS chunk 提示，构建成功；没有添加按需导入或包优化插件。node_modules、dist 和 TS 构建缓存均由根目录 .gitignore 忽略。

## 后端测试

在 `backend` 目录使用现有 Python 3.12 虚拟环境安装开发依赖并运行：

```powershell
.\.venv\Scripts\python.exe -m pip install -r requirements-dev.txt
.\.venv\Scripts\python.exe -m pytest -q
```

激活虚拟环境后也可使用 `pip install -r requirements-dev.txt` 和 `python -m pytest -q`，或直接 `pytest -q`。

测试通过 FastAPI TestClient 调用实际 HTTP 层，每个用例使用独立的 `tmp_path/test.db` SQLite 数据库并开启外键。Router 的 get_db 和健康检查的 Session 均指向测试数据库；TestClient 不进入生产 lifespan，测试守卫禁止生产 engine 连接或 init_db 执行。测试不会读取、清空或修改 `backend/data/aiexphub.db`。临时目录由 pytest 管理，结束后关闭会话、清空 dependency overrides 并 dispose 测试 engine。

开发依赖固定 pytest 9.1.1、httpx 0.28.1，不改变生产运行依赖。当前有 102 个用例，包含原 60 个用例和新增的 42 个比较用例，覆盖核心 API、数据库第二层约束、比较输入和响应、null / 0、最优与并列、最新结果、单条查询和只读行为；测试文件可独立执行。原 Swagger 测试同步增加比较路径和标签。现有 Starlette 1.7.0 会提示 TestClient 使用 httpx 的第三方弃用 warning，调用仍正常，未为消除 warning 升级框架或加入其他测试依赖。

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

阶段 4A 的 102 个 pytest 全部通过（原 60 个 + 比较 42 个）。真实启动 Uvicorn，使用两个项目、三个批次、四个实验验证跨项目比较、部分指标、无结果、并列最优和 loss 最小；PUT 修改 accuracy 后再次比较立即更新最佳实验。HTTP 验证数据已清理，四张表记录数均为 0，服务已停止。自动测试使用隔离数据库，真实 HTTP 验证按要求使用本地运行数据库并在结束后清理。

阶段 4B 已通过真实浏览器联调：前后端同时启动时首页和 `/api/health` 正常；停止后端再检测显示不可用且页面未崩溃；重新启动后端再检测恢复正常。类型检查与前端构建成功，后端 102 个 pytest 保持通过。后端生产代码和冻结规则未修改；健康检查未写入业务数据。

阶段 4C 已通过 A–Q 真实浏览器验收，覆盖项目与批次 CRUD、trim、同名项目、说明清空、选中项目同步、切换不串批次、刷新后持久化和后端断开 / 恢复；另验证两类删除 409、取消删除及真实 422 错误解析。前端类型检查与构建成功，后端 102 个测试保持通过。临时数据通过正常 API 按子到父顺序清理，最终四张表均为空；后端代码、依赖与冻结规则未修改。

阶段 4D 已通过 A–AH 真实浏览器验收，覆盖层级选择、实验 CRUD、JSON 校验、编号重复中文提示、结果录入与完整更新、null / 0、合法边界、更新时间、删除级联、批次删除限制和后端断开 / 恢复。另验证非法或归属不符的 query 回退、嵌套参数和并发首次录入的 409 恢复；通过实际 HTTP 访问日志核对列表无 Result N+1 请求。前端类型检查与构建成功，后端仍为 102 passed。临时数据通过现有 API 按 Experiment→Batch→Project 清理，四表最终为空；未修改后端生产代码、数据库设计、依赖或冻结规则。

阶段 4E 已通过 A–AI 真实浏览器验收：跨项目 / 批次保留选择、加入顺序、去重、null / 无 Result / 0、并列 Precision、Loss 最小、另一标签修改结果后不重选即读取新最佳值、失效实验 404 及手动恢复、后端断开 / 恢复、清空旧结果及重新加入均正常。另验证无项目 / 批次 / 实验空状态、快速切换不串候选，以及真实 422 经前端工具转换为中文；HTTP 访问日志确认比较只有一次 POST，无逐实验 Result 请求。npm run build 成功，后端仍为 102 passed。临时数据通过现有 API 清理，最终四表均为 0；未增加依赖或修改后端、数据库与冻结规则。

## 基础目录结构

```text
AIExpHub/
├── backend/
│   ├── app/
│   │   ├── __init__.py
│   │   ├── main.py          # 初始化、Router 注册与健康检查
│   │   ├── database.py      # Base、连接、get_db 与 init_db
│   │   ├── models.py        # 四个业务 ORM 模型与数据库约束
│   │   ├── schemas.py       # 业务实体与比较请求 / 响应 Schema
│   │   └── routers/
│   │       ├── __init__.py
│   │       ├── projects.py
│   │       ├── batches.py
│   │       ├── experiments.py
│   │       ├── compare.py
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
│   │   ├── test_compare.py
│   │   └── test_database_constraints.py
│   ├── pytest.ini
│   ├── requirements-dev.txt
│   └── requirements.txt
├── frontend/                # 首页、业务管理与实验比较表格
│   ├── src/
│   │   ├── api/
│   │   │   ├── client.ts
│   │   │   ├── health.ts
│   │   │   ├── projects.ts
│   │   │   ├── batches.ts
│   │   │   ├── experiments.ts
│   │   │   ├── results.ts
│   │   │   ├── compare.ts
│   │   │   └── errors.ts
│   │   ├── router/
│   │   │   └── index.ts
│   │   ├── views/
│   │   │   ├── HomeView.vue
│   │   │   ├── ProjectManagementView.vue
│   │   │   ├── ExperimentManagementView.vue
│   │   │   └── ExperimentComparisonView.vue
│   │   ├── utils/
│   │   │   └── datetime.ts
│   │   ├── App.vue
│   │   ├── main.ts
│   │   └── style.css
│   ├── index.html
│   ├── package.json
│   ├── package-lock.json
│   ├── tsconfig.json
│   ├── tsconfig.app.json
│   ├── tsconfig.node.json
│   └── vite.config.ts
├── docs/
│   ├── requirements.md      # 已确认需求、业务规则与待确认事项
│   ├── development-plan.md  # 各阶段目标、产物与验收方式
│   ├── domain-model.md      # 四个核心实体与关系
│   ├── validation-rules.md  # 校验规则与预期异常语义
│   └── api.md               # 已实现 API 的路径与状态码
├── README.md
└── .gitignore
```
