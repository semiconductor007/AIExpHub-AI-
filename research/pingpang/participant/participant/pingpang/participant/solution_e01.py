"""E01 独立入口：participant.solution_e01:Solution。

默认 Solution 保持原样；本入口复用其模型加载与全部落点规则。
"""

from __future__ import annotations

from core.types import RunContext

from .ball_detector_e01 import BallDetectorE01
from .solution import Solution as BaselineSolution


class Solution(BaselineSolution):
    def prepare(self, context: RunContext) -> None:
        super().prepare(context)
        # 父类已完成模型加载与推理 warmup；新检测器从空帧缓冲开始，
        # 后续每条视频仍由继承的 reset() 初始化。
        baseline_detector = self.det
        self.det = BallDetectorE01(baseline_detector._infer, baseline_detector.onnx_path)
        context.info["experiment"] = "E01_peak_connected_component"
