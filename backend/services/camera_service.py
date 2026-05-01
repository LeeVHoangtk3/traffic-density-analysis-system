from backend.schemas.camera_schema import CameraCreate


def normalize_document(document):
    document = dict(document)
    document["id"] = str(document.pop("_id"))
    return document


def list_cameras(db):
    return [
        normalize_document(document)
        for document in db.cameras.find({}).sort("camera_id", 1)
    ]


def create_camera(db, data: CameraCreate):
    document = {
        "camera_id": data.camera_id,
        "name": data.name,
        "location": data.location,
        "baseline_green": data.baseline_green,
        "monitored_direction": data.monitored_direction,
    }
    result = db.cameras.insert_one(document)
    document["_id"] = result.inserted_id
    return normalize_document(document)
