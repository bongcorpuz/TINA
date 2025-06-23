import os
import tempfile
import pytest
from PIL import Image, ImageDraw
from file_utils import extract_text_from_file, save_file, is_valid_file
import docx


def create_temp_file(extension, content=b"test content"):
    tmp = tempfile.NamedTemporaryFile(delete=False, suffix=extension)
    tmp.write(content)
    tmp.close()
    return tmp.name


def test_extract_text_from_txt():
    file_path = create_temp_file(".txt", b"Sample text for testing.")
    text = extract_text_from_file(file_path)
    assert "Sample text" in text
    os.remove(file_path)


def test_extract_text_from_pdf():
    import fitz
    file_path = create_temp_file(".pdf")
    doc = fitz.open()
    page = doc.new_page()
    page.insert_text((72, 72), "PDF content here")
    doc.save(file_path)
    doc.close()
    text = extract_text_from_file(file_path)
    assert "PDF content" in text
    os.remove(file_path)


def test_extract_text_from_jpg():
    file_path = create_temp_file(".jpg")
    img = Image.new("RGB", (200, 100), color=(255, 255, 255))
    draw = ImageDraw.Draw(img)
    draw.text((10, 40), "Text", fill=(0, 0, 0))
    img.save(file_path)
    text = extract_text_from_file(file_path)
    assert "Text" in text
    os.remove(file_path)


def test_save_file_valid():
    tmp_file = tempfile.NamedTemporaryFile(delete=False, suffix=".txt")
    tmp_file.write(b"sample")
    tmp_file.seek(0)
    path, err = save_file(tmp_file)
    assert path is not None and err == ""
    os.remove(path)
    os.remove(tmp_file.name)


def test_is_valid_file():
    tmp = tempfile.NamedTemporaryFile(delete=False, suffix=".txt")
    tmp.write(b"content")
    tmp.seek(0)
    valid, err = is_valid_file(tmp)
    assert valid is True
    tmp.close()
    os.remove(tmp.name)
