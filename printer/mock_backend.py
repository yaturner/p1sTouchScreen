"""Synthetic backend for UI development without a printer.

Exercises exactly the same signals as RealBackend (state_changed,
connection_changed, camera_frame, file_list_ready) so screens never need to
know which backend is active.
"""
from __future__ import annotations

import math
import time
from datetime import datetime, timedelta

from PySide6.QtCore import QTimer, Qt
from PySide6.QtGui import QColor, QImage, QPainter

from printer.base import PrinterBackend
from state import AMSTray, ConnectionState, GcodeState, PrinterState, PrintFile

_NOW = datetime.now()
_MOCK_FILES = [
    PrintFile(name="benchy.gcode.3mf", path="/benchy.gcode.3mf", size_bytes=1_200_000,
              modified=_NOW - timedelta(days=1)),
    PrintFile(name="calibration_cube.3mf", path="/calibration_cube.3mf", size_bytes=340_000,
              modified=_NOW - timedelta(days=10)),
    PrintFile(name="bracket_v3.gcode.3mf", path="/bracket_v3.gcode.3mf", size_bytes=980_000,
              modified=_NOW - timedelta(hours=3)),
]

_AMS_COLORS = ["#1E88E5", "#43A047", "#FDD835", "#E53935"]
_AMS_TYPES = ["PLA", "PETG", "PLA", "ABS"]


