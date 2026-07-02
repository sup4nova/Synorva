# Synorva
### *See sound. Hear images. Compose feeling.*

Upload an image → Synorva reads its emotion → generates a matching music track.
---

## How it works

Synorva extracts the emotional content of any still image and synthesises a coherent audio track from it.
Emotion is encoded as a **valence-arousal** score - the two-axis model used in music psychology - then matched against a curated sample library tuned for cinematic, ambient and electronic genres.

```
image upload
  → computer vision   11 visual features (brightness, warmth, edges, faces...)
  → random forest     valence + arousal score
  → sample selection  emotionally closest kick / bass / melody / riser
  → audio mix         generated track (.wav)
```

---

## Emotion space

```
              HIGH AROUSAL
  aggressive  |  euphoric
              |
SAD ----------+---------- HAPPY
              |
  melancholic |  warm
              LOW AROUSAL
```

| axis | range | meaning |
|---|---|---|
| valence | -1 → +1 | sad to happy |
| arousal | -1 → +1 | calm to energetic |

8 labels: `aggressive` `tense` `euphoric` `uplifting` `melancholic` `warm` `dark` `dreamy`

---

## Stack

**Backend**
- `FastAPI` + uvicorn - async HTTP server
- `librosa` - MFCC, chroma, tempo, spectral analysis
- `OpenCV` + Pillow - color, edges, sharpness, face detection
- `scikit-learn` - RandomForest regressor for valence/arousal prediction
- `soundfile` - audio I/O and mix export

**Frontend**
- `React 19` + TypeScript + Vite
- `Tailwind CSS`

**Infra**
- `Docker` + docker-compose
- `nginx` - serves React build, proxies `/api` to FastAPI

---

## Project structure

```
Synorva/
├── backend/
│   ├── main.py                    # FastAPI app + all routes
│   ├── image_analysis.py          # image -> 11 features + ML prediction
│   ├── audio_analysis.py          # audio file -> ~30 acoustic features
│   ├── auto_arranger.py           # sample selection + audio mix
│   ├── label_audio_emotions.py    # acoustic features -> valence/arousal
│   ├── label_picture_emotions.py  # visual features -> valence/arousal
│   ├── train_picture_reg.py       # trains + saves the RandomForest model
│   ├── build_audio_dataset.py     # scans raw_audio/, extracts features
│   ├── build_picture_dataset.py   # scans raw_picture/, extracts features
│   ├── build_samples_index.py     # builds samples_index.csv
│   ├── collect_images.py          # downloads training images (Unsplash)
│   ├── collect_samples.py         # downloads audio samples (Freesound)
│   ├── pipeline.py                # rebuild all datasets in one command
│   ├── test_pipeline.py           # end-to-end reliability test
│   ├── models/                    # trained .pkl - git-ignored
│   ├── data/                      # samples_index.csv
│   └── static/renders/            # generated audio mixes
├── data/
│   ├── raw_audio/<type>/*.wav     # samples organised by instrument
│   ├── raw_picture/<emotion>/     # training images by emotion
│   └── *.csv                      # feature + label datasets
├── frontend/src/
├── Dockerfile
├── docker-compose.yml
└── .env
```

---

## Setup

**Requirements:** Python 3.11+ · Node.js 20+ · Docker (for deployment)

```bash
# Clone
git clone https://github.com/sup4nova/synorva.git
cd synorva

# Backend
python -m venv venv && source venv/bin/activate
pip install -r requirements.txt

# Frontend
cd frontend && npm install
```

```bash
# Configure
cp .env.example .env
```

Organise your audio samples by instrument:
```
data/raw_audio/kick/   bass/   melody/   pad/   riser/   snare/   hihat/
```

```bash
# Build datasets + train
python -m backend.pipeline --images
python -m backend.train_picture_reg

# Run (two terminals)
uvicorn backend.main:app --reload
cd frontend && npm run dev
```

Open `http://localhost:5173`

---

## Docker

```bash
docker compose up --build -d
```

| service | url |
|---|---|
| frontend | `http://localhost` |
| API | `http://localhost:8000` |

Data, models and generated audio are mounted as volumes and persist across restarts.

```bash
git pull && docker compose up --build -d
```

---

## API

| endpoint | method | returns |
|---|---|---|
| `/health` | GET | liveness check |
| `/api/analyze-image` | POST | `{ valence, arousal }` |
| `/api/build-track` | POST | `{ valence, arousal, mix_url, picks }` |
| `/upload-image` | POST | saves to `/uploads/` (debug) |

All endpoints accept `multipart/form-data` with a `file` field.

---

## Tests

```bash
python -m backend.test_pipeline
```

Runs the full pipeline on synthetic images - no real data required.
Exits `0` if score ≥ 70%, `1` otherwise.

---

## Roadmap

- [ ] GPT-4 Vision - natural language emotion description
- [ ] HuggingFace LLM support (Mistral 7B)
- [ ] Extended sample library
- [ ] MP3 export
- [ ] Mobile UI

---

**sup4nova** - [github.com/sup4nova](https://github.com/sup4nova)
