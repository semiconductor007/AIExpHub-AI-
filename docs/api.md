# 当前 API

当前阶段：3E，ExperimentResult API。本文仅记录已实现接口；未实现比较或统计 API。

本地地址：`http://127.0.0.1:8000`。Swagger：`/docs`，OpenAPI：`/openapi.json`。Swagger 标签为 Health、Projects、Experiment Batches、Experiments、Experiment Results。

## 接口列表

| 方法 | 路径 | 用途 | 成功状态码 | 主要失败状态码 |
| --- | --- | --- | --- | --- |
| GET | `/health` | 执行 SELECT 1 检查数据库连接 | 200 | 503：数据库连接失败 |
| POST | `/projects` | 创建项目 | 201 | 422：输入非法；409：数据库写入冲突 |
| GET | `/projects` | 获取项目数组，按 id ASC 返回 | 200 | — |
| GET | `/projects/{project_id}` | 获取项目详情 | 200 | 404：项目不存在；422：路径参数非法 |
| PUT | `/projects/{project_id}` | 完整更新项目名称与说明 | 200 | 404、409、422 |
| DELETE | `/projects/{project_id}` | 删除没有批次的项目 | 204，无响应 Body | 404：项目不存在；409：存在批次或删除冲突；422：路径参数非法 |
| POST | `/projects/{project_id}/batches` | 在指定项目下创建批次 | 201 | 404：项目不存在；409：数据库写入冲突；422：输入非法 |
| GET | `/projects/{project_id}/batches` | 获取指定项目的批次数组，按 id ASC 返回 | 200 | 404：项目不存在；422：路径参数非法 |
| GET | `/batches/{batch_id}` | 获取批次详情 | 200 | 404：批次不存在；422：路径参数非法 |
| PUT | `/batches/{batch_id}` | 完整更新批次名称与说明 | 200 | 404、409、422 |
| DELETE | `/batches/{batch_id}` | 删除没有实验的批次 | 204，无响应 Body | 404：批次不存在；409：存在实验或删除冲突；422：路径参数非法 |

列表不提供分页、搜索或排序参数。存在但没有批次的项目，其批次列表返回 200 和 `[]`；项目不存在时返回 404。

## 创建与更新请求

项目和批次的 POST / PUT 请求均只允许以下字段：

```json
{
  "name": "Janus Experiments",
  "description": "Spatial reasoning study"
}
```

- name 必填且必须为字符串；trim 首尾空白后保存，trim 后为空则返回 422。
- description 可省略，也可为字符串或 null。PUT 为完整更新：省略 description 或传 null 都会清空原说明；省略 name 返回 422。
- Project 名称和 Batch 名称均不要求唯一，同名允许存在。
- 输入 Schema 使用 `extra="forbid"`：id、created_at 及其他额外字段均返回 422。
- Batch 创建的 project_id 仅来自 URL，不允许在 Body 中提交。Batch PUT 也不接受 project_id，不允许移动所属项目。

ProjectRead 返回 id、name、description、created_at。BatchRead 额外返回 project_id。created_at 由系统生成，按 DateTime 序列化。

## 错误与事务语义

- 404：资源不存在。项目错误为 `{"detail":"Project not found"}`，批次错误为 `{"detail":"Experiment batch not found"}`。
- 409：存在子资源或数据库完整性冲突。项目删除受限时为 `{"detail":"Project has existing batches"}`；批次删除受限时为 `{"detail":"Experiment batch has existing experiments"}`。
- 写入时发生 IntegrityError，先 rollback，再返回 409。创建或更新的冲突信息分别为 `Project write conflict` 或 `Experiment batch write conflict`，不暴露数据库 traceback。
- 422：Pydantic 输入校验失败，包括缺失名称、null、空白名称、类型错误、额外字段和非法路径参数；使用 FastAPI 标准 detail 错误数组。
- 每个请求由 get_db 获得独立 Session，异常时回滚，请求结束后关闭。写操作显式提交后才返回成功。
- 删除前主动检查子记录，数据库 RESTRICT 保留第二层保护，不隐式级联删除 Batch 或 Experiment。

## Experiment API

| 方法 | 路径 | 用途 | 成功状态码 | 主要失败状态码 |
| --- | --- | --- | --- | --- |
| POST | `/batches/{batch_id}/experiments` | 在指定批次下创建实验 | 201 | 404：批次不存在；409：编号重复或写入冲突；422：输入非法 |
| GET | `/batches/{batch_id}/experiments` | 获取指定批次的实验数组，按 id ASC 返回 | 200 | 404：批次不存在；422：路径参数非法 |
| GET | `/experiments/{experiment_id}` | 获取实验详情 | 200 | 404：实验不存在；422：路径参数非法 |
| PUT | `/experiments/{experiment_id}` | 完整更新实验编号、模型、参数和备注 | 200 | 404、409、422 |
| DELETE | `/experiments/{experiment_id}` | 删除实验 | 204，无响应 Body | 404：实验不存在；409：数据库删除冲突；422：路径参数非法 |

存在但没有实验的 Batch，其实验列表返回 200 和 `[]`；Batch 不存在时返回 404。当前没有全局 `GET /experiments`，也没有搜索、分页或排序参数。

创建和更新只允许以下字段：

```json
{
  "experiment_no": " exp-001 ",
  "model_name": "Janus-Pro-1B",
  "parameters": { "learning_rate": 0.0001, "batch_size": 32 },
  "notes": "baseline"
}
```

