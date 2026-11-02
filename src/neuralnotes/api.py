"""HTTP API application and health endpoint."""

from fastapi import FastAPI

from neuralnotes.settings import Settings

settings = Settings()
app = FastAPI(title=settings.app_name)


@app.get("/health", tags=["health"])
async def health_check() -> dict[str, str]:
    """Report that the API process is responding."""
    return {"status": "ok"}
