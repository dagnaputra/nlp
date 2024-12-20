from openai import OpenAI
from api.core.config import settings
import time


openai_api_key = settings.LLM_API_KEY
openai_api_base = settings.LLM_SERVICE_URL

client = OpenAI(
    api_key=openai_api_key,
    base_url=openai_api_base,
)

SYSTEM_PROMPT = """You are an AI assistant for security-focused Retrieval Augmented Generation (RAG) tasks. Your role:
1. Process security queries using:
    - Provided context
    - OpenSearch retrieval results
    - Conversation history (Optional)

2. Deliver clear responses that:
    - Synthesize relevant search results
    - Maintain educational focus
    - Address security concepts accurately
    - Follow conversation context

3. Handle security topics responsibly:
    - Provide factual information
    - Focus on defensive measures
    - Clarify ambiguous requests
    - Note relevant risks

Keep responses clear, relevant, and based on provided search results and context.
"""

def generate_response(message, max_retries=3, delay=1):
    for attempt in range(max_retries):
        try:
            response = client.chat.completions.create(
            messages=[
                {
                    "role": "system", 
                    "content": SYSTEM_PROMPT
                },
                {
                    "role": "user",
                    "content": message,
                }
            ],
            model=settings.LLM_MODEL,
            temperature=0.95,
            stream=False
            )
            return response.choices[0].message.content
        except Exception as e:
            if attempt < max_retries - 1:
                print(f"Error occurred: {e}. Retrying in {delay} seconds...")
                time.sleep(delay)
                delay *= 2  
            else:
                print(f"Failed to get response after {max_retries} attempts: {e}")
                return None
            
# print(generate_response('Chào bạn'))