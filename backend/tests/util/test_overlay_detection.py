import unittest
from typing import Any
from unittest.mock import patch

import numpy as np
from app.schemas.detection import OverlayStyle
from app.types.detection import DetectionKeypoint
from app.util import overlay_detection


class TestOverlayDetection(unittest.TestCase):
    def setUp(self) -> None:
        self.frame = np.zeros((100, 120, 3), dtype=np.uint8)
        self.detections: list[dict[str, Any]] = [
            {
                "bbox": [20, 30, 60, 70],
                "label": "person",
                "confidence": 0.95,
                "keypoints": [{"x": 35, "y": 45}],
                "segments": [
                    [
                        {"x": 25, "y": 35},
                        {"x": 55, "y": 35},
                        {"x": 40, "y": 65},
                    ]
                ],
            },
            {
                "bbox": [80, 20, 110, 50],
                "label": "car",
                "confidence": 0.8,
            },
        ]

    def test_box_draws_boxes_and_available_pose_data(self) -> None:
        with (
            patch.object(
                overlay_detection,
                "draw_overlay",
                side_effect=lambda frame, *_args: frame,
            ) as draw_box,
            patch.object(
                overlay_detection,
                "draw_pose_overlay",
                side_effect=lambda frame, *_args, **_kwargs: frame,
            ) as draw_pose,
            patch.object(
                overlay_detection, "draw_segmentation_overlay"
            ) as draw_segment,
        ):
            overlay_detection.overlay_detection(
                self.frame, self.detections, OverlayStyle.BOX
            )

        self.assertEqual(draw_box.call_count, 2)
        self.assertEqual(draw_pose.call_count, 2)
        draw_segment.assert_not_called()

    def test_aim_draws_full_crosshair_for_first_detection_only(self) -> None:
        with patch.object(
            overlay_detection,
            "draw_crosshair_overlay",
            side_effect=lambda frame, *_args, **_kwargs: frame,
        ) as draw_crosshair:
            overlay_detection.overlay_detection(
                self.frame, self.detections, OverlayStyle.AIM
            )

        self.assertEqual(draw_crosshair.call_count, 2)
        self.assertTrue(draw_crosshair.call_args_list[0].kwargs["full_frame"])
        self.assertFalse(draw_crosshair.call_args_list[1].kwargs["full_frame"])

    def test_mixed_draws_first_crosshair_then_boxes(self) -> None:
        with (
            patch.object(
                overlay_detection,
                "draw_crosshair_overlay",
                side_effect=lambda frame, *_args, **_kwargs: frame,
            ) as draw_crosshair,
            patch.object(
                overlay_detection,
                "draw_overlay",
                side_effect=lambda frame, *_args: frame,
            ) as draw_box,
        ):
            overlay_detection.overlay_detection(
                self.frame, self.detections, OverlayStyle.MIXED
            )

        draw_crosshair.assert_called_once()
        self.assertTrue(draw_crosshair.call_args.kwargs["full_frame"])
        draw_box.assert_called_once()

    def test_pose_draws_labels_and_keypoints_without_boxes(self) -> None:
        with (
            patch.object(
                overlay_detection,
                "draw_label",
                side_effect=lambda frame, *_args: frame,
            ) as draw_label,
            patch.object(
                overlay_detection,
                "draw_pose_overlay",
                side_effect=lambda frame, *_args, **_kwargs: frame,
            ) as draw_pose,
            patch.object(overlay_detection, "draw_overlay") as draw_box,
        ):
            overlay_detection.overlay_detection(
                self.frame, self.detections, OverlayStyle.POSE
            )

        self.assertEqual(draw_label.call_count, 2)
        self.assertEqual(draw_pose.call_count, 2)
        draw_box.assert_not_called()

    def test_segmentation_styles_control_box_rendering(self) -> None:
        for style, expected_box_count in (
            (OverlayStyle.BBOX_SEGMENT, 2),
            (OverlayStyle.NO_BBOX_SEGMENT, 0),
        ):
            with self.subTest(style=style):
                with (
                    patch.object(
                        overlay_detection,
                        "draw_segmentation_overlay",
                        side_effect=lambda frame, *_args: frame,
                    ) as draw_segment,
                    patch.object(
                        overlay_detection,
                        "draw_overlay",
                        side_effect=lambda frame, *_args: frame,
                    ) as draw_box,
                ):
                    overlay_detection.overlay_detection(
                        self.frame, self.detections, style
                    )

                draw_segment.assert_called_once()
                self.assertEqual(draw_box.call_count, expected_box_count)

    def test_semantic_style_uses_only_the_semantic_mask(self) -> None:
        semantic_mask: Any = {
            "width": 1,
            "height": 1,
            "counts": [[1, 1]],
            "classes": {1: "road"},
        }
        with (
            patch.object(
                overlay_detection,
                "draw_semantic_segmentation_overlay",
                return_value=self.frame,
            ) as draw_semantic,
            patch.object(overlay_detection, "draw_overlay") as draw_box,
        ):
            overlay_detection.overlay_detection(
                self.frame,
                self.detections,
                OverlayStyle.SEMANTIC,
                semantic_mask,
            )

        draw_semantic.assert_called_once_with(self.frame, semantic_mask)
        draw_box.assert_not_called()

    def test_crosshair_uses_nose_and_spans_frame_for_primary_target(self) -> None:
        result = overlay_detection.draw_crosshair_overlay(
            self.frame,
            20,
            30,
            60,
            70,
            keypoints=[{"x": 35, "y": 45}],
            full_frame=True,
        )

        self.assertEqual(tuple(result[45, 0]), overlay_detection.OVERLAY_COLOR)
        self.assertEqual(tuple(result[0, 35]), overlay_detection.OVERLAY_COLOR)

    def test_pose_draws_skeleton_and_ignores_missing_keypoints(self) -> None:
        keypoints: list[DetectionKeypoint] = [{"x": 0, "y": 0} for _ in range(17)]
        keypoints[5] = {"x": 10, "y": 20}
        keypoints[7] = {"x": 30, "y": 20}

        result = overlay_detection.draw_pose_overlay(self.frame, keypoints)

        self.assertEqual(tuple(result[20, 20]), overlay_detection.OVERLAY_COLOR)
        self.assertTrue(np.array_equal(result[0, 0], np.zeros(3, dtype=np.uint8)))

    def test_pose_ignores_low_confidence_keypoints(self) -> None:
        keypoints: list[DetectionKeypoint] = [
            {"x": 10, "y": 20, "confidence": 0.01},
            {"x": 30, "y": 20, "confidence": 0.9},
        ]

        result = overlay_detection.draw_pose_overlay(self.frame, keypoints)

        self.assertTrue(np.array_equal(result[20, 10], np.zeros(3, dtype=np.uint8)))
        self.assertEqual(tuple(result[20, 30]), overlay_detection.OVERLAY_COLOR)

    def test_crosshair_ignores_low_confidence_nose(self) -> None:
        result = overlay_detection.draw_crosshair_overlay(
            self.frame,
            20,
            30,
            60,
            70,
            keypoints=[{"x": 25, "y": 35, "confidence": 0.2}],
            full_frame=True,
            keypoint_confidence_threshold=0.5,
        )

        self.assertEqual(tuple(result[50, 0]), overlay_detection.OVERLAY_COLOR)
        self.assertTrue(np.array_equal(result[35, 0], np.zeros(3, dtype=np.uint8)))


if __name__ == "__main__":
    unittest.main()
