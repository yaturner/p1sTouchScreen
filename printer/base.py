"""Backend interface shared by the mock and real printer backends.

UI code talks only to this interface (via Qt signals) and never imports
bambulabs_api or the mock generator directly. Swapping backends is a
one-line change in main.py.
"""
from __future__ import annotations

from abc import abstractmethod

from PySide6.QtCore import QObject, Signal

from state import ConnectionState, PrinterState, PrintFile


class PrinterBackend(QObject):
    # PrinterState
    state_changed = Signal(object)
    # ConnectionState
    connection_changed = Signal(object)
    # QImage
    camera_frame = Signal(object)
    # list[PrintFile]
    file_list_ready = Signal(list)
    # (path: str, thumbnail: QImage) -- emitted lazily per-file after
    # file_list_ready, since fetching a thumbnail means downloading each file
    thumbnail_ready = Signal(str, object)
    # str -- surfaced to the UI as a toast/dialog, e.g. command failures
    error = Signal(str)
    # str -- a specific, actionable reason a resolved print hasn't actually
    # started yet (e.g. an uncertain AMS filament match), shown as a dialog
    # the user must resolve via confirm_pending_print()/
    # cancel_pending_print() rather than a toast that could be missed
    print_start_warning = Signal(str)

    def __init__(self) -> None:
        super().__init__()
        self._state = PrinterState(connection=ConnectionState.DISCONNECTED)

    @property
    def state(self) -> PrinterState:
        return self._state

    # -- lifecycle -----------------------------------------------------
    @abstractmethod
    def connect_printer(self) -> None: ...

    @abstractmethod
    def disconnect_printer(self) -> None: ...

    # -- print job control ----------------------------------------------
    @abstractmethod
    def start_print(self, filename: str, plate: int = 1) -> None: ...

    # No-ops unless a print_start_warning is currently pending (see that
    # signal's docstring) -- confirm actually starts it, cancel abandons it.
    @abstractmethod
    def confirm_pending_print(self) -> None: ...

    @abstractmethod
    def cancel_pending_print(self) -> None: ...

    @abstractmethod
    def pause_print(self) -> None: ...

    @abstractmethod
    def resume_print(self) -> None: ...

    @abstractmethod
    def stop_print(self) -> None: ...

    @abstractmethod
    def set_speed_level(self, level: int) -> None: ...

    # -- temperature / motion --------------------------------------------
    @abstractmethod
    def set_nozzle_target(self, celsius: int) -> None: ...

    @abstractmethod
    def set_bed_target(self, celsius: int) -> None: ...

    @abstractmethod
    def home_axes(self) -> None: ...

    @abstractmethod
    def jog(self, axis: str, distance_mm: float) -> None: ...

    @abstractmethod
    def extrude(self, mm: float) -> None: ...

    @abstractmethod
    def set_fan_speed(self, fan: str, percent: int) -> None: ...

    @abstractmethod
    def light_on(self) -> None: ...

    @abstractmethod
    def light_off(self) -> None: ...

    # -- AMS / filament ---------------------------------------------------
    @abstractmethod
    def load_filament(self, slot: int) -> None: ...

    @abstractmethod
    def unload_filament(self, slot: int) -> None: ...

    # Re-requests the printer's full state (including AMS) right now
    # rather than waiting for the periodic refresh -- there's no local
    # MQTT command that makes the AMS hardware itself re-scan a spool's
    # RFID tag (that's autonomous firmware behavior), so this only
    # refreshes what the app displays from whatever the printer currently
    # knows, e.g. right after physically swapping a spool.
    @abstractmethod
    def sync_ams(self) -> None: ...

    # -- files -------------------------------------------------------------
    @abstractmethod
    def request_file_list(self) -> None: ...
