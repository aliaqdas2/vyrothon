# Progress

**Setup:** Created a Python virtual environment (`.venv`) and installed `requirements.txt`—FastAPI, Uvicorn, SQLAlchemy/Postgres/pgvector, Google Cloud Storage, python-dotenv, plus heavier stacks (`face_recognition`, OpenCV headless, numpy).

**Grabpic implementation:** App package under `app/`: config (`DATABASE_URL`, `GCS_BUCKET`, thresholds), SQLAlchemy models (`crawl_jobs`, `images`, `identities`, `image_faces` with pgvector 128-d), GCS helpers, face encoding + L2 nearest-neighbor clustering into `grab_id`, routes for `POST /crawl` (BackgroundTasks + job polling), `GET /crawl/status/{job_id}`, `POST /auth/selfie`, `GET /users/{grab_id}/images` (signed URLs). Entrypoint [main.py](main.py); OpenAPI at `/docs`.

**Repo hygiene:** `.gitignore` for bytecode, venvs, `.env`, credential JSONs, and common IDE/OS and GCP/terraform clutter.

**GCP:** Multi-stage **Dockerfile** (dlib build + slim runtime); `CMD` uses `${PORT:-8080}` for Cloud Run. **README.md** documents local run, env vars, curls, and `gcloud run deploy` with `--add-cloudsql-instances` and env vars.

**Tests:** `pytest tests/` (embedding helpers + mock nearest-neighbor).
