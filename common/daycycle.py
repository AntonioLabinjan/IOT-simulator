"""Day/night cycle helper shared by sensors that depend on time of day."""
from __future__ import annotations

import math
import time

from common.config import SIM


def day_phase(start_time: float) -> float:
    """Returns a 0..1 value representing progress through the day/night cycle."""
    elapsed = time.time() - start_time
    return (elapsed % SIM.day_length_s) / SIM.day_length_s


def sun_intensity(start_time: float) -> float:
    """Returns 0..1 sun intensity, peaking at midday and zero at night.

    Uses a clipped sine wave so roughly half the cycle is 'night' (flat zero).
    """
    phase = day_phase(start_time)
    raw = math.sin(phase * 2 * math.pi - math.pi / 2)  # -1..1, trough at phase=0
    return max(0.0, raw)


def is_daytime(start_time: float) -> bool:
    return sun_intensity(start_time) > 0.0
