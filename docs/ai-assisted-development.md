# AI 辅助开发说明

本文记录 AIExpHub 的真实开发方式，供课程审阅和学生准备现场讲解。使用工具是本项目聊天中的 Codex；没有证据表明使用了 Cursor、Copilot、Claude Code 等其他工具，不将课程允许的工具列表写成实际使用经历。业务产品没有接入生成式 AI API。

## 开发方式与人工职责

使用者选择第 14 题、提出技术栈、规定每个小阶段的目标与禁止项，并逐步确认领域关系、编号、参数、删除和比较规则。AI 阅读仓库、按阶段产生代码 / 文档、执行运行命令、测试和联调，再按授权通过现有 Git 身份提交 main。过程为：需求确认 → 小阶段提示 → AI 编码 → 实际运行 → 测试 / 验证 → Git 提交 → 下一阶段。

人工审查的已知部分是对选题、范围和关键业务决定的确认，以及逐阶段发出继续指令。文档不声称学生已逐行审查全部 AI 代码、亲自执行全部测试或完成教师验收。6B 需要学生实际阅读并能解释核心实现，不能用“AI 做了”替代口头说明。

## 关键指令与提交证据

下表的指令是本聊天中实际阶段要求的摘要，不是补造的逐字完整 Prompt。规则冻结行保留几个原指令短句。完整聊天不在 Git 仓库内，课堂可展示保留的真实聊天；本表用可核对的提交与文件支撑改动。

| 阶段 / 指令要点 | AI 参与与产物 | 已有提交 |
| --- | --- | --- |
| 1：只建基础目录与需求边界，“不要编写大量业务代码” | 检查现状、目录、README 与计划，未一次生成整个业务平台 | `87b47d5` chore: initialize AIExpHub project structure |
| 2 / 2.5：四实体；调整为 1:0..1；“trim + uppercase”；参数非空 JSON object；删除与比较冻结 | 领域图、校验文档及需求同步，先冻结再建数据库 | `b67229f`、`d3aa9d8` |
| 3A / 3B：先最小后端连接，再只做数据库层 | FastAPI lifespan / health、SQLAlchemy 模型、外键与约束 | `e0165ef`、`531c77d` |
| 3C / 3D / 3E：项目批次 → 实验 → 当前结果 API | Schema、Router、事务、编号与数值校验 | `4146a87`、`1e195df`、`5c98ce6` |
| 3F：不增加功能，只固化 pytest 验收 | tmp_path 数据库、HTTP / 数据库约束测试，隔离生产连接 | `5cc9a46` test: add backend API and database test suite |
| 4A：至少两个不同实验，null 与并列最佳，最新结果 | Compare Request / Response、一次查询、42 个比较用例 | `48c9ec1` feat: add experiment comparison API |
| 4B / 4C / 4D：基础工程 → 项目批次 → 实验结果前端 | Axios / Router / proxy、局部错误解析、表单、层级选择 | `eefd0cb`、`ca4741e`、`5622f5a` |
| 4E：比较表格，复用已有接口、不逐项查询结果 | 跨项目保留已选实验、一次 POST、null 与最佳标签 | `3fc9e4e` feat: add experiment comparison UI |
| 5A：现有比较页增加 ECharts，不改后端 | 综合四指标与独立 Loss 图、响应复用、resize / dispose | `b08db72` feat: add experiment comparison charts |
| 5B：入口、导航、404、title、样式；不增统计或假数据 | 首页与 UI 整理、真实数据回归、空状态、文档 | `38528ce` feat: polish frontend experience |
| 6A：原课程审计与交付材料，不开发新功能 | 读取原文评分图片、代码与测试核对、五份文档及 README / 计划同步 | 本次独立文档提交，使用 Git log 定位 |

提交可用 `git show <SHA>` 检查，不能仅把提交标题当作测试通过证据。自动测试和历史 HTTP / 浏览器记录的来源分别是代码及 [acceptance-matrix.md](acceptance-matrix.md)。

## AI 在各环节中的作用

需求分析时，AI 将第 14 题的项目、批次、模型参数、指标、比较和可视化整理成第一版范围；具体规则由使用者确认。阶段拆分避免同时引入前端、数据库和业务接口，明确禁止登录、训练调度、AI 接入等扩展。

数据模型环节，AI 协助表达四实体关系、选择 SQLite 外键 / UNIQUE / CHECK，以及当前结果的可选单条关联。API 环节，按逐实体阶段生成 Pydantic Schema、Router 和 request-scoped Session；接口路径、完整 PUT 与错误语义通过文档和测试固定。

前端环节，AI 建立 TypeScript API 类型、Axios client、Element Plus 表单 / 表格、层级选择、局部中文错误和比较选择状态。ECharts 环节将相同 Compare Response 用于两张图，保留 null、真实 0 和后端最佳值。没有在前端生成静态结果或接入 AI 模型充当数据来源。

调试与验收环节，AI 使用实际命令、HTTP 层测试及既有真实浏览器操作核对行为；访问日志确认请求数量，排查数值错误响应、并发 / 过期加载、组件实例与图表缩放。前端编译、后端测试以及数据库状态都在提交前检查，不根据文字描述宣称功能通过。

## 真实案例 1 指标类型与非有限值

