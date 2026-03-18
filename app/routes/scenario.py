import json
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from sse_starlette.sse import EventSourceResponse
from app.services.scenario_service import scenario_service

router = APIRouter()


class ScenarioInput(BaseModel):
    humidity: float
    precip: float
    tempmax: float
    tempmin: float
    winddir: float
    windspeed: float
    precipcover: float
    solarenergy: float


class ScenarioRequest(BaseModel):
    scenario_a: ScenarioInput
    scenario_b: ScenarioInput


@router.post("/scenario")
async def compare_scenarios(request: ScenarioRequest):
    try:
        sc_a = request.scenario_a.model_dump()
        sc_b = request.scenario_b.model_dump()
        result = scenario_service.compare_scenarios(sc_a, sc_b)
        return {"success": True, **result}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/scenario/stream")
async def compare_scenarios_stream(request: ScenarioRequest):
    try:
        sc_a = request.scenario_a.model_dump()
        sc_b = request.scenario_b.model_dump()

        async def event_generator():
            for chunk in scenario_service.compare_scenarios_stream(sc_a, sc_b):
                parsed = json.loads(chunk)
                yield {
                    "event": parsed["type"],
                    "data": chunk,
                }
            yield {
                "event": "done",
                "data": json.dumps({"status": "complete"}),
            }

        return EventSourceResponse(event_generator())
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
