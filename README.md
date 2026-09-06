---
title: AI Data Science & AutoML Platform
emoji: 🚀
colorFrom: indigo
colorTo: blue
sdk: gradio
sdk_version: 4.44.0
app_file: server.py
pinned: false
---

# AI-Powered Data Science Platform (Phase 0 Foundation)


Welcome to Phase 0 of the **AI-Powered Data Science Platform**. This project establishes a modular, production-oriented foundation designed for future scaling into an autonomous data science assistant.

> [!IMPORTANT]
> **Phase 0 Scope**: This release contains ONLY the core application architecture, REST API, database layer, dataset file upload service, job execution abstraction, React frontend UI, and Docker containerization. All AI/ML engines, AutoML pipelines, agent orchestration, and automated EDA are intentionally deferred to future phases.

---

## Architecture Overview

```
                      +-----------------------------+
                      | React 18 + TypeScript + Vite |
                      |    Tailwind CSS Frontend    |
                      +--------------+--------------+
                                     |
                             HTTP REST API (/api/v1)
                                     |
                      +--------------v--------------+
                      |    Python 3.11 FastAPI      |
                      |     Uvicorn REST Engine     |
                      +-------+-------------+-------+
                              |             |
        SQLAlchemy ORM + Alembic            Local Storage Handler
                              |             |
                      +-------v-------+  +--v---------------------+
                      |  PostgreSQL   |  | data/                  |
                      |   Database    |  |  ├── uploads/          |
                      +---------------+  |  ├── processed/        |
                                         |  └── results/          |
                                         | models/                |
                                         |  └── saved/            |
                                         +------------------------+
```

---

## Technology Stack

- **Frontend**: React 18, TypeScript, Vite, Tailwind CSS, React Router, Axios, Lucide React.
- **Backend**: Python 3.11+, FastAPI, Uvicorn, Pydantic V2, Pydantic Settings, SQLAlchemy 2.0, PostgreSQL (with SQLite fallback option), Alembic migrations.
- **ML Engine Baseline**: pandas, numpy, scikit-learn (environments initialized for Phase 1+).
- **Containerization**: Docker, Docker Compose, Nginx.
- **Testing**: Pytest, FastAPI TestClient (`httpx`).

---

## Project Folder Structure

```
My Projects/
├── frontend/
│   ├── src/
│   │   ├── components/      # Reusable UI components (UploadZone, DatasetList, JobStatusBadge, ConfirmModal, etc.)
│   │   ├── pages/           # Pages (Dashboard, Datasets, DatasetDetails, Jobs, Settings)
│   │   ├── layouts/         # MainLayout with Sidebar & Header
│   │   ├── services/        # Axios API client (/api/v1)
│   │   ├── hooks/           # Custom React hooks (useDatasets, useJobs)
│   │   ├── types/           # TypeScript interfaces (dataset, job, api)
│   │   ├── utils/           # Formatters for file sizes & dates
│   │   ├── App.tsx          # Application router
│   │   └── main.tsx         # React root entry point
│   ├── package.json
│   ├── tsconfig.json
│   └── vite.config.ts
│
├── backend/
│   ├── app/
│   │   ├── api/
│   │   │   ├── routes/      # REST API route handlers (health, datasets, jobs)
│   │   │   └── router.py    # Master v1 API router
│   │   ├── core/            # App configuration & structured logging
│   │   ├── db/              # SQLAlchemy database setup, models, and Alembic migrations
│   │   ├── schemas/         # Pydantic request/response validation schemas
│   │   ├── services/        # Business logic for dataset storage & job management
│   │   ├── jobs/            # Background worker abstraction for job execution
│   │   └── main.py          # FastAPI application entrypoint
│   ├── alembic.ini
│   ├── requirements.txt
│   └── pytest.ini
│
├── ml_engine/              # Modular ML engine package structure (placeholders for Phase 1+)
│   ├── core/
│   ├── analysis/
│   ├── preprocessing/
│   └── models/
│
├── data/                    # Storage directories
│   ├── uploads/             # Raw dataset uploads (.csv, .xlsx)
│   ├── processed/           # Processed datasets (Future Phase)
│   └── results/             # Job & analysis results (Future Phase)
│
├── models/
│   └── saved/               # Machine learning artifact storage (Future Phase)
│
├── tests/
│   └── backend/             # Pytest test suite
│
├── docker/
│   ├── Dockerfile.backend
│   ├── Dockerfile.frontend
│   └── nginx.conf
│
├── .env.example
├── .gitignore
├── README.md
└── docker-compose.yml
```

