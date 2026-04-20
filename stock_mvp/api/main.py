from fastapi import FastAPI

from stock_mvp.api.routes.evaluation import router as evaluation_router
from stock_mvp.api.routes.health import router as health_router
from stock_mvp.api.routes.jobs import router as jobs_router
from stock_mvp.api.routes.market import router as market_router
from stock_mvp.api.routes.sectors import router as sectors_router
from stock_mvp.api.routes.signals import router as signals_router


def create_app() -> FastAPI:
    app = FastAPI(title="Stock MVP API")
    app.include_router(health_router)
    app.include_router(jobs_router)
    app.include_router(market_router)
    app.include_router(sectors_router)
    app.include_router(signals_router)
    app.include_router(evaluation_router)
    return app


app = create_app()

