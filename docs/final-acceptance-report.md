# 最终课程验收记录

阶段 6B；记录截至 2026-10-08 20:59（Asia/Shanghai）。当前停止在第十三节 5A AA 人工检查点，后续验收、数据清理及最终提交尚未执行。本记录只说明本次真实证据，不代表教师评分。

## 1. 验收环境

| 项目 | 本次实测 |
| --- | --- |
| 日期 | 2026-10-08 |
| OS | Microsoft Windows 11 家庭版 中文版，10.0.26200，Build 26200 |
| Python | 3.12.14，backend/.venv/Scripts/python.exe |
| Node / npm | v24.15.0 / 11.12.1 |
| Browser | Codex In-app Browser；工具未提供版本号，尚待人工补充实际窗口验收所用浏览器名称及版本，未填写估计值 |
| 开始 SHA | 9176d759fde155a80d196a72e6239df9bdac19c2 |
| Backend | http://127.0.0.1:8000 |
| Frontend | http://127.0.0.1:5173/ |

开始时 Git 工作区干净，分支 main；HEAD、origin/main 和远端 main 一致，包含阶段 6A 提交。原课程 Word 的 SHA256 仍为 `21245dfccb1e9a59630ef27f1aaa2ba6ab7d89971833dac2084f49eecb9c3d5c`，没有修改。

## 2. 自动检查

本节记录演示前的本次执行；演示后清理数据的最终回归尚待执行。

| 检查 | 结果 |
| --- | --- |
| pip check | No broken requirements found. |
| pytest -q -rA | 102 个用例，102 passed、0 failed、0 errors、1 warning，8.99s |
| TypeScript | vue-tsc -b 通过 |
| Vite | v8.3.2，2259 modules，build 成功，构建输出耗时 797ms |
| JS / gzip | 1,608.74 kB / 526.65 kB |
| CSS / gzip | 364.35 kB / 49.06 kB |

pytest 保留 Starlette TestClient 使用 httpx 的弃用警告；Vite 保留 >500 kB chunk 警告。未安装、升级依赖或优化打包，package-lock.json 存在。测试采用独立临时 SQLite fixture，不使用演示数据库。

## 3. 核心业务流程

Uvicorn、Vite 真实启动；GET /health 返回 200 和 `{"status":"ok","service":"AIExpHub API"}`，/docs 返回 200。实际首页显示平台介绍、三个入口与正常服务状态。

通过前端创建以下数据，访问日志记录各次创建返回 201：

| 实体 | A | B |
| --- | --- | --- |
| Project | Vision Benchmark（id=1） | Unified Models（id=2） |
| Batch | Baseline（id=1） | Comparison Runs（id=2） |
| Experiment | 输入 `" exp-001 "`，保存 EXP-001（id=1） | EXP-002（id=2） |
| Model / notes | Model-A / baseline | Model-B / comparison |
| parameters | {"seed":42,"temperature":0.7} | {"seed":42,"temperature":0.7} |
| 首次 Result | 0.82 / 0.80 / 0.78 / 0.79 / 0.32 | 0.88 / 0.81 / 0.84 / 0.83 / 0.24 |

Result 顺序为 accuracy / precision / recall / f1 / loss。从项目管理的“管理实验”进入带 projectId / batchId 的实验页面，列表显示模型、参数、备注、时间；首次尚无结果时明确显示“该实验尚未录入结果”。刷新 A 页面并重新选择后，编号、参数与五项结果仍在。

比较页跨项目加入两项，已选记录保留、重复加入按钮禁用；首次表格、摘要及 ECharts 双图一致，完整运行 Project → Batch → Experiment → Result → Compare → Visualization。未使用 Mock、硬编码或 localStorage 结果。未创建可选 EXP-003。

## 4. 业务规则抽查

| 本次现场操作 | 实际结果 |
| --- | --- |
| 第二项目尝试 exp-001 | POST 返回 409；中文“实验编号已存在，请使用其他编号。” |
| parameters={} | 前端提示“实验参数必须是非空 JSON 对象。”，拒绝保存；合法自由键对象保存成功 |
| accuracy=1.2 | 前端提示“指标必须处于 [0, 1]”，拒绝保存 |
| 删除仍有 Batch 的 Project A | DELETE /projects/1 返回 409；中文说明先删除批次 |
| 删除仍有 Experiment 的 Batch A | DELETE /batches/1 返回 409；中文说明先删除实验 |
| 删除 Experiment 后 Result CASCADE | 待人工窗口检查结束后现场执行；本次 pytest 的 API / 数据层级联测试已通过，不代替尚未执行的现场删除 |

本次 pytest 还验证 bool、string 数字、NaN、±Infinity 拒绝，CHECK / UNIQUE / 外键，0 与合法边界、全空结果拒绝、重复 Result POST、完整 PUT、失败后数据保持、比较并列最佳、全 null、loss=0、临时数据库隔离。代表性证据见 [结果测试](../backend/tests/test_results.py)、[数据库约束测试](../backend/tests/test_database_constraints.py)、[比较测试](../backend/tests/test_compare.py)、[fixture](../backend/tests/conftest.py)。这些是自动测试证据，未声称逐项通过 UI 重演。

