import os
import shutil
from datetime import datetime
import pytesseract
from PIL import Image
import fitz  # PyMuPDF
from sentence_transformers import SentenceTransformer
import faiss
import numpy as np
import torch
from docx import Document

UPLOAD_DIR = "knowledge_files"
ALLOWED_EXTENSIONS = {".pdf", ".txt", ".md", ".jpg", ".jpeg", ".png", ".doc", ".docs"}
MAX_FILE_SIZE_MB = 5
INDEX_FILE = "faiss_index.idx"
DOC_FILE = "doc_store.txt"

MODEL = SentenceTransformer('all-MiniLM-L6-v2')
DIM = 384
faiss_index = faiss.IndexFlatL2(DIM)
DOCUMENTS = []

if os.path.exists(INDEX_FILE) and os.path.exists(DOC_FILE):
    faiss_index = faiss.read_index(INDEX_FILE)
    with open(DOC_FILE, "r", encoding="utf-8") as f:
        DOCUMENTS = f.read().split("\n\n" + ("=" * 40) + "\n\n")

def is_valid_file(file):
    ext = os.path.splitext(file.name)[-1].lower()
    if ext not in ALLOWED_EXTENSIONS:
        return False, f"Invalid file type. Allowed: {', '.join(ALLOWED_EXTENSIONS)}."
    file.seek(0, os.SEEK_END)
    size_mb = file.tell() / (1024 * 1024)
    file.seek(0)
    if size_mb > MAX_FILE_SIZE_MB:
        return False, f"File too large. Max size: {MAX_FILE_SIZE_MB}MB."
    return True, ""

def save_file(file):
    if not file:
        return None, "No file provided."

    is_valid, error = is_valid_file(file)
    if not is_valid:
        return None, error

    timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
    filename = f"{timestamp}_{file.name}"
    save_path = os.path.join(UPLOAD_DIR, filename)

    with open(save_path, "wb") as f:
        shutil.copyfileobj(file, f)

    return save_path, ""

def extract_text_from_file(path):
    ext = os.path.splitext(path)[-1].lower()
    try:
        if ext == ".pdf":
            doc = fitz.open(path)
            text = "\n".join([page.get_text() for page in doc])
            return text
        elif ext in [".jpg", ".jpeg", ".png"]:
            return pytesseract.image_to_string(Image.open(path))
        elif ext in [".doc", ".docs"]:
            try:
                doc = Document(path)
                return "\n".join([para.text for para in doc.paragraphs])
            except Exception as docx_err:
                return f"Error reading DOC file: {str(docx_err)}"
        else:
            with open(path, "r", encoding="utf-8") as f:
                return f.read()
    except Exception as e:
        return f"Error extracting text: {str(e)}"

def semantic_search(query, top_k=3):
    if not DOCUMENTS or not faiss_index.ntotal:
        return []
    query_emb = MODEL.encode(query).astype(np.float32)
    D, I = faiss_index.search(np.array([query_emb]), top_k)
    return [DOCUMENTS[i] for i in I[0] if i < len(DOCUMENTS)]

def index_document(text):
    embedding = MODEL.encode(text).astype(np.float32)
    faiss_index.add(np.array([embedding]))
    DOCUMENTS.append(text)

    with open(DOC_FILE, "w", encoding="utf-8") as f:
        f.write("\n\n" + ("=" * 40) + "\n\n".join(DOCUMENTS))
    faiss.write_index(faiss_index, INDEX_FILE)
