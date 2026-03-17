"""
Scenario Service - What-If Simulation.

GenAI Technique: Scenario Simulation
- Compare two weather scenarios
- Run prediction + SHAP for both
- LLM analyzes the differences
"""

import json

import google.generativeai as genai

from app.config import settings
from app.prompts.scenario import SCENARIO_SYSTEM_PROMPT
from app.services.model_service import model_service
from app.services.explainer_service import explainer_service


class ScenarioService:
    def __init__(self):
        self._llm_configured = False
        self.llm_model = None

    def _ensure_llm_configured(self):
        if not self._llm_configured:
            genai.configure(api_key=settings.GEMINI_API_KEY)
            self.llm_model = genai.GenerativeModel(
                model_name=settings.GEMINI_MODEL,
                system_instruction=SCENARIO_SYSTEM_PROMPT,
            )
            self._llm_configured = True

    def compare_scenarios(self, scenario_a: dict, scenario_b: dict) -> dict:
        self._ensure_llm_configured()

        pred_a = model_service.predict(scenario_a)
        pred_b = model_service.predict(scenario_b)

        prompt = self._build_comparison_prompt(scenario_a, pred_a, scenario_b, pred_b)

        response = self.llm_model.generate_content(prompt)

        return {
            "scenario_a": {
                "input": scenario_a,
                "prediction": pred_a,
            },
            "scenario_b": {
                "input": scenario_b,
                "prediction": pred_b,
            },
            "differences": {
                "tempmax_diff": round(pred_b["tempmax"] - pred_a["tempmax"], 2),
                "tempmin_diff": round(pred_b["tempmin"] - pred_a["tempmin"], 2),
            },
            "llm_analysis": response.text,
        }

    def compare_scenarios_stream(self, scenario_a: dict, scenario_b: dict):
        self._ensure_llm_configured()

        pred_a = model_service.predict(scenario_a)
        pred_b = model_service.predict(scenario_b)

        predictions_data = {
            "scenario_a": {"input": scenario_a, "prediction": pred_a},
            "scenario_b": {"input": scenario_b, "prediction": pred_b},
            "differences": {
                "tempmax_diff": round(pred_b["tempmax"] - pred_a["tempmax"], 2),
                "tempmin_diff": round(pred_b["tempmin"] - pred_a["tempmin"], 2),
            },
        }

        yield json.dumps({"type": "predictions", "data": predictions_data})

        prompt = self._build_comparison_prompt(scenario_a, pred_a, scenario_b, pred_b)

        response = self.llm_model.generate_content(prompt, stream=True)
        for chunk in response:
            if chunk.text:
                yield json.dumps({"type": "text", "data": chunk.text})

    def _build_comparison_prompt(self, sc_a, pred_a, sc_b, pred_b):
        def format_scenario(sc, pred, label):
            return f"""
**{label}:**
- Humidity: {sc.get('humidity', 'N/A')}%
- Precipitation: {sc.get('precip', 'N/A')} mm
- Wind Direction: {sc.get('winddir', 'N/A')}°
- Wind Speed: {sc.get('windspeed', 'N/A')} km/h
- Precipitation Coverage: {sc.get('precipcover', 'N/A')}%
- Solar Energy: {sc.get('solarenergy', 'N/A')} MJ/m²
- Predicted TempMax: {pred.get('tempmax', 'N/A')}°C
- Predicted TempMin: {pred.get('tempmin', 'N/A')}°C"""

        changes = []
        for key in sc_a:
            if key in sc_b and sc_a[key] != sc_b[key]:
                changes.append(
                    f"- {key}: {sc_a[key]} -> {sc_b[key]} (change: {sc_b[key] - sc_a[key]:+.1f})"
                )

        return f"""
Compare these two agricultural weather scenarios and analyze the impact:

{format_scenario(sc_a, pred_a, "Scenario A (Current/Baseline)")}

{format_scenario(sc_b, pred_b, "Scenario B (Modified/What-If)")}

**Key Changes from A to B:**
{chr(10).join(changes) if changes else "No changes detected"}

**Temperature Impact:**
- TempMax change: {pred_b['tempmax'] - pred_a['tempmax']:+.2f}°C
- TempMin change: {pred_b['tempmin'] - pred_a['tempmin']:+.2f}°C

Analyze:
1. Why did these input changes cause these temperature shifts?
2. What are the agricultural implications of these changes?
3. Which scenario is better for farming, and why?
4. What specific actions should farmers take for each scenario?
"""


scenario_service = ScenarioService()
