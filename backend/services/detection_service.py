from backend.schemas.detection_schema import DetectionCreate


def normalize_document(document):
    if not document:
        return None
    document["id"] = str(document["_id"])
    document["_id"] = str(document["_id"])
    return document


def get_detection_by_event_id(db, event_id: str):
    return normalize_document(
        db.vehicle_detections.find_one({"event_id": event_id})
    )


def create_detection(db, data: DetectionCreate):
    document = {
        "event_id": data.event_id,
        "camera_id": data.camera_id,
        "track_id": str(data.track_id),
        "vehicle_type": data.vehicle_type.value,
        "density": data.density.value if data.density else None,
        "direction": data.direction or "inbound",
        "event_type": data.event_type.value,
        "confidence": data.confidence,
        "timestamp": data.timestamp,
    }
    result = db.vehicle_detections.insert_one(document)
    document["_id"] = result.inserted_id
    return normalize_document(document)
