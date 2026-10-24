# I1：基准实验与绝对差值比较

2026-10-13 完成经用户授权的 I1 增量。用于观察相对基准的收益与代价；I2 配置复制及其后阶段未启动。

## 页面使用

1. 在实验比较页加入至少两个不同实验。
2. 在“已选实验”区域选择“基准实验（可选）”。基准来自已选列表，可以跨批次，选择后点击开始比较。
3. 比较表格保留原始值与最佳标签，在指标下方展示 Δ、改善 / 退步 / 无变化，基准行有标记。图表仍展示原始值，放在表格之后。
4. 更换或清除基准、增删选中实验会清空旧结果，需要重新比较；移除基准实验同时清除基准选择。只切换上方候选项目 / 批次保留已选实验和基准。
5. 实验结果修改后，已开始比较的页面支持同源标签页通知及切回页面自动检查；也可点击“重新比较”，读取最新值、最佳、差值和状态。更新失败会保留旧数据并明确提示，已知资源删除则清除旧结果。见 [自动同步说明](comparison-auto-sync.md)。不选择基准时保留普通比较模式。

指标多时表格可横向查看。自定义指标显示项目、单位和方向，不把原始值或差值转换为百分比。

## 已实现规则

- Δ = 当前实验数值 − 基准数值。max 指标正差改善、负差退步；min 指标负差改善、正差退步。差值为 0 时无变化；基准自身有效指标的差值为 0。
- 例如 accuracy 0.80 → 0.83 显示 +0.03 改善；loss 0.4 → 0.3 显示 -0.1 改善；耗时 30 ms → 18 ms 显示 -12 ms 改善。数值与范围继续沿用已有规则。
- 有效的 0 正常计算，缺失不补 0。基准或实验没有 Result、单项指标缺失时返回无法比较和具体原因；允许选择无 Result 的基准，明确提示基准未录入结果。
- 自定义指标限所属项目。基准或目标实验不属于该定义项目时无法计算，跨项目相同键名不会合并；所属项目内的最佳标签仍按原规则计算。
- 系统指标保留跨项目数值对照，页面明确提示需自行确认评测条件一致。数值改善不代表任务、数据集或评测口径必然相同。
- 差值状态与全体最佳 / 并列最佳分别展示，没有综合评分。基准选择不改变最佳算法。
- 后端保存完整浮点差值，前端以 12 位有效数字消除常见尾差，非零微小值保留科学计数法；极大数相减溢出时返回无法计算，不返回 NaN / Infinity。

## 比较 API 扩展

继续使用 `POST /experiments/compare`，可选请求字段 baseline_experiment_id：

```json
{"experiment_ids":[1,2],"baseline_experiment_id":1}
```

基准必须是严格正整数且属于 experiment_ids，否则 422；已选资源实际不存在时沿用 404。省略或传 null 均保持原行为，并且响应不增加空的 baseline_comparison 字段。

指定基准时，原 experiments、best_by_metric 及可选 custom_metrics 保留，额外包含 baseline_comparison：

| 字段 | 含义 |
| --- | --- |
| baseline_experiment_id | 本次实际基准 ID |
| metrics | 五项系统指标及所选项目的自定义指标列表 |
| metrics[].key / name / unit / direction | 指标键、显示名称、单位和方向 |
| metrics[].project_id | 自定义定义的所属项目；系统指标为 null |
| metrics[].baseline_value | 该指标有效基准数值；缺失或不属该项目时为 null |
| metrics[].comparisons | 按实验 ID 的差值对象；JSON 对象键为 ID 字符串 |
| comparisons[ID].delta | 有符号差值，无法计算时为 null |
| comparisons[ID].status | improved / regressed / unchanged / unavailable |
| comparisons[ID].reason | 无法计算原因；正常计算为 null |

reason 支持 baseline_project_mismatch、experiment_project_mismatch、baseline_result_missing、experiment_result_missing、baseline_metric_missing、experiment_metric_missing、overflow。先判断自定义指标项目归属，再判断 Result 和指标缺失，最后判断算术溢出；页面使用对应中文说明。

差值只使用既有比较查询已加载的数据，一条 SELECT、一次 POST、无额外 Result 请求、无 commit 或历史缓存。没有新增路径、数据库表、ORM 字段、依赖或比较历史。

## 验证记录

- 后端 184 passed、0 failed、0 errors、1 warning（19.81s）。原 169 个用例保留，新增 15 个用例覆盖基准类型 / 归属 / 404、旧响应兼容、max / min / 0 / null、同值、无 Result、项目隔离、单位、负值、极小值、溢出、最新结果、单 SELECT 与只读。
- Node 内置测试：原文件读取 4 个用例及差值格式化 3 个用例，共 7 passed。构建通过，2275 modules，Vite 5.88s，JS 1,637.71 kB / gzip 535.04 kB；保留既有 >500 kB 和 TestClient 弃用警告。
- 真实页面以基准 0.8 / 0.4 / 30 ms 比较候选 0.83 / 0.3 / 18 ms，显示 +0.03 / -0.1 / -12 ms 改善；两项 Precision=0 保留并列最佳和零差值，缺失 Result 明确提示。
- 换候选为基准，旧结果清空，原基准的差值 / 方向正确反转。把候选更新为 0.75 / 0.5 / 40 ms 后重新比较，显示 -0.05 / +0.1 / +10 ms 退步，原基准成为对应最佳。
- 跨项目同名自定义指标保持 ms / min 与分 / max 两组定义，项目不符明确无法比较；无 Result 的基准明确提示，移除后基准和结果清空，普通模式不显示差值。
- 本轮应用 warn / error 日志为空。截图保存在仓库外；未将截图验收冒充实际窗口拖动或课程人工验收。
- 临时四个实验、两个批次、两个项目通过正常 API 清理；原五表所有行摘要与验证前一致，计数 2 / 2 / 3 / 2 / 0，外键检查无错误；未修改原课程 Word。

本轮完成 I1 后停止。相对百分比、加权综合排名、显著性检验、额外差值图表和 I2 配置复制仍未实现。
