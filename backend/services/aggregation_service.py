def compute_congestion(vehicle_count):

    if vehicle_count < 10:
        return "Low"

    elif vehicle_count < 30:
        return "Medium"

    elif vehicle_count < 60:
        return "High"

    else:
        return "Severe"