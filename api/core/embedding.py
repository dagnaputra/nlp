import httpx
from api.core.config import settings
from typing import List

async def get_embedding(text: str) -> List[float]:
    async with httpx.AsyncClient() as client:
        response = await client.post(
            f"{settings.EMBEDDING_SERVICE_URL}/embed",
            json={"texts": [text]}
        )
        response.raise_for_status()
        return response.json()["embeddings"]