# 课程评分标准审计

审计日期：2026-10-08；阶段：6A。实现基线为 `38528ce9135f019e958695dc60cd443ed8a61b93`（阶段 5B）。本文件对照原始课程要求，建立实现与证据的映射，不是教师评分或阶段 6B 最终验收结论。

## 原始依据与判定范围

原文为仓库上级目录 [综合实践项目选题与验收标准.docx](../../综合实践项目选题与验收标准.docx)，完整标题为“企业级 AI 软件设计与开发综合实践项目选题与验收标准”。依据为“一、实践说明”“二、所有项目统一完成要求”“三、统一评分标准”及“四、项目选题与专项验收标准”中的第 14 题。评分表是 Word 内嵌图片，已逐行读取；原文件 SHA256 为 `21245dfccb1e9a59630ef27f1aaa2ba6ab7d89971833dac2084f49eecb9c3d5c`，未修改。

课程原件在本工作区上级目录，不随本次 Git 提交；仅克隆仓库时该原件链接不会自动具备，核对原件需使用课程提供的文件。本文件保留标准名称、原分值及必做 / 可选边界以便审计。

原文统一要求：正常启动、核心功能可操作、业务规则真实有效、关键数据持久化、典型异常处理、README 和演示视频。第 14 题必做功能是实验项目创建、批次管理、模型与参数记录、指标记录、实验列表与详情、多实验比较；可视化要求为指标对比、趋势或最优结果。当前实现指标对比与最佳结果，不要求额外增加趋势统计。

原文明确“可选 AI 扩展”不属于必做内容；第 14 题的 AI 自动比较、参数影响总结及实验报告均为可选。现有确定性比较 API 属于必做的结果对比，未接入生成式 AI，不能将两者混淆。其他 19 个选题的文件上传、权限或任务规则不适用于本选题。

状态含义：**已满足**表示仓库实现或本阶段材料有明确证据；**部分满足**表示存在成果但交付或讲解尚缺；**待人工验收**表示需要最终真实操作或主观评价；**不适用**表示不是本题必做项。已满足也不替代教师现场操作，分值仅复制原表，不据此计算预计得分。

证据分三类：6A 本次实跑与只读扫描；既有 pytest 的具体断言；3C–5B 历史 HTTP / 浏览器验证记录。历史记录在文末保留，本次未重新执行浏览器最终验收、创建业务数据或录制视频。

## 统一评分表

| 验收项 | 分值 | 当前实现 | 代码 / 页面证据 | 测试 / 演示证据 | 状态 |
| --- | ---: | --- | --- | --- | --- |
| A 核心功能完成度 | 40 | 项目、批次、实验、模型参数、结果、列表详情、跨实验比较可操作 | [Routers](../backend/app/routers)、[项目页](../frontend/src/views/ProjectManagementView.vue)、[实验页](../frontend/src/views/ExperimentManagementView.vue)、[比较页](../frontend/src/views/ExperimentComparisonView.vue)；下表逐项对应 | [tests](../backend/tests) 与文末 4C–5B 记录；6B 仍须现场完整演示 | 已满足 |
| B 正确性与数据闭环 | 10 | SQLite 持久化、完整更新、最新结果比较、同一响应驱动表与图、受控删除 | [database.py](../backend/app/database.py)、[models.py](../backend/app/models.py)、[results.py](../backend/app/routers/results.py)、[compare.py](../backend/app/routers/compare.py) | `test_result_update_is_visible_on_next_comparison`、两层删除约束测试；历史页面刷新与重新比较 | 已满足 |
| C 业务规则与异常处理 | 10 | Schema、事务回滚和数据库约束共同保护；中文前端错误、404 / 409 / 422 | [schemas.py](../backend/app/schemas.py)、[models.py](../backend/app/models.py)、[errors.ts](../frontend/src/api/errors.ts) | 下文规则证据表；本次 102 个测试通过 | 已满足 |
| D 代码结构与质量 | 10 | Router / Schema / ORM 分层，统一请求与类型、工具函数、独立图表组件 | [app](../backend/app)、[api](../frontend/src/api)、[datetime.ts](../frontend/src/utils/datetime.ts)、[ComparisonCharts.vue](../frontend/src/components/ComparisonCharts.vue) | 只读扫描无遗留调试命中、构建通过、测试数据库隔离；不宣称完成安全或高并发审计 | 已满足 |
| E AI 辅助开发过程 | 10 | 分阶段指令、可追溯提交、五个真实案例、验证过程已整理 | [AI 辅助说明](ai-assisted-development.md)、Git 阶段提交、对应代码和测试 | 书面材料已补齐；学生对关键 Prompt、修改及验证的现场讲解待 6B，没有虚构人工逐行审查记录 | 部分满足 |
| F 界面美观程度 | 5 | 四页入口与管理、统一样式、中文空状态、表格与双图 | [HomeView.vue](../frontend/src/views/HomeView.vue)、[App.vue](../frontend/src/App.vue)、[style.css](../frontend/src/style.css)、比较页及图表组件 | 5B 浏览器回归及 iframe 宽度记录；主观美观评价和 5A AA 实际窗口拖动尚待人工 | 待人工验收 |
| G 演示视频 | 5 | 已有 7 分 30 秒脚本草案与数据，尚无演示视频 | [demo-script.md](demo-script.md) | 6B 才录制、检查播放及交付链接；原文录制时间不限，5–8 分钟是本项目演示安排 | 部分满足 |
| H README / 项目说明 | 5 | 简介、技术、功能、启动、测试、规则、目录、AI 与交付材料、限制可定位 | [README](../README.md) | 本次按真实运行命令和仓库文件检查，构建 / pip check / pytest 可复现；干净环境首次安装待 6B | 已满足 |
| I 开发设计文档 | 5 | 整体架构、模块、模型、API、比较、图表、异常、测试与 AI 流程 | [design.md](design.md)，以及冻结设计和现有 API 文档 | 15 章设计与仓库实现逐项对照；最终讲解与课程提交待 6B | 已满足 |

