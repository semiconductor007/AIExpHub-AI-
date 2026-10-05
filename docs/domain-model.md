# 领域模型

当前阶段：阶段 2.5，冻结数据库实现前的剩余业务决策。本文件描述第一版的业务实体与关系，不包含数据库表、ORM、接口或页面实现。属性是领域层面的暂定名称，不代表已经确定数据库字段类型。

## 核心关系

```mermaid
erDiagram
    Project ||--o{ ExperimentBatch : contains
    ExperimentBatch ||--o{ Experiment : contains
    Experiment ||--o| ExperimentResult : has_current_result
```

- 一个 Project 可以包含多个 ExperimentBatch，也可以暂时没有批次；每个批次必须属于一个存在的项目。
- 一个 ExperimentBatch 可以包含多个 Experiment，也可以暂时没有实验；每个实验必须属于一个存在的批次。
- Experiment 与 ExperimentResult 的关系为 1 : 0..1。实验可以先创建、之后再录入结果；每份结果必须属于一个存在的实验，每个实验最多一份当前有效结果。
- 第一次录入时创建结果，后续修改时更新现有结果，不新增重复结果，也不创建结果历史版本。
- 实验所属项目通过批次确定，暂不在 Experiment 中重复设置 `project_id`，避免两处关联不一致。

没有 ExperimentResult 是允许的；一旦录入 ExperimentResult，其指标必须满足非空结果规则，不能用全空结果代替尚未录入结果的状态。

## Project 实验项目

**职责：**组织一个完整实验研究项目，例如“Janus-Pro 空间推理实验”。

| 暂定属性 | 含义 | 当前约定 |
| --- | --- | --- |
| `id` | 内部稳定标识 | 用于实体关联，具体类型后续确定。 |
| `name` | 项目名称 | 必填，不能是空字符串或仅含空白字符。 |
| `description` | 项目说明 | 暂定可选。 |
| `created_at` | 创建时间 | 暂定由系统记录。 |

**关系：**Project 1:N ExperimentBatch。项目名称的唯一性未作要求，不将其视为唯一标识。

## ExperimentBatch 实验批次

**职责：**组织项目中的一次实验批次或一组用于比较的实验，例如“不同干预方式对比实验”。

| 暂定属性 | 含义 | 当前约定 |
| --- | --- | --- |
| `id` | 内部稳定标识 | 用于实体关联。 |
| `project_id` | 所属项目标识 | 必须指向一个存在的 Project。 |
| `name` | 批次展示名称 | 必填；缺失、null、空字符串和仅含空白字符均不合法。 |
| `description` | 批次说明 | 可选。 |
| `created_at` | 创建时间 | 暂定由系统记录。 |

**关系：**每个批次属于一个 Project，同时可包含多个 Experiment。批次用于组织实验；允许跨批次、跨项目比较实验。

## Experiment 单次实验

**职责：**记录一次具体实验的身份、模型与实验配置。

| 暂定属性 | 含义 | 当前约定 |
| --- | --- | --- |
| `id` | 内部稳定标识 | 用于关联结果，与实验编号分开。 |
| `batch_id` | 所属批次标识 | 必须指向一个存在的 ExperimentBatch。 |
| `experiment_no` | 实验编号 | 用户输入；保存和唯一性比较前执行 trim + uppercase，规范化后非空且全局唯一。 |
| `model_name` | 模型名称 | 必填，不能是空字符串或仅含空白字符。 |
| `parameters` | 实验参数 | 必填，必须为非空 JSON object；参数键不固定。 |
| `created_at` | 创建时间 | 暂定由系统记录。 |
| `notes` | 实验备注 | 暂定可选。 |

参数示例：

```json
{
  "learning_rate": 0.0001,
  "batch_size": 32,
  "seed": 42,
  "optimizer": "AdamW"
}
```

不同模型允许不同参数，例如 `{ "temperature": 0.7 }` 同样合法。当前不要求 learning_rate、batch_size 等任何具体键一定存在。

第一版“缺失参数”指 parameters 字段未提供、不是 JSON object 或为空对象 `{}`，均应拒绝；null、数组、字符串、数字和布尔值不能替代参数对象。无效 JSON 也应拒绝，不静默丢弃或擅自补默认值。

**关系：**每个 Experiment 属于一个 ExperimentBatch，与 ExperimentResult 为 1 : 0..1。

`experiment_no` 由用户输入，不实现自动编号；保存和比较唯一性之前统一执行 trim + uppercase。`" exp-001 "`、`"EXP-001"`、`"exp-001"` 均规范化为 `EXP-001`，在任何项目或批次中均视为同一编号。不要求固定采用 `EXP-001` 格式，只要求规范化后非空且全局唯一。

选择全局唯一是为了实现简单、避免实验比较时的编号歧义，并便于自动化测试和课程验收。本阶段不实现规范化或唯一约束代码。

## ExperimentResult 实验结果

**职责：**在实验录入结果后，保存该实验唯一的一份当前有效结果，供详情、比较、统计和图表使用。

| 暂定属性 | 含义 | 当前约定 |
| --- | --- | --- |
| `id` | 内部稳定标识 | 标识当前结果。 |
| `experiment_id` | 所属实验标识 | 必须指向一个存在的 Experiment；同一实验不能有重复当前结果。 |
| `accuracy` | 准确率 | 可为空；提供时必须是 [0, 1] 内的有限数值。 |
| `precision` | 精确率 | 可为空；提供时必须是 [0, 1] 内的有限数值。 |
| `recall` | 召回率 | 可为空；提供时必须是 [0, 1] 内的有限数值。 |
| `f1` | F1 指标 | 可为空；提供时必须是 [0, 1] 内的有限数值。 |
| `loss` | 损失值 | 可为空；提供时必须是大于等于 0 的有限数值。 |
| `updated_at` | 最近更新时间 | 暂定由系统在结果保存或修改时记录。 |

五项指标中至少一项非空。`0` 是合法数值，不等于空值；不能通过新增一份结果绕过修改校验。结果修改后，后续详情、比较、统计与图表必须使用最新结果。

## 删除与比较边界

- Project 下仍有 ExperimentBatch 时拒绝删除，只有没有任何批次的项目才允许删除。
- ExperimentBatch 下仍有 Experiment 时拒绝删除，只有没有任何实验的批次才允许删除。
- Experiment 允许删除；如存在 ExperimentResult，删除实验时同时删除该结果。结果没有脱离实验独立存在的业务意义。
- 允许跨 Project、跨 ExperimentBatch 比较至少两个不同且真实存在的 Experiment。
- 没有结果的实验应明确标识，不能伪造结果；单项缺失指标保持 null，不用 0 或其他默认值填充。
- accuracy、precision、recall、f1 越大越好，loss 越小越好；每项指标的最佳结果只使用该指标非 null 的实验，全空时没有最佳实验，并列时可标记多个最佳实验。

结果首次录入、后续修改、删除与比较规则均仅在本阶段记录，不实现数据库级联或 API。

第一版不单独建立模型、参数、用户或指标定义实体。具体校验与异常语义见 [业务校验规则](validation-rules.md)。
