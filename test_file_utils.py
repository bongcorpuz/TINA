import os
import tempfile
import pytest
from PIL import Image, ImageDraw, ImageFont
import docx
from file_utils import extract_text_from_file, save_file, is_valid_file

def create_temp_file(extension, content=b"test content"):
    tmp = tempfile.NamedTemporaryFile(delete=False, suffix=extension)
    tmp.write(content)
    tmp.close()
    return tmp.name

def test_extract_text_from_txt():
    path = create_temp_file(".txt", b"Sample text for testing.")
    text = extract_text_from_file(path)
    assert "Sample text" in text
    os.remove(path)

def test_extract_text_from_pdf():
    import fitz
    path = create_temp_file(".pdf")
    doc = fitz.open()
    page = doc.new_page()
    page.insert_text((72, 72), "PDF content here")
    doc.save(path)
    doc.close()
    text = extract_text_from_file(path)
    assert "PDF content" in text
    os.remove(path)

def test_extract_text_from_jpg():
    path = create_temp_file(".jpg")
    img = Image.new("RGB", (200, 100), color="white")
    draw = ImageDraw.Draw(img)
    draw.text((10, 40), "Text", fill="black")
    img.save(path)
    text = extract_text_from_file(path)
    assert "Text" in text
    os.remove(path)

def test_ocr_image_to_text():
    path = create_temp_file(".png")
    img = Image.new("RGB", (300, 150), color="white")
    draw = ImageDraw.Draw(img)
    draw.text((20, 60), "TINA OCR", fill="black")
    img.save(path)
    text = extract_text_from_file(path)
    assert "TINA" in text
    os.remove(path)

def test_ocr_noisy_image():
    path = create_temp_file(".png")
    img = Image.new("RGB", (300, 150), color="white")
    draw = ImageDraw.Draw(img)
    for x in range(0, 300, 10):
        for y in range(0, 150, 10):
            draw.rectangle([x, y, x+2, y+2], fill="gray")
    draw.text((50, 60), "TINA", fill="black")
    img.save(path)
    text = extract_text_from_file(path)
    assert "TINA" in text.upper()
    os.remove(path)

def test_ocr_rotated_text():
    path = create_temp_file(".png")
    img = Image.new("RGB", (300, 150), color="white")
    draw = ImageDraw.Draw(img)
    text_img = Image.new("RGB", (300, 150), color="white")
    draw_text = ImageDraw.Draw(text_img)
    draw_text.text((50, 50), "TINA", fill="black")
    rotated = text_img.rotate(45, expand=1)
    img.paste(rotated, (0, 0))
    img.save(path)
    text = extract_text_from_file(path)
    assert "TINA" in text.upper()
    os.remove(path)

def test_extract_text_from_docx():
    path = create_temp_file(".docx")
    doc = docx.Document()
    doc.add_paragraph("Docx content test")
    doc.save(path)
    text = extract_text_from_file(path)
    assert "Docx content test" in text
    os.remove(path)

def test_is_valid_file_accepts_allowed():
    for ext in [".txt", ".pdf", ".jpg", ".docx"]:
        file = tempfile.NamedTemporaryFile(delete=False, suffix=ext)
        assert is_valid_file(file.name)
        file.close()
        os.remove(file.name)

def test_is_valid_file_rejects_disallowed():
    disallowed = [".exe", ".bat", ".zip", ".md", ".csv"]
    for ext in disallowed:
        file = tempfile.NamedTemporaryFile(delete=False, suffix=ext)
        assert not is_valid_file(file.name)
        file.close()
        os.remove(file.name)

def test_save_file_valid(tmp_path):
    file_path = tmp_path / "sample.txt"
    file_path.write_bytes(b"content")
    with open(file_path, "rb") as f:
        f.name = file_path.name
        path, err = save_file(f)
    assert os.path.exists(path)
    assert err == ""
    os.remove(path)
    os.rmdir(os.path.dirname(path))
