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

## Model notes

`valence`/`arousal` are currently produced by a **hand-tuned weighted heuristic** over the 11 visual features (see `label_picture_emotions.py`) - not learned from human-perceived emotion. The RandomForest in `train_picture_reg.py` is trained on those same heuristic labels, so it distills/smooths the heuristic rather than learning an independent ground truth; its R² measures how well a forest can re-fit a deterministic formula of its own inputs, not how well it predicts human-perceived emotion.

This is an intentional first pass, not a hidden flaw - see [Roadmap](#roadmap) for the plan to validate (and if needed, recalibrate) the heuristic against real human annotations.

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
│   ├── models/                    # trained .pkl - committed so image analysis works out of the box
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

**What works right after cloning, without any local data:** image analysis (`/api/analyze-image`) — the trained regressor (`backend/models/picture_valaro.pkl`) is committed, so brightness/warmth/etc. → valence/arousal prediction works immediately.

**What needs local data:** full track generation (`/api/build-track`) needs audio samples in `data/raw_audio/<instrument>/` (not included - see [Freesound](https://freesound.org/apiv2/apply/) licensing) plus `python -m backend.pipeline` to build the sample index. Pre-rendered example outputs (image + generated track) are shipped in `frontend/public/demo/` for a no-setup preview.

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
| `/api/upload-image` | POST | saves to `/uploads/` (debug) |

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

**Step 1 - Validate before adding complexity (in progress)**

Today's labels come from a hand-made heuristic: my quality score currently measures a model re-fitting its own formula, not real perceived emotion. I'm collecting human annotations (clickable valence/arousal pad, 2-3 annotators, inter-annotator agreement) to get real ground truth and measure the gap via Pearson correlation / MAE.

- Sample 200-300 images from `data/raw_picture/`, balanced across the 8 emotion classes, shuffled
- Build a small annotation tool (static HTML/JS or Streamlit) with a clickable 2D valence/arousal pad (Russell circumplex) → saves `image_id, valence_human, arousal_human, annotator_id` to CSV
- Collect annotations from 2-3 people (with some overlap) to measure inter-annotator agreement
- Average/median per image = human ground truth; compare against the heuristic (`compute_valence_arousal_images`) via Pearson correlation / MAE / R² - this becomes the real quality signal, replacing the current heuristic-vs-heuristic R²
- Optionally refit the heuristic's weights via linear regression on human labels and compare to the hand-picked weights

**Step 2 - Move to a neural network (planned)**

Once real human ground truth is in place, replace the heuristic + RandomForest with a learned model (CNN / vision transformer, or CLIP-style fine-tuning) trained on those annotations. The key point: the neural network doesn't come before quality data to train it on - otherwise it's just added complexity without a solid foundation.

**Step 3 - Product enrichment**

- [ ] GPT-4 Vision - natural language emotion description
- [ ] HuggingFace LLM support (Mistral 7B)
- [ ] Extended sample library
- [ ] MP3 export
- [ ] Mobile UI

---

**sup4nova** - [github.com/sup4nova](https://github.com/sup4nova)
