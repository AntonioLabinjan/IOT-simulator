"""Live terminal dashboard for the greenhouse simulator, built with Rich."""
from __future__ import annotations

import json
import logging
import threading
import time
from dataclasses import dataclass, field

from rich.console import Console, Group
from rich.live import Live
from rich.panel import Panel
from rich.table import Table

from common.config import MQTT, SIM, TOPICS, default_thresholds
from common.models import ActuatorStatus, SensorReading
from common.mqtt_client import MQTTClientWrapper

logging.basicConfig(level=logging.WARNING, format="%(asctime)s [%(name)s] %(message)s")
logger = logging.getLogger("dashboard")


@dataclass
class DashboardState:
    """Latest known values, updated by MQTT callbacks and read by the render loop."""
    temperature: SensorReading | None = None
    humidity: SensorReading | None = None
    soil: SensorReading | None = None
    light: SensorReading | None = None
    fan: ActuatorStatus | None = None
    pump: ActuatorStatus | None = None
    lamp: ActuatorStatus | None = None
    thresholds: dict = field(default_factory=lambda: default_thresholds().__dict__.copy())
    lock: threading.Lock = field(default_factory=threading.Lock)


class Dashboard:
    """Subscribes to all greenhouse topics and renders a live Rich terminal UI."""

    def __init__(self) -> None:
        self._state = DashboardState()
        self._client = MQTTClientWrapper("greenhouse-dashboard", MQTT)
        self._console = Console()

    # -- MQTT handlers --------------------------------------------------
    def _on_sensor(self, topic: str, payload: str) -> None:
        reading = SensorReading.from_json(payload)
        with self._state.lock:
            setattr(self._state, reading.sensor, reading)

    def _on_status(self, topic: str, payload: str) -> None:
        status = ActuatorStatus.from_json(payload)
        with self._state.lock:
            setattr(self._state, status.actuator, status)

    def _on_thresholds(self, topic: str, payload: str) -> None:
        try:
            data = json.loads(payload)
        except json.JSONDecodeError:
            return
        with self._state.lock:
            self._state.thresholds.update(data)

    # -- rendering --------------------------------------------------
    def _sensor_table(self) -> Table:
        table = Table(title="Sensors", expand=True)
        table.add_column("Sensor")
        table.add_column("Value", justify="right")
        table.add_column("Updated", justify="right")

        def row(name: str, reading: SensorReading | None) -> None:
            if reading is None:
                table.add_row(name, "—", "—")
            else:
                age = time.time() - reading.timestamp
                table.add_row(name, f"{reading.value:.1f} {reading.unit}", f"{age:.0f}s ago")

        row("Temperature", self._state.temperature)
        row("Humidity", self._state.humidity)
        row("Soil moisture", self._state.soil)
        row("Light", self._state.light)
        return table

    def _actuator_table(self) -> Table:
        table = Table(title="Actuators", expand=True)
        table.add_column("Actuator")
        table.add_column("State", justify="center")

        def row(name: str, status: ActuatorStatus | None) -> None:
            if status is None:
                table.add_row(name, "—")
            else:
                style = "bold green" if status.state.value == "ON" else "dim"
                table.add_row(name, f"[{style}]{status.state.value}[/{style}]")

        row("Fan", self._state.fan)
        row("Irrigation pump", self._state.pump)
        row("Grow lamp", self._state.lamp)
        return table

    def _threshold_panel(self) -> Panel:
        t = self._state.thresholds
        text = (
            f"Temp fan:  ON above {t['temp_high']:.1f}C | OFF below {t['temp_low']:.1f}C\n"
            f"Soil pump: ON below {t['soil_low']:.1f}% | OFF above {t['soil_high']:.1f}%\n"
            f"Light lamp: ON below {t['light_low']:.0f}lux | OFF above {t['light_high']:.0f}lux"
        )
        return Panel(text, title="Active thresholds", border_style="cyan")

    def _render(self) -> Panel:
        with self._state.lock:
            body = Group(self._sensor_table(), self._actuator_table(), self._threshold_panel())
        return Panel(body, title="🌱 Smart Greenhouse Dashboard", border_style="green")

    def run(self) -> None:
        self._client.connect()
        self._client.subscribe(TOPICS.sensors_all, self._on_sensor)
        self._client.subscribe(TOPICS.status_all, self._on_status)
        self._client.subscribe(TOPICS.threshold_update, self._on_thresholds)

        try:
            with Live(self._render(), console=self._console, refresh_per_second=1, screen=False) as live:
                while True:
                    time.sleep(SIM.dashboard_interval_s)
                    live.update(self._render())
        except KeyboardInterrupt:
            pass
        finally:
            self._client.disconnect()


if __name__ == "__main__":
    Dashboard().run()
