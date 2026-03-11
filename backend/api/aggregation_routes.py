from fastapi import APIRouter
from backend.services.aggregation_service import compute_congestion

router = APIRouter()

@router.get("/aggregation")
def get_aggregation(vehicle_count: int):

    level = compute_congestion(vehicle_count)

    return {
        "vehicle_count": vehicle_count,
        "congestion_level": level
    }