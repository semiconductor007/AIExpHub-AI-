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
| ORM | SQLAlchemy 2.x（核心实体、项目指标定义及结果映射模板） |
| 数据库 | SQLite |
| 测试 | pytest + httpx / FastAPI TestClient（已建立后端验收测试） |

## 当前开发阶段

阶段 1 至阶段 6A 已完成，阶段 6B 的核心页面闭环已有验证，实际窗口拖动、学生讲解和视频交付仍待人工完成。2026-10-13 完成另行授权的 JSON 自动填入、项目共享指标、文件与批量导入、基准差值比较与复杂 JSON 映射增量，并于 2026-10-24 完成复制配置、项目级映射模板及比较页轻量自动同步；2026-10-27 增加比较导出和可选 AI 总结。当前正在进行一次小范围工程化收口：只拆分实验配置与结果录入表单，补齐前端统一测试入口；比较页、后端结构、数据库和业务 API 不在本次范围内。最新 pytest 为 249 passed、1 warning，前端 74 个测试和 TypeScript / build 通过；用户原有数据保留，AI 已完成合成数据真实调用验收。此次功能交付不代表课程最终验收通过。10 月 8 日的 6B 检查记录见 [最终验收报告](docs/final-acceptance-report.md)。

## 当前功能

2026-10-27 完成页面流程收敛：项目列表进入工作区，默认查看项目全部实验，批次作为筛选；详情使用抽屉，批次和指标按需管理。实验列表勾选后直接比较，地址可恢复选择；比较使用表格、可视化、AI 总结三个标签页。使用与验收见 [项目工作区与比较流程](docs/workspace-navigation.md)。 指标表格已改为指标按行、实验按列的对照表，支持指标筛选、空指标展开及固定基准的实验分组，完整 CSV 不受筛选影响；见 [指标对照表](docs/comparison-table.md)。

2026-10-27 增加可选 DeepSeek 实验总结：同项目实验可预览允许发送的指标和参数，确认后手动生成五章节总结；事实由后端计算，数据变化后旧总结明确标为过期。后端读取 `backend/.env`，公开模板默认关闭，配置后启用；已使用独立测试库的合成实验完成 deepseek-flash 真实调用验收（约 6.23 秒），不涉及已有实验数据。模型仅引用证据，实验 / 指标关联由后端派生；单次成功不保证所有自然语言准确。配置、API 和验证见 [AI 实验总结](docs/ai-experiment-summary.md)。

2026-10-27 完成比较结果导出：比较表可下载 CSV（含自定义指标、最佳 / 并列结果和可选基准差值），系统指标与自定义指标图可单独下载带标题、单位、时间和完整编号的 PNG。每次导出先获取最新比较，失败不导出旧数据；生成期间固定快照并保留通知待处理。前端 55 个测试与 TypeScript / build 通过，使用与验证见 [比较结果导出](docs/comparison-export.md)。

2026-10-24 完成比较页轻量自动同步：首次比较后，同源标签页保存相关结果 / 配置 / 指标定义，以及切回已打开的比较页时自动获取最新比较。连续通知合并、隐藏页等待恢复可见；选择、基准和图例开关保留。网络失败保留上次数据并标明未更新，已知实验删除则清除旧表图；手动重新比较保留。未增加服务器推送、轮询或后端接口。详见 [使用与验证](docs/comparison-auto-sync.md)。

2026-10-24 完成录入效率改进：实验列表“复制配置”预填模型、独立参数及备注，填写新编号后可保存到同项目其他批次，新实验不携带旧结果。结果弹窗可保存、使用、重命名、更新和删除项目级 JSON 映射模板；每次提取新文件数值，失效路径 / 指标须明确处理，应用后仍可手动修正。旧库先备份再新增模板表，原记录保留。使用、API 与验收见 [录入效率改进](docs/entry-efficiency.md)。

