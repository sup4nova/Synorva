# backend/tests/test_api.py
# Exercises the FastAPI endpoints directly (no audio samples required,
# so this runs fully in CI - unlike backend/test_pipeline.py's stage 3).

import io
import shutil

from fastapi.testclient import TestClient
from PIL import Image

from backend.main import app, UPLOADS_DIR

client = TestClient(app)


def _png_bytes(color=(255, 200, 0), size=(64, 64)) -> bytes:
    buf = io.BytesIO()
    Image.new("RGB", size, color).save(buf, format="PNG")
    return buf.getvalue()


def test_root():
    res = client.get("/")
    assert res.status_code == 200
    assert res.json() == {"message": "FastAPI is connected."}


def test_health():
    res = client.get("/health")
    assert res.status_code == 200
    assert res.json() == {"ok": True}


def test_analyze_image_returns_valence_arousal():
    files = {"file": ("test.png", _png_bytes(), "image/png")}
    res = client.post("/api/analyze-image", files=files)
    assert res.status_code == 200
    body = res.json()
    assert "valence" in body and "arousal" in body
    assert isinstance(body["valence"], float)
    assert isinstance(body["arousal"], float)


def test_analyze_image_rejects_non_image():
    files = {"file": ("test.txt", b"not an image", "text/plain")}
    res = client.post("/api/analyze-image", files=files)
    assert res.status_code == 400


def test_upload_image_saves_file():
    files = {"file": ("test.png", _png_bytes(), "image/png")}
    try:
        res = client.post("/api/upload-image", files=files)
        assert res.status_code == 200
        body = res.json()
        assert body["message"] == "ok"
        assert body["size"] > 0
    finally:
        shutil.rmtree(UPLOADS_DIR, ignore_errors=True)


def test_upload_image_rejects_non_image():
    files = {"file": ("test.txt", b"not an image", "text/plain")}
    res = client.post("/api/upload-image", files=files)
    assert res.status_code == 400
