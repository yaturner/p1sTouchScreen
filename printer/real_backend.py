"""Backend that talks to a real P1S over the local network via bambulabs_api.

Method names below were confirmed by introspecting the installed
bambulabs_api package (BambuTools/bambulabs_api on PyPI), not guessed from
docs alone -- see the comments next to anything that's still an assumption
pending a live printer to verify against.
"""
from __future__ import annotations

import hashlib
import json
import logging
import queue
import threading
import zipfile
from datetime import datetime
from io import BytesIO
from pathlib import Path

import bambulabs_api as bl
from PySide6.QtCore import QThread, QTimer, Signal
from PySide6.QtGui import QImage

from printer.base import PrinterBackend
from printer.hms_codes import describe_hms
from printer.image_convert import pil_to_qimage
from state import AMSTray, ConnectionState, GcodeState, PrinterState, PrintFile

logger = logging.getLogger(__name__)

_GCODE_STATE_MAP = {
    "IDLE": GcodeState.IDLE,
    "PREPARE": GcodeState.RUNNING,
    "RUNNING": GcodeState.RUNNING,
    "PAUSE": GcodeState.PAUSE,
    "FINISH": GcodeState.FINISH,
    "FAILED": GcodeState.FAILED,
    "UNKNOWN": GcodeState.UNKNOWN,
}

_RECONNECT_INTERVAL_MS = 5000
_POLL_INTERVAL_MS = 1000
_CAMERA_INTERVAL_MS = 400


class CameraPollThread(QThread):
    """Repeatedly pulls a JPEG frame over the network; this blocks, hence a thread."""

    frame_ready = Signal(object)  # QImage

    def __init__(self, printer: "bl.Printer", parent=None) -> None:
        super().__init__(parent)
        self._printer = printer
        self._running = False

    def run(self) -> None:
        self._running = True
        while self._running:
            try:
                pil_image = self._printer.get_camera_image()
                self.frame_ready.emit(pil_to_qimage(pil_image))
            except Exception:
                logger.debug("camera frame fetch failed", exc_info=True)
            self.msleep(_CAMERA_INTERVAL_MS)

    def stop(self) -> None:
        self._running = False
        self.wait(2000)


# 3MF files above this size aren't worth a full download just for the
# embedded preview PNG -- there's no cheap partial-fetch of one zip member
# over this printer's FTP server, so a full download is the only option.
_MAX_THUMBNAIL_FILE_BYTES = 15 * 1024 * 1024


class ThumbnailLoader(QThread):
    """Downloads each queued 3MF and extracts its embedded preview PNG.

    Runs one file at a time in the background so a large file library never
    blocks the UI or the main poll loop -- thumbnails just pop in as they're
    ready (see thumbnail_ready).
    """

    thumbnail_ready = Signal(str, object)  # (path, QImage)

    def __init__(self, printer: "bl.Printer", ftp_lock: threading.Lock, parent=None) -> None:
        super().__init__(parent)
        self._printer = printer
        self._ftp_lock = ftp_lock
        self._queue: queue.Queue[tuple[str, Path]] = queue.Queue()
        self._running = False

    def enqueue(self, path: str, cache_path: Path) -> None:
        self._queue.put((path, cache_path))

    def run(self) -> None:
        self._running = True
        while self._running:
            try:
                path, cache_path = self._queue.get(timeout=0.5)
            except queue.Empty:
                continue
            image = self._extract_thumbnail(path, cache_path)
            if image is not None:
                self.thumbnail_ready.emit(path, image)

    def stop(self) -> None:
        self._running = False
        self.wait(2000)

    def _extract_thumbnail(self, path: str, cache_path: Path) -> QImage | None:
        try:
            # ftplib's FTP object isn't thread-safe -- this thread and the
            # main-thread file-list request share the same client, so both
            # must hold this lock around every use of it.
            with self._ftp_lock:
                buf = self._printer.ftp_client.download_file(path)
        except Exception:
            logger.debug("thumbnail download failed for %s", path, exc_info=True)
            return None
        try:
            with zipfile.ZipFile(buf) as zf:
                candidates = [n for n in zf.namelist() if n.startswith("Metadata/") and n.lower().endswith(".png")]
                if not candidates:
                    return None
                # Bambu Studio/OrcaSlicer name the main plate preview
                # "Metadata/plate_1.png"; prefer that over auxiliary
                # thumbnails (top view, no-light variant, etc.) if present.
                preferred = next((n for n in candidates if "plate_1" in n), candidates[0])
                png_bytes = zf.read(preferred)
        except Exception:
            logger.debug("thumbnail extraction failed for %s", path, exc_info=True)
            return None
        try:
            cache_path.write_bytes(png_bytes)
        except Exception:
            logger.debug("failed to write thumbnail cache for %s", path, exc_info=True)
        image = QImage.fromData(png_bytes, "PNG")
        return image if not image.isNull() else None