2026-10-13 根据用户反馈增加复杂结果 JSON 识别与映射：可保留日志 / 元数据，按项目指标展示嵌套路径候选，多候选由用户选定，不同字段名可以手动映射。复杂模式先确认，再填入选定指标，未映射项保留当前输入；平铺指标继续自动填入。无关内容不写入 Result，指标范围与类型校验保持严格。该次前端 24 个测试、后端 184 个测试和 build 通过，见 [复杂 JSON 使用说明](docs/result-json-mapping.md)。

2026-10-13 完成 I1：比较页可从已选实验中指定基准，表格保留原始指标与最佳标签，额外展示绝对差值及改善 / 退步 / 无变化；缺失结果和跨项目自定义指标明确提示无法比较。换基准清空旧结果，重新比较读取最新数据；图表继续展示原始值。该次 I1 验证为后端 184 个测试、前端 7 个测试和 build 通过，使用规则见 [基准差值比较](docs/baseline-comparison.md)。I2 配置复制与 E2 映射模板已于 2026-10-24 完成。

2026-10-13 新增 JSON 文件录入、项目模板下载和批量导入预览：实验管理选好批次后，上传文件、逐行核对 / 修正，再确认整批新增。重复编号或非法指标不覆盖已有数据；确认时重新校验，失败整批回滚。单结果文件自动填入后仍可手动修正。该次导入验证为后端 169 个测试、文件读取 4 个测试通过，TypeScript / build 通过，原有数据保留。格式、限制和验证见 [JSON 文件与批量导入](docs/json-file-import.md)。

后端提供 `/health` 健康检查、Project、ExperimentBatch 和 Experiment CRUD API，以及 ExperimentResult 首次录入、查询和完整更新 API、多实验比较 API、对应的 Pydantic Schema 与请求级数据库 Session。核心四个 ORM 模型及项目指标定义已建立，核心 API、数据库约束及比较规则已通过 pytest 自动验收。前端已实现首页功能入口与健康状态、Project / Batch 管理、Experiment / Result 管理、Experiment Compare 表格和 ECharts 指标比较可视化，以及明确的 404 页面。

2026-10-13 完成经用户授权的项目级共享指标增量：在项目管理中选中项目后新增指标键、名称、单位、最佳方向和可选上下限，所有批次与实验共用定义，分别记录数值。结果 JSON 自动识别项目指标，比较表格和独立图表按项目、单位、方向展示最佳及并列结果。已有数值引用的定义仅允许改显示名称；原五项指标、跨项目比较和已有数据保留。该次共享指标验证为 139 passed、1 warning（16.60s），TypeScript / build 通过。使用、API、升级与真实验证见 [项目共享指标](docs/project-metrics-proposal.md)，课程人工验收仍待完成。

使用顺序：在项目管理创建并进入项目，在工作区管理批次、录入模型、JSON 参数及结果，勾选至少两个实验后直接比较；比较页可额外跨项目添加实验，切换表格、可视化和 AI 总结标签；同源页面修改结果后自动同步，切回比较页检查最新值，也可手动重新比较。示例数据与 7 分 30 秒演示草案见 [演示脚本](docs/demo-script.md)。

2026-10-12 经用户另行确认，增加结果 JSON 快速录入：在“录入结果”或“编辑结果”弹窗粘贴指标对象后自动填入表单，核对或修改下方数值后点击“保存结果”；“重新填入指标”仅用于再次应用 JSON。未提供或为 null 的指标会清空对应输入，非法 JSON 不覆盖已填内容并阻止保存，可修改 JSON 或清空后手动录入。示例与本次验证见 [JSON 快速录入说明](docs/result-json-entry.md)。此增量改进不表示阶段 6B 人工验收已完成。

开发由本聊天中的 Codex 按小阶段协助需求分析、领域 / API / 前端代码、测试和调试，使用者确定规则与推进范围，实际测试与 Git 提交控制改动。真实 Prompt 摘要、提交及五个验证案例见 [AI 辅助开发说明](docs/ai-assisted-development.md)。业务产品现已增加独立的可选 DeepSeek 总结入口，需用户配置后启用；原课程明确生成式 AI 扩展为可选，不影响核心验收。