Python 的 bool 可以被当作数值，字符串数字可能被框架自动转换；非标准 JSON NaN / Infinity 还可能出现在校验错误回显中。使用者要求合法数值校验，AI 协助在 `_ExperimentResultInput.require_numeric_metric` 明确拒绝 bool 和非 int / float，以 `allow_inf_nan=False` 拒绝非有限值；`main.validation_error_response` 将回显中的非有限 float 转为文本，保证错误响应仍是合法 JSON。

不是仅接受生成的校验代码：3E 有真实 HTTP 验证记录；[test_results.py](../backend/tests/test_results.py) 的 `test_result_invalid_inputs_preserve_state` 与 `test_result_nonfinite_http_input_rejected` 实际发送非法 Body，断言 422、错误可解析和原数据未被破坏。6A 复跑整套测试保持通过，才将该项列为有证据支撑。

## 真实案例 2 null 与并列最佳

比较规则由使用者明确：缺失不能补 0，0 是真实值，四项 max、loss min，全空无最佳，允许多个并列最佳。AI 将规则实现为 [compare.py](../backend/app/routers/compare.py) 的 `_best_metric`，判断 `value is not None`，全空返回 null / []，相等值收集所有 ID。

[test_compare.py](../backend/tests/test_compare.py) 固定缺失结果、部分 null、0、每项最佳、并列顺序及精确浮点行为，防止之后“简化”时把合法 0 丢掉。最佳结论来自后端，前端标签不自行重算。这些是实际代码与测试，不是自动生成的自然语言实验分析。

## 真实案例 3 比较避免 N+1

AI 协助比较接口用 joinedload 一条 SELECT 获取实验及关联当前结果；前端 `compareExperiments` 每次发送一次 POST，图表不调用 API，也不为已选实验逐个 GET Result。

验证同时检查两层：[test_compare.py](../backend/tests/test_compare.py) 的 `test_comparison_is_one_read_query_without_commits_or_database_changes` 捕获实际 SQL，断言仅一条 SELECT、禁止 commit、比较前后表内容不变；4E / 5A / 5B 的实际 HTTP 访问日志确认一次比较只有 Compare POST，没有额外 Result GET。这里依据访问日志，没有把它写成未执行过的浏览器 Network 面板检查。

## 真实案例 4 Loss 独立数值轴

四个比例指标在 [0,1]，Loss 没有 1 的上界。使用者指定可视化业务含义，AI 生成四指标分组柱与独立 Loss 图；[ComparisonCharts.vue](../frontend/src/components/ComparisonCharts.vue) 将比例 Y 轴固定 0–1，而 Loss 从 0 起自适应。

5A 历史浏览器验证包括 Loss=2.5、Loss=0 最佳标签、缺失指标、两类全空状态和并列。此设计经过实际可视化检查，并未把所有指标直接放在同一尺度或转换为百分比。图表只消费响应，精确数值同时保留在表格。

## 真实案例 5 生成结果后仍实跑验收

AI 编码后实际执行 `pytest` 与 `npm run build`，并在 4B–5B 使用真实前后端及浏览器验证创建、更新、删除、网络断开恢复和跨项目比较。另一个标签修改 Result 后重新比较，表格与双图使用最新值；验收样例通过正常 API 清理，不删除数据库或 SQL 强制清表。

6A 本次只做文档与审计：pip check 正常、102 passed / 0 failed / 1 warning / 7.15s，前端类型与构建无错误。没有新增最终浏览器验收、录视频或宣称 100% 覆盖率。

## 没有未经验证直接接受的部分

可核对的修正是使用者把最初 1:1 进一步明确为 1:0..1，并在编码前冻结 parameters、编号、删除及比较规则；不是让 AI 自行决定模型键或增加用户系统。对数值合法性、null / 0、最新比较和 SQL 请求量均用实际测试检验生成实现。前端保留精确表格，Loss 分轴依据业务语义，不仅依据图表默认外观。

工具不能拖动实际预览窗口时，没有直接接受“响应式已全部通过”的结论。容器 / iframe 检查只作为已有证据，**5A AA 待人工窗口拖动** 保留在清单。现有 chunk warning 与 Starlette 弃用 warning 被记录，没有为了消除提示随机升级依赖或越阶段重构。

以上说明的是明确规则和验证门槛，不能据此虚构某个不存在的“AI 错误建议”或声称人工曾拒绝并重写某一段没有记录的代码。

## 局限与风险

AI 可能遗漏边界条件、误判完成度、产生过期文档或超出范围；测试通过只说明当前断言通过，不能替代完整覆盖率、浏览器操作和教师验收。工具存在实际窗口操作限制，临时 iframe 验收也记录过 MutationObserver 的 Node 类型错误，独立应用页未复现。

项目通过小阶段明确禁止项、只读检查、隔离测试、真实联调与 Git diff 控制改动范围；阶段 6A 仅读写文档，冻结规则及生产代码不改。Git 使用授权的现有用户身份提交，这不意味着每行代码由人手工编写。依赖没有在收尾阶段升级，也没有调用未经授权的外部 AI 服务。

## 6B 人工讲解准备

学生仍需阅读并能定位：编号规范化与唯一性、Result 校验与 422 回显、比较 `_best_metric`、生产数据库隔离、前端一次 POST、Loss 分轴及实例释放。课堂展示真实阶段 Prompt、一个对应 Git diff 和一个测试断言，说明规则为何这样定、AI 修改了哪里、验证证明了什么以及还有哪些限制。

文档提供讲解材料，不替代学生实际理解、录制演示或教师确认；这些保留为 [最终验收清单](final-acceptance-checklist.md) 的未勾项目。
