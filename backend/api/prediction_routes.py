from fastapi import APIRouter

router = APIRouter()

@router.get("/predict-next")
def predict_next():

    return {
        "predicted_density": 0.45
    }