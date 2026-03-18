from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from app.config import settings
from app.routes import predict, explain, scenario

app = FastAPI(
    title="AgriSmart AI",
    description="AI-Powered Agricultural Decision Support System",
    version="1.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(predict.router, prefix="/api", tags=["Prediction"])
app.include_router(explain.router, prefix="/api", tags=["Explanation"])
app.include_router(scenario.router, prefix="/api", tags=["Scenario"])

app.mount("/", StaticFiles(directory=settings.FRONTEND_DIR, html=True), name="frontend")


@app.on_event("startup")
async def startup_event():
    from app.services.model_service import model_service

    model_service.load_models()