原表分值合计为 **100**，这里只列标准总分，不给项目打分。

## 核心功能映射

下表分值全部计入 A 的 40 分，不再人为拆分或重复计分。

| 验收项 | 分值 | 当前实现 | 代码 / 页面证据 | 测试 / 演示证据 | 状态 |
| --- | ---: | --- | --- | --- | --- |
| Project 创建 / 查询 / 编辑 / 删除 | 计入 A | POST / GET `/projects`，GET / PUT / DELETE `/projects/{id}` | [projects.py](../backend/app/routers/projects.py)；项目页的 `submitForm`、`removeEntity` | [test_projects.py](../backend/tests/test_projects.py)：creation、put、missing、delete_restrict；4C / 5B 回归 | 已满足 |
| ExperimentBatch 管理 | 计入 A | 项目下创建 / 列表，`/batches/{id}` 查询 / 更新 / 删除 | [batches.py](../backend/app/routers/batches.py)；项目页批次 Card | [test_batches.py](../backend/tests/test_batches.py)：scoped_ordered_list、put_preserves_parent、delete_restrict | 已满足 |
| Experiment 管理及模型名称 | 计入 A | `/batches/{id}/experiments` 创建 / 列表，`/experiments/{id}` 详情 / 更新 / 删除 | [experiments.py](../backend/app/routers/experiments.py)；[实验管理页](../frontend/src/views/ExperimentManagementView.vue) | [test_experiments.py](../backend/tests/test_experiments.py)：creation_normalization_scoped_list、put_full_update、delete | 已满足 |
| parameters JSON | 计入 A | 非空对象，自由键；表单解析 JSON，API 严格验证并持久化 | `schemas._ExperimentInput`；实验页 `parseParameters`、`submitExperiment`；JSON ORM 列 | `test_experiment_invalid_input`、creation、put；4D 嵌套参数与非法 JSON 回归 | 已满足 |
| ExperimentResult | 计入 A | `/experiments/{id}/result` POST 首次录入、GET 查询、PUT 完整更新 | [results.py](../backend/app/routers/results.py)；实验页结果详情 / 表单 | [test_results.py](../backend/tests/test_results.py)：create_read_and_duplicate、put_replaces_metrics、invalid_inputs | 已满足 |
| 实验列表与详情 | 计入 A | 层级实验列表展示编号、模型、参数、备注、时间；选择实验展示当前结果；独立详情 API | `list_batch_experiments`、`get_experiment`；实验页 `loadExperiments`、`loadResult` | 实验 / 结果的 GET 断言；4D / 5B 列表与结果查询，未伪称有单独详情路由页面 | 已满足 |
| 多实验结果比较 | 计入 A | `POST /experiments/compare`，跨项目 / 批次，表格、五项最佳摘要 | [compare.py](../backend/app/routers/compare.py)、[compare.ts](../frontend/src/api/compare.ts)、比较页 `startComparison` | [test_compare.py](../backend/tests/test_compare.py) 共 42 个参数化用例；4E / 5B 跨项目回归 | 已满足 |
| 不同模型指标对比与最优结果可视化 | 计入 A / F，不另设分 | 综合四指标与独立 Loss 柱图，后端最佳 / 并列最佳，精确表格 | [ComparisonCharts.vue](../frontend/src/components/ComparisonCharts.vue)；比较页共用 `comparisonResult` | 5A / 5B 历史双图、空值与最佳标签验证；实际窗口拖动在 F 中留待人工 | 已满足 |
| 生成式 AI 自动分析 / 报告 | — | 原文可选扩展，当前未实现，不影响必做功能审计 | 原文“一、实践说明”及第 14 题“可选 AI 扩展” | 不接外部大模型，不将 AI 辅助开发过程误作产品功能 | 不适用 |

