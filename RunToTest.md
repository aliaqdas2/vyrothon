# Grabpic — judge test sheet (copy-paste)

<p><strong style="color:#c62828;">Important Note:</strong> <strong style="color:#c62828;">For best results and compatibility with dlib, please upload images in JPEG/RGB format.</strong></p>

> **For hackathon judges:** you **do not need Google Cloud Console, `gcloud`, or `gsutil`**. Add photos through the API only: open **[Swagger UI](https://grabpic-api-357617293030.us-central1.run.app/docs)** and use **Try it out** on **`POST /upload`**, then **`POST /crawl`**, **`POST /auth/selfie`**, **`GET /users/{grab_id}/images`**. Optional: the **`curl`** commands below match that same flow.

**Primary link (upload and test in the browser):**  
**[https://grabpic-api-357617293030.us-central1.run.app/docs](https://grabpic-api-357617293030.us-central1.run.app/docs)**

Host for **`curl`** (no trailing slash on the host):

**`https://grabpic-api-357617293030.us-central1.run.app`**

Replace local file paths and IDs (`JOB_ID_HERE`, `GRAB_ID_HERE`) where noted.

---

## Prerequisites (for judges)

- The deployed service is configured by the team (**`DATABASE_URL`**, **`GCS_BUCKET`**, etc.). You only call the HTTP API.
- For **`POST /auth/selfie`**, have a **local face photo** (e.g. `./selfie.jpg`) if you use **`curl`**, or choose a file in Swagger.

---

## 1) Health

```bash
curl -s "https://grabpic-api-357617293030.us-central1.run.app/health"
```

Expect: `{"status":"ok"}`  
(In Swagger: **`GET /health`**.)

---

## 2) Upload test images (required before crawl)

**Use Swagger (recommended):** **[https://grabpic-api-357617293030.us-central1.run.app/docs](https://grabpic-api-357617293030.us-central1.run.app/docs)** → **`POST /upload`** → **Try it out** → choose a file (≤ 10 MiB; `.jpg`, `.jpeg`, `.png`, `.webp`). Repeat for multiple photos.

This stores images **through the API** (default prefix `judge-uploads/`). You never log into GCP.

**Optional `curl`:**

```bash
curl -s -X POST "https://grabpic-api-357617293030.us-central1.run.app/upload" \
  -F "file=@./photo1.jpg"
```

Response includes **`gcs_uri`** and **`blob_name`**.

---

## 3) Start indexing (“crawl”)

Swagger: **`POST /crawl`** → **Try it out**.

```bash
curl -s -X POST "https://grabpic-api-357617293030.us-central1.run.app/crawl"
```

Copy **`job_id`** from the JSON.

---

## 4) Poll crawl status

Replace `JOB_ID_HERE`:

```bash
curl -s "https://grabpic-api-357617293030.us-central1.run.app/crawl/status/JOB_ID_HERE"
```

Poll until **`status`** is **`done`** (or **`error`**).

---

## 5) Selfie authentication (“Selfie-as-a-Key”)

Swagger: **`POST /auth/selfie`** → attach one **single-face** image.

```bash
curl -s -X POST "https://grabpic-api-357617293030.us-central1.run.app/auth/selfie" \
  -F "file=@./selfie.jpg"
```

Copy **`grab_id`** from the response.

---

## 6) List that user’s images

Replace `GRAB_ID_HERE`:

```bash
curl -s "https://grabpic-api-357617293030.us-central1.run.app/users/GRAB_ID_HERE/images"
```

Open the **HTTPS URLs** in a browser (they expire after the configured TTL).

---

## Troubleshooting (judges)

| Issue | What to check |
|-------|----------------|
| **`404`** on `/auth/selfie` (“No indexed identities”) | Run **`POST /upload`** in **[Swagger](https://grabpic-api-357617293030.us-central1.run.app/docs)**, then **`POST /crawl`** until the job is **`done`**. |
| **`401`** on `/auth/selfie` | Try another selfie (lighting/angle); ask the team about **`FACE_DIST_THRESHOLD`**. |
| **`503`** on `/upload` | **`GCS_BUCKET`** not set on the service (team configuration). |
| **Upload / crawl errors** | Deployment / service-account issue — ask the team (outside judge testing). |
| **Connection failed** | Typo in the URL above. |

---

## Security note

**`POST /upload`** is open on **`--allow-unauthenticated`** deployments: anyone could push objects into the bucket prefix. Intended for **judging and demos**; production should use IAM, API keys, or IAP.
