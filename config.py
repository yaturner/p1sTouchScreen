"""Load/save app configuration from a YAML file.

Looks for config.yaml next to this file by default (simple, single-user
kiosk deployment -- no XDG dance needed for a Pi that runs one app).
"""
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import yaml

DEFAULT_CONFIG_PATH = Path(__file__).resolve().parent / "config.yaml"


@dataclass
class PrinterConfig:
    ip: str = ""
    access_code: str = ""
    serial: str = ""

    @property
    def is_complete(self) -> bool:
        return bool(self.ip and self.access_code and self.serial)


@dataclass
class AppConfig:
    backend: str = "mock"  # "mock" | "real"
    fullscreen: bool = True
    screen_width: int = 1024
    screen_height: int = 600
    # This printer's real-world FTPS throughput is slow (tens of KB/s, not
    # the multi-MB/s you'd expect on a LAN), so downloading+caching a
    # thumbnail for every file in a large library can take several minutes
    # the first time Print Files loads. Lets a user with a large/slow
    # library skip that entirely.
    skip_thumbnails: bool = False


@dataclass
class Config:
    printer: PrinterConfig
    app: AppConfig
    path: Path

    @property
    def is_ready(self) -> bool:
        """True if enough info is present to skip the first-run setup screen."""
        return self.app.backend == "mock" or self.printer.is_complete


def load_config(path: Path | None = None) -> Config:
    path = path or DEFAULT_CONFIG_PATH
    if not path.exists():
        return Config(printer=PrinterConfig(), app=AppConfig(backend="mock"), path=path)

    with path.open("r") as fh:
        raw = yaml.safe_load(fh) or {}

    printer_raw = raw.get("printer") or {}
    app_raw = raw.get("app") or {}

    printer = PrinterConfig(
        ip=str(printer_raw.get("ip", "")),
        access_code=str(printer_raw.get("access_code", "")),
        serial=str(printer_raw.get("serial", "")),
    )
    app = AppConfig(
        backend=str(app_raw.get("backend", "mock")),
        fullscreen=bool(app_raw.get("fullscreen", True)),
        screen_width=int(app_raw.get("screen_width", 1024)),
        screen_height=int(app_raw.get("screen_height", 600)),
        skip_thumbnails=bool(app_raw.get("skip_thumbnails", False)),
    )
    return Config(printer=printer, app=app, path=path)


def save_config(config: Config) -> None:
    data = {
        "printer": {
            "ip": config.printer.ip,
            "access_code": config.printer.access_code,
            "serial": config.printer.serial,
        },
        "app": {
            "backend": config.app.backend,
            "fullscreen": config.app.fullscreen,
            "screen_width": config.app.screen_width,
            "screen_height": config.app.screen_height,
            "skip_thumbnails": config.app.skip_thumbnails,
        },
    }
    with config.path.open("w") as fh:
        yaml.safe_dump(data, fh, default_flow_style=False)
