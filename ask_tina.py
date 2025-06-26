import os
import hashlib
import logging
from file_utils import semantic_search, index_document
from database import store_file_text
from app import fallback_to_chatgpt

def answer_query_with_knowledge(query: str) -> tuple[list[str], str]:
    try:
        results = semantic_search(query, top_k=3)
        if not results or all(r.strip() == "" for r in results):
            raise ValueError("No relevant semantic result")
        return results, "semantic"
    except Exception as e:
        logging.warning(f"Semantic search failed or empty. Using fallback: {e}")
        fallback_answer = fallback_to_chatgpt(query)
        filename = f"chatgpt_{hashlib.sha256(fallback_answer.encode()).hexdigest()}.txt"
        path = os.path.join("knowledge_files", filename)
        if not os.path.exists(path):
            with open(path, "w", encoding="utf-8") as f:
                f.write(fallback_answer)
            index_document(fallback_answer)
            store_file_text(filename, fallback_answer)
        return [fallback_answer], "chatgpt"
