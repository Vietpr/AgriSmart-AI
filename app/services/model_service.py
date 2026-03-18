import joblib
import numpy as np
import pandas as pd

from app.config import settings


class ModelService:
    def __init__(self):
        self.model_tempmax = None
        self.model_tempmin = None
        self.scaler = None
        self.feature_names = None
        self._loaded = False

    def load_models(self):
        if self._loaded:
            return
        self.model_tempmax = joblib.load(settings.TEMPMAX_MODEL_PATH)
        self.model_tempmin = joblib.load(settings.TEMPMIN_MODEL_PATH)
        self.scaler = joblib.load(settings.SCALER_PATH)
        self.feature_names = joblib.load(settings.FEATURE_NAMES_PATH)
        self._loaded = True

    def predict(self, features: dict) -> dict:
        self.load_models()

        input_df = pd.DataFrame([features], columns=settings.FEATURE_COLUMNS)
        scaled_input = self.scaler.transform(input_df)
        scaled_df = pd.DataFrame(scaled_input, columns=settings.FEATURE_COLUMNS)

        tempmax_features = [c for c in settings.FEATURE_COLUMNS if c != "tempmax"]
        tempmin_features = [c for c in settings.FEATURE_COLUMNS if c != "tempmin"]

        tempmax_pred_scaled = self.model_tempmax.predict(scaled_df[tempmax_features])[0]
        tempmin_pred_scaled = self.model_tempmin.predict(scaled_df[tempmin_features])[0]

        tempmax_idx = settings.FEATURE_COLUMNS.index("tempmax")
        tempmin_idx = settings.FEATURE_COLUMNS.index("tempmin")

        dummy = np.zeros((1, len(settings.FEATURE_COLUMNS)))
        dummy[0, tempmax_idx] = tempmax_pred_scaled
        original_tempmax = self.scaler.inverse_transform(dummy)[0][tempmax_idx]

        dummy = np.zeros((1, len(settings.FEATURE_COLUMNS)))
        dummy[0, tempmin_idx] = tempmin_pred_scaled
        original_tempmin = self.scaler.inverse_transform(dummy)[0][tempmin_idx]

        return {
            "tempmax": round(float(original_tempmax), 2),
            "tempmin": round(float(original_tempmin), 2),
            "input_features": features,
        }


model_service = ModelService()