class _FileListWorker(QThread):
    """One-shot background fetch of the FTP file listing.

    request_file_list() is called directly from the UI thread (a button
    click handler); doing the FTP round-trip there would block the GUI even
    without contention, and would block for however long a concurrent
    ThumbnailLoader download holds _ftp_lock. Runs once and exits, unlike
    the long-lived CameraPollThread/ThumbnailLoader.
    """

    result_ready = Signal(list)  # list[PrintFile]
    failed = Signal(str)

    def __init__(self, printer: "bl.Printer", ftp_lock: threading.Lock,
                 extensions: tuple[str, ...], parent=None) -> None:
        super().__init__(parent)
        self._printer = printer
        self._ftp_lock = ftp_lock
        self._extensions = extensions

    def run(self) -> None:
        try:
            # list_cache_dir()'s first return value is NOT a path -- it's
            # ftplib's raw server response line for the LIST command (e.g.
            # "226 Directory send OK."), confirmed by reading
            # PrinterFTPClient.list_directory()'s source. The actual
            # directory listed is hardcoded to "cache" by list_cache_dir()
            # itself, so that's the real prefix for each file's path.
            with self._ftp_lock:
                _ftp_status_line, entries = self._printer.ftp_client.list_cache_dir()
        except Exception as exc:
            self.failed.emit(str(exc))
            return
        files = []
        for entry in entries:
            name, size_bytes, modified = _parse_ftp_list_entry(entry)
            if name.lower().endswith(self._extensions):
                files.append(PrintFile(
                    name=name, path=f"cache/{name}", size_bytes=size_bytes, modified=modified,
                ))
        self.result_ready.emit(files)


