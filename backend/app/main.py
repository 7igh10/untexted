from fastapi import FastAPI

app = FastAPI(title="Untexted API")


@app.get("/health")
async def health() -> dict[str, str]:
    """Return the current service health status."""
    return {"status": "ok"}
