# Grabpic API

**Important Note:** For best results and compatibility with dlib, please upload images in **JPEG/RGB** format.

Set **`BASE_URL`** to your deployed origin (Cloud Run service URL) or `http://127.0.0.1:8000` locally. Full URLs below are **`{BASE_URL}` + path** (paste your host in place of `{BASE_URL}`).

**Interactive API docs:** `{BASE_URL}/docs` (Swagger UI), `{BASE_URL}/redoc` (ReDoc).

---

### Root

- **Link:** `{BASE_URL}/`
- **Method:** `GET`

Returns JSON with the service name and hints to the OpenAPI UIs (`/docs`, `/redoc`).  
Use it to confirm the service is up and to discover documentation links.

---

### Health

- **Link:** `{BASE_URL}/health`
- **Method:** `GET`

Liveness endpoint; returns `{"status":"ok"}` for probes and health checks.  
Suitable for Cloud Run / load balancer health configuration, not for app authentication.

---

### Start crawl

- **Link:** `{BASE_URL}/crawl`
- **Method:** `POST`

Queues ingestion of images from the configured GCS bucket: face detection, `grab_id` assignment, and DB writes.  
Responds with `202 Accepted` and a `job_id`; use the status endpoint to track progress.

---

### Crawl job status

- **Link:** `{BASE_URL}/crawl/status/{job_id}`
- **Method:** `GET`

Returns one crawl job row: `status`, `total_images`, `processed`, `faces_found`, `identities_created`, timestamps, and `error` if any.  
Poll every 2–3 seconds while the job is `pending` or `processing`.

---

### Selfie authentication

- **Link:** `{BASE_URL}/auth/selfie`
- **Method:** `POST` (`multipart/form-data`, field `file`: single-face image)

Compares the uploaded face to indexed identities and returns `grab_id`, `distance`, and `match` when within the configured threshold.  
Returns `400` if no face or multiple faces, `404` if nothing has been indexed yet, `401` if the nearest face is beyond the threshold.

---

### User images

- **Link:** `{BASE_URL}/users/{grab_id}/images`
- **Method:** `GET`

Returns signed HTTPS URLs (or `gs://` fallbacks) for all images associated with that `grab_id`.  
Call after a successful selfie match to build a per-user photo gallery.
