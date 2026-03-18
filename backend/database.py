from sqlalchemy import create_engine, inspect, text
from sqlalchemy.orm import sessionmaker, declarative_base

DATABASE_URL = "sqlite:///./traffic.db"

engine = create_engine(
    DATABASE_URL,
    connect_args={"check_same_thread": False}
)

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
        "track_id": "TEXT",
        "density": "TEXT",
        "event_type": "TEXT",
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
