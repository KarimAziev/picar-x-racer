"""Read Raspberry Pi PMIC ADC channels with bounded command execution."""

import math
import re
import subprocess
import threading
import time
from datetime import datetime, timezone

from app.schemas.system import PmicReading, PmicStatus


_READING = re.compile(
    r"^\s*(\w+)\s+(current|volt)\(\d+\)=([+-]?(?:\d+(?:\.\d*)?|\.\d+)(?:[eE][+-]?\d+)?)([AV])\s*$"
)


def parse_pmic_readings(output: str) -> list[PmicReading]:
    """Accept finite ADC values whose channel, measurement and unit agree."""
    readings: dict[str, PmicReading] = {}
    for line in output.splitlines():
        match = _READING.fullmatch(line)
        if match is None:
            continue
        name, kind, raw_value, unit = match.groups()
        expected_unit = "A" if kind == "current" else "V"
        value = float(raw_value)
        if (
            unit != expected_unit
            or not name.endswith(f"_{expected_unit}")
            or not math.isfinite(value)
        ):
            continue
        readings[name] = PmicReading(name=name, value=value, unit=expected_unit)
    return list(readings.values())


class PmicService:
    """Share samples across clients for one second and serialize firmware reads."""

    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._sample: PmicStatus | None = None
        self._sample_time = 0.0

    def read(self) -> PmicStatus:
        with self._lock:
            if self._sample is not None and time.monotonic() - self._sample_time < 1:
                return self._sample
            self._sample = self._read()
            self._sample_time = time.monotonic()
            return self._sample

    def _read(self) -> PmicStatus:
        try:
            result = subprocess.run(
                ["vcgencmd", "pmic_read_adc"],
                capture_output=True,
                text=True,
                timeout=3,
                check=True,
            )
        except FileNotFoundError:
            return PmicStatus(error="PMIC monitoring requires vcgencmd on the server.")
        except subprocess.TimeoutExpired:
            return PmicStatus(error="PMIC measurement timed out. Try refreshing again.")
        except (OSError, subprocess.CalledProcessError):
            return PmicStatus(
                error="Cannot read PMIC measurements. Check board support and vcgencmd permissions."
            )
        readings = parse_pmic_readings(result.stdout)
        if not readings:
            return PmicStatus(
                error="No PMIC ADC readings available. This board or firmware may not support pmic_read_adc."
            )
        return PmicStatus(
            readings=readings, measured_at=datetime.now(timezone.utc).isoformat()
        )
