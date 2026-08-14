"""Documented bambulabs_api / raw MQTT (mqtt_dump()) field names.

bambulabs_api's high-level getters don't expose everything the A1-style UI
needs (chamber temp, per-tray AMS detail, fan speeds, HMS errors). Where
that's true, real_backend._normalize() falls back to reading these keys
directly out of printer.mqtt_dump(). Names are taken from Bambu's local
MQTT report schema (see OpenBambuAPI's mqtt.md) -- CONFIRM against a live
printer's mqtt_dump() output the first time real_backend.py is run against
real hardware, since P1-series only reports *changed* fields (not a full
snapshot) after the initial pushall.
"""

NOZZLE_TEMPER = "nozzle_temper"
NOZZLE_TARGET = "nozzle_target_temper"
BED_TEMPER = "bed_temper"
BED_TARGET = "bed_target_temper"
CHAMBER_TEMPER = "chamber_temper"

GCODE_STATE = "gcode_state"  # "IDLE" / "RUNNING" / "PAUSE" / "FINISH" / "FAILED"
MC_PERCENT = "mc_percent"
MC_REMAINING_TIME = "mc_remaining_time"  # minutes
LAYER_NUM = "layer_num"
TOTAL_LAYER_NUM = "total_layer_num"
SUBTASK_NAME = "subtask_name"
SPEED_LEVEL = "spd_lvl"  # 1..4

COOLING_FAN_SPEED = "cooling_fan_speed"  # part cooling, 0-15 -> *100/15 %
BIG_FAN1_SPEED = "big_fan1_speed"  # aux
BIG_FAN2_SPEED = "big_fan2_speed"  # chamber

LIGHTS_REPORT = "lights_report"  # list of {"node": "chamber_light", "mode": "on"/"off"}

AMS = "ams"
AMS_LIST = "ams"  # ams.ams -> list of AMS units, each with "tray": [...]
TRAY_NOW = "tray_now"
HMS = "hms"
