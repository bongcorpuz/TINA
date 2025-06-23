# file_utils.py
import os
import fitz  # PyMuPDF
import pdfplumber
import pytesseract
from PIL import Image
from sentence_transformers import SentenceTransformer, util
import faiss
import numpy as np
import logging
from docx import Document

try:
    import openai
    openai.api_key = os.getenv("OPENAI_API_KEY")
except ImportError:
    openai = None

MODEL_NAME = "sentence-transformers/all-MiniLM-L6-v2"
INDEX_FILE = "faiss_index.idx"
VERSION_FILE = "index_version.txt"
CURRENT_VERSION = "v1.0.0"
model = SentenceTransformer(MODEL_NAME)

index = None
knowledge_texts = []

ALLOWED_EXTENSIONS = {".pdf", ".txt", ".jpg", ".jpeg", ".png", ".docx", ".odt", ".rtf"}

def is_valid_file(filename):
    return os.path.splitext(filename)[1].lower() in ALLOWED_EXTENSIONS

def save_file(file):
    filepath = os.path.join("knowledge_files", file.name)
    with open(filepath, "wb") as f:
        f.write(file.read())
    return filepath, None

def extract_text_from_file(path):
    ext = os.path.splitext(path)[1].lower()
    try:
        if ext == ".pdf":
            with pdfplumber.open(path) as pdf:
                return "\n".join([page.extract_text() or "" for page in pdf.pages])
        elif ext in [".jpg", ".jpeg", ".png"]:
            return pytesseract.image_to_string(Image.open(path))
        elif ext == ".txt":
            with open(path, "r", encoding="utf-8") as f:
                return f.read()
        elif ext == ".docx":
            doc = Document(path)
            return "\n".join([p.text for p in doc.paragraphs])
        elif ext in [".odt", ".rtf"]:
            try:
                import textract
                return textract.process(path).decode("utf-8")
            except Exception as e:
                return f"[Error reading file: {e}] Make sure LibreOffice is installed."
        else:
            return "[Unsupported file format]"
    except Exception as e:
        return f"[Failed to extract text: {str(e)}]"

def index_document(text):
    if not text:
        return
    global knowledge_texts, index
    embedding = model.encode([text], convert_to_tensor=False)
    knowledge_texts.append(text)
    if index is None:
        index = faiss.IndexFlatL2(len(embedding[0]))
    index.add(np.array(embedding, dtype=np.float32))
    persist_faiss_index()

def semantic_search(query, top_k=3):
    if index is None:
        raise RuntimeError("FAISS index is not initialized.")
    query_vec = model.encode([query], convert_to_tensor=False)
    scores, indices = index.search(np.array(query_vec, dtype=np.float32), top_k)
    return [knowledge_texts[i] for i in indices[0] if i < len(knowledge_texts)]

def persist_faiss_index():
    if index is not None:
        faiss.write_index(index, INDEX_FILE)
        with open(VERSION_FILE, "w") as f:
            f.write(CURRENT_VERSION)

def load_or_create_faiss_index(skip_versioning=False):
    global index, knowledge_texts
    if os.path.exists(INDEX_FILE):
        try:
            index = faiss.read_index(INDEX_FILE)
            if not skip_versioning:
                with open(VERSION_FILE, "r") as f:
                    version = f.read().strip()
                if version != CURRENT_VERSION:
                    logging.warning("Index version mismatch. Rebuilding index.")
                    rebuild_index()
        except Exception as e:
            logging.warning(f"Failed loading FAISS index: {e}, rebuilding...")
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

def fallback_to_chatgpt(prompt):
    logging.warning("Fallback to ChatGPT activated.")
    if not openai:
        return "[OpenAI is not available]"
    try:
        response = openai.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=[{"role": "user", "content": prompt}]
        )
        return response.choices[0].message.content.strip()
    except Exception as e:
        return f"[ChatGPT Error] {str(e)}"
