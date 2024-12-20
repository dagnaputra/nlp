from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from sentence_transformers import SentenceTransformer
import uvicorn
import torch
from typing import List, Optional
from contextlib import asynccontextmanager

# Define startup event to properly initialize GPU model
@asynccontextmanager
async def lifespan(app: FastAPI):
    # Load model on GPU during startup
    app.state.device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    app.state.model = SentenceTransformer('all-MiniLM-L6-v2')
    app.state.model.to(app.state.device)
    print(f"Model loaded on device: {app.state.device}")
    yield
    # Clean up GPU memory on shutdown
    if torch.cuda.is_available():
        torch.cuda.empty_cache()

app = FastAPI(lifespan=lifespan)

class EmbeddingRequest(BaseModel):
    texts: List[str]
    batch_size: Optional[int] = 32

class EmbeddingResponse(BaseModel):
    embeddings: List[List[float]]
    device: str

@app.post("/embed", response_model=EmbeddingResponse)
async def get_embeddings(request: EmbeddingRequest):
    try:
        # Process in batches for memory efficiency
        embeddings = []
        for i in range(0, len(request.texts), request.batch_size):
            batch = request.texts[i:i + request.batch_size]
            with torch.no_grad():  # Disable gradient computation for inference
                batch_embeddings = app.state.model.encode(
                    batch,
                    convert_to_tensor=True,
                    device=app.state.device
                )
                # Move to CPU and convert to list
                embeddings.extend(batch_embeddings.cpu().numpy().tolist())
        
        return EmbeddingResponse(
            embeddings=embeddings,
            device=str(app.state.device)
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/health")
async def health_check():
    return {
        "status": "healthy",
        "device": str(app.state.device),
        "cuda_available": torch.cuda.is_available(),
        "cuda_device_count": torch.cuda.device_count() if torch.cuda.is_available() else 0
    }

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8002)