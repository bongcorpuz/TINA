# file_utils.py
import os, shutil
from datetime import datetime

UPLOAD_DIR = "uploads"
MAX_FILE_MB = 5
ALLOWED = {".pdf", ".txt", ".md", ".jpg", ".jpeg", ".png"}

def ensure_dir(): os.makedirs(UPLOAD_DIR, exist_ok=True)

def is_valid(file): ...
def save_file(file): ...