## 课程交付文档

| 文档 | 用途 |
| --- | --- |
| [评分标准审计](docs/acceptance-matrix.md) | 原表 100 分标准的实现 / 证据映射、本次自动检查及历史验证记录，不是项目评分 |
| [整体设计](docs/design.md) | 当前架构、模块、四实体、API、比较算法、图表、异常与测试 |
| [AI 辅助开发说明](docs/ai-assisted-development.md) | 分阶段指令、提交、真实案例与人工审查边界 |
| [最终验收清单](docs/final-acceptance-checklist.md) | 6B 环境、流程、业务规则、真实窗口补测和视频交付，未预先全勾 |
| [最终验收报告](docs/final-acceptance-report.md) | 本次 6B 真实环境、自动检查、页面操作和人工待办；当前停在窗口检查点 |
| [演示脚本草案](docs/demo-script.md) | 5–8 分钟顺序、稳定示例数据与清理要求；视频待 6B |
| [需求边界](docs/requirements.md) / [领域模型](docs/domain-model.md) / [校验规则](docs/validation-rules.md) | 保留阶段 2.5 冻结设计和当时范围文字，历史“未实现”不表示当前功能状态 |
| [后端 API](docs/api.md) | 截至 4A 已确定的路径、请求响应及状态码；前端现状见本文与整体设计 |
| [开发计划](docs/development-plan.md) | 6B 当前进度、验收与人工交付边界 |

## 核心业务规则

已确认业务设计保留在 [需求边界](docs/requirements.md)、[领域模型](docs/domain-model.md)和[业务校验规则](docs/validation-rules.md)中，阶段安排见 [阶段开发计划](docs/development-plan.md)。

已实现接口及状态码见 [当前 API](docs/api.md)。名称 trim 后非空，列表按 id ASC 返回；PUT 完整更新 name / description，省略或传 null 的 description 会清空。输入不接受 id、created_at 或 Batch 的 project_id；删除项目或批次时保留 RESTRICT 规则，存在子记录返回 409。资源不存在返回 404，输入校验失败返回 422。

Experiment 编号在 Schema 中 trim + uppercase，应用层检查全局唯一，数据库 UNIQUE 提供第二层保护；模型名称 trim 后非空，parameters 必须为非空 JSON object、参数键不固定。Experiment PUT 完整更新编号、模型、参数和备注，省略 notes 或传 null 会清空，不允许移动所属 Batch。实验可以没有 Result，响应暂不包含结果；提供批次内及项目内全部实验列表。

Result 通过 `/experiments/{experiment_id}/result` 访问：POST 仅首次创建，重复录入返回 409；GET / PUT 区分实验不存在与结果未录入，均返回对应 404，PUT 不执行 upsert。系统与自定义指标合计至少一项非 null，允许整数和浮点数，拒绝 bool、string、NaN / Infinity；前四项范围 [0, 1]，loss >= 0。PUT 完整替换指标，省略项清空，真实修改后 updated_at 刷新。没有 Result DELETE 或全局结果列表。

`POST /experiments/compare` 接收至少两个不同的严格正整数 ID，允许跨项目、批次和模型，按输入顺序返回实验。缺失结果或指标保持 null；accuracy / precision / recall / f1 取最大，loss 取最小，并列最优全部返回，全空指标没有最佳实验。每次只读查询最新 Result，不保存或缓存比较结果；请求非法返回 422，实验不存在返回包含缺失 ID 的 404。详细结构见 [当前 API](docs/api.md)。

## Windows 一键启动

