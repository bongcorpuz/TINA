# file_utils.py (patched to support separate fine-tuned embedding model for semantic search)

import os
import fitz
import pdfplumber
import pytesseract
from PIL import Image
from docx import Document
import numpy as np
import faiss
import logging

from sentence_transformers import SentenceTransformer  # use dedicated model for embeddings

# Optional: use LoRA + HuggingFace transformers if needed for embedding
# from transformers import AutoTokenizer, AutoModel
# from peft import PeftModel

# Embedding model path (can be your LoRA fine-tuned encoder if desired)
EMBED_MODEL_PATH = os.getenv("EMBED_MODEL_PATH", "sentence-transformers/all-MiniLM-L6-v2")
model = SentenceTransformer(EMBED_MODEL_PATH)

INDEX_FILE = "faiss_index.idx"
VERSION_FILE = "index_version.txt"
CURRENT_VERSION = "v1.0.0"

index = None
knowledge_texts = []
ALLOWED_EXTENSIONS = {".pdf", ".txt", ".jpg", ".jpeg", ".png", ".doc", ".docx", ".odt", ".rtf"}

def is_valid_file(filename: str) -> bool:
    return os.path.splitext(filename)[1].lower() in ALLOWED_EXTENSIONS

def save_file(file) -> tuple[str, str]:
    filepath = os.path.join("knowledge_files", file.name)
    with open(filepath, "wb") as f:
        f.write(file.read())
    return filepath, ""

def extract_text_from_file(path: str) -> str:
    ext = os.path.splitext(path)[1].lower()
    try:
        if ext == ".pdf":
            with pdfplumber.open(path) as pdf:
                return "\n".join([page.extract_text() or "" for page in pdf.pages])
        if ext in [".jpg", ".jpeg", ".png"]:
            return pytesseract.image_to_string(Image.open(path))
        if ext == ".txt":
            with open(path, "r", encoding="utf-8") as f:
                return f.read()
        if ext == ".docx":
            doc = Document(path)
            return "\n".join([p.text for p in doc.paragraphs])
        if ext in [".odt", ".rtf", ".doc"]:
            import textract
            return textract.process(path).decode("utf-8")
    except Exception as e:
        return f"[Failed to extract text: {e}]"
    return "[Unsupported file format]"

def index_document(text: str):
    global knowledge_texts, index
    if not text:
        return
    embedding = model.encode([text], convert_to_tensor=False)
    knowledge_texts.append(text)
    if index is None:
        index = faiss.IndexFlatL2(len(embedding[0]))
    index.add(np.array(embedding, dtype=np.float32))
    persist_faiss_index()

def semantic_search(query: str, top_k: int = 3) -> list[str]:
    if index is None:
        raise RuntimeError("FAISS index is not initialized.")
    query_vec = model.encode([query], convert_to_tensor=False)
    scores, indices = index.search(np.array(query_vec, dtype=np.float32), top_k)
    return [knowledge_texts[i] for i in indices[0] if i < len(knowledge_texts)]

def persist_faiss_index():
    if index:
        faiss.write_index(index, INDEX_FILE)
        with open(VERSION_FILE, "w") as f:
            f.write(CURRENT_VERSION)

def load_or_create_faiss_index(skip_versioning: bool = False):
    global index, knowledge_texts
    if os.path.exists(INDEX_FILE):
        try:
            index = faiss.read_index(INDEX_FILE)
            if not skip_versioning:
                with open(VERSION_FILE, "r") as f:
                    if f.read().strip() != CURRENT_VERSION:
                        logging.warning("Index version mismatch. Rebuilding index.")
                        rebuild_index()
        except Exception as e:
            logging.warning(f"Failed to load FAISS index: {e}, rebuilding...")
            rebuild_index()
    else:
        rebuild_index()

def rebuild_index():
    global index, knowledge_texts
    index = None
    knowledge_texts = []
    os.makedirs("knowledge_files", exist_ok=True)
    for filename in os.listdir("knowledge_files"):
        path = os.path.join("knowledge_files", filename)
        if is_valid_file(path):
            text = extract_text_from_file(path)
            index_document(text)
