FROM python:3.10-slim as builder
RUN apt-get update && apt-get install -y cmake build-essential && rm -rf /var/lib/apt/lists/*
RUN pip install --user dlib==19.24.1 face_recognition

FROM python:3.10-slim
RUN apt-get update && apt-get install -y libgl1 libglib2.0-0 && rm -rf /var/lib/apt/lists/*
WORKDIR /app
COPY --from=builder /root/.local /root/.local
ENV PATH=/root/.local/bin:$PATH
COPY requirements.txt .
# requirements.txt pins setuptools<81 so face_recognition_models can import pkg_resources
RUN pip install --no-cache-dir -r requirements.txt
COPY . .
EXPOSE 8080
ENV PORT=8080
CMD ["sh", "-c", "uvicorn main:app --host 0.0.0.0 --port ${PORT:-8080}"]