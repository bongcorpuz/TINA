# ask_tina.py

import os
import time
import logging
import openai
from functools import lru_cache
from file_utils import semantic_search
from dotenv import load_dotenv

load_dotenv()
openai.api_key = os.getenv("OPENAI_API_KEY")

@lru_cache(maxsize=32)
def fallback_to_chatgpt(prompt: str) -> str:
    logging.warning("Fallback to ChatGPT activated.")
    last_error = ""
    for attempt in range(3):
        try:
            response = openai.ChatCompletion.create(
                model="gpt-3.5-turbo",
                messages=[{"role": "user", "content": prompt}]
            )
            return response.choices[0].message["content"].strip()
        except Exception as e:
            last_error = str(e)
            logging.error(f"[ChatGPT Retry {attempt+1}] {last_error}")
            time.sleep(1.5)
    return f"[ChatGPT Error] All retries failed. Reason: {last_error}"

def answer_query_with_knowledge(query: str) -> tuple[list[str], str]:
    try:
        results = semantic_search(query, top_k=3)
        return results, "semantic"
    except Exception as e:
        logging.warning(f"Semantic search failed, falling back to ChatGPT: {e}")
        fallback_answer = fallback_to_chatgpt(query)
        return [fallback_answer], "chatgpt"
