import unittest

from app.managers.detection.detection_process import model_labels


class TestDetectionProcessMetadata(unittest.TestCase):
    def test_orders_mapping_labels_by_class_index(self) -> None:
        model = type("Model", (), {"names": {2: "car", 0: "person", 1: "bike"}})()

        self.assertEqual(model_labels(model), ["person", "bike", "car"])

    def test_accepts_sequence_labels(self) -> None:
        model = type("Model", (), {"names": ["person", "car"]})()

        self.assertEqual(model_labels(model), ["person", "car"])


if __name__ == "__main__":
    unittest.main()
