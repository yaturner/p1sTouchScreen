"""Entrypoint: builds config, backend, and the main window, then runs the app.

Usage:
    python3 main.py             # uses config.yaml's app.backend setting
    python3 main.py --mock      # force the mock backend (no printer needed)
    python3 main.py --windowed  # don't go fullscreen (handy on a dev machine)
"""
from __future__ import annotations

import argparse
import logging
import sys
from pathlib import Path

from PySide6.QtWidgets import QApplication

from config import load_config
from printer.mock_backend import MockBackend
from ui.main_window import MainWindow


def build_backend(config, force_mock: bool):
    backend_kind = "mock" if force_mock else config.app.backend
    if backend_kind == "real":
        # imported lazily: bambulabs_api pulls in paho-mqtt/pyftpdlib-style
        # deps that the mock-only dev workflow shouldn't need to have installed.
        from printer.real_backend import RealBackend
        return RealBackend(config.printer.ip, config.printer.access_code, config.printer.serial)
    return MockBackend()


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--mock", action="store_true", help="force the mock backend")
    parser.add_argument("--windowed", action="store_true", help="disable fullscreen kiosk mode")
    parser.add_argument("-v", "--verbose", action="store_true")
    args = parser.parse_args()

    logging.basicConfig(level=logging.DEBUG if args.verbose else logging.INFO)

    config = load_config()

    app = QApplication(sys.argv)
    style_path = Path(__file__).resolve().parent / "resources" / "style.qss"
    if style_path.exists():
        app.setStyleSheet(style_path.read_text())

    backend = build_backend(config, force_mock=args.mock)
    if args.mock:
        config.app.backend = "mock"

    window = MainWindow(backend, config)
    window.resize(config.app.screen_width, config.app.screen_height)
    window.apply_window_mode(config.app.fullscreen and not args.windowed)

    backend.connect_printer()

    exit_code = app.exec()
    backend.disconnect_printer()
    return exit_code


if __name__ == "__main__":
    sys.exit(main())