class RealBackend(PrinterBackend):
    def __init__(self, ip: str, access_code: str, serial: str) -> None:
        super().__init__()
        self._printer = bl.Printer(ip, access_code, serial)
        self._camera_thread: CameraPollThread | None = None
        self._thumbnail_loader: ThumbnailLoader | None = None
        # Persistent on-disk cache so revisiting Print Files doesn't
        # re-download every thumbnail over this printer's (fairly slow) FTP
        # server every time. Survives app restarts, not just navigation.
        self._thumbnail_cache_dir = Path(__file__).resolve().parent.parent / ".cache" / "thumbnails"
        self._thumbnail_cache_dir.mkdir(parents=True, exist_ok=True)
        # bambulabs_api's ftp_client wraps a single ftplib.FTP control
        # connection that isn't thread-safe; the ThumbnailLoader thread and
        # request_file_list() (main thread) both use it, so every use must
        # go through this lock.
        self._ftp_lock = threading.Lock()
        self._file_list_worker: _FileListWorker | None = None

        self._poll_timer = QTimer(self)
        self._poll_timer.setInterval(_POLL_INTERVAL_MS)
        self._poll_timer.timeout.connect(self._poll)

        self._connecting = False

    # -- lifecycle -----------------------------------------------------
    def connect_printer(self) -> None:
        self._state.connection = ConnectionState.CONNECTING
        self.connection_changed.emit(ConnectionState.CONNECTING)
        self._try_connect()
        self._poll_timer.start()

    def disconnect_printer(self) -> None:
        self._poll_timer.stop()
        if self._camera_thread is not None:
            self._camera_thread.stop()
            self._camera_thread = None
        if self._thumbnail_loader is not None:
            self._thumbnail_loader.stop()
            self._thumbnail_loader = None
        try:
            self._printer.disconnect()
        except Exception:
            logger.debug("disconnect() raised", exc_info=True)
        self._state.connection = ConnectionState.DISCONNECTED
        self.connection_changed.emit(ConnectionState.DISCONNECTED)

    def _try_connect(self) -> None:
        try:
            self._printer.connect()
        except Exception as exc:
            logger.warning("printer.connect() failed: %s", exc)
            self.error.emit(f"Connection failed: {exc}")
            return
        if self._thumbnail_loader is None:
            self._thumbnail_loader = ThumbnailLoader(self._printer, self._ftp_lock, self)
            self._thumbnail_loader.thumbnail_ready.connect(self.thumbnail_ready.emit)
            self._thumbnail_loader.start()
        if self._camera_thread is None:
            self._camera_thread = CameraPollThread(self._printer, self)
            self._camera_thread.frame_ready.connect(self.camera_frame.emit)
            self._camera_thread.start()

    # -- poll loop -----------------------------------------------------
    def _poll(self) -> None:
        try:
            connected = bool(self._printer.mqtt_client_connected())
        except Exception:
            connected = False

        prev = self._state.connection
        if connected:
            if prev != ConnectionState.CONNECTED:
                self._state.connection = ConnectionState.CONNECTED
                self.connection_changed.emit(ConnectionState.CONNECTED)
            self._pull_state()
        else:
            new_state = ConnectionState.RECONNECTING if prev == ConnectionState.CONNECTED \
                else ConnectionState.CONNECTING
            if prev != new_state:
                self._state.connection = new_state
                self.connection_changed.emit(new_state)
            self._try_connect()

    def _pull_state(self) -> None:
        p = self._printer
        s = self._state
        try:
            raw = p.mqtt_dump() or {}
            s.raw = raw
            # mqtt_dump() returns the whole received envelope
            # ({"pushing": ..., "info": ..., "print": {...actual telemetry...}}),
            # confirmed against a live printer -- all per-field state (ams,
            # hms, etc.) lives under raw["print"], not at the top level.
            raw_print = raw.get("print") or {}

            s.nozzle_temp = _safe(p.get_nozzle_temperature)
            s.bed_temp = _safe(p.get_bed_temperature)
            s.chamber_temp = _safe(p.get_chamber_temperature)
            s.nozzle_target = _safe(getattr(p.mqtt_client, "get_nozzle_temperature_target", None))
            s.bed_target = _safe(getattr(p.mqtt_client, "get_bed_temperature_target", None))

            # p.get_state() (bambulabs_api's own decoded getter) was found
            # to get stuck on a long-running connection -- it kept
            # reporting PAUSE well after the raw telemetry (and a fresh
            # connection's own get_state()) had moved on to RUNNING.
            # Read the raw string directly instead, consistent with how
            # every other field here is sourced from raw_print.
            gstate_str = raw_print.get("gcode_state")
            s.gcode_state = _GCODE_STATE_MAP.get(gstate_str, GcodeState.UNKNOWN)

            percent = _safe(p.get_percentage)
            s.print_percent = percent if isinstance(percent, int) else None
            s.current_layer = _safe(p.current_layer_num)
            s.total_layer = _safe(p.total_layer_num)
            remaining = _safe(p.get_time)
            s.remaining_minutes = remaining if isinstance(remaining, int) else None
            s.current_file = _safe(p.subtask_name) or _safe(p.get_file_name)
            s.speed_level = _safe(p.get_print_speed)

            light = _safe(p.get_light_state)
            s.light_on = (str(light).lower() == "on") if light is not None else None

            s.fan_speeds = {
                "part": _pct(_safe(getattr(p.mqtt_client, "get_part_fan_speed", None))),
                "aux": _pct(_safe(getattr(p.mqtt_client, "get_aux_fan_speed", None))),
                "chamber": _pct(_safe(getattr(p.mqtt_client, "get_chamber_fan_speed", None))),
            }

            s.ams_trays = self._read_ams_trays(raw_print)
            s.hms_errors = self._describe_hms_entries(raw_print.get("hms"))

            self.state_changed.emit(s)
        except Exception:
            logger.exception("failed to pull/normalize printer state")

    @staticmethod
    def _describe_hms_entries(entries) -> list[str]:
        if not isinstance(entries, list):
            return []
        described = []
        for entry in entries:
            if not isinstance(entry, dict):
                continue
            attr, code = entry.get("attr"), entry.get("code")
            if attr is None or code is None:
                continue
            try:
                described.append(describe_hms(int(attr), int(code)))
            except (TypeError, ValueError):
                continue
        return described

    def _read_ams_trays(self, raw: dict) -> list[AMSTray]:
        trays: list[AMSTray] = []
        try:
            hub = self._printer.ams_hub()
            ams_unit = hub[0]
            active_index = self._active_tray_index(raw)
            for i in range(4):
                ft = ams_unit.get_filament_tray(i)
                if ft is None:
                    trays.append(AMSTray(slot_index=i, is_empty=True))
                    continue
                trays.append(AMSTray(
                    slot_index=i,
                    filament_type=getattr(ft, "tray_type", None) or None,
                    color_hex=_normalize_color(getattr(ft, "tray_color", None)),
                    is_active=(i == active_index),
                    is_empty=not bool(getattr(ft, "tray_type", None)),
                ))
        except Exception:
            logger.debug("AMS read failed (no AMS attached, or hub not yet populated)", exc_info=True)
        return trays

    @staticmethod
    def _active_tray_index(raw: dict) -> int | None:
        # "ams.tray_now" is a global tray index per Bambu's local MQTT schema;
        # 255/"255" conventionally means "no tray active". Verify against a
        # live printer's mqtt_dump() the first time this runs for real.
        ams_block = raw.get("ams") or {}
        tray_now = ams_block.get("tray_now") if isinstance(ams_block, dict) else None
        try:
            idx = int(tray_now)
        except (TypeError, ValueError):
            return None
        return idx if 0 <= idx < 4 else None

    # -- print job control ------------------------------------------------
    _PRINT_START_RETRY_DELAY_MS = 6000

    def start_print(self, filename: str, plate: int = 1) -> None:
        # bambulabs_api's start_print()/start_print_3mf() reference the file
        # via "url": "ftp:///{filename}". Confirmed live on a P1S this
        # reliably fails to actually start the print (gcode_state stuck on
        # IDLE/FAILED, 0% progress, no heating) even for a file that prints
        # fine via Bambu Studio/Handy. Live-tested fix: reference the file
        # via its LOCAL path on the printer's own SD card
        # ("file:///sdcard/<path>") instead -- this went
        # IDLE -> PREPARE -> RUNNING in ~12s with no retry needed. Kept a
        # one-shot retry as a safety net anyway, since a brand-new
        # (not-yet-cached) job occasionally needed a second attempt via
        # Bambu's own official client too, for reasons unrelated to payload
        # correctness.
        self._start_print_attempt(filename, plate, allow_retry=True)

    def _start_print_attempt(self, filename: str, plate: int, allow_retry: bool) -> None:
        bare_name = filename.rsplit("/", 1)[-1]
        plate_location = f"Metadata/plate_{int(plate)}.gcode" if isinstance(plate, int) else plate
        self._call(self._publish_raw, {
            "print": {
                "sequence_id": "2000",
                "command": "project_file",
                "param": plate_location,
                "subtask_name": bare_name,
                "file": bare_name,
                "url": f"file:///sdcard/{filename}",
                "timelapse": False,
                "bed_leveling": True,
                "bed_type": "textured_plate",
                "flow_cali": True,
                "vibration_cali": True,
                "layer_inspect": False,
                # use_ams=True + ams_mapping=[0]: live-tested both
                # directions on a P1S with an AMS attached (no external
                # spool). use_ams=False caused a DIFFERENT real failure --
                # "External filament is missing" -- because it tells the
                # printer to feed from the external spool holder, which
                # doesn't exist here. use_ams=True + ams_mapping=[0] (map
                # the file's first/only filament to AMS slot 0) is correct
                # for single-material files; a file whose embedded
                # object/color mapping expects more than one filament may
                # still fail with HMS_0700_7000_0002_0008 ("failed to get
                # AMS mapping table") since this app doesn't parse a 3MF's
                # internal multi-material metadata to build a real mapping.
                # That failure now surfaces as a readable message (see
                # hms_codes.py) instead of silently doing nothing.
                "use_ams": True,
                "ams_mapping": [0],
            },
        })
        if allow_retry:
            QTimer.singleShot(
                self._PRINT_START_RETRY_DELAY_MS,
                lambda: self._check_print_start_result(filename, plate),
            )

    def _check_print_start_result(self, filename: str, plate: int) -> None:
        raw_print = (self._printer.mqtt_dump() or {}).get("print") or {}
        if raw_print.get("gcode_state") == "FAILED":
            logger.info("start_print failed on first attempt, retrying once")
            self._start_print_attempt(filename, plate, allow_retry=False)

    def pause_print(self) -> None:
        self._call(self._printer.pause_print)

    def resume_print(self) -> None:
        self._call(self._printer.resume_print)

    def stop_print(self) -> None:
        self._call(self._printer.stop_print)

    def set_speed_level(self, level: int) -> None:
        self._call(self._printer.set_print_speed, level)

    # -- temperature / motion --------------------------------------------
    def set_nozzle_target(self, celsius: int) -> None:
        # Printer.set_nozzle_temperature() doesn't expose the underlying
        # mqtt_client's `override` param, which defaults to False and
        # silently REJECTS any target below 60C ("not recommended") --
        # including 0, i.e. "turn the heater off". Our keypad already lets
        # the user pick any value in [0, 300], so that guard is redundant
        # here and would otherwise break turning heat off. Confirmed via
        # live-printer testing that override=True is required for this to
        # actually take effect at all (bare Printer-level call returned
        # False for a 200C target on this printer's firmware).
        self._call(self._printer.mqtt_client.set_nozzle_temperature, celsius, override=True)

    def set_bed_target(self, celsius: int) -> None:
        self._call(self._printer.mqtt_client.set_bed_temperature, celsius, override=True)

    def home_axes(self) -> None:
        self._call(self._printer.home_printer)

    def jog(self, axis: str, distance_mm: float) -> None:
        # No dedicated relative-jog method in bambulabs_api's high-level API.
        # move_z_axis()/set_bed_height() looked like a Z-jog helper but is
        # actually an ABSOLUTE move (G0 Z<height>) -- using it here would
        # send the nozzle to a fixed height rather than nudging it by
        # distance_mm from wherever it currently is, which for a Z- press
        # could mean an unexpected large move toward the bed. Use the same
        # relative G91/G1/G90 pattern as X/Y for all three axes instead.
        axis = axis.upper()
        feed = 600 if axis == "Z" else 3000  # slower default feedrate for Z
        self._call(self._printer.gcode, ["G91", f"G1 {axis}{distance_mm} F{feed}", "G90"])

    def extrude(self, mm: float) -> None:
        # M83: relative extrusion mode, so mm can be negative to retract.
        self._call(self._printer.gcode, ["M83", f"G1 E{mm} F300"])

    def set_fan_speed(self, fan: str, percent: int) -> None:
        setter = {
            "part": self._printer.set_part_fan_speed,
            "aux": self._printer.set_aux_fan_speed,
            "chamber": self._printer.set_chamber_fan_speed,
        }.get(fan)
        if setter is None:
            logger.warning("unknown fan %r", fan)
            return
        # These setters interpret an int as a raw 0-255 PWM value (not a
        # percent!) and a float as a 0-1 fraction -- but the float path has
        # its own bug (computes 255/speed instead of 255*speed, and
        # ZeroDivisions at speed=0.0). Confirmed via source inspection.
        # Convert our UI's 0-100 percent to raw PWM and use the int path,
        # which is the only one that's actually correct.
        percent = max(0, min(100, int(percent)))
        raw_pwm = round(percent / 100 * 255)
        self._call(setter, raw_pwm)

    def light_on(self) -> None:
        self._call(self._printer.turn_light_on)

    def light_off(self) -> None:
        self._call(self._printer.turn_light_off)

    # -- AMS / filament ---------------------------------------------------
    # bambulabs_api doesn't wrap AMS load/unload at the high level (only
    # load_filament_spool()/unload_filament_spool() for the single external
    # "vt_tray" holder). Confirmed against OpenBambuAPI's documented local
    # MQTT schema (github.com/Doridian/OpenBambuAPI/blob/main/mqtt.md) and
    # verified live on a real P1S + AMS:
    #   print.ams_change_filament: {"target": <tray id>, "curr_temp": ...,
    #     "tar_temp": ...} -- switches the active tray and handles the
    #     nozzle temperature transition for the swap.
    #   print.unload_filament: no params -- unloads whatever is active.
    _DEFAULT_NOZZLE_TARGET_TEMP = 220

    def load_filament(self, slot: int) -> None:
        current_temp = self._printer.get_nozzle_temperature()
        curr_temp = int(current_temp) if current_temp is not None else 0
        tar_temp = self._DEFAULT_NOZZLE_TARGET_TEMP
        try:
            tray = self._printer.ams_hub()[0].get_filament_tray(slot)
            if tray is not None and getattr(tray, "nozzle_temp_min", None):
                tar_temp = int(tray.nozzle_temp_min)
        except Exception:
            logger.debug("couldn't read tray nozzle_temp_min, using default", exc_info=True)

        self._call(self._publish_raw, {
            "print": {
                "sequence_id": "0",
                "command": "ams_change_filament",
                "target": slot,
                "curr_temp": curr_temp,
                "tar_temp": tar_temp,
            }
        })

    def unload_filament(self, slot: int) -> None:
        self._call(self._publish_raw, {
            "print": {
                "sequence_id": "0",
                "command": "unload_filament",
            }
        })

    def _publish_raw(self, payload: dict) -> None:
        client = self._printer.mqtt_client
        ok = client._client.publish(client.command_topic, json.dumps(payload))
        ok.wait_for_publish()
        if not ok.is_published():
            raise RuntimeError(f"MQTT publish failed for {payload}")

    # -- files ----------------------------------------------------------------
    _PRINT_FILE_EXTENSIONS = (".3mf", ".stl")

    def request_file_list(self) -> None:
        if self._file_list_worker is not None and self._file_list_worker.isRunning():
            return  # a request is already in flight
        worker = _FileListWorker(self._printer, self._ftp_lock, self._PRINT_FILE_EXTENSIONS, self)
        worker.result_ready.connect(self._on_file_list_result)
        worker.failed.connect(self._on_file_list_failed)
        worker.finished.connect(worker.deleteLater)
        self._file_list_worker = worker
        worker.start()

    def _on_file_list_failed(self, message: str) -> None:
        logger.warning("file list failed: %s", message)
        self.error.emit(f"Couldn't list files: {message}")
        self.file_list_ready.emit([])

    def _on_file_list_result(self, files: list[PrintFile]) -> None:
        self.file_list_ready.emit(files)

        # Only .3mf files actually embed a thumbnail (a raw .stl has none).
        for f in files:
            if not f.name.lower().endswith(".3mf") or (f.size_bytes or 0) > _MAX_THUMBNAIL_FILE_BYTES:
                continue
            cache_path = self._thumbnail_cache_path(f.path, f.size_bytes or 0)
            cached_image = self._load_cached_thumbnail(cache_path)
            if cached_image is not None:
                self.thumbnail_ready.emit(f.path, cached_image)
            elif self._thumbnail_loader is not None:
                self._thumbnail_loader.enqueue(f.path, cache_path)

    def _thumbnail_cache_path(self, path: str, size_bytes: int) -> Path:
        # Keyed on path+size rather than path alone: a same-named file
        # re-sliced/re-uploaded with different content will very likely
        # differ in size too, so this catches the common "file changed"
        # case without needing to parse FTP LIST's date column.
        key = hashlib.sha1(f"{path}:{size_bytes}".encode()).hexdigest()
        return self._thumbnail_cache_dir / f"{key}.png"

    @staticmethod
    def _load_cached_thumbnail(cache_path: Path) -> QImage | None:
        if not cache_path.exists():
            return None
        image = QImage(str(cache_path))
        return image if not image.isNull() else None

    # -- helpers ----------------------------------------------------------------
    def _call(self, fn, *args, **kwargs):
        try:
            fn(*args, **kwargs)
        except Exception as exc:
            logger.warning("%s failed: %s", getattr(fn, "__name__", fn), exc)
            self.error.emit(str(exc))


