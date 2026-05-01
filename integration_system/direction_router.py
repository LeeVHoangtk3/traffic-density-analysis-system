"""
integration_system/direction_router.py
=======================================
Ánh xạ camera_id → pha đèn tín hiệu (phase) tương ứng tại giao lộ.

Mục đích
--------
Khi hệ thống có nhiều camera theo dõi các hướng khác nhau tại cùng một giao
lộ, module này xác định pha đèn nào cần áp dụng green_time được tính từ
DeltaApplier — tránh nhầm lẫn giữa các hướng North/South/East/West.

Cấu trúc dict
-------------
CAMERA_PHASE_MAP: Dict[str, Dict[str, str]]
    {
        "<camera_id>": {
            "phase"     : "<tên_pha_đèn>",   # ví dụ: "north_green"
            "direction" : "<hướng_luồng>",   # "inbound" | "outbound"
            "junction"  : "<giao_lộ>",        # tên/ID giao lộ (tuỳ chọn)
        }
    }

API công khai
-------------
get_phase(camera_id)           → dict  (thông tin pha đầy đủ)
get_phase_name(camera_id)      → str   (chỉ tên pha, e.g. "north_green")
get_direction(camera_id)       → str   (chỉ hướng, e.g. "inbound")
list_cameras()                 → list  (tất cả camera_id được cấu hình)
"""

from __future__ import annotations

# ---------------------------------------------------------------------------
# Bảng cấu hình — chỉnh theo sơ đồ vật lý của từng dự án
# ---------------------------------------------------------------------------

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

# ---------------------------------------------------------------------------
# API
# ---------------------------------------------------------------------------


def get_phase(camera_id: str) -> dict[str, str]:
    """
    Trả về dict thông tin pha đầy đủ cho camera_id.

    Tham số
    -------
    camera_id : str
        ID camera (ví dụ: "CAM_01").

    Trả về
    ------
    dict
        {"phase": ..., "direction": ..., "junction": ...}

    Raises
    ------
    KeyError
        Nếu camera_id chưa được cấu hình trong CAMERA_PHASE_MAP.
    """
    if camera_id not in CAMERA_PHASE_MAP:
        raise KeyError(
            f"[DirectionRouter] Camera '{camera_id}' chưa được cấu hình. "
            f"Camera hợp lệ: {list(CAMERA_PHASE_MAP.keys())}"
        )
    return CAMERA_PHASE_MAP[camera_id].copy()


def get_phase_name(camera_id: str) -> str:
    """
    Trả về tên pha đèn (str) của camera_id.

    Ví dụ: get_phase_name("CAM_01") → "north_green"
    """
    return get_phase(camera_id)["phase"]


def get_direction(camera_id: str) -> str:
    """
    Trả về hướng luồng xe của camera_id ("inbound" hoặc "outbound").

    Ví dụ: get_direction("CAM_01") → "inbound"
    """
    return get_phase(camera_id)["direction"]


def list_cameras() -> list[str]:
    """Trả về danh sách tất cả camera_id đã được cấu hình."""
    return list(CAMERA_PHASE_MAP.keys())


def register_camera(
    camera_id: str,
    phase: str,
    direction: str = "inbound",
    junction: str = "JCT_DEFAULT",
) -> None:
    """
    Đăng ký (hoặc cập nhật) cấu hình pha cho camera mới tại runtime.

    Tham số
    -------
    camera_id : str   ID camera mới
    phase     : str   Tên pha đèn (ví dụ: "north_green")
    direction : str   "inbound" | "outbound"  (mặc định "inbound")
    junction  : str   ID hoặc tên giao lộ     (mặc định "JCT_DEFAULT")
    """
    CAMERA_PHASE_MAP[camera_id] = {
        "phase":     phase,
        "direction": direction,
        "junction":  junction,
    }
    print(
        f"[DirectionRouter] Registered: {camera_id} -> "
        f"phase='{phase}', direction='{direction}', junction='{junction}'"
    )


# ---------------------------------------------------------------------------
# Chạy thử nhanh: python -m integration_system.direction_router
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    print("=" * 50)
    print("  DirectionRouter — Demo")
    print("=" * 50)

    for cam in list_cameras():
        info = get_phase(cam)
        print(
            f"  {cam}: phase='{info['phase']}' | "
            f"direction='{info['direction']}' | "
            f"junction='{info['junction']}'"
        )

    print()
    # Thêm camera mới tại runtime
    register_camera("CAM_05", phase="north_green", direction="outbound", junction="JCT_B")
    print(f"  get_phase_name('CAM_05') = {get_phase_name('CAM_05')}")
    print(f"  get_direction('CAM_05')  = {get_direction('CAM_05')}")
    print("=" * 50)
