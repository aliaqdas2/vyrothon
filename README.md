# Grabpic

**Intelligent Identity & Retrieval Engine** — indexes event photos from **Google Cloud Storage**, detects faces with **face_recognition** / **dlib**, stores a stable **`grab_id`** per person in **PostgreSQL** + **pgvector**, lets users prove identity with a **selfie** (“Selfie-as-a-Key”), and returns **signed URLs** to their photos.

---

## How it works (end-to-end)

1. **Upload images to Google Cloud Storage** — The API does not accept a bulk upload of marathon photos. You (or your pipeline) place **JPEG / PNG / WebP** files in a **GCS bucket** (any prefix/folder structure is fine).
2. **Configure the app** with that bucket name (`GCS_BUCKET`) and a **Postgres** URL (`DATABASE_URL`).
3. **Run the API** and call **`POST /crawl`** — it lists objects in the bucket, downloads each image, detects faces, assigns or merges **`grab_id`** values, and saves rows in the database.
4. **User takes a selfie** — **`POST /auth/selfie`** compares the face to indexed identities and returns a **`grab_id`** when the match is within the distance threshold.
5. **Fetch their photos** — **`GET /users/{grab_id}/images`** returns time-limited **HTTPS URLs** (signed) for each object that contains that person.

---

## Google Cloud prerequisites

| Piece | Why |
|-------|-----|
| **GCS bucket** | Stores the raw event images. The app reads from it during `/crawl` and signs URLs for `/users/.../images`. |
| **Cloud SQL for PostgreSQL** (or any Postgres **15+** with **pgvector**) | Stores `grab_id`, embeddings, crawl jobs, and image metadata. |
| **Service account (Cloud Run)** | Needs **Cloud SQL Client** (if using Cloud SQL connector), **Storage Object Viewer** on the bucket, and permission to **sign URLs** (typically **Storage Admin** on the bucket or a role that allows `signBlob` / V4 signed URLs for that bucket). |

**Uploading photos to GCS** (pick one):

