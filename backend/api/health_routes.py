from datetime import datetime

from fastapi import APIRouter, Depends

from backend.mongo_database import ping_mongo
from backend.services.db_service import get_db

router = APIRouter(tags=["health"])


@router.get("/health")
def health_check(db=Depends(get_db)):
    db_status = "ok"
    try:
        ping_mongo()
    except Exception:
        db_status = "error"

    return {
        "status": "ok",
        "database": db_status,
        "timestamp": datetime.utcnow(),
    }
