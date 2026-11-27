from contextlib import asynccontextmanager
from fastapi import FastAPI

from src.api.routes import router as migration_router
from src.config import get_logger

logger = get_logger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("Stored Procedure Migration service starting up")
    yield
    logger.info("Stored Procedure Migration service shutting down")


app = FastAPI(
    title="Stored Procedure Migration",
    version="0.1.0",
    description=(
        "MSSQL/MySQL stored procedure migration to PostgreSQL. "
        "The migration endpoint currently reports when conversion stages "
        "are unavailable."
    ),
    lifespan=lifespan,
)


app.include_router(migration_router)

@app.get("/health_check")
def health_check():
    return {"message": "Stored Procedure Migration service is running"}