- **Console:** [Cloud Storage](https://console.cloud.google.com/storage) → your bucket → **Upload** or create folders and upload files.
- **CLI:** [Install `gcloud` and `gsutil`](https://cloud.google.com/sdk/docs/install), then e.g.  
  `gsutil -m cp -r ./local-photos-folder/* gs://YOUR_BUCKET_NAME/event-2026/`
- **Any workflow** that puts objects whose names end in `.jpg`, `.jpeg`, `.png`, or `.webp` (case-insensitive) in the bucket.

**Postgres:** Create a database and user. Enable the **`vector`** extension once (Cloud SQL: use `database_flags` or run `CREATE EXTENSION vector` as a superuser / via console). The app also runs `CREATE EXTENSION IF NOT EXISTS vector` on startup when it can connect.

---

## Local development prerequisites

- **Python 3.10+** (3.10 matches the **Dockerfile** base image).
- **PostgreSQL** reachable from your machine, with **pgvector** installed.
- **Google Application Default Credentials** with access to the GCS bucket — e.g.  
  `gcloud auth application-default login`  
  or a service account JSON and `GOOGLE_APPLICATION_CREDENTIALS=/path/to/key.json`.
- **Environment file** — copy `.env.example` to **`.env`** in the project root (same directory as `main.py`).

---

## Install and run (local)

From the project root (this repository):

```bash
python3 -m venv .venv
source .venv/bin/activate          # Windows: .venv\Scripts\activate
pip install --upgrade pip
pip install -r requirements.txt
cp .env.example .env               # then edit .env — see table below
```

**Important:** `face_recognition` depends on **`pkg_resources`** from **setuptools**. This repo pins **`setuptools>=70,<81`** because setuptools **82+** removed `pkg_resources`, which breaks `face_recognition_models`. If you see `No module named 'pkg_resources'`, run:

```bash
pip install 'setuptools>=70,<81'
```

Start the API:

```bash
uvicorn main:app --reload --host 0.0.0.0 --port 8000
```

If you see **“address already in use”**, another process is using that port — choose another (e.g. `--port 8001`) and use the same port in the URLs below.

- **Swagger UI:** http://127.0.0.1:8000/docs  
- **ReDoc:** http://127.0.0.1:8000/redoc  
- **Health:** http://127.0.0.1:8000/health  

On first successful startup, the app connects to Postgres and **creates tables** (`CREATE EXTENSION vector` + SQLAlchemy `create_all`). You do **not** need to create tables manually if the DB user is allowed to create extensions/objects.

---

## Environment variables

Create **`.env`** in the project root (loaded automatically by `app/config.py`). On **Cloud Run**, set the same names under **Variables and secrets**.

| Variable | Required | Description |
|----------|----------|-------------|
| `DATABASE_URL` | **Yes** | SQLAlchemy URL, e.g. `postgresql+psycopg2://USER:PASS@HOST:5432/DBNAME`. For Cloud Run + Cloud SQL unix socket, see [Deploy on Cloud Run](#deploy-on-google-cloud-run) below. |
| `GCS_BUCKET` | **Yes** for `/crawl` | **Bucket name only** (e.g. `my-event-photos`). No `gs://` prefix. All crawlable images must already be **uploaded to this bucket** in GCS. |
| `FACE_DIST_THRESHOLD` | No | L2 distance threshold for matching / merging faces (default **0.6**). |
| `SIGNED_URL_TTL_SECONDS` | No | Lifetime in seconds for signed GET URLs from `/users/{grab_id}/images` (default **900** = 15 minutes). |

---

## Typical API flow (curl)

Replace `http://127.0.0.1:8000` with your base URL if different.

**1. Ingest bucket images (after files are in GCS and `GCS_BUCKET` is set)**

```bash
curl -s -X POST http://127.0.0.1:8000/crawl
```

Response includes a **`job_id`**.

**2. Poll crawl status**

```bash
curl -s http://127.0.0.1:8000/crawl/status/JOB_ID_HERE
```

Repeat every few seconds until `status` is `done` or `error`.

**3. Selfie authentication** (single face in the image)

```bash
curl -s -X POST http://127.0.0.1:8000/auth/selfie \
  -F "file=@/path/to/your/selfie.jpg"
```

**4. List that user’s images** (use `grab_id` from step 3)

```bash
curl -s http://127.0.0.1:8000/users/GRAB_ID_UUID_HERE/images
```

If signed URL generation fails (e.g. local credentials), the response may fall back to raw `gs://` URIs for debugging.

---

## Docker (local container)

```bash
docker build -t grabpic .
docker run --rm -p 8080:8080 \
  -e DATABASE_URL="postgresql+psycopg2://USER:PASS@host.docker.internal:5432/grabpic" \
  -e GCS_BUCKET="your-bucket-name" \
  -v "$HOME/.config/gcloud:/root/.config/gcloud:ro" \
  grabpic
```

Adjust `host.docker.internal` only if Postgres runs on your Mac/Windows host. On Linux you may need `--add-host=host.docker.internal:host-gateway`. The **GCS bucket** must still contain your images; credentials must allow the container to read the bucket.

Cloud Run’s **`PORT`** is respected: the image runs Uvicorn on **`${PORT:-8080}`**.

---

## Deploy on Google Cloud Run

1. **Cloud SQL:** Postgres instance with **pgvector**; database and user created.
2. **GCS:** Bucket with images uploaded; note the **bucket name**.
3. **Deploy** (replace placeholders; use your service name and region):

```bash
gcloud run deploy grabpic-api \
  --source . \
  --region us-central1 \
  --allow-unauthenticated \
  --add-cloudsql-instances PROJECT_ID:REGION:INSTANCE_NAME \
  --set-env-vars "DATABASE_URL=postgresql+psycopg2://DB_USER:DB_PASS@/DB_NAME?host=/cloudsql/PROJECT_ID:REGION:INSTANCE_NAME,GCS_BUCKET=your-bucket-name"
```

- **`DATABASE_URL`** must use the **Cloud SQL Auth Proxy socket** path `/cloudsql/PROJECT:REGION:INSTANCE` as in the [Cloud Run + Cloud SQL docs](https://cloud.google.com/sql/docs/postgres/connect-run).
- Grant the **Cloud Run service account** **Cloud SQL Client** and appropriate **Storage** roles on the bucket.

After deploy, open **`https://YOUR-SERVICE-URL.run.app/docs`** to try the API.

---

## Data model (summary)

| Table | Role |
|-------|------|
| `crawl_jobs` | Background crawl progress and error message. |
| `images` | One row per `gs://bucket/object` processed. |
| `identities` | `grab_id`, 128-D **centroid** (pgvector), `face_count`. |
| `image_faces` | Links an image to many `grab_id`s (multi-face photos). |

---

## Tests

```bash
pytest tests/ -q
```

---

## Troubleshooting

| Symptom | What to do |
|---------|------------|
| `No module named 'pkg_resources'` | `pip install 'setuptools>=70,<81'` (see [Install and run](#install-and-run-local)). |
| Port already in use | Use `--port 8001` (or free port) for Uvicorn. |
| Crawl does nothing / errors on GCS | Set **`GCS_BUCKET`**, ensure ADC or workload identity can **list and read** objects, and that **images are uploaded** to that bucket. |
| `/auth/selfie` returns 404 “No indexed identities” | Run **`POST /crawl`** successfully first. |
| DB connection fails on Cloud Run | Check **`DATABASE_URL`**, **`--add-cloudsql-instances`**, and IAM **Cloud SQL Client**. |

---

## License

Hackathon / demo — adjust as needed for your project.
