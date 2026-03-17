import json
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from sse_starlette.sse import EventSourceResponse

from app.services.model_service import model_service
from app.services.explainer_service import explainer_service

router = APIRouter()


class ExplainRequest(BaseModel):
    humidity: float
    precip: float
    tempmax: float
    tempmin: float
    winddir: float
    windspeed: float
    precipcover: float
    solarenergy: float


@router.post("/explain")
async def explain(request: ExplainRequest):
    try:
        features = request.model_dump()
        prediction = model_service.predict(features)
        explanation = explainer_service.explain(features, prediction)

        return {
            "success": True,
            **explanation,
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/explain/stream")
async def explain_stream(request: ExplainRequest):
    try:
        features = request.model_dump()
        prediction = model_service.predict(features)

        async def event_generator():
            yield {
                "event": "prediction",
                "data": json.dumps(prediction),
            }

            for chunk in explainer_service.explain_stream(features, prediction):
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
