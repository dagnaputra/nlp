from pydantic_settings import BaseSettings
from dotenv import load_dotenv
#from loguru import logger
from api.core.prompts import NLP_TO_DSL_PROMPT

load_dotenv()

ENV_ERR_MSG = """
    "Error missing ENVIRONMENT variable. "
    "Please update your .env file. "
"""

class Settings(BaseSettings):
    OPENSEARCH_URL: str = "https://elastics.metanotech.id"
    OPENSEARCH_USERNAME: str = "admin"
    OPENSEARCH_PASSWORD: str = "O3HWIt2onHi5fHHaeI11j3w437PPzURr"
    LLM_SERVICE_URL: str = "test"
    LLM_API_KEY: str = "test"
    EMBEDDING_SERVICE_URL: str = "http://localhost:8002"
    VECTOR_DB_TYPE: str = "qdrant" 
    VECTOR_DB_URL: str = "https://d28baf5b-41c3-4b16-b8b8-d72feef39e63.us-east4-0.gcp.cloud.qdrant.io:6333"
    VECTOR_DB_API_KEY: str = "EfKosYjvpOmIQRyhUh2n8Ksn4i4UX7X8DMUl0GifCusdhK0gVJ1Esg"
    LLM_MODEL: str = "qwen14b"  # Default model, can be changed

    class Config:
        env_file = ".env"

try:
    settings = Settings()
except Exception:
    message = ENV_ERR_MSG
    logger.error(message)
    raise Exception(message)
