# Grabpic

**This README is for hackathon judges** — to **test** the live API and **understand** how the system works (upload via **`POST /upload`**, face indexing, selfie-as-a-key, per-user photo retrieval). **No Google Cloud account is required:** use **[Swagger](https://grabpic-api-357617293030.us-central1.run.app/docs)**. Terminal commands are optional.

**Quick start:** Use **[Swagger UI](https://grabpic-api-357617293030.us-central1.run.app/docs)** (`/docs`) to upload and test: **Try it out** on **`POST /upload`** (add test images to the bucket), then **`POST /crawl`**, **`POST /auth/selfie`**, and **`GET /users/{grab_id}/images`** — full flow without terminal commands.

## Live deployment (start here)

| | URL |
|---|-----|
| **API (root)** | https://grabpic-api-357617293030.us-central1.run.app/ |
| **Swagger UI** (try every endpoint) | https://grabpic-api-357617293030.us-central1.run.app/docs |
| **ReDoc** (reference-style API docs) | https://grabpic-api-357617293030.us-central1.run.app/redoc |

**Pro-tip:** If **`/docs` (Swagger UI)** loads, **the service** is **100% “Gold.”** **All** HTTP endpoints can be exercised from that page — **no terminal commands** required. Use **Try it out** on each operation. **ReDoc** (`/redoc`) documents the same API in a long-form reference layout.

---

**Grabpic** is aimed at large events (marathons, concerts, etc.) where photographers upload thousands of photos. It **finds faces in those photos**, assigns each distinct person a stable ID called **`grab_id`**, and supports **selfie-as-a-key** so a participant can retrieve **only their own** photos—without manual tagging.

**The API does not store the raw photo archive in-process.** Behind the scenes, objects live in **Google Cloud Storage**; Grabpic reads them during indexing and returns **time-limited HTTPS links** for galleries. **Judges do not need a Google Cloud login** — use the **`POST /upload`** endpoint (see below) so files reach storage through the API.

### For hackathon judges

**Quick checklist:**

1. Open **[Swagger UI](https://grabpic-api-357617293030.us-central1.run.app/docs)** — use **Try it out** on **`POST /upload`** to add test images (`.jpg`, `.jpeg`, `.png`, `.webp`), then **`POST /crawl`**, **`POST /auth/selfie`**, **`GET /users/{grab_id}/images`**.
2. Optional: **[RunToTest.md](RunToTest.md)** has the same flow as **`curl`** if you prefer the terminal.
3. Deeper sections below cover **operators** (local runs, env vars, deployment). Judges can ignore GCP Console / `gcloud` / `gsutil`.

---

## Using Grabpic

### Judge flow (no GCP access required)

Work entirely in the browser at **[https://grabpic-api-357617293030.us-central1.run.app/docs](https://grabpic-api-357617293030.us-central1.run.app/docs)**:

1. **`GET /health`** — confirm the service is up.
2. **`POST /upload`** — upload one or more event photos (stored by the API; default prefix `judge-uploads/`).
3. **`POST /crawl`** — start indexing; note **`job_id`**, then **`GET /crawl/status/{job_id}`** until **`status`** is **`done`**.
4. **`POST /auth/selfie`** — upload a single-face selfie; copy **`grab_id`** from the response.
5. **`GET /users/{grab_id}/images`** — open the signed URLs in the response.

For a **local** deployment, use **`http://127.0.0.1:8000/docs`** after starting the server.

### Before you begin (operators / local development)

1. **Indexed photos** — For production-scale ingestion, operators may bulk-upload to the bucket with **`gsutil`** or the GCS Console; **judges should use only `POST /upload` via Swagger** (above). Supported formats: `.jpg`, `.jpeg`, `.png`, `.webp`.
2. **PostgreSQL** — With the **pgvector** extension. The app creates tables on first startup.
3. **Configuration** — Set **`DATABASE_URL`** and **`GCS_BUCKET`** in **`.env`** locally or in **Cloud Run** env vars.

---

### Step 1 — Configure the app (local or deployment)

In the project folder, copy the example env file and edit it:

```bash
cp .env.example .env
```

Set at least:

- **`DATABASE_URL`** — How the app connects to Postgres (user, password, host, database name).
- **`GCS_BUCKET`** — The **bucket name only** (no `gs://` prefix).

Save the file. The app loads **`.env`** automatically when you run it locally.

---

### Step 2 — Run the API (local development)

Install dependencies and start the server (see [Install and run locally](#install-and-run-locally) for full commands). Then open:

- **Swagger:** http://127.0.0.1:8000/docs — use **`POST /upload`** here to add images (same as the deployed judge flow).
- **Health:** http://127.0.0.1:8000/health — should show `{"status":"ok"}`

If the server won’t start, check [Troubleshooting](#troubleshooting).

---

### Step 3 — Index faces (“crawl”) — curl examples for localhost

**Judges** should use **[Swagger](https://grabpic-api-357617293030.us-central1.run.app/docs)** for crawl/selfie/gallery. The commands below are for **local** testing after `uvicorn` is running.

This step **downloads each image from GCS**, detects faces, and stores **`grab_id`** and embeddings in the database. It can take a while for many photos.

**Start a crawl** (returns a `job_id`):

```bash
curl -s -X POST http://127.0.0.1:8000/crawl
```

**Check progress** until `status` is `done` (poll every few seconds):

```bash
curl -s http://127.0.0.1:8000/crawl/status/YOUR_JOB_ID
```

You must complete this successfully before selfie login will work.

---

### Step 4 — Log in with a selfie

A user sends **one clear photo of their face** (single person). The API finds the closest matching **`grab_id`** from the indexed faces.

```bash
curl -s -X POST http://127.0.0.1:8000/auth/selfie \
  -F "file=@/path/to/selfie.jpg"
```

If the face matches an indexed identity (within the configured distance threshold), the response includes a **`grab_id`** (UUID). Otherwise the API may return **`401`** with details.

---

### Step 5 — Get that person’s photos

Use the **`grab_id`** from the previous step:

```bash
curl -s http://127.0.0.1:8000/users/YOUR_GRAB_ID/images
```

The response lists **temporary HTTPS URLs** (or `gs://` fallbacks if signing isn’t available). Open those links in a browser to download or display the images that contain that person.

---

### What you should understand

| Concept | Meaning |
|--------|---------|
| **`grab_id`** | Internal ID for one identity (one face cluster). Same person across many photos should map to one `grab_id` after indexing. |
| **Crawl** | One-off or repeated job that reads **everything** in **`GCS_BUCKET`** and updates the database. Skips images already processed. |
| **Selfie auth** | Compares one face to **indexed** identities. Run **crawl** first. |

---

## Install and run locally

Prerequisites: **Python 3.10+**, **Postgres with pgvector**, and **Google credentials** that can read the configured GCS bucket (`gcloud auth application-default login` or a service account key via `GOOGLE_APPLICATION_CREDENTIALS`).

```bash
python3 -m venv .venv
source .venv/bin/activate          # Windows: .venv\Scripts\activate
pip install --upgrade pip
pip install -r requirements.txt
cp .env.example .env               # edit DATABASE_URL and GCS_BUCKET
```

If you see **`No module named 'pkg_resources'`**, run:

```bash
pip install 'setuptools>=70,<81'
```

Start the server:

```bash
uvicorn main:app --reload --host 0.0.0.0 --port 8000
```

If port **8000** is busy, use another port (e.g. `8001`) and change the URLs in the steps above.

On first startup, the app **creates database tables** if the database role may run `CREATE EXTENSION vector` and create tables.

---

## Environment variables

| Variable | Required | Description |
|----------|----------|-------------|
| `DATABASE_URL` | Yes | Postgres URL, e.g. `postgresql+psycopg2://USER:PASS@HOST:5432/DBNAME` |
| `GCS_BUCKET` | Yes for indexing | Bucket name only (e.g. `my-photos`). **Judges** add images only via **`POST /upload`** in **[Swagger](https://grabpic-api-357617293030.us-central1.run.app/docs)**; operators may bulk-load the bucket separately. |
| `GCS_UPLOAD_PREFIX` | No | Object prefix for **`POST /upload`** (default **`judge-uploads`**). |
| `MAX_UPLOAD_BYTES` | No | Max size for **`POST /upload`** (default **10485760** = 10 MiB). |
| `FACE_DIST_THRESHOLD` | No | Face match sensitivity (default **0.6**). |
| `SIGNED_URL_TTL_SECONDS` | No | How long gallery links stay valid (default **900** seconds). |

On **Cloud Run**, set these under **Variables and secrets** instead of `.env`.

**`POST /upload`** is how **judges** (and demos) send images: the API writes them to the team’s bucket — **no Google Cloud login or Console**. The Cloud Run service account must allow **`storage.objects.create`**. On a public unauthenticated service, anyone can upload—acceptable for hackathon judging; lock down for production.

**Judges:** **[RunToTest.md](RunToTest.md)** mirrors the same steps with **`curl`**; **[Swagger](https://grabpic-api-357617293030.us-central1.run.app/docs)** is preferred if you avoid the terminal.

---

## Google Cloud setup (reference — operators)

Judges **do not** need to configure GCP; they only use **[Swagger](https://grabpic-api-357617293030.us-central1.run.app/docs)**. This table is for teams deploying the service.

| Piece | Role |
|-------|------|
| **GCS bucket** | Backend object store; **`POST /upload`** writes here for judges; bulk tools (`gsutil`, Console) are optional for operators. |
| **Postgres + pgvector** | Stores identities, embeddings, and which image contains which face. |
| **Service account (when deployed)** | Typically needs **Cloud SQL Client**, **Storage** access to the bucket, and ability to **sign URLs** for that bucket. |

---

## Docker

```bash
docker build -t grabpic .
docker run --rm -p 8080:8080 \
  -e DATABASE_URL="postgresql+psycopg2://USER:PASS@host.docker.internal:5432/grabpic" \
  -e GCS_BUCKET="your-bucket-name" \
  -v "$HOME/.config/gcloud:/root/.config/gcloud:ro" \
  grabpic
```

On Linux you may need `--add-host=host.docker.internal:host-gateway` to reach Postgres on the host. The image listens on **`PORT`** (default **8080**), as Cloud Run expects.

---

## Deploy on Google Cloud Run

1. **Cloud SQL** with **pgvector** and a database user.  
2. **GCS bucket** created; note the bucket **name** (judges can seed images later via **`POST /upload`** in Swagger).  
3. Deploy (replace placeholders):

```bash
gcloud run deploy grabpic-api \
  --source . \
  --region us-central1 \
  --allow-unauthenticated \
  --add-cloudsql-instances PROJECT_ID:REGION:INSTANCE_NAME \
  --set-env-vars "DATABASE_URL=postgresql+psycopg2://DB_USER:DB_PASS@/DB_NAME?host=/cloudsql/PROJECT_ID:REGION:INSTANCE_NAME,GCS_BUCKET=your-bucket-name"
```

Use the [Cloud SQL + Cloud Run connection string format](https://cloud.google.com/sql/docs/postgres/connect-run). Then open **`https://YOUR-SERVICE-URL.run.app/docs`** and follow [Using Grabpic](#using-grabpic) with that base URL instead of `localhost`.

---

## Data model (summary)

| Table | Role |
|-------|------|
| `crawl_jobs` | Crawl progress and errors. |
| `images` | One row per object in GCS that was processed. |
| `identities` | Each **`grab_id`** and a face **centroid** (vector). |
| `image_faces` | Links an image to one or more **`grab_id`**s (multi-face photos). |

---

## Tests

**For judges:** use **[Swagger](https://grabpic-api-357617293030.us-central1.run.app/docs)** first; **[RunToTest.md](RunToTest.md)** is the same flow with **`curl`** (no GCP access needed).

**For developers** (unit tests in this repository):

```bash
pytest tests/ -q
```

---

## Troubleshooting

| Symptom | What to do |
|---------|------------|
| `No module named 'pkg_resources'` | `pip install 'setuptools>=70,<81'` |
| Port already in use | Change `--port` for Uvicorn |
| Crawl fails or sees no images | Call **`POST /upload`** in **[Swagger](https://grabpic-api-357617293030.us-central1.run.app/docs)** first, then **`POST /crawl`**; ensure **`GCS_BUCKET`** is set on the service |
| `/auth/selfie` says no indexed identities | Finish **`POST /crawl`** successfully first |
| Cloud Run can’t reach the database | Check **`DATABASE_URL`**, **`--add-cloudsql-instances`**, and IAM **Cloud SQL Client** |

---

## License

Hackathon / demo — adjust as needed for downstream use.
