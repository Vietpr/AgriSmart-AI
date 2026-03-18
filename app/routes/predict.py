import json
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from sse_starlette.sse import EventSourceResponse
from app.services.model_service import model_service
from app.services.llm_service import llm_service

router = APIRouter()


class PredictRequest(BaseModel):
    humidity: float
    precip: float
    tempmax: float
    tempmin: float
    winddir: float
    windspeed: float
    precipcover: float
    solarenergy: float


@router.post("/predict")
async def predict(request: PredictRequest):
    try:
        features = request.model_dump()
        prediction = model_service.predict(features)
        advisory = llm_service.generate_advisory(prediction, features)

        return {
            "success": True,
            "prediction": prediction,
            "advisory": advisory,
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/predict/stream")
async def predict_stream(request: PredictRequest):
    try:
        features = request.model_dump()
        prediction = model_service.predict(features)

        async def event_generator():
            yield {
                "event": "prediction",
                "data": json.dumps(prediction),
            }

            for chunk in llm_service.generate_advisory_stream(prediction, features):
                yield {
                    "event": "advisory",
                    "data": json.dumps({"text": chunk}),
                }

            yield {
                "event": "done",
                "data": json.dumps({"status": "complete"}),
            }

        return EventSourceResponse(event_generator())
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
