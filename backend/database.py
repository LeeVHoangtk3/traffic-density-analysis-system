from sqlalchemy import create_engine, inspect, text
from sqlalchemy.orm import declarative_base, sessionmaker

from backend.config import settings

engine_kwargs = {}
if settings.database_url.startswith("sqlite"):
    engine_kwargs["connect_args"] = {"check_same_thread": False}

engine = create_engine(settings.database_url, **engine_kwargs)

SessionLocal = sessionmaker(
    autocommit=False,
    autoflush=False,
    bind=engine
)

Base = declarative_base()


def sync_vehicle_detection_schema():
    inspector = inspect(engine)

    if "vehicle_detections" not in inspector.get_table_names():
        return

    existing_columns = {
        column["name"]
        for column in inspector.get_columns("vehicle_detections")
    }

    required_columns = {
        "event_id": "TEXT",
        "camera_id": "TEXT",
        "track_id": "TEXT",
        "vehicle_type": "TEXT",
        "density": "TEXT",
        "event_type": "TEXT",
        "confidence": "FLOAT",
        "timestamp": "DATETIME",
    }

    with engine.begin() as connection:
        for column_name, column_type in required_columns.items():
            if column_name in existing_columns:
                continue

            connection.execute(
                text(
                    f"ALTER TABLE vehicle_detections "
                    f"ADD COLUMN {column_name} {column_type}"
                )
            )

    camera_columns = {
        "camera_id": "TEXT",
    }

    if "cameras" in inspector.get_table_names():
        existing_camera_columns = {
            column["name"]
            for column in inspector.get_columns("cameras")
        }
        with engine.begin() as connection:
            for column_name, column_type in camera_columns.items():
                if column_name in existing_camera_columns:
                    continue
                connection.execute(
                    text(
                        f"ALTER TABLE cameras "
                        f"ADD COLUMN {column_name} {column_type}"
                    )
                )

    prediction_columns = {
        "camera_id": "TEXT",
        "horizon_minutes": "INTEGER DEFAULT 15",
        "source": "TEXT DEFAULT 'fallback'",
        "suggested_delta": "FLOAT",
    }

    if "traffic_predictions" in inspector.get_table_names():
        existing_prediction_columns = {
            column["name"]
            for column in inspector.get_columns("traffic_predictions")
        }
        with engine.begin() as connection:
            for column_name, column_type in prediction_columns.items():
                if column_name in existing_prediction_columns:
                    continue
                connection.execute(
                    text(
                        f"ALTER TABLE traffic_predictions "
                        f"ADD COLUMN {column_name} {column_type}"
                    )
                )
