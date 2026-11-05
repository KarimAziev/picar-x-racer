import subprocess
import unittest
from unittest.mock import patch

from app.services.pmic_service import PmicService, parse_pmic_readings


SAMPLE = """
   3V3_SYS_A current(1)=0.19030640A
  DDR_VDDQ_A current(4)=0.00343140A
   3V3_SYS_V volt(9)=3.30260900V
  DDR_VDDQ_V volt(12)=0.60036570V
     EXT5V_V volt(24)=4.86822000V
      BATT_V volt(25)=0.00598290V
"""


class TestPmicParser(unittest.TestCase):
    def test_preserves_channels_units_and_precision(self) -> None:
        readings = parse_pmic_readings(SAMPLE)
        self.assertEqual(len(readings), 6)
        self.assertEqual(readings[0].name, "3V3_SYS_A")
        self.assertEqual(readings[0].unit, "A")
        self.assertEqual(readings[0].value, 0.19030640)
        self.assertEqual(readings[-1].name, "BATT_V")
        self.assertEqual(readings[-1].unit, "V")
        self.assertEqual(readings[-1].value, 0.00598290)

    def test_ignores_noise_malformed_values_and_mismatched_units(self) -> None:
        self.assertEqual(
            parse_pmic_readings(
                "error=1 error_msg=Command not registered\n"
                "3V3_SYS_V volt(9)=nanV\n"
                "3V3_SYS_V volt(9)=1e999V\n"
                "3V3_SYS_V current(9)=3.3V\n"
                "3V3_SYS_A volt(9)=3.3V\n"
                "3V3_SYS_V volt(9)=3.3A\n"
            ),
            [],
        )

    def test_accepts_zero_and_signed_scientific_values(self) -> None:
        readings = parse_pmic_readings(
            " BATT_V volt(25)=0V\n3V3_SYS_A current(1)=-1.2e-3A\n"
        )
        self.assertEqual([r.value for r in readings], [0.0, -0.0012])


class TestPmicService(unittest.TestCase):
    @patch("app.services.pmic_service.subprocess.run")
    def test_reads_fixed_command_with_timeout_and_caches_sample(self, run) -> None:
        run.return_value = subprocess.CompletedProcess([], 0, stdout=SAMPLE)
        service = PmicService()
        with patch("app.services.pmic_service.time.monotonic", return_value=10):
            sample = service.read()
            self.assertIs(service.read(), sample)
        run.assert_called_once_with(
            ["vcgencmd", "pmic_read_adc"],
            capture_output=True,
            text=True,
            timeout=3,
            check=True,
        )
        self.assertIsNone(sample.error)
        self.assertIsNotNone(sample.measured_at)
        with patch("app.services.pmic_service.time.monotonic", return_value=12):
            service.read()
        self.assertEqual(run.call_count, 2)

    def test_command_failures_return_empty_readings(self) -> None:
        failures = [
            FileNotFoundError(),
            PermissionError(),
            subprocess.TimeoutExpired("vcgencmd", 3),
            subprocess.CalledProcessError(1, "vcgencmd"),
        ]
        for failure in failures:
            with self.subTest(failure=type(failure).__name__):
                with patch(
                    "app.services.pmic_service.subprocess.run", side_effect=failure
                ):
                    sample = PmicService().read()
                self.assertEqual(sample.readings, [])
                self.assertIsNone(sample.measured_at)
                self.assertTrue(sample.error)

    @patch("app.services.pmic_service.subprocess.run")
    def test_unsupported_output_is_not_success(self, run) -> None:
        run.return_value = subprocess.CompletedProcess(
            [], 0, stdout="error=1 error_msg=Command not registered"
        )
        self.assertTrue(PmicService().read().error)

    @patch("app.services.pmic_service.subprocess.run")
    def test_failed_refresh_does_not_return_stale_readings(self, run) -> None:
        run.side_effect = [
            subprocess.CompletedProcess([], 0, stdout=SAMPLE),
            subprocess.TimeoutExpired("vcgencmd", 3),
            subprocess.CompletedProcess([], 0, stdout=SAMPLE),
        ]
        service = PmicService()
        with patch("app.services.pmic_service.time.monotonic", return_value=10):
            self.assertTrue(service.read().readings)
        with patch("app.services.pmic_service.time.monotonic", return_value=12):
            self.assertEqual(service.read().readings, [])
        with patch("app.services.pmic_service.time.monotonic", return_value=14):
            self.assertIsNone(service.read().error)