## 数据闭环证据

| 验收项 | 分值 | 当前实现 | 代码 / 页面证据 | 测试 / 演示证据 | 状态 |
| --- | ---: | --- | --- | --- | --- |
| Project → Batch → Experiment → Result → Compare → Visualization | 计入 B | 父资源已存在才能写入，结果通过实验访问，比较只读 | 五个 Router、ORM 外键、两个管理页、比较页和图表组件 | CRUD、关联、结果、比较测试；3C–5B 历史流程 | 已满足 |
| 保存后刷新仍可读取 | 计入 B | 写操作 commit 后返回；SQLite 文件固定路径，列表每次 GET | `database.DATABASE_PATH`、各 Router `_commit_or_conflict`、前端列表加载 | HTTP 层写后读并核对 ORM；4C / 4D 历史页面刷新持久化；6B 再做页面刷新 | 已满足 |
| 修改结果使用最新值 | 计入 B | PUT 更新当前 Result；重新比较重新 SELECT，表与图同时替换同一响应 | `results.update_result`、`compare_experiments`、`startComparison`、`watch(props.result)` | `test_result_update_is_visible_on_next_comparison`；5A / 5B 另一标签修改后重新比较 | 已满足 |
| 删除完整性 | 计入 B | Project / Batch RESTRICT，Experiment → Result CASCADE；失败不破坏数据 | models 外键、删除 Router 的检查 / rollback | API 删除限制、`test_experiment_delete_cascades_result_over_http`、数据库 loaded_result CASCADE | 已满足 |

## 业务规则与异常证据

本表均计入 C 的 10 分；完整 `test_*` 是现有函数标识，其余短名称是函数名关键词或用例要点，便于用 pytest `-k` 或源码定位。

