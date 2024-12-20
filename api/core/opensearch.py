from opensearchpy import OpenSearch
from api.core.config import settings
import json

from langchain_openai import ChatOpenAI
# from api.core.logging import Logger

from langchain_core.prompts import ChatPromptTemplate


def get_opensearch_client():
    return OpenSearch(
        settings.OPENSEARCH_URL,
        http_auth=(settings.OPENSEARCH_USERNAME,settings.OPENSEARCH_PASSWORD),
        use_ssl=True,
        verify_certs=False,
        ssl_show_warn=False,
    )

opensearch_client = get_opensearch_client()

def convert_response_to_json(response_str):

    clean_str = response_str.replace("```json", "").replace("```", "").strip()
    json_obj = json.loads(clean_str)
    
    return json_obj

async def extract_dsl_query(user_query: str, request_id: str):
    # logger = Logger(request_id=request_id)

    # logger.info("Calling model ...")
    try:
        llm = ChatOpenAI(
            model=settings.openai_model_name,
            api_key=settings.openai_api_key,
        )

        prompt = ChatPromptTemplate.from_messages([
            ("system", settings.nlp_to_dsl_prompt + f' {user_query}')
        ])

        logger.debug(f"Prompt created: {prompt}")

        chain = prompt | llm

        logger.debug(f"Chain created: {chain}")

        response = await chain.ainvoke({"input": user_query})

        json_response = convert_response_to_json(response.content)
        logger.info(f"Response received: {json_response}")

    except Exception as e:
        logger.error(f"Error occurred in extract_dsl_query: {e}")
        response = {"error": str(e)}

    return json_response
