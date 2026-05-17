"""
integration_system/direction_router.py
=======================================
Ánh xạ camera_id → pha đèn tín hiệu (phase) tương ứng tại giao lộ.
"""

# Config dict: { "CAM_01": { "phase": "north_green", "direction": "inbound" } }
CAMERA_PHASE_MAP: dict[str, dict[str, str]] = {
    "CAM_01": {
        "phase":     "north_green",
        "direction": "inbound",
        "junction":  "JCT_A",
    },
    "CAM_02": {
        "phase":     "south_green",
        "direction": "inbound",
        "junction":  "JCT_A",
    },
    "CAM_03": {
        "phase":     "east_green",
        "direction": "inbound",
        "junction":  "JCT_A",
    },
    "CAM_04": {
        "phase":     "west_green",
        "direction": "outbound",
        "junction":  "JCT_A",
    },
}

def get_phase(camera_id: str) -> dict[str, str]:
    """
    Trả về pha đèn tương ứng cho camera_id.
    """
    if camera_id not in CAMERA_PHASE_MAP:
        # Default fallback
        return {
            "phase": "unknown",
            "direction": "unknown",
            "junction": "unknown"
        }
    return CAMERA_PHASE_MAP[camera_id].copy()

if __name__ == "__main__":
    print(get_phase("CAM_01"))