| 验收项 | 分值 | 当前实现 | 代码 / 页面证据 | 测试 / 演示证据 | 状态 |
| --- | ---: | --- | --- | --- | --- |
| Project / Batch 名称 trim 后非空 | 计入 C | strict string、strip、min_length=1 | `schemas.Name`、两个名称表单 | `test_project_invalid_create_input`、`test_batch_invalid_input` | 已满足 |
| model_name 非空 | 计入 C | 同 Name 类型，表单 trim | `_ExperimentInput`、实验页 | `test_experiment_invalid_input` | 已满足 |
| experiment_no trim + uppercase，非空且全局唯一 | 计入 C | 新建 / 更新规范化；更新排除自身；全局查询和 UNIQUE | Schema validator、`_check_number_available`、models | creation_normalization、number_globally_unique、put_full_update_and_own_number、database_unique | 已满足 |
| parameters 必须为非空 JSON object | 计入 C | strict dict，拒绝缺失 / null / {} / 非对象，自由参数键 | Schema 与 `parseParameters` | `test_experiment_invalid_input`；4D 前端 JSON 解析 | 已满足 |
| Result 至少一项非空、可缺失单项 | 计入 C | model validator 与至少一项非 NULL CHECK | `_ExperimentResultInput`、结果表单、models | invalid_inputs_preserve_state、valid_boundaries_and_partial_null、database_checks | 已满足 |
| 四项指标 [0,1]、loss ≥ 0，含边界 0 | 计入 C | Schema ge / le；ORM CHECK；Loss 不设 1 上界 | Schema、models、`parseMetric` | `test_result_valid_boundaries_and_partial_null`、invalid_inputs、database_checks | 已满足 |
| bool / string / NaN / ±Infinity 拒绝 | 计入 C | before validator + allow_inf_nan=False；422 非有限回显转文本 | Schema、`main.validation_error_response` | `test_result_invalid_inputs_preserve_state`、`test_result_nonfinite_http_input_rejected` | 已满足 |
| Experiment 可无 Result；首次 POST、已有 PUT、一份当前结果 | 计入 C | 1:0..1、结果外键 UNIQUE，POST 冲突，PUT 不 upsert | models、results、实验页未录入结果状态 | result_create_read_and_duplicate、missing_resources_and_put_not_upsert、result_experiment_database_unique | 已满足 |
| 父资源存在、Project / Batch 删除限制 | 计入 C | 外键及 Router 404 / 409，禁止关联迁移 | models、projects / batches / experiments | missing_parent_and_resources、put_preserves_parent、两级 API / database RESTRICT | 已满足 |
| 删除 Experiment 同时删除 Result | 计入 C | CASCADE，前端删除提示结果也删除 | models、experiments、实验页删除确认 | HTTP CASCADE 与数据库 CASCADE，含 ORM 已加载结果 | 已满足 |
| Compare 至少两个不同合法 Experiment ID | 计入 C | strict 正整数数组，min_length=2，拒绝重复 | `ExperimentCompareRequest`、比较按钮状态和 ID 去重 | `test_invalid_comparison_request` | 已满足 |
| 跨 Project / Batch / model 比较 | 计入 C | 不限定相同父资源或模型 | `compare_experiments`、比较页跨上下文保留选择 | `test_cross_batch_and_project_comparison` | 已满足 |
| null 不补 0，无 Result 明确标识，0 有效 | 计入 C | result=null / metric=null 原样返回；表显示 -，图保持 null | compare、`metricValue`、图表系列与 Tooltip | missing_result_and_partial_metrics_remain_null、all_experiments_without_results、zero_is_a_valid_best_value | 已满足 |
| 四项 max、loss min、全空无最佳、并列全部返回 | 计入 C | `_best_metric`；前端使用 best_by_metric，不重算 | compare、摘要 / 标签、图表 series | best_value_for_each_metric、tied_best_experiments_follow_input_order、all_experiments_without_results | 已满足 |
| 404 / 409 / 422 与网络异常 | 计入 C | 资源缺失、重复 / 受限、输入错误分别处理；前端中文映射 | Router HTTPException、Schema、`errors.ts`、首页 health | missing 系列、duplicate / conflict / invalid 系列、health_database_unavailable；5B 中文与断开恢复记录 | 已满足 |
| 非法更新不覆盖有效结果 / 事务回滚 | 计入 C | 请求校验在写入前完成，IntegrityError rollback | Schema、各 `_commit_or_conflict` | invalid_inputs_preserve_state、put_conflict_and_protected_fields_preserve_data；3C–3E 提交失败历史验证 | 已满足 |

## 6A 本次运行与扫描记录

| 检查 | 实际结果 | 范围与限制 |
| --- | --- | --- |
| Git 基线 | 工作区干净；HEAD、origin/main、远端 main 均为 38528ce | 提交前再次检查仅含文档变化 |
| `backend/.venv/Scripts/python.exe -m pip check` | No broken requirements found | 未安装或升级依赖 |
| `python -m pytest -q` | 102 passed、0 failed、1 warning，7.15s | 原有 Starlette / httpx 弃用 warning；无 coverage 数据 |
| `frontend/npm run build` | vue-tsc 和 Vite 成功，0 TypeScript / build error；Vite build 5.89s | JS 1,608.74 kB，gzip 526.65 kB，保留 >500 kB warning |
| 数据库 | 四表各 0，文件保留；SHA256 967a673800c80afeea3757b76d9c33865b2cb8542ff686c5120bc86dc0a229b4 | 只读 mode=ro 核对，本阶段没有业务写入 |
| 调试扫描 | TODO、FIXME、HACK、console.log、debugger、@ts-ignore、@ts-nocheck 无命中 | 扫描 backend/app、backend/tests、frontend/src、vite.config.ts，排除依赖 / 构建缓存 |
| 类型与数据扫描 | frontend/src 无显式 any；生产源文件无 Mock、EXP-001/002 等样例或临时 viewport 验收页 | Python 的 Any 用于自由 JSON 参数，测试 fixture 的样例用于隔离数据库，不是产品假数据 |

