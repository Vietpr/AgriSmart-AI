"""
Explainer Service - SHAP + LLM for Explainable AI.

GenAI Technique: Explainable AI
- Compute SHAP feature importance for a prediction
- Feed SHAP values to Gemini for natural language explanation
"""

import json

import joblib
import numpy as np
import pandas as pd
import shap

import google.generativeai as genai

from app.config import settings
from app.prompts.explainer import EXPLAINER_SYSTEM_PROMPT
from app.services.model_service import model_service


class ExplainerService:
    def __init__(self):
        self.explainer_tempmax = None
        self.explainer_tempmin = None
        self._loaded = False
        self._llm_configured = False
        self.llm_model = None

    def _ensure_models_loaded(self):
        if self._loaded:
            return
        model_service.load_models()
        self.explainer_tempmax = shap.TreeExplainer(model_service.model_tempmax)
        self.explainer_tempmin = shap.TreeExplainer(model_service.model_tempmin)
        self._loaded = True

    def _ensure_llm_configured(self):
        if not self._llm_configured:
            genai.configure(api_key=settings.GEMINI_API_KEY)
            self.llm_model = genai.GenerativeModel(
                model_name=settings.GEMINI_MODEL,
                system_instruction=EXPLAINER_SYSTEM_PROMPT,
            )
            self._llm_configured = True

    def explain(self, features: dict, prediction: dict) -> dict:
        self._ensure_models_loaded()
        self._ensure_llm_configured()

        input_df = pd.DataFrame([features], columns=settings.FEATURE_COLUMNS)
        scaled_input = model_service.scaler.transform(input_df)
        scaled_df = pd.DataFrame(scaled_input, columns=settings.FEATURE_COLUMNS)

        tempmax_features = [c for c in settings.FEATURE_COLUMNS if c != "tempmax"]
        tempmin_features = [c for c in settings.FEATURE_COLUMNS if c != "tempmin"]

        shap_tempmax = self.explainer_tempmax.shap_values(scaled_df[tempmax_features])
        shap_tempmin = self.explainer_tempmin.shap_values(scaled_df[tempmin_features])

        tempmax_contributions = {
            feature: round(float(value), 6)
            for feature, value in zip(tempmax_features, shap_tempmax[0])
        }
        tempmin_contributions = {
            feature: round(float(value), 6)
            for feature, value in zip(tempmin_features, shap_tempmin[0])
        }

        prompt = self._build_explanation_prompt(
            features, prediction, tempmax_contributions, tempmin_contributions
        )

        response = self.llm_model.generate_content(prompt)

        return {
            "prediction": prediction,
            "shap_analysis": {
                "tempmax_contributions": tempmax_contributions,
                "tempmin_contributions": tempmin_contributions,
            },
            "llm_explanation": response.text,
        }

    def explain_stream(self, features: dict, prediction: dict):
        self._ensure_models_loaded()
        self._ensure_llm_configured()

        input_df = pd.DataFrame([features], columns=settings.FEATURE_COLUMNS)
        scaled_input = model_service.scaler.transform(input_df)
        scaled_df = pd.DataFrame(scaled_input, columns=settings.FEATURE_COLUMNS)

        tempmax_features = [c for c in settings.FEATURE_COLUMNS if c != "tempmax"]
        tempmin_features = [c for c in settings.FEATURE_COLUMNS if c != "tempmin"]

        shap_tempmax = self.explainer_tempmax.shap_values(scaled_df[tempmax_features])
        shap_tempmin = self.explainer_tempmin.shap_values(scaled_df[tempmin_features])

        tempmax_contributions = {
            feature: round(float(value), 6)
            for feature, value in zip(tempmax_features, shap_tempmax[0])
        }
        tempmin_contributions = {
            feature: round(float(value), 6)
            for feature, value in zip(tempmin_features, shap_tempmin[0])
        }

        shap_data = {
            "tempmax_contributions": tempmax_contributions,
            "tempmin_contributions": tempmin_contributions,
        }

        yield json.dumps({"type": "shap", "data": shap_data})

        prompt = self._build_explanation_prompt(
            features, prediction, tempmax_contributions, tempmin_contributions
        )

        response = self.llm_model.generate_content(prompt, stream=True)
        for chunk in response:
            if chunk.text:
                yield json.dumps({"type": "text", "data": chunk.text})

    def _build_explanation_prompt(
        self, features, prediction, tempmax_contributions, tempmin_contributions
    ):
        sorted_tempmax = sorted(
            tempmax_contributions.items(), key=lambda x: abs(x[1]), reverse=True
        )
        sorted_tempmin = sorted(
            tempmin_contributions.items(), key=lambda x: abs(x[1]), reverse=True
        )

        return f"""
Giải thích dự đoán nhiệt độ sau đây dựa trên đóng góp SHAP của từng đặc trưng:

**Điều kiện thời tiết đầu vào:**
- Độ ẩm: {features.get('humidity', 'N/A')}%
- Lượng mưa: {features.get('precip', 'N/A')} mm
- Hướng gió: {features.get('winddir', 'N/A')}°
- Tốc độ gió: {features.get('windspeed', 'N/A')} km/h
- Độ phủ mưa: {features.get('precipcover', 'N/A')}%
- Năng lượng mặt trời: {features.get('solarenergy', 'N/A')} MJ/m²

**Nhiệt độ dự đoán:**
- Tối đa: {prediction.get('tempmax', 'N/A')}°C
- Tối thiểu: {prediction.get('tempmin', 'N/A')}°C

**Đóng góp SHAP cho TempMax (sắp xếp theo mức độ quan trọng):**
{chr(10).join(f'- {f}: {v:+.6f}' for f, v in sorted_tempmax)}

**Đóng góp SHAP cho TempMin (sắp xếp theo mức độ quan trọng):**
{chr(10).join(f'- {f}: {v:+.6f}' for f, v in sorted_tempmin)}

Hãy giải thích rõ ràng bằng ngôn ngữ tự nhiên TẠI SAO mô hình đưa ra các dự đoán này.
Tập trung vào đặc trưng nào có tác động lớn nhất và theo hướng nào.
Giải thích trong bối cảnh nông nghiệp mà nông dân có thể hiểu được.
Trả lời bằng tiếng Việt.
"""


explainer_service = ExplainerService()
