"""Shared data models (dataclasses) used across sensors, controller and dashboard."""
from __future__ import annotations

import json
import time
from dataclasses import dataclass, asdict
from enum import Enum


class ActuatorState(str, Enum):
    ON = "ON"
    OFF = "OFF"


@dataclass(frozen=True)
class SensorReading:
    """A single timestamped sensor reading."""
    sensor: str
    value: float
    unit: str
    timestamp: float

    def to_json(self) -> str:
        return json.dumps(asdict(self))

    @staticmethod
    def from_json(payload: str) -> "SensorReading":
        data = json.loads(payload)
        return SensorReading(**data)

    @staticmethod
    def now(sensor: str, value: float, unit: str) -> "SensorReading":
        return SensorReading(sensor=sensor, value=round(value, 2), unit=unit, timestamp=time.time())


@dataclass(frozen=True)
class ActuatorCommand:
    """A command sent to an actuator."""
    actuator: str
    state: ActuatorState
    reason: str
    timestamp: float

    def to_json(self) -> str:
        d = asdict(self)
        d["state"] = self.state.value
        return json.dumps(d)

    @staticmethod
    def from_json(payload: str) -> "ActuatorCommand":
        data = json.loads(payload)
        data["state"] = ActuatorState(data["state"])
        return ActuatorCommand(**data)

    @staticmethod
    def now(actuator: str, state: ActuatorState, reason: str) -> "ActuatorCommand":
        return ActuatorCommand(actuator=actuator, state=state, reason=reason, timestamp=time.time())


@dataclass(frozen=True)
class ActuatorStatus:
    """A status report published by an actuator after acting on a command."""
    actuator: str
    state: ActuatorState
    timestamp: float

    def to_json(self) -> str:
        d = asdict(self)
        d["state"] = self.state.value
        return json.dumps(d)

    @staticmethod
    def from_json(payload: str) -> "ActuatorStatus":
        data = json.loads(payload)
        data["state"] = ActuatorState(data["state"])
        return ActuatorStatus(**data)

    @staticmethod
    def now(actuator: str, state: ActuatorState) -> "ActuatorStatus":
        return ActuatorStatus(actuator=actuator, state=state, timestamp=time.time())
