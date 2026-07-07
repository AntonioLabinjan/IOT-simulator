"""Central configuration for the greenhouse simulator."""
from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class MQTTConfig:
    host: str = "localhost"
    port: int = 1883
    keepalive: int = 60


@dataclass(frozen=True)
class Topics:
    """MQTT topic hierarchy used across the project."""
    temperature: str = "greenhouse/sensor/temperature"
    humidity: str = "greenhouse/sensor/humidity"
    soil: str = "greenhouse/sensor/soil"
    light: str = "greenhouse/sensor/light"

    cmd_fan: str = "greenhouse/cmd/fan"
    cmd_pump: str = "greenhouse/cmd/pump"
    cmd_lamp: str = "greenhouse/cmd/lamp"

    status_fan: str = "greenhouse/status/fan"
    status_pump: str = "greenhouse/status/pump"
    status_lamp: str = "greenhouse/status/lamp"

    threshold_update: str = "greenhouse/config/thresholds"
    sim_clock: str = "greenhouse/sim/clock"

    sensors_all: str = "greenhouse/sensor/#"
    status_all: str = "greenhouse/status/#"
    cmd_all: str = "greenhouse/cmd/#"


@dataclass
class Thresholds:
    """Mutable control thresholds. Updated live via MQTT or dashboard input."""
    temp_high: float = 30.0
    temp_low: float = 24.0
    soil_low: float = 30.0
    soil_high: float = 55.0
    light_low: float = 250.0
    light_high: float = 450.0


@dataclass(frozen=True)
class SimulationConfig:
    """Timing and random-walk tuning parameters."""
    sensor_interval_s: float = 2.0
    controller_interval_s: float = 1.0
    dashboard_interval_s: float = 1.0
    day_length_s: float = 300.0  # full day/night cycle length in seconds

    temp_walk_step: float = 0.15
    humidity_walk_step: float = 0.3
    soil_drain_rate: float = 0.25
    soil_irrigation_gain: float = 1.2
    light_walk_step: float = 8.0


MQTT = MQTTConfig()
TOPICS = Topics()
SIM = SimulationConfig()


def default_thresholds() -> Thresholds:
    return Thresholds()
