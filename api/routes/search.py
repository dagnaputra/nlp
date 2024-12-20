from fastapi import APIRouter, HTTPException, Query, Header
from api.core.opensearch import opensearch_client, extract_dsl_query
from api.models.response import SearchResponse
from uuid import uuid4
from typing import Optional, Union
#from api.core.logging import Logger

router = APIRouter()

@router.get("/search", response_model=SearchResponse)
async def search(
    collection_name: str = "engine01-000001",
    query: str = Query(..., description="The search query"),
    request_id: Optional[str] = Header(None, alias="X-Request-ID", description="Unique request ID for tracing")
):
    if not request_id:
        request_id = str(uuid4())

    logger = Logger(request_id=request_id)
    try:
        logger.info(f"Converting {query} to query ...")
        query = await extract_dsl_query(user_query=query, request_id=request_id)
        logger.debug(f"generated query: {query}")
        logger.info(f"Querying from collection {collection_name} ....")
        response = opensearch_client.search(
            index=collection_name,
            body=query
        )
        
        aggregations = response.get('aggregations', {})
        hits = response["hits"]["hits"]
        
        if hits:
            logger.info(f"Found {len(hits)} records.")
            logger.info(f"hit: {hits[0]}")
            results = [{"id": hit["_id"], "event_original": hit["_source"]["event"]["original"]} for hit in hits]
        else:
            results = []
        
        aggregation_results = {}
        if aggregations:
            agg_data = list(aggregations.values())[0]
            for agg_name, agg_data in aggregations.items():
                aggregation_results[agg_name] = agg_data.get("buckets", [])
        
        return SearchResponse(request_id=request_id, results=results, aggregations=aggregation_results)
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error during search: {str(e)}")
