import os
import shutil
from datetime import datetime
import fitz  # PyMuPDF
from PIL import Image
import pytesseract

UPLOAD_DIR = "knowledge_files"
ALLOWED_EXTENSIONS = {".pdf", ".txt", ".md", ".jpg", ".jpeg", ".png"}
MAX_FILE_SIZE_MB = 5


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


def extract_text_from_file(file_path):
    ext = os.path.splitext(file_path)[-1].lower()
    if ext == ".pdf":
        try:
            text = ""
            doc = fitz.open(file_path)
            for page in doc:
                text += page.get_text()
            return text.strip()
        except Exception as e:
            return f"Error reading PDF: {str(e)}"
    elif ext in {".jpg", ".jpeg", ".png"}:
        try:
            img = Image.open(file_path)
            return pytesseract.image_to_string(img).strip()
        except Exception as e:
            return f"Error processing image: {str(e)}"
    elif ext in {".txt", ".md"}:
        try:
            with open(file_path, "r", encoding="utf-8") as f:
                return f.read().strip()
        except Exception as e:
            return f"Error reading file: {str(e)}"
    else:
        return "Unsupported file format."