首次按下文准备 Python / Node 和依赖后，双击根目录 `启动平台.cmd`，等待检查与服务就绪，浏览器将打开 `http://127.0.0.1:5173/`；用完双击 `停止平台.cmd`。支持重复启动复用、明确的端口冲突提示、启动失败清理和手动诊断；启动成功后检查结束，不新增运行期间轮询。环境准备、日志和故障处理见 [一键启动说明](docs/local-startup.md)。原有手动启动方式保留如下。

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

Vue Router 当前提供 `/` 首页、`/projects` 项目管理、`/experiments` 项目工作区和 `/compare` 实验比较。首页通过关系卡片解释项目、批次和实验，提供各页面功能导航及六步可点击使用流程；结构示例明确标注为非真实数据。“新建实验”选择项目后直达表单，无项目或无批次时先引导创建，保存后继续；“创建项目”直达创建表单，快捷操作取消或刷新不重复弹窗。详见 [首页介绍与首次使用引导](docs/home-guide.md)。顶部导航标记当前页面，支持 hover、键盘焦点和窄屏换行，点击 AIExpHub 可回首页。首页页尾显示真实后端服务状态，首次加载检查一次，保留手动重新检测和 aria-live，不持续轮询。

Router afterEach 使用 meta.title 设置 document.title：首页为 AIExpHub，业务页为“页面名称 | AIExpHub”。末尾 catch-all 路由显示“404 / 页面不存在 / 当前地址无对应页面。”及“返回首页”按钮，标题为“页面不存在 | AIExpHub”，不自动跳转。通用标题、Card、操作按钮和选择区样式集中在 style.css；首页与业务页沿用 1200px 容器，首页关系卡片和步骤在窄屏重新排列，业务表格保留滚动。

项目管理集中创建、编辑和删除项目，“进入项目”打开工作区。工作区按需打开批次管理及共享指标管理弹窗。项目与批次名称 trim 后非空，允许同名；空说明传 null。原有子资源删除限制保持不变。

API 文件复用统一 client，批次创建与列表使用 `/projects/{id}/batches`，编辑、删除使用 `/batches/{id}`，不移动所属项目。errors.ts 解析后端 detail 字符串、422 数组及网络错误；项目存在批次、批次存在实验的 409 显示中文提示，不自动删除子资源。加载、提交和删除有独立状态防止重复操作；切换项目时忽略旧批次请求。日期使用原生 Intl.DateTimeFormat，后端无偏移的 UTC 时间按 UTC 解析，失败时显示原始值，不增加日期依赖。

项目工作区默认请求当前项目全部实验，批次仅筛选列表；切换筛选保留项目内勾选，切换项目清空。支持旧 projectId / batchId 链接，非法或不匹配批次明确提示并显示项目全部实验。各层请求计数器阻止过期响应覆盖新选择。详情抽屉按需加载 Result，关闭后保留筛选和勾选；新建和导入明确选择所属批次。

实验表单对编号 trim + uppercase、模型名称 trim 后检查非空；多行参数使用 JSON.parse 校验为非空对象，允许自由键和嵌套对象。PUT 完整提交四个可编辑字段，空备注传 null，不发送 batch_id。结果未录入的特定 404 显示空状态；首次录入 POST、已有结果 PUT，共用按项目定义生成的指标表单。空输入传 null，有限数值须满足范围，至少一项非空且 0 合法；保存后重新 GET 最新结果和更新时间。null 显示 `-`，0 显示 `0`，不转换百分比或固定小数位。删除实验需确认已有结果也将删除，使用已有后端 CASCADE，不提供 Result DELETE。

实验列表勾选后进入比较，通过 ids 和可选 baseline 地址参数恢复选择、读取最新实验与批次资料并自动执行普通比较。候选实验移入“添加实验”弹窗，已选实验使用紧凑名单。表格、可视化、AI 总结共用选择和基准；AI 保留手动确认生成。无 Result 或缺失指标保持为空、0 保留，最佳与并列使用后端响应；失效实验明确标记，可移除后重试。添加、移除、清空或改变基准会清空旧比较。此页面不写实验或结果，不保存比较历史。

