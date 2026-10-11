"""无需 TensorRT 的 E01 解码与帧对齐检查；不代表真实视频精度。"""

from __future__ import annotations

import os
import sys
import unittest
from pathlib import Path
from types import ModuleType, SimpleNamespace
from unittest.mock import patch

WORKSPACE = Path(__file__).resolve().parents[2]
TASK_ROOT = Path(os.environ.get("PINGPANG_TASK_ROOT", str(WORKSPACE / "participant/participant/pingpang")))
if not (TASK_ROOT / "core/types.py").is_file():
    raise unittest.SkipTest("E01 checks require the official pingpang framework; set PINGPANG_TASK_ROOT")
sys.path.insert(0, str(TASK_ROOT))

import numpy as np  # noqa: E402

from participant.ball_detector import BallDetector, IN_H, IN_W  # noqa: E402
from participant.ball_detector_e01 import BallDetectorE01, extract_candidates  # noqa: E402
from participant.solution import CONF_TH, Solution as BaselineSolution  # noqa: E402
from participant.solution_e01 import Solution as E01Solution  # noqa: E402


def fake_infer(heat):
    output = np.zeros((1, 3, IN_H, IN_W), dtype=np.float32)
    output[0, 1] = heat
    return lambda _inp: output


class DecoderChecks(unittest.TestCase):
    def test_single_region_matches_original_with_scaling(self):
        heat = np.zeros((IN_H, IN_W), np.float32)
        heat[15, 20:23] = [0.8, 0.95, 0.72]
        frame = np.zeros((20, 30, 3), np.uint8)
        old = BallDetector(fake_infer(heat), "unused.onnx").detect(frame, 1266, 720)
        new = BallDetectorE01(fake_infer(heat), "unused.onnx").detect(frame, 1266, 720)
        for key in ["x", "y", "conf"]:
            self.assertAlmostEqual(old[key], new[key], places=10)

    def test_separate_distractor_cannot_pull_selected_center(self):
        heat = np.zeros((IN_H, IN_W), np.float32)
        heat[50, 40:42] = [0.95, 0.8]
        heat[180, 400:402] = [0.9, 0.8]
        frame = np.zeros((10, 10, 3), np.uint8)
        old = BallDetector(fake_infer(heat), "unused.onnx").detect(frame, IN_W, IN_H)
        new = BallDetectorE01(fake_infer(heat), "unused.onnx").detect(frame, IN_W, IN_H)
        self.assertGreater(old["x"], 100)
        self.assertTrue(40 <= new["x"] <= 41)
        self.assertEqual(new["y"], 50)

    def test_peak_has_priority_over_area_and_mass(self):
        heat = np.zeros((30, 30), np.float32)
        heat[2, 2] = 0.95
        heat[15:25, 15:25] = 0.85
        points = extract_candidates(heat, 30, 30)
        self.assertEqual(points[0].area, 1)
        self.assertEqual((points[0].x, points[0].y), (2, 2))

    def test_peak_ties_use_mass_then_raster_position(self):
        heat = np.zeros((10, 10), np.float32)
        heat[1, 1] = 0.9
        heat[5, 5:7] = 0.9
        points = extract_candidates(heat, 10, 10)
        self.assertEqual(points[0].area, 2)
        heat[1, 2] = 0.9
        points = extract_candidates(heat, 10, 10)
        self.assertEqual(points[0].first_pixel, 11)

    def test_diagonal_neighbors_are_one_region(self):
        heat = np.zeros((5, 5), np.float32)
        heat[1, 1] = heat[2, 2] = 0.9
        points = extract_candidates(heat, 5, 5)
        self.assertEqual(len(points), 1)
        self.assertEqual((points[0].x, points[0].y), (1.5, 1.5))

    def test_empty_strict_threshold_border_and_low_confidence(self):
        heat = np.zeros((IN_H, IN_W), np.float32)
        heat[0, 0] = 0.7
        self.assertEqual(extract_candidates(heat, 1920, 1080), [])
        heat[-1, -1] = 0.74
        point = extract_candidates(heat, 1920, 1080)[0]
        self.assertLess(point.conf, CONF_TH)
        self.assertAlmostEqual(point.x, (IN_W - 1) * 1920 / IN_W)
        self.assertAlmostEqual(point.y, (IN_H - 1) * 1080 / IN_H)

    def test_invalid_inputs_fail_explicitly(self):
        for value in [np.nan, np.inf, -np.inf]:
            with self.subTest(value=value):
                with self.assertRaises(ValueError):
                    extract_candidates(np.array([[value]], np.float32), 1, 1)
        for heat in [np.empty((0, 2)), np.zeros((1, 2, 3))]:
            with self.assertRaises(ValueError):
                extract_candidates(heat, 1, 1)
        with self.assertRaises(ValueError):
            extract_candidates(np.zeros((2, 2)), 0, 1)

    def test_middle_channel_and_frame_buffer_match_original(self):
        output = np.zeros((1, 3, IN_H, IN_W), np.float32)
        output[0, 0, 200, 200] = 1
        output[0, 1, 20, 30] = 0.9
        output[0, 2, 100, 100] = 1
        captured = [[], []]

        def infer(index):
            def run(inp):
                captured[index].append(inp.copy())
                return output
            return run

        old = BallDetector(infer(0), "unused.onnx")
        new = BallDetectorE01(infer(1), "unused.onnx")
        for value in [10, 40, 90]:
            frame = np.full((30, 40, 3), value, np.uint8)
            old.detect(frame, IN_W, IN_H)
            point = new.detect(frame, IN_W, IN_H)
            self.assertEqual((point["x"], point["y"]), (30, 20))
        old.reset()
        new.reset()
        frame = np.zeros((30, 40, 3), np.uint8)
        old.detect(frame, IN_W, IN_H)
        new.detect(frame, IN_W, IN_H)
        for old_input, new_input in zip(*captured):
            np.testing.assert_array_equal(old_input, new_input)
            self.assertEqual(new_input.shape, (1, 9, IN_H, IN_W))

    def test_event_rules_keep_confidence_gate_and_one_frame_compensation(self):
        class DetectionSequence:
            def reset(self):
                self.points = iter([0.9, 0.74, 0.9, 0.9, 0.9])
                self.heights = iter([10, 50, 13, 11, 10])

            def detect(self, _frame, _w, _h):
                return {"x": 20.0, "y": next(self.heights), "conf": next(self.points)}

        all_outputs = []
        for cls in [BaselineSolution, E01Solution]:
            solution = cls()
            solution.det = DetectionSequence()
            solution.reset(None)
            events = []
            for fid in range(5):
                events += solution.process_frame(None, {"frame_id": fid, "width": 512, "height": 288})
            events += solution.finish_video(None)
            all_outputs.append([(p.frame_id, p.x, p.y) for p in events])
        self.assertEqual(all_outputs, [[(1, 20.0, 13)], [(1, 20.0, 13)]])

    def test_prepare_reuses_loaded_model_and_reset_initializes_new_detector(self):
        heat = np.zeros((IN_H, IN_W), np.float32)
        heat[20, 30] = 0.9
        infer_calls = []
        output = fake_infer(heat)(None)

        def infer(inp):
            infer_calls.append(inp.copy())
            return output

        trt_stub = ModuleType("core.trt")
        trt_stub.load_or_build = lambda *_args, **_kwargs: (SimpleNamespace(infer=infer), "loaded")
        context = SimpleNamespace(output_dir="unused_output", info={})
        solution = E01Solution()
        with patch.dict(sys.modules, {"core.trt": trt_stub}):
            solution.prepare(context)
        self.assertIsInstance(solution.det, BallDetectorE01)
        self.assertEqual(len(infer_calls), 1)
        self.assertEqual(context.info["backend"], "tensorrt_loaded")
        solution.reset(None)
        point = solution.det.detect(np.zeros((10, 10, 3), np.uint8), IN_W, IN_H)
        self.assertEqual((point["x"], point["y"]), (30, 20))
        np.testing.assert_array_equal(infer_calls[0], infer_calls[1])


if __name__ == "__main__":
    unittest.main()
