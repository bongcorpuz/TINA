# test_file_upload_admin_only.py
import os
import pytest
from file_utils import extract_text_from_file, index_document
from database import get_conn, store_file_text
from auth import is_admin

@pytest.fixture(scope="module")
def sample_txt_file(tmp_path_factory):
    file_path = tmp_path_factory.mktemp("data") / "test_doc.txt"
    file_path.write_text("This is a tax document.")
    return file_path

def test_upload_denied_for_non_admin():
    non_admin_user = "guest"
    assert not is_admin(non_admin_user)


def test_upload_allowed_for_admin(sample_txt_file):
    admin_user = "admin"
    assert is_admin(admin_user)

    # Simulate upload handling
    path = str(sample_txt_file)
    extracted = extract_text_from_file(path)
    assert "tax document" in extracted

    index_document(extracted)
    stored = store_file_text("admin_test.txt", extracted)
    assert os.path.exists(stored)