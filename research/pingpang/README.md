# 乒乓球触台检测实验方案

本目录保存乒乓球触台检测的实验计划、记录模板和 E01 球心解码原型。实验按顺序独立比较，真实视频成绩与速度全部待测；现有方案尚未替换比赛默认基线。

- [完整实验计划](experiments/README.md)：E00 基线、D01 热图诊断、E01–E06 后处理方案与后续学习模型。
- [球心定位备选 E01 / E01b](experiments/E01.md)：E01 分开热图亮斑，E01b 固定候选区域后比较内部中心估计。
- [实验记录](experiments/实验记录.md)：逐视角指标、错误案例、运行环境和保留决定。
- [基线指纹](experiments/baseline_manifest.json)：原比赛工作区的源码、权重和数据校验值；路径以原工作区根目录为基准。

## 原型与状态

E01 独立入口为 `participant.solution_e01:Solution`，已通过 10 项合成解码与接入检查。E01b 仅为备选，未实现、未实测。其他方案的状态以实验记录为准；合成检查不表示真实定位、触台 F1 或速度已有提升。

本目录保留原工作区相对路径，原型依赖官方比赛框架和现有 `BallDetector` / `Solution`。在完整比赛工作区，将本目录的两个新增文件放到相同相对路径：

- `participant/participant/pingpang/participant/ball_detector_e01.py`
- `participant/participant/pingpang/participant/solution_e01.py`

随后按 [E01 运行说明](experiments/E01.md) 使用独立入口。模型、视频数据和完整比赛运行环境需要沿用原工作区。`experiments/baselines/official_v0/` 仅保存源码比对快照。

## 检查

在完整比赛工作区根目录运行：

```powershell
python -B -m unittest discover -s experiments/tests -p test_e01_decoder.py -v
```

从本仓库根目录检查时，可用 `PINGPANG_TASK_ROOT` 指向已经包含 E01 原型的官方乒乓球任务目录：

```powershell
$env:PINGPANG_TASK_ROOT = 'F:\动感地带落点预测\participant\participant\pingpang'
python -B -m unittest discover -s research/pingpang/experiments/tests -p test_e01_decoder.py -v
```

没有官方框架时，这组检查明确跳过，不计为通过 E01 验证。默认基线、ONNX 权重和受保护框架保持原样。
