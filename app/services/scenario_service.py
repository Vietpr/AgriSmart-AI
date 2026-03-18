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
            try:
                if chunk.text:
                    yield json.dumps({"type": "text", "data": chunk.text})
            except ValueError:
                pass

    def _build_comparison_prompt(self, sc_a, pred_a, sc_b, pred_b):
        def format_scenario(sc, pred, label):
            return f"""
**{label}:**
- Current Humidity (Today): {sc.get('humidity', 'N/A')}%
- Current Precipitation (Today): {sc.get('precip', 'N/A')} mm
- Current Max Temp (Today): {sc.get('tempmax', 'N/A')}°C
- Current Min Temp (Today): {sc.get('tempmin', 'N/A')}°C
- Current Wind Direction (Today): {sc.get('winddir', 'N/A')}°
- Current Wind Speed (Today): {sc.get('windspeed', 'N/A')} km/h
- Current Precip Coverage (Today): {sc.get('precipcover', 'N/A')}%
- Current Solar Energy (Today): {sc.get('solarenergy', 'N/A')} MJ/m²
- TOMORROW'S Predicted TempMax: {pred.get('tempmax', 'N/A')}°C
- TOMORROW'S Predicted TempMin: {pred.get('tempmin', 'N/A')}°C"""

        changes = []
        for key in sc_a:
            if key in sc_b and sc_a[key] != sc_b[key]:
                changes.append(
                    f"- {key}: {sc_a[key]} -> {sc_b[key]} (change: {sc_b[key] - sc_a[key]:+.1f})"
                )

        return f"""
Compare these two agricultural weather scenarios and analyze the impact of current conditions on tomorrow's temperatures:

{format_scenario(sc_a, pred_a, "Scenario A (Baseline)")}

{format_scenario(sc_b, pred_b, "Scenario B (Modified Today)")}

**Key Changes in Today's Weather from A to B:**
{chr(10).join(changes) if changes else "No changes detected"}

**Impact on TOMORROW'S Temperature:**
- TempMax change: {pred_b['tempmax'] - pred_a['tempmax']:+.2f}°C
- TempMin change: {pred_b['tempmin'] - pred_a['tempmin']:+.2f}°C

Analyze:
1. Why did these changes in today's weather cause these future temperature shifts?
2. What are the overall agricultural implications of these scenarios looking towards tomorrow?
3. Which scenario leads to a more favorable condition for farming tomorrow, and why?
4. What specific actions should farmers take today in response to each scenario to prepare for tomorrow?
"""


scenario_service = ScenarioService()
