"""
LLM Service - Gemini API integration for agricultural advisory.

GenAI Techniques:
- LLM Reasoning: Analyze predictions + weather context
- Structured Output: JSON with risk_level, recommendations, suitable_crops, warnings
- Streaming: SSE via generate_content(stream=True)
"""

import json

import google.generativeai as genai

from app.config import settings
from app.prompts.advisor import ADVISOR_SYSTEM_PROMPT


class LLMService:
    def __init__(self):
        self._configured = False
        self.model = None

    def _ensure_configured(self):
        if not self._configured:
            genai.configure(api_key=settings.GEMINI_API_KEY)
            self.model = genai.GenerativeModel(
                model_name=settings.GEMINI_MODEL,
                system_instruction=ADVISOR_SYSTEM_PROMPT,
            )
            self._configured = True

    def generate_advisory(self, prediction: dict, features: dict) -> dict:
        self._ensure_configured()

        prompt = self._build_advisory_prompt(prediction, features)

        response = self.model.generate_content(prompt)
        text = response.text

        try:
            cleaned = text.strip()
            if cleaned.startswith("```json"):
                cleaned = cleaned[7:]
            if cleaned.startswith("```"):
                cleaned = cleaned[3:]
            if cleaned.endswith("```"):
                cleaned = cleaned[:-3]

            result = json.loads(cleaned.strip())
            return result
        except (json.JSONDecodeError, Exception):
            return {
                "risk_level": "unknown",
                "analysis": text,
                "recommendations": [],
                "suitable_crops": [],
                "warnings": [],
            }

    def generate_advisory_stream(self, prediction: dict, features: dict):
        self._ensure_configured()

        prompt = self._build_advisory_prompt(prediction, features)

        response = self.model.generate_content(prompt, stream=True)

        for chunk in response:
            if chunk.text:
                yield chunk.text

    def _build_advisory_prompt(self, prediction: dict, features: dict) -> str:
        return f"""
Phân tích dự đoán thời tiết nông nghiệp sau và đưa ra tư vấn:

**Điều kiện thời tiết đầu vào:**
- Độ ẩm: {features.get('humidity', 'N/A')}%
- Lượng mưa: {features.get('precip', 'N/A')} mm
- Hướng gió: {features.get('winddir', 'N/A')}°
- Tốc độ gió: {features.get('windspeed', 'N/A')} km/h
- Độ phủ mưa: {features.get('precipcover', 'N/A')}%
- Năng lượng mặt trời: {features.get('solarenergy', 'N/A')} MJ/m²

**Nhiệt độ dự đoán:**
- Nhiệt độ tối đa: {prediction.get('tempmax', 'N/A')}°C
- Nhiệt độ tối thiểu: {prediction.get('tempmin', 'N/A')}°C

Dựa trên các điều kiện này, hãy phân tích và trả về JSON với cấu trúc sau:
{{
  "risk_level": "low|medium|high|critical",
  "analysis": "phân tích chi tiết về điều kiện thời tiết và tác động nông nghiệp",
  "recommendations": ["khuyến nghị 1", "khuyến nghị 2", ...],
  "suitable_crops": ["cây trồng 1", "cây trồng 2", ...],
  "warnings": ["cảnh báo 1", "cảnh báo 2", ...]
}}

Chỉ trả về JSON, không thêm text khác. Trả lời bằng tiếng Việt.
"""


llm_service = LLMService()
