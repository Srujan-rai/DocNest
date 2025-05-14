# ---- Base image ----
FROM python:3.11-slim

# ---- System dependencies ----
RUN apt-get update && apt-get install -y \
    curl \
    unzip \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

# ---- Set work directory ----
WORKDIR /app

# ---- Copy app and requirements ----
COPY backend/pyproject.toml backend/requirements.txt ./
COPY backend/prisma ./prisma
COPY backend .

# ---- Install Python dependencies ----
RUN pip install --upgrade pip \
    && pip install -r requirements.txt

# ---- Fetch Prisma binary for Python client ----
RUN prisma py fetch

# ---- Generate Prisma client and push schema (optional, can also be runtime step) ----
RUN prisma generate && prisma db push

# ---- Expose and run FastAPI ----
EXPOSE 8000
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
