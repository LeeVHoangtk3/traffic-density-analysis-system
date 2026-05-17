@router.get("/predict-next", response_model=PredictionResponse)
def predict_next(camera_id: str | None = None, db=Depends(get_db)):
    prediction = predict_next_density(db=db, camera_id=camera_id)

    return PredictionResponse(
        camera_id=prediction.camera_id,
        predicted_density=prediction.predicted_density,
        predicted_congestion_level=prediction.predicted_congestion_level,
        horizon_minutes=prediction.horizon_minutes,
        source=prediction.source,
        timestamp=prediction.timestamp,
        avg_density=prediction.avg_density,  # 👈 NEW
        time_green_light=None  # 👈 chưa có
    )