所有 API 调用通过统一 Axios client（baseURL=`/api`，timeout=10000ms），HealthResponse 和 getHealth() 有明确类型。Vite 开发代理将 `/api` 请求转发至 `http://127.0.0.1:8000` 并移除前缀，例如 `/api/health` → `/health`，参见 [Vite proxy 文档](https://vite.dev/config/server-options.html#server-proxy)。浏览器始终请求前端同源路径，后端没有添加 CORS，未加入认证拦截器、重试或缓存；部署配置留待后续确定。

```powershell
npm run build
npm run preview
```

build 执行 `vue-tsc -b && vite build`，先类型检查，再生成 `frontend/dist/`。Element Plus 按本阶段要求全量注册，构建有大于 500 kB 的 JS chunk 提示，构建成功；没有添加按需导入或包优化插件。node_modules、dist 和 TS 构建缓存均由根目录 .gitignore 忽略。

比较结果在“指标表格”和“可视化”标签分别展示精确数据与图表。ComparisonCharts.vue 接收同一份 Compare Response，不请求 API、不计算最优值；Accuracy / Precision / Recall / F1 使用四系列分组柱状图，Y 轴固定 0–1，Loss 使用独立数值轴（下界为 0）。图表标签首次打开才挂载，切回时刷新尺寸；null 保持缺失、0 保留原值，Tooltip 显示原始值或 `-`。

最佳与并列最佳仅根据 best_by_metric.experiment_ids 显示柱顶标签，loss=0 时标签仍位于零轴上方。综合四项全空或 Loss 全空时分别显示独立空状态。重新比较期间使用加载遮罩，成功后表格与图表同时更新；网络更新失败保留旧结果并显示明确提示，资源不存在或选择变化清空旧结果。组件复用实例、保留图例显示状态并使用 setOption(notMerge)、ResizeObserver.resize，卸载时 disconnect / dispose。仅新增直接依赖 echarts，采用官方 BarChart、GridComponent、TooltipComponent、LegendComponent、CanvasRenderer 模块；未引入图表包装库或打包插件，初始化及尺寸管理参考 [ECharts 官方说明](https://echarts.apache.org/handbook/en/basics/import/)。

## 后端测试

在 `backend` 目录使用现有 Python 3.12 虚拟环境安装开发依赖并运行：

```powershell
.\.venv\Scripts\python.exe -m pip install -r requirements-dev.txt
.\.venv\Scripts\python.exe -m pytest -q
```

激活虚拟环境后也可使用 `pip install -r requirements-dev.txt` 和 `python -m pytest -q`，或直接 `pytest -q`。

测试通过 FastAPI TestClient 调用实际 HTTP 层，每个用例使用独立的 `tmp_path/test.db` SQLite 数据库并开启外键。Router 的 get_db 和健康检查的 Session 均指向测试数据库；TestClient 不进入生产 lifespan，测试守卫禁止生产 engine 连接或 init_db 执行。测试不会读取、清空或修改 `backend/data/aiexphub.db`。临时目录由 pytest 管理，结束后关闭会话、清空 dependency overrides 并 dispose 测试 engine。

开发依赖固定 pytest 9.1.1；httpx 0.28.1 同时用于测试与 AI 运行请求，python-dotenv 1.2.4 用于本地配置。当前有 249 个用例，包含原业务 / 数据库用例和 AI 快照、配置、调用与异常用例；AI 测试使用模拟 HTTP，不产生费用。测试覆盖严格校验、数据库约束、项目隔离、最新结果、差值与缺失原因、只读预览、整批回滚、引用保护和迁移保留 / 回滚；测试文件可独立执行。现有 Starlette 1.7.0 会提示 TestClient 使用 httpx 的第三方弃用 warning，调用仍正常，未为消除 warning 升级框架。前端使用 Node 内置测试运行器，在 `frontend` 执行 `npm test`（等价于 `node --test tests/*.test.ts`），当前 74 个测试通过，无额外测试依赖。

## 当前限制

- 当前使用本地 SQLite，部署与多人使用方案尚未确定。
- 启动提供本次结果表升级与备份，随后使用 `create_all` 创建缺失表；没有 Alembic 或通用版本迁移系统。
- 无登录认证、用户系统或权限管理。
- 不保存比较历史，比较每次读取当前有效结果。
- AI 总结需配置后手动确认发送，已完成合成数据真实调用验收；没有自动付费分析、总结历史、Dashboard / Statistics 或统计聚合接口。
- Element Plus / ECharts 构建仍有 >500 kB chunk warning，不影响当前运行；本阶段未调整打包策略。
- 阶段 5A AA 的真实浏览器窗口拖动验收待人工补充，课程最终验收与交付材料尚未完成。

## 当前数据库层

应用启动时调用 `init_db()`，注册模型并检测旧结果表；需要时先备份并事务升级，再执行 `create_all` 创建缺失表、安装指标约束触发器：

- `projects`
- `experiment_batches`
- `experiments`
- `experiment_results`
- `project_metrics`

本次指定升级保留旧结果的 ID、五项指标和时间，新增 custom_metrics 初始化为 {}；重复启动跳过已完成升级。备份位置和安全边界见 [共享指标说明](docs/project-metrics-proposal.md#sqlite-升级和备份)，不删除或清空原数据库。

每个新数据库连接通过 engine 的 `connect` 事件执行 `PRAGMA foreign_keys=ON`。Project → Batch、Batch → Experiment 使用 RESTRICT；Experiment → Result 使用 CASCADE。ORM 双向关系使用 `back_populates`，父端设置 `passive_deletes="all"`，由数据库处理删除，避免 ORM 将子记录外键改为 NULL；实验结果关系为可选单条结果。

实验编号全局 UNIQUE，结果的 `experiment_id` UNIQUE。结果表 CHECK 保证四项 [0,1]、非负 loss、JSON 对象与有效非空结果；SQLite 触发器另验证自定义值的有限数值、项目归属和范围，保护已使用定义。创建时间使用系统 UTC 时间，结果的 `updated_at` 在 ORM 更新时刷新；原生 SQL 更新不会触发 ORM 的 onupdate。

数据库提供第二层完整性保护，Project 与 Batch 名称、Experiment 编号与模型名称、非空 JSON object 和结果指标的输入校验已在 Schema 实现。422 错误回显中的非有限值转为文本，避免响应序列化失败；非法指标不会保存。实验参数仍没有 JSON 扩展 CHECK。参数列使用 `JSON(none_as_null=True)`，使 Python None 作为 SQL NULL 接受 NOT NULL 约束检查。

已实际验证外键开启、两级 RESTRICT、两项 UNIQUE、指标范围、全空结果拒绝、合法边界及结果 CASCADE。本轮临时验证数据经正常 API 清理，用户已有数据保持不变；数据库与升级备份不提交。

## 验证状态

2026-10-08 阶段 6A：依赖检查无冲突；后端 102 passed、0 failed、1 warning、7.15s；前端类型与构建成功，0 TypeScript / build error，JS chunk 1,608.74 kB（gzip 526.65 kB），保留 >500 kB warning。调试代码扫描无遗留，四表记录数均为 0；仅修改交付文档，未安装依赖、修改生产代码或写入业务数据库。

既有真实 HTTP / 浏览器回归及完整阶段验证信息已集中到 [评分标准审计的历史记录](docs/acceptance-matrix.md#历史阶段验证记录)，不再在本使用说明逐阶段重复。最新比较、null / 0、并列、CASCADE、RESTRICT 和请求量均有代码 / 测试对应证据；本次未重做最终浏览器验收。5A AA 实际窗口拖动、学生讲解与视频交付仍留待 6B，参见未全勾的验收清单。

## 基础目录结构

```text
AIExpHub/
├── 启动平台.cmd             # Windows 一键检查、启动与打开首页
├── 停止平台.cmd             # 停止本工具管理且核验通过的服务
├── scripts/
│   ├── manage-local.ps1     # 启动、停止、手动诊断
│   └── tests/run-tests.ps1  # 独立 PowerShell 脚本验收
├── backend/
│   ├── app/
│   │   ├── __init__.py
│   │   ├── main.py          # 初始化、Router 注册与健康检查
│   │   ├── database.py      # Base、连接、get_db 与 init_db
│   │   ├── models.py        # 核心模型、共享指标与约束
│   │   ├── migrations.py    # 旧结果表指定升级与备份
│   │   ├── metric_constraints.py # 自定义指标 SQLite 触发器
│   │   ├── comparison_deltas.py # 已加载指标的基准差值计算
│   │   ├── mapping_schemas.py # 结果映射模板请求 / 响应
│   │   ├── schemas.py       # 业务实体与比较请求 / 响应 Schema
│   │   └── routers/
│   │       ├── __init__.py
│   │       ├── projects.py
│   │       ├── batches.py
│   │       ├── experiments.py
│   │       ├── compare.py
│   │       ├── results.py
│   │       ├── metrics.py
│   │       ├── mapping_templates.py # 项目级结果路径模板
│   │       └── imports.py     # 模板、只读预览与整批事务导入
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
│   │   ├── test_database_constraints.py
│   │   ├── test_project_metrics.py
│   │   ├── test_metric_migration.py
│   │   ├── test_imports.py
│   │   ├── test_baseline_compare.py
│   │   └── test_mapping_templates.py
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
│   │   │   ├── metrics.ts
│   │   │   ├── mapping-templates.ts
│   │   │   ├── imports.ts
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
│   │   │   ├── datetime.ts
│   │   │   ├── json-files.ts
│   │   │   ├── metric-delta.ts
│   │   │   ├── comparison-changes.ts
│   │   │   ├── comparison-refresh.ts
│   │   │   ├── comparison-export.ts
│   │   │   ├── chart-export-layout.ts
│   │   │   ├── chart-image.ts
│   │   │   ├── download.ts
│   │   │   ├── experiment-copy.ts
│   │   │   ├── experiment-parameters.ts
│   │   │   ├── mapping-templates.ts
│   │   │   └── json-metrics.ts
│   │   ├── components/
│   │   │   ├── ExperimentFormDialog.vue
│   │   │   ├── ExperimentParametersEditor.vue
│   │   │   ├── ExperimentResultDialog.vue
│   │   │   ├── ComparisonCharts.vue
│   │   │   ├── CustomMetricChart.vue
│   │   │   ├── ProjectMetrics.vue
│   │   │   ├── ExperimentImport.vue
│   │   │   ├── MetricDeltaDisplay.vue
│   │   │   ├── ResultMappingTemplates.vue
│   │   │   └── ResultJsonMapper.vue
│   │   ├── App.vue
│   │   ├── main.ts
│   │   └── style.css
│   ├── index.html
│   ├── tests/                # 使用 Node 内置测试运行器
│   │   ├── experiment-parameters.test.ts
│   │   ├── json-files.test.ts
│   │   ├── metric-delta.test.ts
│   │   ├── comparison-sync.test.ts
│   │   ├── comparison-export.test.ts
│   │   ├── experiment-copy.test.ts
│   │   ├── mapping-templates.test.ts
│   │   └── json-metrics.test.ts
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
│   ├── result-json-entry.md
│   ├── json-file-import.md
│   ├── baseline-comparison.md
│   ├── result-json-mapping.md
│   ├── comparison-auto-sync.md
│   ├── comparison-export.md
│   ├── entry-efficiency.md
│   ├── improvement-plan.md
│   ├── project-metrics-proposal.md # 共享指标设计、使用与验证
│   └── demo-script.md       # 演示草案，尚未录制
├── README.md
└── .gitignore
```
