# AIExpHub — AI 模型实验结果管理平台

快速查阅：[项目简介](#项目简介) · [技术栈](#当前技术栈) · [当前功能](#当前功能) · [目录](#基础目录结构) · [后端启动](#后端安装与启动) · [前端启动](#前端安装与启动) · [后端测试](#后端测试) · [核心业务规则](#核心业务规则) · [课程交付文档](#课程交付文档) · [当前限制](#当前限制)

## 项目简介

本项目对应课程综合实践选题第 14 题，是用于管理 AI / 机器学习实验结果的 Web 平台，支持实验项目与批次管理、模型参数与结果指标记录、跨实验比较和可视化分析。项目采用分阶段开发，课程最终验收与交付材料尚未完成。

## 当前技术栈

| 用途 | 技术 |
| --- | --- |
| 前端 | Vue 3 + Vite + TypeScript，Vue Router，Axios（基础工程已初始化） |
| UI | Element Plus（当前全量注册） |
| 图表 | ECharts 6.1.0（按模块引入，Canvas 渲染） |
| 后端 | Python 3.12 + FastAPI + Uvicorn + Pydantic v2 |
| ORM | SQLAlchemy 2.x（已建立四个业务模型与数据库约束） |
| 数据库 | SQLite |
| 测试 | pytest + httpx / FastAPI TestClient（已建立后端验收测试） |

## 当前开发阶段

阶段 1 至阶段 5B 已完成，当前阶段 6A：课程评分标准审计与交付文档已完成。阶段 6B：最终真实验收与演示交付尚未开始；演示视频未录制，阶段 5A AA 仍待实际浏览器窗口拖动。文档准备和既有验证不代表课程最终验收通过。

## 当前功能

后端提供 `/health` 健康检查、Project、ExperimentBatch 和 Experiment CRUD API，以及 ExperimentResult 首次录入、查询和完整更新 API、多实验比较 API、对应的 Pydantic Schema 与请求级数据库 Session。四个 ORM 模型和业务表已建立，核心 API、数据库约束及比较规则已通过 pytest 自动验收。前端已实现首页功能入口与健康状态、Project / Batch 管理、Experiment / Result 管理、Experiment Compare 表格和 ECharts 指标比较可视化，以及明确的 404 页面。

使用顺序：在项目管理创建项目与批次，进入实验管理录入模型、JSON 参数及结果，再到实验比较跨项目加入至少两个实验，查看表格和双图；修改结果后点击重新比较读取最新值。示例数据与 7 分 30 秒演示草案见 [演示脚本](docs/demo-script.md)。

开发由本聊天中的 Codex 按小阶段协助需求分析、领域 / API / 前端代码、测试和调试，使用者确定规则与推进范围，实际测试与 Git 提交控制改动。真实 Prompt 摘要、提交及五个验证案例见 [AI 辅助开发说明](docs/ai-assisted-development.md)，没有在业务产品中接入大模型。原课程明确生成式 AI 扩展为可选，不影响核心验收。

## 课程交付文档

| 文档 | 用途 |
| --- | --- |
| [评分标准审计](docs/acceptance-matrix.md) | 原表 100 分标准的实现 / 证据映射、本次自动检查及历史验证记录，不是项目评分 |
| [整体设计](docs/design.md) | 当前架构、模块、四实体、API、比较算法、图表、异常与测试 |
| [AI 辅助开发说明](docs/ai-assisted-development.md) | 分阶段指令、提交、真实案例与人工审查边界 |
| [最终验收清单](docs/final-acceptance-checklist.md) | 6B 环境、流程、业务规则、真实窗口补测和视频交付，未预先全勾 |
| [演示脚本草案](docs/demo-script.md) | 5–8 分钟顺序、稳定示例数据与清理要求；视频待 6B |
| [需求边界](docs/requirements.md) / [领域模型](docs/domain-model.md) / [校验规则](docs/validation-rules.md) | 保留阶段 2.5 冻结设计和当时范围文字，历史“未实现”不表示当前功能状态 |
| [后端 API](docs/api.md) | 截至 4A 已确定的路径、请求响应及状态码；前端现状见本文与整体设计 |
| [开发计划](docs/development-plan.md) | 6A 与 6B 分开，完成 6A 后停止 |

## 核心业务规则

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

Vue Router 当前提供 `/` 首页、`/projects` 项目管理、`/experiments` 实验管理和 `/compare` 实验比较。首页由简介、三个功能入口 Card 和真实后端健康状态组成；入口通过 Element Plus 按钮进入现有路由，不展示统计或假数据。顶部导航标记当前页面，支持 hover、键盘焦点和窄屏换行，点击 AIExpHub 可回首页。首页加载自动检测后端，显示连接中、服务正常和服务名称，或后端服务不可用；“重新检测”可在后端停止、恢复后更新状态，检测过程中禁用重复点击，保留 aria-live。

Router afterEach 使用 meta.title 设置 document.title：首页为 AIExpHub，业务页为“页面名称 | AIExpHub”。末尾 catch-all 路由显示“404 / 页面不存在 / 当前地址无对应页面。”及“返回首页”按钮，标题为“页面不存在 | AIExpHub”，不自动跳转。通用标题、Card、操作按钮和选择区样式集中在 style.css；首页内容限宽 1040px，业务页保留原有 1200px 布局与表格滚动。

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

比较结果按“最佳指标摘要 → 可视化 → 精确表格”展示。ComparisonCharts.vue 只接收同一份 Compare Response，不请求 API、不计算最优值；Accuracy / Precision / Recall / F1 使用四系列分组柱状图，Y 轴固定 0–1，Loss 使用独立的自适应数值轴（下界为 0）。横轴保持响应中的实验编号顺序，长编号旋转并截断。null 保持缺失、0 保留真实数值，Tooltip 显示原始值或 `-`，不转百分比或归一化。

最佳与并列最佳仅根据 best_by_metric.experiment_ids 显示柱顶标签，loss=0 时标签仍位于零轴上方。综合四项全空或 Loss 全空时分别显示独立空状态。重新比较期间使用加载遮罩，成功后表格与图表同时更新；失败或选择变化清空旧结果。组件复用实例并使用 setOption(notMerge)、ResizeObserver.resize，卸载时 disconnect / dispose。仅新增直接依赖 echarts，采用官方 BarChart、GridComponent、TooltipComponent、LegendComponent、CanvasRenderer 模块；未引入图表包装库或打包插件，初始化及尺寸管理参考 [ECharts 官方说明](https://echarts.apache.org/handbook/en/basics/import/)。

## 后端测试

在 `backend` 目录使用现有 Python 3.12 虚拟环境安装开发依赖并运行：

```powershell
.\.venv\Scripts\python.exe -m pip install -r requirements-dev.txt
.\.venv\Scripts\python.exe -m pytest -q
```

激活虚拟环境后也可使用 `pip install -r requirements-dev.txt` 和 `python -m pytest -q`，或直接 `pytest -q`。

测试通过 FastAPI TestClient 调用实际 HTTP 层，每个用例使用独立的 `tmp_path/test.db` SQLite 数据库并开启外键。Router 的 get_db 和健康检查的 Session 均指向测试数据库；TestClient 不进入生产 lifespan，测试守卫禁止生产 engine 连接或 init_db 执行。测试不会读取、清空或修改 `backend/data/aiexphub.db`。临时目录由 pytest 管理，结束后关闭会话、清空 dependency overrides 并 dispose 测试 engine。

开发依赖固定 pytest 9.1.1、httpx 0.28.1，不改变生产运行依赖。当前有 102 个用例，包含原 60 个用例和新增的 42 个比较用例，覆盖核心 API、数据库第二层约束、比较输入和响应、null / 0、最优与并列、最新结果、单条查询和只读行为；测试文件可独立执行。原 Swagger 测试同步增加比较路径和标签。现有 Starlette 1.7.0 会提示 TestClient 使用 httpx 的第三方弃用 warning，调用仍正常，未为消除 warning 升级框架或加入其他测试依赖。

## 当前限制

- 当前使用本地 SQLite，部署与多人使用方案尚未确定。
- 启动使用 `create_all` 创建缺失表，没有 Alembic，不能自动迁移已有表结构。
- 无登录认证、用户系统或权限管理。
- 不保存比较历史，比较每次读取当前有效结果。
- 无 AI 自动分析、Dashboard / Statistics 或统计聚合接口。
- Element Plus / ECharts 构建仍有 >500 kB chunk warning，不影响当前运行；本阶段未调整打包策略。
- 阶段 5A AA 的真实浏览器窗口拖动验收待人工补充，课程最终验收与交付材料尚未完成。

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

## 验证状态

2026-10-08 阶段 6A：依赖检查无冲突；后端 102 passed、0 failed、1 warning、7.15s；前端类型与构建成功，0 TypeScript / build error，JS chunk 1,608.74 kB（gzip 526.65 kB），保留 >500 kB warning。调试代码扫描无遗留，四表记录数均为 0；仅修改交付文档，未安装依赖、修改生产代码或写入业务数据库。

既有真实 HTTP / 浏览器回归及完整阶段验证信息已集中到 [评分标准审计的历史记录](docs/acceptance-matrix.md#历史阶段验证记录)，不再在本使用说明逐阶段重复。最新比较、null / 0、并列、CASCADE、RESTRICT 和请求量均有代码 / 测试对应证据；本次未重做最终浏览器验收。5A AA 实际窗口拖动、学生讲解与视频交付仍留待 6B，参见未全勾的验收清单。

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
├── frontend/                # 首页、业务管理、比较表格与图表
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
│   │   │   ├── ExperimentComparisonView.vue
│   │   │   └── NotFoundView.vue
│   │   ├── utils/
│   │   │   └── datetime.ts
│   │   ├── components/
│   │   │   └── ComparisonCharts.vue
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
│   ├── api.md               # 已实现 API 的路径与状态码
│   ├── acceptance-matrix.md # 课程评分要求与证据映射
│   ├── design.md            # 当前整体设计
│   ├── ai-assisted-development.md
│   ├── final-acceptance-checklist.md
│   └── demo-script.md       # 演示草案，尚未录制
├── README.md
└── .gitignore
```