class MockBackend(PrinterBackend):
    def __init__(self) -> None:
        super().__init__()
        self._connected = False
        self._printing = False
        self._t0 = time.monotonic()
        self._nozzle_target = 0
        self._bed_target = 0
        self._light_on = True
        self._speed_level = 2
        self._ams_trays = [
            AMSTray(slot_index=i, filament_type=_AMS_TYPES[i], color_hex=_AMS_COLORS[i],
                     is_active=(i == 0), is_empty=False)
            for i in range(4)
        ]
        # Simulated "AMS busy" window so the Load/Unload/Sync-disabling UI
        # can be exercised without real hardware -- real backend derives
        # this from tray_tar != tray_now instead (see _is_ams_busy).
        self._ams_busy_until = 0.0

        self._poll_timer = QTimer(self)
        self._poll_timer.setInterval(1000)
        self._poll_timer.timeout.connect(self._tick)

        self._camera_timer = QTimer(self)
        self._camera_timer.setInterval(500)
        self._camera_timer.timeout.connect(self._emit_fake_frame)

    # -- lifecycle -----------------------------------------------------
    def connect_printer(self) -> None:
        self.connection_changed.emit(ConnectionState.CONNECTING)
        self._connected = True
        self.connection_changed.emit(ConnectionState.CONNECTED)
        self._poll_timer.start()
        self._camera_timer.start()
        self._tick()

    def disconnect_printer(self) -> None:
        self._connected = False
        self._poll_timer.stop()
        self._camera_timer.stop()
        self.connection_changed.emit(ConnectionState.DISCONNECTED)

    # -- print job control ------------------------------------------------
    def start_print(self, filename: str, plate: int = 1) -> None:
        self._printing = True
        self._print_started_at = time.monotonic()
        self._current_file = filename
        self._state.gcode_state = GcodeState.RUNNING
        self._tick()

    def confirm_pending_print(self) -> None:
        pass  # mock never emits print_start_warning, so nothing is ever pending

    def cancel_pending_print(self) -> None:
        pass

    def pause_print(self) -> None:
        self._state.gcode_state = GcodeState.PAUSE
        self._tick()

    def resume_print(self) -> None:
        self._state.gcode_state = GcodeState.RUNNING
        self._tick()

    def stop_print(self) -> None:
        self._printing = False
        self._state.gcode_state = GcodeState.IDLE
        self._state.print_percent = None
        self._state.current_layer = None
        self._state.current_file = None
        self._tick()

    def set_speed_level(self, level: int) -> None:
        self._speed_level = level
        self._tick()

    # -- temperature / motion --------------------------------------------
    def set_nozzle_target(self, celsius: int) -> None:
        self._nozzle_target = celsius
        self._tick()

    def set_bed_target(self, celsius: int) -> None:
        self._bed_target = celsius
        self._tick()

    def home_axes(self) -> None:
        pass  # no-op in mock; real backend sends G28

    def jog(self, axis: str, distance_mm: float) -> None:
        pass  # no physical motion to simulate meaningfully

    def extrude(self, mm: float) -> None:
        pass

    def set_fan_speed(self, fan: str, percent: int) -> None:
        self._state.fan_speeds[fan] = percent
        self._tick()

    def light_on(self) -> None:
        self._light_on = True
        self._tick()

    def light_off(self) -> None:
        self._light_on = False
        self._tick()

    # -- AMS ----------------------------------------------------------------
    _AMS_BUSY_SECONDS = 3.0

    def load_filament(self, slot: int) -> None:
        self._ams_busy_until = time.monotonic() + self._AMS_BUSY_SECONDS
        self._tick()
        QTimer.singleShot(int(self._AMS_BUSY_SECONDS * 1000), lambda: self._finish_ams_swap(slot, active=True))

    def unload_filament(self, slot: int) -> None:
        self._ams_busy_until = time.monotonic() + self._AMS_BUSY_SECONDS
        self._tick()
        QTimer.singleShot(int(self._AMS_BUSY_SECONDS * 1000), lambda: self._finish_ams_swap(slot, active=False))

    def _finish_ams_swap(self, slot: int, active: bool) -> None:
        for tray in self._ams_trays:
            tray.is_active = active and tray.slot_index == slot
        self._tick()

    def sync_ams(self) -> None:
        self._tick()  # nothing to actually re-request in mock mode

    # -- files ----------------------------------------------------------------
    def request_file_list(self) -> None:
        self.file_list_ready.emit(list(_MOCK_FILES))
        # Fake the real backend's "thumbnails pop in a bit after the list"
        # behavior (there it's a background download; here it's just a
        # deliberate delay) so the UI's incremental-icon-loading path gets
        # exercised in mock mode too.
        for i, f in enumerate(_MOCK_FILES):
            QTimer.singleShot(400 + i * 250, lambda f=f: self._emit_mock_thumbnail(f))

    def _emit_mock_thumbnail(self, f: PrintFile) -> None:
        image = QImage(96, 96, QImage.Format.Format_RGB32)
        color = _AMS_COLORS[hash(f.path) % len(_AMS_COLORS)]
        image.fill(QColor(color))
        self.thumbnail_ready.emit(f.path, image)

    # -- internal ----------------------------------------------------------
    def _tick(self) -> None:
        elapsed = time.monotonic() - self._t0
        # smoothly ramp fake temps toward targets
        nozzle = self._nozzle_target * (1 - math.exp(-elapsed / 20)) if self._nozzle_target else 25 + 2 * math.sin(elapsed / 5)
        bed = self._bed_target * (1 - math.exp(-elapsed / 30)) if self._bed_target else 24 + math.sin(elapsed / 7)

        s = self._state
        s.connection = ConnectionState.CONNECTED if self._connected else ConnectionState.DISCONNECTED
        s.nozzle_temp = round(nozzle, 1)
        s.nozzle_target = self._nozzle_target
        s.bed_temp = round(bed, 1)
        s.bed_target = self._bed_target
        s.chamber_temp = 28.0
        s.light_on = self._light_on
        s.speed_level = self._speed_level
        s.ams_trays = self._ams_trays
        s.ams_busy = time.monotonic() < self._ams_busy_until
        s.hms_errors = []

        if self._printing:
            print_elapsed = time.monotonic() - self._print_started_at
            total_seconds = 600  # fake 10-minute print
            pct = min(100, int(print_elapsed / total_seconds * 100))
            s.gcode_state = s.gcode_state if s.gcode_state == GcodeState.PAUSE else GcodeState.RUNNING
            s.print_percent = pct
            s.total_layer = 120
            s.current_layer = min(120, int(pct / 100 * 120))
            s.remaining_minutes = max(0, int((total_seconds - print_elapsed) / 60))
            s.current_file = getattr(self, "_current_file", None)
            if pct >= 100:
                s.gcode_state = GcodeState.FINISH
                self._printing = False
        else:
            s.gcode_state = GcodeState.IDLE if s.gcode_state != GcodeState.FINISH else s.gcode_state

        self.state_changed.emit(s)

    def _emit_fake_frame(self) -> None:
        img = QImage(320, 240, QImage.Format.Format_RGB32)
        hue = int((time.monotonic() * 40) % 360)
        img.fill(QColor.fromHsv(hue, 120, 60))
        painter = QPainter(img)
        painter.setPen(QColor("white"))
        label = "PRINTING" if self._printing else "MOCK CAMERA"
        painter.drawText(img.rect(), Qt.AlignmentFlag.AlignCenter, label)
        painter.end()
        self.camera_frame.emit(img)
