# 当前 API

当前阶段：3C，Project + ExperimentBatch 基础 API。本文仅记录已实现接口；未实现 Experiment、ExperimentResult、比较或统计 API。

本地地址：`http://127.0.0.1:8000`。Swagger：`/docs`，OpenAPI：`/openapi.json`。Swagger 标签为 Health、Projects、Experiment Batches。

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