## 5. Compare 与图表

首次 EXP-002 的 Accuracy=0.88、Loss=0.24 标为最佳。综合图四项共用 0–1 轴，Loss 独立自适应轴，最佳标签与表格一致。

保持比较页的两个已选实验不变，在另一标签页编辑 EXP-001 Result，仅把 accuracy 改为 0.94，保留其余四项 0.80 / 0.78 / 0.79 / 0.32。保存后回原页点击“重新比较”，Accuracy 摘要变为 0.94，表格和图表的最佳标记移到 EXP-001；Loss 最佳仍为 EXP-002。

本次请求量证据采用 **Uvicorn 访问日志**。读取完前序操作日志后，执行一次重新比较，再读取新增日志，仅有 `POST /experiments/compare HTTP/1.1` → 200，没有逐实验 GET Result。未声称检查了浏览器 Network。自动测试另证明 Compare 单条只读 SELECT、无 commit。

null 不补 0、全空无最佳、并列最佳、真实 0 的规则由本次 pytest 验证；本轮两项 UI 数据五项均非 null，未把它们写成现场空值图表验证。Tooltip、额外图表边界及路由反复卸载检查尚未在本轮执行。

截至此处，两张实际操作标签页的 warn / error Console 日志均为空；未捕获 Vue、ECharts error 或未处理 Promise rejection。首页、项目、实验、比较的实际标题正确；404、网络断开 / 恢复抽查尚待执行。

## 6. 实际窗口响应式验收

**待人工补充，未通过。** 按用户第十三节要求，停止在此检查点：请人工拖动有比较数据的实际浏览器窗口，宽 → 中等 → 较窄 → 恢复，确认两图随宽度变化、每图只有一个 canvas、X 轴正常、页面无明显横向溢出、恢复后正常、Console 无新增 ECharts error。

当前仅有真实页面截图和双图更新证据；未使用 iframe / CSS 容器缩放替代。只有用户明确回复实际操作正常后才能勾选 5A AA。

## 7. AI 辅助开发现场讲解要点

以下为准备提示，**学生本人尚未确认完成讲解**。

1. Project 组织研究项目，Batch 组织实验组，Experiment 记录一次实验；0..1 Result 允许先建实验、后录结果，始终只保留一份当前结果。
2. 编号 trim + uppercase 消除空格与大小写歧义，全局唯一让跨项目比较和测试明确定位实验。
3. parameters 用非空 JSON object，保证有参数记录并允许不同模型使用不同键。
4. 0 是合法真实指标；bool、string 和非有限数字不属于可比较的有限数值，必须拒绝。
5. null 表示未测量，补 0 会伪造数据并改变最佳结果。
6. accuracy / precision / recall / f1 越大越好取 max，loss 越小越好取 min。
7. 并列最优都应保留，不能任意挑一个实验。
8. 前端一次 Compare POST 获取完整结果，避免逐实验 Result GET；后端一次 SELECT 读取当前数据。
9. 四项比例指标共用 [0,1] 图，loss 可能超过 1，单独画图防止混淆量纲。
10. AI 用于辅助需求、代码与测试开发；业务平台没有接入生成式 AI，开发者需说明关键 Prompt、实际修改和验证断言。

## 8. 演示视频

**尚待人工录制。** 沿用 [demo-script.md](demo-script.md) 的约 7 分 30 秒顺序。未生成视频、摄像头声明、音频质量结论或上传链接。

用户真实完成后再补：文件名 / 真实链接、实际时长、是否含声音、是否完整播放、课程指定提交位置及上传状态。

## 9. 已知限制

保留 TestClient 弃用与前端 chunk 警告。实际窗口拖动、学生讲解、视频及课程平台交付需要人工证据；浏览器版本号尚未取得。后续 404 / 网络恢复、现场 CASCADE、清理后回归尚未执行。截至人工检查点未发现阻断业务的 bug，未修改生产代码。

## 10. 数据清理与 Git 状态

开始时四表只读计数均为 0。20:59 人工检查点时 projects / experiment_batches / experiments / experiment_results 各为 2，均为本轮创建的数据；为窗口检查和后续演示暂时保留。

后续须通过正常 API 按 Experiment → Batch → Project 清理本轮数据，由 CASCADE 删除 Result，复核四表归零，保留数据库，再按用户要求重新 pytest / build。不得删除数据库或 SQL DELETE 强制清表。

本阶段仅新增本报告并同步四份现有交付文档；未提交、未推送。最终 commit SHA 尚未产生；main / origin/main 仍停留开始 SHA。本轮后端和前端服务保持运行供人工检查，最终清理与停止尚待执行。临时截图在仓库外，不提交 Git。

## 11. 最终结论

**尚有人工交付项。** 演示前自动检查、核心闭环、主要规则和最新结果比较已执行；当前按指令停止等待真实窗口拖动确认。项目侧最终验收尚未全部完成，不能宣称教师验收通过或课程已通过。
