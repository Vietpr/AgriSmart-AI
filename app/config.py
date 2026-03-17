import os
from dotenv import load_dotenv

load_dotenv()


class Settings:
    GEMINI_API_KEY: str = os.getenv("GEMINI_API_KEY", "")
    MLFLOW_TRACKING_URI: str = os.getenv("MLFLOW_TRACKING_URI", "./mlruns")
    HOST: str = os.getenv("HOST", "0.0.0.0")
    PORT: int = int(os.getenv("PORT", "8004"))

    MODEL_DIR: str = os.path.join(os.path.dirname(os.path.dirname(__file__)), "models")
    DATA_DIR: str = os.path.join(os.path.dirname(os.path.dirname(__file__)), "data")
    FRONTEND_DIR: str = os.path.join(
        os.path.dirname(os.path.dirname(__file__)), "frontend"
    )

    TEMPMAX_MODEL_PATH: str = os.path.join(MODEL_DIR, "xgboost_tempmax.pkl")
    TEMPMIN_MODEL_PATH: str = os.path.join(MODEL_DIR, "xgboost_tempmin.pkl")
    SCALER_PATH: str = os.path.join(MODEL_DIR, "scaler.pkl")
    FEATURE_NAMES_PATH: str = os.path.join(MODEL_DIR, "feature_names.pkl")

    FEATURE_COLUMNS: list = [
        "humidity",
        "precip",
        "tempmax",
        "tempmin",
        "winddir",
        "windspeed",
        "precipcover",
        "solarenergy",
    ]

    GEMINI_MODEL: str = "gemini-2.5-flash"


settings = Settings()
