"""Curated filament presets for the AMS slot "Edit" dialog.

Each preset's tray_info_idx/nozzle_temp_min/nozzle_temp_max/tray_type is
copied directly from bambulabs_api's own Filament enum
(bambulabs_api/filament_info.py) -- not guessed. That enum only
distinguishes Bambu Lab's own lines, PolyLite, and PolyTerra by brand; the
AMS RFID/preset system has no separate tray_info_idx for other
third-party brands. So Overature/eSUN's presets below use their own
real product-line names (e.g. eSUN's "PLA+") but are still mapped onto
Bambu's "Generic" PLA tray_info_idx (GFL99) under the hood -- only the
label is brand-specific, not the underlying MQTT payload. "Generic" (the
explicit catch-all manufacturer) gets the full Generic material list
instead of a brand-specific one.
"""
from __future__ import annotations

from dataclasses import dataclass

MANUFACTURERS = ["Bambu Lab", "PolyLite", "Overature", "Generic", "PolyTerra", "eSUN"]


@dataclass(frozen=True)
class FilamentPreset:
    label: str
    tray_info_idx: str
    nozzle_temp_min: int
    nozzle_temp_max: int
    tray_type: str


_BAMBU_PRESETS = [
    FilamentPreset("PLA Basic", "GFA00", 190, 230, "PLA"),
    FilamentPreset("PLA Matte", "GFA01", 190, 230, "PLA"),
    FilamentPreset("PLA Silk", "GFA05", 210, 230, "PLA"),
    FilamentPreset("PLA-CF", "GFA50", 210, 240, "PLA"),
    FilamentPreset("PETG HF", "GFG02", 230, 260, "PETG"),
    FilamentPreset("PETG-CF", "GFG50", 240, 270, "PETG"),
    FilamentPreset("ABS", "GFB00", 240, 270, "ABS"),
    FilamentPreset("ASA", "GFB01", 240, 270, "ASA"),
    FilamentPreset("PC", "GFC00", 260, 280, "PC"),
    FilamentPreset("PA-CF", "GFN03", 270, 300, "PA-CF"),
    FilamentPreset("TPU for AMS", "GFU02", 230, 230, "TPU"),
    FilamentPreset("Support (PLA/PETG)", "GFS05", 190, 220, "Support"),
]

# The GFxx99 "Generic" family -- what any non-Bambu/PolyLite/PolyTerra
# spool reads as to the printer, regardless of its actual brand.
_GENERIC_PRESETS = [
    FilamentPreset("PLA", "GFL99", 190, 250, "PLA"),
    FilamentPreset("PLA-CF", "GFL98", 190, 250, "PLA"),
    FilamentPreset("PETG", "GFG99", 220, 260, "PETG"),
    FilamentPreset("ABS", "GFB99", 240, 270, "ABS"),
    FilamentPreset("ASA", "GFB98", 240, 270, "ASA"),
    FilamentPreset("PA", "GFN99", 270, 300, "PA"),
    FilamentPreset("PA-CF", "GFN98", 270, 300, "PA"),
    FilamentPreset("PC", "GFC99", 260, 280, "PC"),
    FilamentPreset("TPU", "GFU99", 200, 250, "TPU"),
    FilamentPreset("PVA", "GFS99", 190, 250, "PVA"),
]

PRESETS_BY_MANUFACTURER: dict[str, list[FilamentPreset]] = {
    "Bambu Lab": _BAMBU_PRESETS,
    "PolyLite": [FilamentPreset("PLA", "GFL00", 190, 250, "PLA")],
    "PolyTerra": [FilamentPreset("PLA", "GFL01", 190, 250, "PLA")],
    # Overature/eSUN product-line names, still mapped onto the Generic PLA
    # tray_info_idx (GFL99) -- there's no brand-specific index for either
    # in bambulabs_api's enum, only the label differs from "Generic".
    "Overature": [
        FilamentPreset("Matte PLA", "GFL99", 190, 230, "PLA"),
        FilamentPreset("PLA", "GFL99", 190, 250, "PLA"),
    ],
    "Generic": _GENERIC_PRESETS,
    "eSUN": [FilamentPreset("PLA+", "GFL99", 190, 230, "PLA")],
}


def preset_key(manufacturer: str, label: str) -> str:
    return f"{manufacturer}|{label}"


# Flat lookup by preset_key(), for the backend command layer -- it only
# needs the resolved preset, not which manufacturer picked it.
FILAMENT_PRESETS: dict[str, FilamentPreset] = {
    preset_key(manufacturer, preset.label): preset
    for manufacturer, presets in PRESETS_BY_MANUFACTURER.items()
    for preset in presets
}
