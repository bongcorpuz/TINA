# file_utils.py
import os
import shutil
import logging
from datetime import datetime
import pytesseract
from PIL import Image
import fitz  # PyMuPDF
import pdfplumber
from docx import Document  # added docx support
import subprocess
import tempfile
from sentence_transformers import SentenceTransformer, util
import numpy as np
import faiss
import pickle

UPLOAD_DIR = "knowledge_files"
INDEX_FILE = "faiss_index.idx"
EMBEDDINGS_FILE = "embeddings.pkl"
INDEX_VERSION_FILE = "faiss_index.version"
MODEL_VERSION = "all-MiniLM-L6-v2"
SKIP_VERSIONING = os.getenv("TINA_SKIP_VERSIONING", "false").lower() == "true"

ALLOWED_EXTENSIONS = {".pdf", ".txt", ".md", ".jpg", ".jpeg", ".png", ".doc", ".docs", ".docx", ".odt", ".rtf"}
MAX_FILE_SIZE_MB = 5

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

model = SentenceTransformer(MODEL_VERSION)

index = None
corpus = []

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
            with pdfplumber.open(path) as pdf:
                return "\n".join(page.extract_text() or "" for page in pdf.pages)
        elif ext in {".jpg", ".jpeg", ".png"}:
            return pytesseract.image_to_string(Image.open(path))
        elif ext in {".txt", ".md"}:
            with open(path, "r", encoding="utf-8", errors="ignore") as f:
                return f.read()
        elif ext in {".doc", ".docs", ".docx"}:
            try:
                doc = Document(path)
                return "\n".join(para.text for para in doc.paragraphs)
            except Exception:
                return "[Unreadable or unsupported Word document]"
        elif ext in {".odt", ".rtf"}:
            try:
                result = subprocess.run(["soffice", "--headless", "--convert-to", "txt:Text", "--outdir", tempfile.gettempdir(), path], capture_output=True)
                if result.returncode != 0:
                    return f"[LibreOffice conversion error: {result.stderr.decode().strip()}]"
                txt_path = os.path.join(tempfile.gettempdir(), os.path.splitext(os.path.basename(path))[0] + ".txt")
                if os.path.exists(txt_path):
                    with open(txt_path, "r", encoding="utf-8", errors="ignore") as f:
                        return f.read()
            except FileNotFoundError:
                return "[LibreOffice not installed. Cannot extract .odt/.rtf files.]"
            except Exception as e:
                return f"[Failed to convert .odt or .rtf: {str(e)}]"
        return ""
    except Exception as e:
        return f"[Extraction failed: {str(e)}]"

def index_document(text):
    global index, corpus
    if not text.strip():
        return
    corpus.append(text)
    embedding = model.encode(text, convert_to_tensor=False, normalize_embeddings=True)
    embedding = np.array([embedding]).astype("float32")

    if index is None:
        index = faiss.IndexFlatL2(embedding.shape[1])

    index.add(embedding)
    save_index()

def semantic_search(query, top_k=3):
    global index, corpus
    if index is None or not corpus:
        logger.info("FAISS fallback: semantic index is empty, using ChatGPT instead.")
        return []
    query_vec = model.encode(query, convert_to_tensor=False, normalize_embeddings=True)
    D, I = index.search(np.array([query_vec]).astype("float32"), top_k)
    return [corpus[i] for i in I[0] if i < len(corpus)]

def save_index():
    faiss.write_index(index, INDEX_FILE)
    with open(EMBEDDINGS_FILE, "wb") as f:
        pickle.dump(corpus, f)
    with open(INDEX_VERSION_FILE, "w") as f:
        f.write(MODEL_VERSION)

def load_or_create_faiss_index():
    global index, corpus
    try:
        if os.path.exists(INDEX_FILE) and os.path.exists(EMBEDDINGS_FILE) and os.path.exists(INDEX_VERSION_FILE):
            with open(INDEX_VERSION_FILE, "r") as f:
                stored_version = f.read().strip()
            if stored_version == MODEL_VERSION or SKIP_VERSIONING:
                index = faiss.read_index(INDEX_FILE)
                with open(EMBEDDINGS_FILE, "rb") as f:
                    corpus = pickle.load(f)
                return
        rebuild_index_from_knowledge()
    except Exception as e:
        logger.warning(f"[FAISS index load failed: {e}] Falling back to ChatGPT.")
        index = None
        corpus = []

def rebuild_index_from_knowledge():
    global index, corpus
    index = None
    corpus = []
    for fname in os.listdir(UPLOAD_DIR):
        full_path = os.path.join(UPLOAD_DIR, fname)
        text = extract_text_from_file(full_path)
        if text.strip():
            index_document(text)
    save_index()