分层与质量证据还包括：`get_db` 请求级 Session、异常回滚与关闭；模型 UNIQUE / CHECK / 外键；conftest 使用 tmp_path、dependency override、生产连接守卫；前端统一 api 类型、errors.ts、日期 utils、Router、Vite 同源 proxy；图表组件只消费 Compare Response，实例复用并卸载 dispose。已有少量 CRUD 提交辅助函数重复，没有据此扩大重构，也不宣称质量扫描等于完整安全审计。

## 缺口与 6B 交接

真实缺口是演示视频文件 / 链接、学生对关键 Prompt 与改动的讲解、真实浏览器窗口拖动补测、最终环境与全流程人工验收。6A 已补五份交付文档，没有发现原题必做功能缺失或本次构建 / 测试阻断；最终是否通过仍需 6B 与教师操作。

尤其 **5A AA 待人工窗口拖动**：既有容器 / iframe 视口证据不能勾选最终实际窗口调整。参见 [最终验收清单](final-acceptance-checklist.md)。界面美观程度也保留人工评价，不因已有样式而自动给分。

## 历史阶段验证记录

以下保留原 README 的阶段验证信息，属于既有记录，不表示 6A 重做了这些操作；代码与自动测试证据见上表。

阶段 3C 已通过真实 Uvicorn HTTP 调用验证项目和批次的创建、查询、修改、删除、404 / 409 / 422、空列表、名称 trim、列表顺序、只读字段拒绝和数据库提交失败处理。

阶段 3D 已通过 A–X 真实 HTTP 验证，包括实验 CRUD、编号规范化、跨项目全局唯一、PUT 排除自身、参数校验与 Batch RESTRICT 回归。另验证了数据库 UNIQUE、提交时唯一冲突和其他 IntegrityError 的回滚；HTTP 验证数据与临时触发器已清理，四张表记录数均为 0，服务已停止。

阶段 3E 已通过 A–AA 真实 HTTP 验证：结果首次录入、查询、完整更新、数值边界、bool / string / 非有限值拒绝、更新时间和 Experiment 删除 CASCADE 均正常。NaN、Infinity、-Infinity 实测均返回 422；另确认 UNIQUE / CHECK 及提交失败回滚有效。临时数据与触发器已清理，四张表记录数均为 0，服务已停止。

阶段 4A 的 102 个 pytest 全部通过（原 60 个 + 比较 42 个）。真实启动 Uvicorn，使用两个项目、三个批次、四个实验验证跨项目比较、部分指标、无结果、并列最优和 loss 最小；PUT 修改 accuracy 后再次比较立即更新最佳实验。HTTP 验证数据已清理，四张表记录数均为 0，服务已停止。自动测试使用隔离数据库，真实 HTTP 验证按要求使用本地运行数据库并在结束后清理。

阶段 4B 已通过真实浏览器联调：前后端同时启动时首页和 `/api/health` 正常；停止后端再检测显示不可用且页面未崩溃；重新启动后端再检测恢复正常。类型检查与前端构建成功，后端 102 个 pytest 保持通过。后端生产代码和冻结规则未修改；健康检查未写入业务数据。

阶段 4C 已通过 A–Q 真实浏览器验收，覆盖项目与批次 CRUD、trim、同名项目、说明清空、选中项目同步、切换不串批次、刷新后持久化和后端断开 / 恢复；另验证两类删除 409、取消删除及真实 422 错误解析。前端类型检查与构建成功，后端 102 个测试保持通过。临时数据通过正常 API 按子到父顺序清理，最终四张表均为空；后端代码、依赖与冻结规则未修改。