---

## Local Setup & Quickstart

### Prerequisites
- Python 3.11+
- Node.js 18+ and `npm`
- (Optional) Docker and Docker Compose

---

### Option A: Running with Docker Compose (Recommended)

1. Clone or navigate to the project directory:
   ```bash
   cd "My Projects"
   ```

2. Start the full stack (PostgreSQL, FastAPI Backend, React Frontend):
   ```bash
   docker-compose up --build
   ```

3. Open your browser:
   - Frontend Dashboard: [http://localhost:3000](http://localhost:3000)
   - Backend OpenAPI Docs: [http://localhost:8000/docs](http://localhost:8000/docs)
   - Health Check Endpoint: [http://localhost:8000/api/v1/health](http://localhost:8000/api/v1/health)

---

### Option B: Running Locally (Development Mode)

#### 1. Backend Setup

1. Navigate to the root directory and set up a Python virtual environment:
   ```bash
   python -m venv venv
   # On Windows (PowerShell):
   .\venv\Scripts\Activate.ps1
   # On Linux/macOS:
   source venv/bin/activate
   ```

2. Install dependencies:
   ```bash
   pip install -r backend/requirements.txt
   ```

3. Copy the environment variables:
   ```bash
   cp .env.example .env
   ```

4. Start the FastAPI server (uses SQLite fallback by default if PostgreSQL is not active):
   ```bash
   python backend/app/main.py
   ```
   The backend will run on `http://localhost:8000`.

#### 2. Frontend Setup

1. Open a new terminal and navigate to `frontend/`:
   ```bash
   cd frontend
   npm install
   ```

2. Start the Vite development server:
   ```bash
   npm run dev
   ```
   The frontend will run on `http://localhost:5173`.

---

## Environment Variables Configuration

Refer to `.env.example` for all configurable environment variables:

| Variable | Default Value | Description |
|---|---|---|
| `DATABASE_URL` | `sqlite:///./app.db` | Connection string for database (PostgreSQL or SQLite) |
| `UPLOAD_DIR` | `./data/uploads` | Path to store uploaded dataset files |
| `PROCESSED_DIR` | `./data/processed` | Path for processed datasets |
| `RESULTS_DIR` | `./data/results` | Path for job result outputs |
| `MODEL_DIR` | `./models/saved` | Path for trained model artifacts |
| `MAX_UPLOAD_SIZE` | `52428800` (50MB) | Maximum allowed file upload size in bytes |
| `API_PREFIX` | `/api/v1` | Root API route prefix |
| `CORS_ORIGINS` | `["http://localhost:5173", ...]` | Allowed origins for CORS requests |

---

## REST API Specification (`/api/v1`)

| Method | Endpoint | Description |
|---|---|---|
| `GET` | `/api/v1/health` | Health check endpoint returning backend status |
| `POST` | `/api/v1/datasets/upload` | Upload CSV or XLSX dataset with file validation |
| `GET` | `/api/v1/datasets` | List all uploaded datasets metadata |
| `GET` | `/api/v1/datasets/{id}` | Get metadata for a specific dataset |
| `DELETE` | `/api/v1/datasets/{id}` | Delete dataset record and stored file from disk |
| `GET` | `/api/v1/jobs` | List all background jobs and status lifecycle |
| `GET` | `/api/v1/jobs/{id}` | Get specific job execution status |
| `POST` | `/api/v1/jobs/test` | Trigger demo background job (PENDING → RUNNING → COMPLETED/FAILED) |

---

## Running Automated Tests

Run backend unit tests with `pytest`:

```bash
# Make sure virtual environment is activated
pytest tests/backend
```

Tests cover:
- `/api/v1/health` availability
- CSV dataset upload & metadata extraction
- Unsupported extension rejection (.exe, .txt)
- Dataset listing and safe deletion
- Job system creation and status polling

---

## What Has NOT Been Implemented Yet (Phase 1+ Roadmap)

The following components are explicitly out-of-scope for Phase 0 and will be added in subsequent phases:

- ❌ LLM / LangGraph Agent Integration & Autonomous Agents
- ❌ Automated Exploratory Data Analysis (EDA) & Summary Generation
- ❌ Feature Engineering & Data Cleaning Pipelines
- ❌ AutoML Model Training, Evaluation, and Comparison
- ❌ SHAP Explainability & Model Predictions
- ❌ Dynamic Interactive Chart / Dashboard Generation
- ❌ One-Click Model Deployment & REST Model Serving
