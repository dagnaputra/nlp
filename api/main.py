from fastapi import FastAPI
from api.routes import search, enrich
from typing import Dict

app = FastAPI(title="NLP Search Service")

app.include_router(search.router)
app.include_router(enrich.router)

@app.get("/")
async def root():
    return {"message": "Welcome to the NLP Search Service"}

@app.get(
    "/health",
    summary="Health Check",
    response_description="Service health status",
)
def health_check() -> Dict[str, str]:
    """
    Health check endpoint to verify the service is running.

    Args:
    - None

    Returns:
    - JSON response containing the health status of the service
    """
    return {"status": "healthy"}