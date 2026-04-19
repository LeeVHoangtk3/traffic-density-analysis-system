import os


class Settings:
    def __init__(self) -> None:
        self.database_url = os.getenv("DATABASE_URL", "sqlite:///./traffic.db")
        self.api_title = os.getenv("BACKEND_API_TITLE", "Traffic AI Backend")
        self.default_page_size = int(os.getenv("DEFAULT_PAGE_SIZE", "100"))
        self.max_page_size = int(os.getenv("MAX_PAGE_SIZE", "500"))
        self.prediction_horizon_minutes = int(
            os.getenv("PREDICTION_HORIZON_MINUTES", "15")
        )


settings = Settings()
