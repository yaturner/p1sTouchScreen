"""Bambu HMS (Health Management System) error code lookup.

The 4998-entry English code->message table is vendored from
greghesp/ha-bambulab's pybambu/hms_error_text/hms_en.json.gz (that project
maintains it from Bambu's own official multi-language HMS text resources),
flattened to {16-hex-digit code: message}. Loaded lazily and cached -- it's
only needed when an HMS entry actually shows up.
"""
from __future__ import annotations

import gzip
import json
from functools import lru_cache
from pathlib import Path

_DATA_PATH = Path(__file__).resolve().parent.parent / "resources" / "data" / "hms_codes_en.json.gz"


@lru_cache(maxsize=1)
def _load() -> dict[str, str]:
    try:
        with gzip.open(_DATA_PATH, "rt", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return {}


def hms_code_string(attr: int, code: int) -> str:
    """The wiki.bambulab.com-style code, e.g. "0700_7000_0002_0008"."""
    attr_h = format(attr & 0xFFFFFFFF, "08x")
    code_h = format(code & 0xFFFFFFFF, "08x")
    return f"{attr_h[:4]}_{attr_h[4:]}_{code_h[:4]}_{code_h[4:]}"


def describe_hms(attr: int, code: int) -> str:
    """Human-readable message for an HMS entry, or the raw code if unknown."""
    key = f"{attr & 0xFFFFFFFF:08x}{code & 0xFFFFFFFF:08x}"
    message = _load().get(key)
    code_string = hms_code_string(attr, code)
    return f"{message} (HMS_{code_string})" if message else f"Unknown HMS error (HMS_{code_string})"
