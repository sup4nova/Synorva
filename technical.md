# Synorva — Technical Documentation

## Overview

Synorva is a generative AI application that analyses the emotional content of an image and produces a matching music track in response. It combines computer vision, audio processing, and supervised machine learning into a single multimodal pipeline.

---

## Tech Stack

### Backend — Python

| Library | Role |
|---|---|
| `FastAPI` + `uvicorn` | HTTP server and async API routing |
| `starlette` | Async web framework underlying FastAPI |
| `librosa` | Audio feature extraction (MFCC, chroma, tempo, spectral analysis) |
| `OpenCV` | Image analysis — brightness, edges, face detection, color space |
| `scikit-learn` | Supervised ML — RandomForest regressor for valence/arousal prediction |
| `numpy` / `numba` | Numerical computing and JIT compilation for performance |
| `pandas` | Dataset management and CSV processing |
| `Pillow` | Image resizing and pixel-level stats |
| `soundfile` / `scipy` | Audio I/O and signal processing |
| `python-dotenv` | Environment variable management |

### Frontend — React + TypeScript

| Tool | Role |
|---|---|
| `React 19` | UI framework |
| `Vite` | Dev server and bundler |
| `TypeScript` | Static typing |
| `Tailwind CSS` | Styling |

### Infrastructure

| Tool | Role |
|---|---|
| `Docker` | Containerisation of backend and frontend |
| `docker-compose` | Multi-service orchestration |
| `nginx` | Serves the React build and proxies `/api` to FastAPI |

---

## Key ML Concepts

**Feature engineering** — Transforming raw audio and image files into numeric vectors that a machine learning model can process. `librosa` extracts ~30 audio descriptors per file; `OpenCV` extracts 11 visual descriptors per image.

**Supervised learning** — A `RandomForestRegressor` is trained on labeled data (image features → valence/arousal). At inference time it predicts emotion scores for any new uploaded image.

**Multimodal pipeline** — Image and audio are processed independently then combined: the image determines the target emotion, audio samples are selected to match it.

---

## Emotion Space

Synorva maps all content onto two axes:

**Valence** — the positive/negative dimension of emotion

```
-1.0            0            +1.0
 sad ◄──────────┼──────────► happy
```

**Arousal** — the energy/intensity dimension of emotion

```
-1.0            0            +1.0
calm ◄──────────┼──────────► energetic
```

These two values together define one of 8 emotion labels:

`euphoric` · `uplifting` · `warm` · `dreamy` · `dark` · `melancholic` · `tense` · `aggressive`

---

## Request Flow

### Image upload → generated track

```
User selects an image in the React frontend
│
│  POST /api/build-track
│  Content-Type: multipart/form-data
│  Body: { file: <image bytes> }
▼
FastAPI receives the image (UploadFile)
  → cv2.imdecode()            decode bytes → numpy BGR array
  → extract_image_features()  compute 11 visual descriptors
  → predict_valaro_from_bgr() RandomForest → { valence, arousal }
  → render_track()            select + mix audio samples → mix.wav
│
│  HTTP 200 — application/json
│  { valence, arousal, mix_url, picks }
▼
React receives the JSON
  → displays valence / arousal / emotion label
  → loads the audio track via <audio src={mix_url} />
```

### Protocol summary

| Step | Protocol | Format |
|---|---|---|
| Image upload | HTTP POST | `multipart/form-data` |
| Prediction result | HTTP Response | `application/json` |
| Audio file delivery | HTTP GET | `audio/wav` (static file) |

> The WAV file is not embedded in the JSON — React fetches it separately as a static file served by FastAPI at `/static/renders/mix.wav`.

---

## API Endpoints

### `GET /health`

Liveness probe. Returns `{ "ok": true }`. Used by the frontend to confirm the backend is reachable.

---

### `POST /upload-image`

Saves an uploaded image to `/uploads/` for debugging purposes. Not part of the main emotion pipeline.

> **Security note:** the filename is sanitised with `Path(file.filename).name` to strip any directory traversal components (e.g. `../../etc/passwd`). Files are stored with a `uuid4` prefix to prevent collisions and overwrites. The endpoint does not execute or process the file — write-only storage.

---

### `POST /api/analyze-image`

Runs the image feature extraction and ML prediction without generating audio. Returns `{ valence, arousal, features_used }`. Used to display the detected emotion in the UI before committing to a full render.

---

### `POST /api/build-track`

Full pipeline endpoint — the core feature of the application.

```
1. Decode uploaded image bytes → OpenCV BGR array
2. predict_valaro_from_bgr()  → { valence, arousal }
3. render_track()             → select samples, mix, write mix.wav
4. Return { valence, arousal, mix_url, picks }
```

---

## Scripts

### Core pipeline

| Script | Role |
|---|---|
| `main.py` | FastAPI app — initialises server, mounts static files, defines all routes |
| `image_analysis.py` | Extracts 11 visual features from a BGR image array |
| `audio_analysis.py` | Extracts ~30 acoustic features from a WAV/MP3 file |
| `label_audio_emotions.py` | Converts audio features → valence / arousal / emotion label |
| `label_picture_emotions.py` | Converts image features → valence / arousal / emotion label |
| `auto_arranger.py` | Selects and mixes audio samples to match a target valence/arousal |
| `train_picture_reg.py` | Trains and saves the RandomForest model (`picture_valaro.pkl`) |

### Dataset builders

| Script | Role |
|---|---|
| `build_audio_dataset.py` | Scans `data/raw_audio/`, extracts features, saves labeled CSV |
| `build_picture_dataset.py` | Scans `data/raw_picture/`, extracts visual features, saves CSV |
| `build_samples_index.py` | Builds `samples_index.csv` used by `auto_arranger` at runtime |
| `collect_images.py` | Downloads training images from the Unsplash API by emotion keyword |
| `collect_samples.py` | Downloads audio samples from the Freesound API (optional — manual import supported) |

### Utilities

| Script | Role |
|---|---|
| `pipeline.py` | Single command to rebuild all datasets in order |
| `test_pipeline.py` | End-to-end reliability test — synthetic images, no real data required |

---

## Rebuild Pipeline

Run after adding new audio samples or training images:

```bash
# Rebuild all datasets (audio + image)
python -m backend.pipeline --images

# Retrain the image emotion model
python -m backend.train_picture_reg

# Verify the full pipeline
python -m backend.test_pipeline
```

---

## Docker Deployment

```bash
# Build and start all services
docker compose up --build -d

# Apply code changes
git pull && docker compose up --build -d
```

| Service | Port | Description |
|---|---|---|
| `backend` | 8000 | FastAPI server |
| `frontend` | 80 | React app served by nginx |

> Persistent data (datasets, trained model, generated audio) is mounted as Docker volumes and survives container restarts.

---

## Audio Sample Import

Audio samples are organised by instrument type in subdirectories:

```
data/raw_audio/
├── kick/
├── snare/
├── hihat/
├── bass/
├── melody/
├── pad/
└── vocal/
```

Manual import via BandLab is supported. After adding files, run `python -m backend.pipeline` to process them.

---

> **Notes for completion:**
> - **Valence/arousal** — verify that the axis definitions match what you want displayed in the frontend.
> - **Security (`/upload-image`)** — reasonably secure for a personal app; for public production, add server-side MIME type validation and file size limits.