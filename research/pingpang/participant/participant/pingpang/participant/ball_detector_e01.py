"""E01：连通区域独立求中心，按峰值选择候选。

沿用原检测器的模型输入、阈值和中间帧。此实验不引入轨迹关联、
面积过滤或形状假设；热图区域也不代表球的真实分割。
"""

from __future__ import annotations

from dataclasses import dataclass

import cv2
import numpy as np

from .ball_detector import BallDetector, OUT_CHANNEL, SCORE_TH


@dataclass(frozen=True)
class HeatmapCandidate:
    """坐标为原图像素；mass 为区域响应总量，不能当作置信概率。"""

    x: float
    y: float
    conf: float
    mass: float
    area: int
    first_pixel: int


def extract_candidates(
    heat: np.ndarray, orig_w: int, orig_h: int
) -> list[HeatmapCandidate]:
    """提取 8 邻接区域；按峰值、响应总量、栅格位置稳定排序。"""
    heat = np.asarray(heat)
    if heat.ndim != 2 or not heat.size:
        raise ValueError("Expected a nonempty 2-D heatmap")
    if not np.isfinite(heat).all():
        raise ValueError("Heatmap contains non-finite values")
    if not np.isfinite([orig_w, orig_h]).all() or orig_w <= 0 or orig_h <= 0:
        raise ValueError("Original image dimensions must be finite and positive")

    mask = heat > SCORE_TH
    if not mask.any():
        return []
    count, labels, stats, _ = cv2.connectedComponentsWithStats(
        mask.astype(np.uint8), connectivity=8
    )
    ys, xs = np.nonzero(mask)
    region_ids = labels[ys, xs]
    weights = heat[ys, xs].astype(np.float64)
    masses = np.bincount(region_ids, weights=weights, minlength=count)
    sum_x = np.bincount(region_ids, weights=xs * weights, minlength=count)
    sum_y = np.bincount(region_ids, weights=ys * weights, minlength=count)
    peaks = np.full(count, -np.inf, dtype=np.float64)
    np.maximum.at(peaks, region_ids, weights)
    first_pixels = np.full(count, heat.size, dtype=np.int64)
    np.minimum.at(first_pixels, region_ids, ys * heat.shape[1] + xs)
    scale_x = orig_w / heat.shape[1]
    scale_y = orig_h / heat.shape[0]

    candidates = [
        HeatmapCandidate(
            x=float(sum_x[region] / masses[region] * scale_x),
            y=float(sum_y[region] / masses[region] * scale_y),
            conf=float(peaks[region]),
            mass=float(masses[region]),
            area=int(stats[region, cv2.CC_STAT_AREA]),
            first_pixel=int(first_pixels[region]),
        )
        for region in range(1, count)
    ]
    candidates.sort(key=lambda point: (-point.conf, -point.mass, point.first_pixel))
    return candidates


class BallDetectorE01(BallDetector):
    """只替换解码；归一化、缓冲与 reset 继承原检测器。"""

    def detect(self, frame_rgb: np.ndarray, orig_w: int, orig_h: int) -> dict | None:
        self._buf.append(self._normalize(frame_rgb))
        self._buf = self._buf[-3:]
        inp = np.concatenate(self._buf, axis=0)[None]
        heat = self._infer(inp)[0, OUT_CHANNEL]
        candidates = extract_candidates(heat, orig_w, orig_h)
        if not candidates:
            return None
        point = candidates[0]
        return {"x": point.x, "y": point.y, "conf": point.conf}
