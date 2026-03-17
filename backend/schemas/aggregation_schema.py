from pydantic import BaseModel

class AggregationResponse(BaseModel):

    vehicle_count: int
    congestion_level: str