from fastapi import APIRouter, HTTPException, Header
from pydantic import BaseModel
from api.core.embedding import get_embedding
from api.core.llm import generate_response
from api.core.vector_db import get_vector_db
from api.models.response import EnrichResponse
#from api.utils.logging import Logger
from uuid import uuid4
from typing import Optional
import httpx

router = APIRouter()

class EnrichRequest(BaseModel):
    query: str
    collection: str
    limit: int = 3

    class Config:
        schema_extra = {
            "example": {
                "query": "What are common web security vulnerabilities?",
                "collection": "security_docs",
                "limit": 3
            }
        }

@router.post("/enrich", response_model=EnrichResponse)
async def enrich(
    request: EnrichRequest,
    request_id: Optional[str] = Header(None, alias="X-Request-ID", description="Unique request ID for tracing")
):
    if not request_id:
        request_id = str(uuid4())

    logger = Logger(request_id=request_id)

    try:
        logger.info(f"Processing enrichment request for query: {request.query}")
        
        # Create HTTP client with proper timeout and SSL settings
        async with httpx.AsyncClient(timeout=30.0, verify=True) as client:
            # Generate embedding for query
            logger.info("Generating query embedding...")
            query_embedding =  await get_embedding(request.query)
            
            # Get vector database instance
            vector_db = get_vector_db()
            
            # Search vector database
            logger.info(f"Searching collection {request.collection}...")
            
            search_result = vector_db.search(
                collection_name=request.collection,
                query_vector=query_embedding[0],
                limit=request.limit
            )
            
            # Extract and format context
            context = "\n".join([
                hit.payload["content"] if hasattr(hit, 'payload') else hit['content'] 
                for hit in search_result
            ])
            
            # Generate prompt and get response
            logger.info("Generating enriched response...")
            prompt = f"""Query: {request.query}

Context: {context}

Based on the above context and maintaining conversation history if provided, 
please provide a detailed answer to the query. Focus on security concepts 
and defensive measures while noting any relevant risks."""

            enriched_response =  generate_response(prompt)
            
            logger.info("Successfully generated enriched response")
            return EnrichResponse(
                request_id=request_id, 
                enriched_response=enriched_response
            )

    except Exception as e:
        logger.error(f"Error during enrichment: {str(e)}")
        raise HTTPException(
            status_code=500, 
            detail=f"Error during enrichment: {str(e)}"
        )