阶段 4D 已通过 A–AH 真实浏览器验收，覆盖层级选择、实验 CRUD、JSON 校验、编号重复中文提示、结果录入与完整更新、null / 0、合法边界、更新时间、删除级联、批次删除限制和后端断开 / 恢复。另验证非法或归属不符的 query 回退、嵌套参数和并发首次录入的 409 恢复；通过实际 HTTP 访问日志核对列表无 Result N+1 请求。前端类型检查与构建成功，后端仍为 102 passed。临时数据通过现有 API 按 Experiment→Batch→Project 清理，四表最终为空；未修改后端生产代码、数据库设计、依赖或冻结规则。

阶段 4E 已通过 A–AI 真实浏览器验收：跨项目 / 批次保留选择、加入顺序、去重、null / 无 Result / 0、并列 Precision、Loss 最小、另一标签修改结果后不重选即读取新最佳值、失效实验 404 及手动恢复、后端断开 / 恢复、清空旧结果及重新加入均正常。另验证无项目 / 批次 / 实验空状态、快速切换不串候选，以及真实 422 经前端工具转换为中文；HTTP 访问日志确认比较只有一次 POST，无逐实验 Result 请求。npm run build 成功，后端仍为 102 passed。临时数据通过现有 API 清理，最终四表均为 0；未增加依赖或修改后端、数据库与冻结规则。

阶段 5A 已通过真实浏览器 A–Z、AB–AF：四项分组柱、独立 Loss、null / 无 Result / 0、并列标签、Loss=0 的可见最佳、Loss=2.5、两类全空状态、另一标签修改 accuracy 后同步更新、选择清空及网络恢复均正常。另验证八个实验与长编号；重新比较实例 ID 保持不变，路由切换后每图仅一个 canvas，无 ECharts / dispose 错误。一次比较的 HTTP 访问日志只有一条 Compare POST，没有额外 Result GET。AA 使用临时容器宽度从 1110px 收窄至 777px 再恢复来验证 ResizeObserver，画布与容器宽度一致、实例不重建且无横向溢出，临时样式已撤回；当前预览工具未能调整实际浏览器窗口，因此 AA 的窗口调整步骤仍待人工确认。npm run build 类型检查及构建成功，JS chunk 为 1,606.83 kB（gzip 526.00 kB），保留 >500 kB warning，不调整打包策略；后端仍为 102 passed。临时数据通过现有 API 按 Experiment→Batch→Project 清理，最终四表均为 0；未修改后端生产代码、依赖、数据库或冻结规则。

阶段 5B 已完成 A–AH 全局回归中的可执行检查：首页入口、四个导航与 active、项目 / 批次 CRUD、实验编辑、结果查询与修改、跨项目比较、精确表格、双图、最佳标签、重新比较、404、五页 title，以及后端停止 / 恢复均正常。另一标签修改 Accuracy 后，重新比较同步读取最新值；独立应用页面控制台无新的 Vue / ECharts error。网络、404、409 的实际页面提示及真实 422 的 errors.ts 解析保持中文；访问日志确认一次重新比较只有一个 Compare POST，无额外 Result GET，首页仅请求 health。

基础响应式使用临时浏览器 iframe 加载真实应用，检查实际 CSS 视口 1440 / 1024 / 768 / 480px：首页入口分别为三 / 三 / 二 / 一列，导航可换行，页面无横向溢出，窄屏 Dialog 在视口内、表格内部可滚动。比较双图从宽到窄再恢复时 canvas 尺寸随容器变化、每图仅一个 canvas、实例不重建，X 轴无明显错位。iframe 验收期间浏览器工具曾记录 MutationObserver.observe 的 Node 类型错误，独立应用页面未复现；没有据此修改业务代码。临时验收页已移除。当前工具仍不能拖动实际预览窗口，因此不将 iframe 视口检查冒充实际窗口验收：**阶段 5A AA 待人工窗口拖动**。

阶段 5B 的 npm run build 类型检查与构建成功，0 TypeScript / build error，JS chunk 为 1,608.74 kB（gzip 526.65 kB），保留 >500 kB warning；后端仍为 102 passed，保留原有 1 个 Starlette / httpx 弃用 warning。验收数据通过现有 API 按 Experiment→Batch→Project 清理，Result 自动 CASCADE，四表最终均为 0。后端生产代码、数据库结构、依赖和冻结业务规则未改动；服务已停止。本阶段没有新增统计、假数据或其他业务功能，未开始阶段 6。
