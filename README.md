# IoT Smart Greenhouse Simulator

A realistic, modular simulation of a smart greenhouse built from independent
virtual IoT devices that communicate exclusively over MQTT — the same
architecture pattern used in real IoT deployments (sensors, a rules
controller, and actuators, all decoupled through a message broker).

## Overview

Four sensor clients (temperature, humidity, soil moisture, light) each run
as their own process and publish readings on a random-walk basis, shaped by
a continuous day/night cycle. A central controller subscribes to all sensor
topics, applies hysteresis-based rules, and issues actuator commands —
never calling actuator code directly. Three actuator clients (fan,
irrigation pump, grow lamp) subscribe to their command topics, change
state, and publish status. A Rich-powered terminal dashboard subscribes to
everything and renders a live, auto-refreshing view of the whole
greenhouse.

Every component is an independent MQTT client. Nothing talks directly to
anything else — this mirrors how real IoT fleets are built, and means you
can kill/restart any single component without breaking the rest.

## Architecture

```
                     ┌────────────────────┐
                     │  Mosquitto Broker  │
                     └─────────┬──────────┘
        ┌───────────┬──────────┼───────────┬────────────┐
        │           │          │           │            │
   ┌────▼───┐  ┌────▼───┐ ┌────▼───┐  ┌────▼─────┐ ┌────▼─────┐
   │  Temp  │  │Humidity│ │  Soil  │  │  Light   │ │Controller│
   │ Sensor │  │ Sensor │ │ Sensor │  │  Sensor  │ │ (rules)  │
   └────────┘  └────────┘ └────────┘  └──────────┘ └────┬─────┘
                                                          │ cmd/*
                                            ┌─────────────┼─────────────┐
                                       ┌────▼───┐    ┌────▼───┐    ┌────▼───┐
                                       │  Fan   │    │  Pump  │    │  Lamp  │
                                       └────────┘    └────────┘    └────────┘

                     All of the above are also observed live by:
                     ┌────────────────────┐
                     │   Rich Dashboard   │
                     └────────────────────┘
```

- **`common/`** — shared MQTT wrapper, config/thresholds, dataclass models, day/night helper.
- **`devices/`** — sensors (publish readings) and actuators (subscribe to commands, publish status).
- **`controller/`** — subscribes to sensors, applies hysteresis rules, publishes commands.
- **`dashboard/`** — Rich terminal UI, subscribes to everything, read-only.

Design choices: no global state (everything lives in class instances),
dataclasses + type hints throughout, JSON-over-MQTT payloads, and logging
instead of ad-hoc prints (actuators still print state changes for a nice
CLI demo experience).

## MQTT Topic Hierarchy

| Topic                              | Publisher       | Payload                          |
|-------------------------------------|-----------------|-----------------------------------|
| `greenhouse/sensor/temperature`     | temperature sensor | `{sensor, value, unit, timestamp}` |
| `greenhouse/sensor/humidity`        | humidity sensor    | `{sensor, value, unit, timestamp}` |
| `greenhouse/sensor/soil`            | soil sensor        | `{sensor, value, unit, timestamp}` |
| `greenhouse/sensor/light`           | light sensor       | `{sensor, value, unit, timestamp}` |
| `greenhouse/cmd/fan`                | controller         | `{actuator, state, reason, timestamp}` |
| `greenhouse/cmd/pump`               | controller         | `{actuator, state, reason, timestamp}` |
| `greenhouse/cmd/lamp`               | controller         | `{actuator, state, reason, timestamp}` |
| `greenhouse/status/fan`             | fan actuator       | `{actuator, state, timestamp}` |
| `greenhouse/status/pump`            | pump actuator      | `{actuator, state, timestamp}` |
| `greenhouse/status/lamp`            | lamp actuator      | `{actuator, state, timestamp}` |
| `greenhouse/config/thresholds`      | controller         | partial `{field: value}` dict, retained |

The soil sensor also **subscribes** to `greenhouse/status/pump` so its
simulated moisture rises while irrigation is active and drains otherwise.

## Control Rules (hysteresis)

| Actuator | ON condition            | OFF condition           |
|----------|--------------------------|---------------------------|
| Fan      | temperature > 30°C       | temperature < 24°C        |
| Pump     | soil moisture < 30%      | soil moisture > 55%       |
| Lamp     | light < 250 lux          | light > 450 lux           |

Thresholds are mutable at runtime (see below) and live in a single
`Thresholds` dataclass inside the controller.

## Installation

Requires Python 3.12+.

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

## Start the MQTT Broker

```bash
docker compose up -d
```

This starts Eclipse Mosquitto on `localhost:1883`. Check logs with
`docker compose logs -f mosquitto`, stop with `docker compose down`.

## Launch the Components

Run each in its own terminal (all connect to `localhost:1883` by default —
see `common/config.py` to change host/port):

```bash
# Sensors
python -m devices.temperature_sensor
python -m devices.humidity_sensor
python -m devices.soil_sensor
python -m devices.light_sensor

# Actuators
python -m devices.fan
python -m devices.irrigation
python -m devices.lamp

# Controller (interactive — type e.g. "temp_high 32" then Enter to adjust live)
python -m controller.greenhouse_controller

# Dashboard
python -m dashboard.dashboard
```

Run these from the `greenhouse_sim/` project root so the `common`, `devices`,
etc. packages resolve correctly.

## Interactive Threshold Control

While the controller is running, type commands directly into its terminal:

```
Controller interactive mode. Commands: <field> <value> | help | quit
Fields: temp_high, temp_low, soil_low, soil_high, light_low, light_high
> temp_high 32
OK: temp_high = 32.0
```

Updates apply immediately to the running rule engine and are broadcast
(retained) on `greenhouse/config/thresholds`, so the dashboard picks them up
too.

## Day/Night Cycle

A shared `day_phase()` helper (`common/daycycle.py`) turns wall-clock time
into a repeating cycle (default 300s = 5 minutes per full day, configurable
in `common/config.py`). Light intensity follows a clipped sine wave (zero at
night, peaking at midday); temperature drift is nudged upward during
daylight and downward at night, with a bounded random walk layered on top
for realism.

## Example Dashboard (placeholder)

```
┌──────────────────── 🌱 Smart Greenhouse Dashboard ─────────────────────┐
│                          Sensors                                       │
│  Temperature      27.4 C        2s ago                                 │
│  Humidity         61.2 %        1s ago                                 │
│  Soil moisture    41.8 %        2s ago                                 │
│  Light            512.0 lux     1s ago                                 │
│                          Actuators                                     │
│  Fan              OFF                                                  │
│  Irrigation pump  OFF                                                  │
│  Grow lamp        OFF                                                  │
│  Active thresholds: temp 24-30C | soil 30-55% | light 250-450lux       │
└──────────────────────────────────────────────────────────────────────┘
```

*(Actual output renders in color with Rich tables/panels; screenshot placeholder — replace with a real terminal capture.)*

## Project Structure

```
greenhouse_sim/
├── docker-compose.yml
├── requirements.txt
├── broker/
│   └── config/mosquitto.conf
├── devices/
│   ├── temperature_sensor.py
│   ├── humidity_sensor.py
│   ├── soil_sensor.py
│   ├── light_sensor.py
│   ├── irrigation.py
│   ├── fan.py
│   └── lamp.py
├── controller/
│   └── greenhouse_controller.py
├── dashboard/
│   └── dashboard.py
├── common/
│   ├── mqtt_client.py
│   ├── config.py
│   ├── models.py
│   └── daycycle.py
└── README.md
```
