from fastapi import FastAPI

from api.routes.health import router as health_router
from api.routes.jobs import router as jobs_router
from api.routes.market import router as market_router
from api.routes.sectors import router as sectors_router
from api.routes.signals import router as signals_router
from api.routes.evaluation import router as evaluation_router


def create_app() -> FastAPI:
    app = FastAPI(title="Stock MVP API")
    app.include_router(health_router)
    app.include_router(jobs_router)
    app.include_router(market_router)
    app.include_router(sectors_router)
    app.include_router(signals_router)
    app.include_router(evaluation_router)
    return app

