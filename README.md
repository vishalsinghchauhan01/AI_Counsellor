# UttaraPath — AI Career Counsellor

Full-stack AI-powered career counselling chatbot for students in Uttarakhand, India. Uses RAG with **local PostgreSQL (pgvector)** + OpenAI for colleges, careers, entrance exams, and scholarships.

## Tech Stack

- **Frontend:** Next.js 14 (App Router), JavaScript, Tailwind CSS, Zustand, Axios
- **Backend:** FastAPI, Python 3.11, Uvicorn
- **AI/RAG:** OpenAI (gpt-4o-mini, text-embedding-3-small, Whisper, TTS), **PostgreSQL + pgvector** (local vector store)
- **DB:** Local PostgreSQL for RAG; Supabase optional (user profiles)

## Setup

### 1. Local PostgreSQL + pgvector

Install PostgreSQL and the pgvector extension, then create the database. See **[POSTGRES_SETUP.md](POSTGRES_SETUP.md)** for step-by-step instructions.

### 2. Backend

```bash
cd backend
python -m venv venv
# Windows:
venv\Scripts\activate
# macOS/Linux:
source venv/bin/activate

pip install -r requirements.txt
cp .env.example .env
# Edit .env: OPENAI_API_KEY, DATABASE_URL=postgresql://postgres:password@localhost:5432/uttarapath
```

### 3. Ingest data into PostgreSQL (one time)

```bash
cd backend
python rag/ingest.py
# Wait for: "✅ Ingestion complete!"
```

### 4. Frontend

```bash
cd frontend
npm install
cp .env.local.example .env.local
# Set NEXT_PUBLIC_API_URL=http://localhost:8000 and Supabase keys if needed
```

### 5. Supabase (optional)

Run the SQL in `supabase_schema.sql` in your Supabase project’s SQL Editor.

## Run locally

**Terminal 1 — Backend**

```bash
cd backend
uvicorn main:app --reload --port 8000
```

**Terminal 2 — Frontend**

```bash
cd frontend
npm run dev
```

Open [http://localhost:3000](http://localhost:3000).

## Env vars

**Backend `.env`**

- `OPENAI_API_KEY` — OpenAI API key  
- `DATABASE_URL` — e.g. `postgresql://postgres:password@localhost:5432/uttarapath` (local PostgreSQL + pgvector)  
- `SUPABASE_URL`, `SUPABASE_SERVICE_KEY` — optional, for user profiles  
- `ENVIRONMENT` — e.g. `development`

**Frontend `.env.local`**

- `NEXT_PUBLIC_API_URL` — e.g. `http://localhost:8000`  
- `NEXT_PUBLIC_SUPABASE_URL`, `NEXT_PUBLIC_SUPABASE_ANON_KEY` — Supabase (optional for basic chat)

## Project structure

- `backend/` — FastAPI app, RAG (ingest, retriever, vector_store for PostgreSQL/pgvector, prompts), routers (chat, voice, colleges, user)
- `frontend/` — Next.js app (onboarding, chat), components (ChatWindow, MessageBubble, VoiceButton, CollegeCard, etc.)
- `data/` — `uttarakhand_colleges_db.json`, `career_paths.json`, `entrance_exams.json`, `scholarships.json`

## Deployment

- **Frontend:** Vercel (connect repo, set env vars).  
- **Backend:** Railway (use provided `backend/Dockerfile`, set env vars, expose port 8000).
