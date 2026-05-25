"""
integration_system/direction_router.py
=======================================
Ánh xạ camera_id → pha đèn tín hiệu (phase) tương ứng tại giao lộ.
"""

# Config dict maps each camera to the physical light and the 2-phase optimizer
# phase it controls.
CAMERA_PHASE_MAP: dict[str, dict[str, str]] = {
    "CAM_01": {
        "phase": "north_green",
        "controlled_phase": "phase_1",
        "direction": "straight_right",
        "junction": "JCT_A",
    },
    "CAM_02": {
        "phase": "south_green",
        "controlled_phase": "phase_1",
        "direction": "straight_right",
        "junction": "JCT_A",
    },
    "CAM_03": {
        "phase": "east_green",
        "controlled_phase": "phase_2",
        "direction": "left",
        "junction": "JCT_A",
    },
    "CAM_04": {
        "phase": "west_green",
        "controlled_phase": "phase_1",
        "direction": "straight_right",
        "junction": "JCT_A",
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
            "controlled_phase": "phase_1",
            "direction": "unknown",
            "junction": "unknown"
        }
    return CAMERA_PHASE_MAP[camera_id].copy()

if __name__ == "__main__":
    print(get_phase("CAM_01"))
