# 🛡️ VoxGuard / EchoGuard AI — Enterprise Voice Security Platform

> **Real-Time Multi-Modal Voice Trust, Deepfake Detection & Identity Threat Defense Engine (AMVTF v2.4)**

[![Python 3.11+](https://img.shields.io/badge/Python-3.11+-blue.svg)](https://python.org)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.115+-009688.svg)](https://fastapi.tiangolo.com)
[![Next.js 16](https://img.shields.io/badge/Next.js-16-black.svg)](https://nextjs.org)
[![PostgreSQL](https://img.shields.io/badge/Database-PostgreSQL%20%7C%20SQLite-336791.svg)](https://www.postgresql.org)
[![License: Enterprise](https://img.shields.io/badge/License-Enterprise-red.svg)](#)

---

## 📋 Table of Contents
1. [Architecture Overview](#-architecture-overview)
2. [Security & Zero Data-Leak Guarantee](#-security--zero-data-leak-guarantee)
3. [Cloud Database Setup (Neon / Supabase / Render)](#-cloud-database-setup)
4. [Local Development](#-local-development)
5. [Production Cloud Deployment](#-production-cloud-deployment)
   - [Backend Deployment (Render / Railway)](#backend-deployment)
   - [Frontend Deployment (Vercel)](#frontend-deployment)
6. [API Endpoints](#-api-endpoints)

---

## 🏗️ Architecture Overview

VoxGuard is designed with a decoupled, high-performance architecture:
- **Detection Core (AMVTF v2.4)**: Real-time Audio Multi-Vector Threat Filtering combining AASIST GNN spoof detection, ECAPA-TDNN speaker verification, and contextual NLP threat analysis.
- **Backend API**: High-throughput FastAPI service with WebSocket audio streaming and dual-engine persistence (Cloud PostgreSQL / Local SQLite fallback).
- **Web Console (EchoGuard)**: Next.js 16 SOC Dashboard with real-time spectrum visualizers, call interception telemetry, and biometrics management.

---

## 🔒 Security & Zero Data-Leak Guarantee

This repository enforces strict enterprise security policies:
- **No Operational Database Leaks**: Operational `.db` files, session tokens, and password hashes are strictly ignored by `.gitignore` and never committed.
- **No Secret/Credential Leaks**: All credentials must be passed via environment variables. `.env*` files are ignored; refer to `.env.example`.
- **No Large Training Data Bloat**: Multi-gigabyte training audio sets (`training_data/`) and Windows runtime binaries (`python-runtime/`) are excluded from version control.
- **Git LFS for ML Weights**: Machine learning weights (`*.joblib`) are managed securely via Git Large File Storage (Git LFS).

---

## 🗄️ Cloud Database Setup

VoxGuard features a **Dual-Mode Hybrid Engine** in `backend/database.py`. It runs seamlessly on:
- **Local SQLite** (default when `DATABASE_URL` is omitted)
- **Cloud PostgreSQL** (automatically enabled when `DATABASE_URL` is provided)

### Recommended Free Cloud PostgreSQL Providers:
1. **Neon Serverless Postgres** (Recommended):
   - Create a free project at [neon.tech](https://neon.tech).
   - Copy the connection string:
     ```env
     DATABASE_URL=postgresql://neondb_owner:password@ep-sample.us-east-2.aws.neon.tech/neondb?sslmode=require
     ```
2. **Supabase**:
   - Create a project at [supabase.com](https://supabase.com).
   - In Settings > Database > Connection String (URI), copy the connection pooler or direct URI.
3. **Render PostgreSQL**:
   - Create a new PostgreSQL instance on [render.com](https://render.com).
   - Copy the "External Database URL".

*Tables, indexes, and default administrator profiles will be created automatically on the first server launch.*

---

## 💻 Local Development

### 1. Prerequisites
- Python 3.11+
- Node.js 18+ & npm
- Git & Git LFS (`git lfs install`)

### 2. Start Both Services (Windows Quick Launch)
Simply run the included launcher:
```bat
run_project.bat
```

Or run manually:
```bash
# Terminal 1 - Backend
cd backend
pip install -r requirements.txt
uvicorn main:app --host 127.0.0.1 --port 8000 --reload

# Terminal 2 - Frontend
cd echoguard
npm install
npm run dev
```

Visit:
- **Dashboard**: [http://localhost:3000](http://localhost:3000)
- **Interactive Swagger Docs**: [http://127.0.0.1:8000/docs](http://127.0.0.1:8000/docs)

---

## 🚀 Production Cloud Deployment

### Backend Deployment (Render)
1. Push this repository to GitHub.
2. Log in to [Render](https://render.com) and click **New + > Web Service**.
3. Select your GitHub repository.
4. Set:
   - **Root Directory**: `backend`
   - **Environment**: `Python 3`
   - **Build Command**: `pip install -r requirements.txt`
   - **Start Command**: `uvicorn main:app --host 0.0.0.0 --port $PORT`
5. Under **Environment Variables**, add:
   - `DATABASE_URL`: `your_cloud_postgres_connection_string`
   - `SECRET_KEY`: `random_64_character_hex_key`
   - `ALLOWED_ORIGINS`: `https://your-frontend.vercel.app`
6. Click **Deploy**. Note your backend URL (e.g., `https://voxguard-backend.onrender.com`).

### Frontend Deployment (Vercel)
1. Log in to [Vercel](https://vercel.com) and click **Add New > Project**.
2. Select your GitHub repository and set the **Root Directory** to `echoguard`.
3. Under **Environment Variables**, add:
   - `NEXT_PUBLIC_API_URL`: `https://voxguard-backend.onrender.com`
4. Click **Deploy**. Your dashboard is now live globally!

---

## 📡 API Endpoints

| Method | Endpoint | Description |
| :--- | :--- | :--- |
| `GET` | `/api/health` | System status & AI model readiness |
| `POST` | `/api/analyze/voice` | Multi-vector voice authenticity scoring |
| `GET` | `/api/calls` | Telemetry & call interception log |
| `GET` | `/api/identities` | Biometric voice enrollment directory |
| `POST` | `/api/auth/login` | SOC operator authentication |
| `GET` | `/api/keys` | Token & API key billing management |
| `GET` | `/docs` | OpenAPI / Swagger interactive documentation |