- experiment_no 必填、strict string，在 Schema 中先 trim 再 uppercase，以上编号保存为 `EXP-001`。规范化后不能空白，不要求固定编号格式，不自动编号。
- experiment_no 全局唯一：主动检查整个 experiments 表，跨项目和跨批次也不能重复。PUT 检查时排除当前实验，保留自身编号允许成功。
- model_name 必填、strict string、trim 后非空，不要求唯一。
- parameters 必填且必须是非空 JSON object；缺失、null、数组、字符串、数字、布尔值和 `{}` 均返回 422。参数键不固定，`{"temperature":0.7}` 同样合法，不增加具体参数值规则。
- notes 可省略或为 string / null，不要求 trim、非空或长度限制。PUT 为完整更新，experiment_no、model_name、parameters 必须重新提交，省略 notes 或传 null 均清空备注。
- 输入使用 `extra="forbid"`，id、batch_id、created_at、result、project_id 及其他额外字段均返回 422。创建的 batch_id 来自 URL；PUT 保留原所属 Batch，不允许迁移。
- ExperimentRead 返回 id、batch_id、experiment_no、model_name、parameters、created_at、notes，不包含 Result。Experiment 可以合法地暂时没有 Result。

实验不存在返回 `{"detail":"Experiment not found"}`；父 Batch 不存在返回 `{"detail":"Experiment batch not found"}`。主动编号冲突返回 409 和 `{"detail":"Experiment number already exists"}`，拒绝修改原数据。

数据库 UNIQUE 保留第二层保护。commit 发生 IntegrityError 时先 rollback；SQLite 的 experiment_no UNIQUE 冲突返回上述明确编号冲突信息，其他完整性冲突返回 409 和 `{"detail":"Experiment write conflict"}`，不暴露数据库内部异常。

Experiment 允许删除，不因已有 Result 而阻止；数据库 CASCADE 规则负责删除关联结果。结果通过以下独立接口访问，不嵌入 ExperimentRead。

## ExperimentResult API

| 方法 | 路径 | 用途 | 成功状态码 | 主要失败状态码 |
| --- | --- | --- | --- | --- |
| POST | `/experiments/{experiment_id}/result` | 首次录入实验结果 | 201 | 404：实验不存在；409：结果已存在或写入冲突；422：输入非法 |
| GET | `/experiments/{experiment_id}/result` | 查询当前实验结果 | 200 | 404：实验或结果不存在；422：路径参数非法 |
| PUT | `/experiments/{experiment_id}/result` | 完整替换已有结果的五项指标 | 200 | 404：实验或结果不存在；409：写入冲突；422：输入非法 |

结果始终通过 Experiment 访问；没有 Result DELETE、全局结果列表或按 result_id 查询的接口。Experiment 可以合法地暂时没有 Result。

### 输入与数值校验

Create / Update 均只允许 accuracy、precision、recall、f1、loss 五项指标；每项可省略或为 null，但至少一项非 null。

- accuracy、precision、recall、f1：有限数值，范围 [0, 1]，包含两端。
- loss：大于等于 0 的有限数值，没有已确定的有限上界，2.5 等大于 1 的值合法。
- JSON integer 和 float 均允许；0 是有效指标，`{"loss":0}` 合法。
- before 字段校验明确拒绝 bool、string、数组和对象；字符串数字不自动转换。
- `allow_inf_nan=False` 拒绝 NaN、Infinity、-Infinity。非标准 JSON 数值被解析后仍须通过有限数值校验；422 错误回显中的非有限值转为文本，保证响应可序列化，不写入数据库。
- `{}` 和五项全部 null 均返回 422；一项合法不能抵消其他字段的非法值。
- 输入使用 `extra="forbid"`：id、experiment_id、updated_at、experiment、result 及任何额外字段均返回 422。

ExperimentResultRead 返回 id、experiment_id、五项指标和 updated_at，缺失单项指标保持 null，不嵌套 Experiment。

### 首次录入与完整更新

POST 先确认 Experiment 存在，再主动查询是否已有结果。已有结果返回 409 和 `{"detail":"Experiment result already exists"}`，不覆盖原结果。

PUT 只更新已存在的结果，不执行 upsert，id 和 experiment_id 保持不变。PUT 中字段省略与显式 null 都表示该指标清空，例如原有 accuracy=0.8、f1=0.7，提交 `{"accuracy":0.9}` 后仅 accuracy=0.9，其余四项均为 null。更新后仍须至少一项非空；无效更新不能覆盖原有效结果。

真实改变 ORM 指标时，由现有 onupdate 更新 updated_at。完全相同的数据可能不触发 UPDATE，不强制刷新时间。

### 404、事务与数据库保护

- Experiment 不存在：POST / GET / PUT 均返回 404 和 `{"detail":"Experiment not found"}`。
- Experiment 存在但没有 Result：GET / PUT 返回 404 和 `{"detail":"Experiment result not found"}`，不自动创建结果。
- commit 发生 IntegrityError 时先 rollback；experiment_id UNIQUE 冲突返回明确的结果已存在 409，其他完整性冲突返回 409 和 `{"detail":"Experiment result write conflict"}`，不暴露 SQLite / SQLAlchemy traceback。
- 现有 UNIQUE(experiment_id)、指标范围和至少一项非 NULL 的 CHECK 保留第二层保护；本阶段不修改 ORM 关系或约束。
- 删除已有结果的 Experiment 返回 204，数据库 CASCADE 同时删除对应 Result。

阶段 3E 实际 HTTP 验证中，NaN、Infinity、-Infinity 请求均返回 422（finite_number），错误回显 input 分别为文本 nan、inf、-inf；数据库未写入这些非法结果。真实修改指标后 updated_at 变晚；完全相同的 PUT 没有强制刷新时间。
