import os
import sys
from pathlib import Path
import pytest

BASE_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BASE_DIR))

@pytest.fixture(autouse=True, scope="session")
def isolate_test_environment(tmp_path_factory):
    """
    Ensure automated tests run in an isolated temporary database
    and temporary uploads directory so they never pollute the user's
    real assistant.db or uploads/resumes.
    """
    test_dir = tmp_path_factory.mktemp("test_env")
    test_db = test_dir / "test_assistant.db"
    test_uploads = test_dir / "uploads" / "resumes"
    test_uploads.mkdir(parents=True, exist_ok=True)

    import backend.config as config
    original_db = config.DB_PATH
    original_uploads = config.UPLOADS_DIR

    config.DB_PATH = test_db
    config.UPLOADS_DIR = test_uploads

    import backend.database as db
    db.DB_PATH = test_db
    db.init_db()

    yield

    config.DB_PATH = original_db
    config.UPLOADS_DIR = original_uploads
    db.DB_PATH = original_db

