import os

from dotenv import load_dotenv


# Load .env from the backend directory
load_dotenv(os.path.join(os.path.dirname(__file__), '.env'))


class Settings:
    def __init__(self) -> None:
        self.database_url = os.getenv("DATABASE_URL", "sqlite:///./traffic.db")
        self.db_url = os.getenv("DB_URL") or os.getenv("MONGODB_URI")
        self.mongodb_db = os.getenv("MONGODB_DB", "traffic_density")
        self.api_title = os.getenv("BACKEND_API_TITLE", "Traffic AI Backend")
        self.default_page_size = int(os.getenv("DEFAULT_PAGE_SIZE", "100"))
        self.max_page_size = int(os.getenv("MAX_PAGE_SIZE", "500"))
        self.prediction_horizon_minutes = int(
            os.getenv("PREDICTION_HORIZON_MINUTES", "15")
        )


settings = Settings()
