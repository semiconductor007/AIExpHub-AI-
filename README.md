# AIExpHub — AI 模型实验结果管理平台

## 项目简介

本项目对应课程综合实践选题第 14 题，计划开发一个用于管理 AI / 机器学习实验结果的 Web 平台，逐步支持实验项目管理、实验配置与结果指标记录、多实验比较和可视化分析。

## 当前技术栈（暂定）

| 用途 | 技术 |
| --- | --- |
| 前端 | Vue 3 + Vite + TypeScript |
| UI | Element Plus |
| 图表 | ECharts |
| 后端 | FastAPI |
| ORM | SQLAlchemy |
| 数据库 | SQLite |
| 测试 | pytest |

## 当前开发阶段

阶段 1、阶段 2 已完成。当前为阶段 2.5：冻结数据库实现前的剩余业务决策，本阶段仅同步设计文档。

当前已建立基础目录、忽略规则、[需求边界](docs/requirements.md)、[阶段开发计划](docs/development-plan.md)、[领域模型](docs/domain-model.md)和[业务校验规则](docs/validation-rules.md)。前后端目录仅包含占位文件，尚未生成框架工程、安装依赖或实现业务功能，当前没有可运行的 Web 应用。

## 基础目录结构

```text
AIExpHub/
├── backend/                 # 后端工程预留目录
│   └── .gitkeep
├── frontend/                # 前端工程预留目录
│   └── .gitkeep
├── docs/
│   ├── requirements.md      # 已确认需求、业务规则与待确认事项
│   ├── development-plan.md  # 各阶段目标、产物与验收方式
│   ├── domain-model.md      # 四个核心实体与关系
│   └── validation-rules.md  # 校验规则与预期异常语义
├── README.md
└── .gitignore
```