def _parse_ftp_list_entry(entry: str) -> tuple[str, int | None, datetime | None]:
    """Parse one line of list_cache_dir()'s output.

    bambulabs_api's PrinterFTPClient.list_cache_dir() returns raw Unix
    `ls -l`-style directory listing lines (as FTP servers commonly do for
    LIST), not bare filenames, e.g.:
        -rw-rw-rw- 1 root root 43745911 Nov 24 2025 0.16mm layer, 2 walls, 6% infill.3mf
    Filenames themselves may contain spaces, so the split is anchored on
    the 8 fixed-width fields (perms, links, owner, group, size, month,
    day, year-or-time) and everything after that is the filename.
    Falls back to treating the whole line as a filename if it doesn't
    match that shape (e.g. if a future library version returns bare
    names instead).
    """
    parts = entry.split(None, 8)
    if len(parts) == 9 and parts[0][0] in "-dl":
        size_bytes = int(parts[4]) if parts[4].isdigit() else None
        modified = _parse_ftp_mtime(parts[5], parts[6], parts[7])
        return parts[8], size_bytes, modified
    return entry.strip(), None, None


def _parse_ftp_mtime(month: str, day: str, year_or_time: str) -> datetime | None:
    # ls -l shows a time (HH:MM, current year implied) for recent files and
    # a year for older ones -- never both, so the field's shape tells us
    # which case we're in.
    try:
        if ":" in year_or_time:
            year = datetime.now().year
            return datetime.strptime(f"{month} {day} {year} {year_or_time}", "%b %d %Y %H:%M")
        return datetime.strptime(f"{month} {day} {year_or_time}", "%b %d %Y")
    except ValueError:
        return None


def _safe(fn):
    if fn is None:
        return None
    try:
        return fn()
    except Exception:
        return None


def _pct(fan_gear_value) -> int:
    """Bambu reports fan speed as a 0-15 'gear' value on some fields; clamp/scale to 0-100."""
    if fan_gear_value is None:
        return 0
    try:
        value = float(fan_gear_value)
    except (TypeError, ValueError):
        return 0
    if value <= 15:
        return round(value / 15 * 100)
    return round(min(100, value))


def _normalize_color(tray_color) -> str | None:
    if not tray_color:
        return None
    s = str(tray_color).lstrip("#")
    return f"#{s[:6]}" if len(s) >= 6 else None
