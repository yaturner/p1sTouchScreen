"""Normalized printer/app state.

This module is the only contract between the printer/ backend layer and the
ui/ layer. UI code must never import bambulabs_api or read raw MQTT dicts
directly -- it only ever sees these dataclasses, delivered via Qt signals.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum, auto


class ConnectionState(Enum):
    DISCONNECTED = auto()
    CONNECTING = auto()
    CONNECTED = auto()
    RECONNECTING = auto()


class GcodeState(Enum):
    IDLE = auto()
    RUNNING = auto()
    PAUSE = auto()
    FINISH = auto()
    FAILED = auto()
    UNKNOWN = auto()


@dataclass
class AMSTray:
    slot_index: int
    filament_type: str | None = None
    color_hex: str | None = None
    is_active: bool = False
    is_empty: bool = True


@dataclass
class PrintFile:
    name: str
    path: str
    size_bytes: int | None = None
    thumbnail: bytes | None = None


@dataclass
class PrinterState:
    connection: ConnectionState = ConnectionState.DISCONNECTED

    nozzle_temp: float | None = None
    nozzle_target: float | None = None
    bed_temp: float | None = None
    bed_target: float | None = None
    chamber_temp: float | None = None

    gcode_state: GcodeState = GcodeState.UNKNOWN
    print_percent: int | None = None
    current_layer: int | None = None
    total_layer: int | None = None
    remaining_minutes: int | None = None
    current_file: str | None = None
    speed_level: int | None = None  # 1=silent .. 4=ludicrous

    fan_speeds: dict[str, int] = field(default_factory=dict)
    light_on: bool | None = None

    ams_trays: list[AMSTray] = field(default_factory=list)
    hms_errors: list[str] = field(default_factory=list)

    raw: dict = field(default_factory=dict)

    @property
    def is_printing(self) -> bool:
        return self.gcode_state in (GcodeState.RUNNING, GcodeState.PAUSE)
