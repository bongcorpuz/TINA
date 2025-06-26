import os
import shutil
import mimetypes
import logging
import re
import hashlib
from pathlib import Path
from PIL import Image
import pytesseract
import fitz  # PyMuPDF
import pdfplumber
import docx
import faiss
import numpy as np
from sentence_transformers import SentenceTransformer

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Constants and configuration
ALLOWED_EXTENSIONS = {".txt", ".pdf", ".jpg", ".jpeg", ".png", ".docx"}
ALLOWED_MIME_PREFIXES = {
    "text", "image", "application/pdf",
    "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
}

EMBED_MODEL_PATH = os.getenv("EMBED_MODEL_PATH", "sentence-transformers/all-MiniLM-L6-v2")
model = SentenceTransformer(EMBED_MODEL_PATH)

INDEX_FILE = "faiss_index.idx"
VERSION_FILE = "index_version.txt"
CURRENT_VERSION = "v1.0.0"

index = None
knowledge_texts = []

def is_valid_file(file_path: str) -> bool:
    ext = Path(file_path).suffix.lower()
    mime, _ = mimetypes.guess_type(file_path)

    if ext not in ALLOWED_EXTENSIONS:
        logger.debug(f"Rejected file: {file_path} — invalid extension: {ext}")
        return False

    if mime is None:
        logger.debug(f"Rejected file: {file_path} — MIME type could not be guessed")
        return False

    if not any(mime.startswith(prefix) or mime == prefix for prefix in ALLOWED_MIME_PREFIXES):
        logger.debug(f"Rejected file: {file_path} — invalid MIME: {mime}")
        return False

    return True

def extract_text_from_file(file_path: str) -> str:
    ext = Path(file_path).suffix.lower()
    text = ""

    try:
        if ext == ".txt":
            with open(file_path, "r", encoding="utf-8", errors="ignore") as f:
                text = f.read()

        elif ext == ".pdf":
            try:
                with fitz.open(file_path) as doc:
                    text = "\n".join(page.get_text() for page in doc)
            except Exception:
                with pdfplumber.open(file_path) as pdf:
                    text = "\n".join([page.extract_text() or "" for page in pdf.pages])

        elif ext in [".jpg", ".jpeg", ".png"]:
            image = Image.open(file_path)
            text = pytesseract.image_to_string(image)

        elif ext == ".docx":
            doc = docx.Document(file_path)
            text = "\n".join(paragraph.text for paragraph in doc.paragraphs)

    except Exception as e:
        logger.warning(f"Failed to extract text from {file_path}: {e}")

    return text.strip()

def sanitize_filename(filename: str) -> str:
    return re.sub(r'[^a-zA-Z0-9_.-]', '_', filename)

def save_file(file) -> tuple[str, str, str]:
    filename = sanitize_filename(getattr(file, 'name', 'uploaded_file'))
    folder = os.path.join("knowledge_files", "dynamic")
    os.makedirs(folder, exist_ok=True)

    base, ext = os.path.splitext(filename)
    counter = 1
    filepath = os.path.join(folder, filename)
    while os.path.exists(filepath):
        filename = f"{base}_{counter}{ext}"
        filepath = os.path.join(folder, filename)
        counter += 1

    try:
        if hasattr(file, 'file') and hasattr(file.file, 'read'):
            file.file.seek(0)
            with open(filepath, "wb") as f:
                shutil.copyfileobj(file.file, f)
        elif hasattr(file, 'read'):
            try:
                file.seek(0)
            except Exception:
                pass
            with open(filepath, "wb") as f:
                f.write(file.read())
        elif hasattr(file, 'path') and os.path.exists(file.path):
            if not os.path.samefile(file.path, filepath):
                shutil.copy(file.path, filepath)
        elif isinstance(file, str) and os.path.exists(file):
            shutil.copy(file, filepath)
        else:
            raise ValueError(f"Unsupported file object type: {type(file)}")

        logger.info(f"Saved file to: {filepath} ({os.path.getsize(filepath)} bytes)")
        return filepath, filename, ""
    except Exception as e:
        logger.error(f"Failed to save uploaded file: {e}")
        return "", filename, f"Error saving file: {e}"

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

def learn_from_text(content: str, label: str = "dynamic") -> None:
    if not content.strip():
        return
    try:
        filename = f"{label}_{hashlib.sha256(content.encode()).hexdigest()}.txt"
        folder = os.path.join("knowledge_files", "dynamic")
        os.makedirs(folder, exist_ok=True)
        filepath = os.path.join(folder, filename)
        if not os.path.exists(filepath):
            with open(filepath, "w", encoding="utf-8") as f:
                f.write(content)
        index_document(content)
    except Exception as e:
        logger.error(f"Failed to learn from text: {e}")

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
                        logger.warning("Index version mismatch. Rebuilding index.")
                        rebuild_index()
        except Exception as e:
            logger.warning(f"Failed to load FAISS index: {e}, rebuilding...")
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
