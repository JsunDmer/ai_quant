from fastapi import FastAPI

from api.routes.health import router as health_router
from api.routes.jobs import router as jobs_router
from api.routes.market import router as market_router


def create_app() -> FastAPI:
    app = FastAPI(title="Stock MVP API")
    app.include_router(health_router)
    app.include_router(jobs_router)
    app.include_router(market_router)
    return app

