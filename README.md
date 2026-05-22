# NeonGrad 🚀

> An AI-powered job hunting OS — it finds the right jobs for you, ranks them by fit, and tailors your application in 60 seconds.

## Stack

| Layer      | Technology                         |
| ---------- | ---------------------------------- |
| Frontend   | Next.js 15 + Tailwind CSS          |
| Backend    | FastAPI (Python)                   |
| Auth + DB  | Supabase (PostgreSQL + Auth)       |
| Agents     | LangGraph + Groq (Llama 3.1 8B)    |
| Job data   | Adzuna API                         |
| ML scoring | sentence-transformers (fine-tuned) |
| Containers | Docker + Docker Compose            |
| Deployment | Vercel (FE) + Railway (BE)         |

## Repo Structure

```
neongrad/
├── frontend/        # Next.js 15 app (Tailwind, Supabase auth)
│   ├── app/         # App router pages (dashboard, jobs, auth)
│   ├── components/  # Shared UI components
│   └── lib/         # API client, Supabase client
├── backend/         # FastAPI app
│   ├── agents/      # LangGraph pipelines (ranking_agent.py)
│   ├── models/      # ML scorer singleton (scorer.py)
│   ├── routers/     # API route handlers (jobs, profiles, cv)
│   └── tools/       # Shared utilities (supabase client, adzuna)
├── ml/              # Model training scripts
│   ├── generate_dataset.py   # Generates synthetic training data via Groq
│   ├── train_scorer.py       # Fine-tunes all-MiniLM-L6-v2 with regression head
│   └── evaluate_scorer.py    # Pearson/Spearman/MSE evaluation + plots
└── supabase/
    └── migrations/  # SQL schema (apply once in Supabase SQL editor)
```

## Getting Started

### Prerequisites

- Node.js 18+, Python 3.11+
- A [Supabase](https://supabase.com) project (free tier)
- [Adzuna API](https://developer.adzuna.com) key (free tier)
- [Groq API](https://console.groq.com) key (free tier)

---

### Option A — Docker (recommended)

Runs the full stack in one command. No Python or Node setup required.

```bash
# 1. Fill in root .env (frontend public keys)
cp .env.example .env

# 2. Fill in backend/.env (secret keys)
cp backend/.env.example backend/.env

# 3. Start everything
docker compose up --build
```

- Frontend → http://localhost:3001
- Backend → http://localhost:8000

---

### Option B — Local dev (hot reload)

**Backend**

```bash
cd backend
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env   # fill in your keys
uvicorn main:app --reload --port 8000
```

**Frontend**

```bash
cd frontend
npm install
cp .env.local.example .env.local   # fill in your keys
npm run dev   # runs on port 3001 (port 3000 used by macOS AirPlay)
```

---

### Database

Apply the migration once in the Supabase SQL editor:

```
supabase/migrations/001_initial_schema.sql
```

This creates 5 tables: `profiles`, `jobs`, `job_rankings`, `applications`, `interview_preps`.

---

### Environment Variables

**`backend/.env`**

```
SUPABASE_URL=
SUPABASE_SERVICE_ROLE_KEY=
GROQ_API_KEY=
ADZUNA_APP_ID=
ADZUNA_API_KEY=
SCORER_MODEL_ID=          # leave blank to use cosine similarity fallback
```

**`frontend/.env.local`**

```
NEXT_PUBLIC_SUPABASE_URL=
NEXT_PUBLIC_SUPABASE_ANON_KEY=
NEXT_PUBLIC_API_URL=http://localhost:8000
```

---

## How It Works

### Phase 2 — Ranking Engine

The core of NeonGrad is a **LangGraph pipeline** that runs whenever you click "Rank Jobs":

```
load_profile
  → fetch_unranked_jobs
    → score_jobs_raw          # sentence-transformer scores all jobs locally (~5s for 500 jobs)
      → extract_top_jds       # Groq extracts structured skills from top 50 JDs only
        → analyze_gaps        # deterministic Python skill matching + Groq qualitative summary
          → assign_strategies # strong_match / decent / stretch / skip
            → store_rankings  # upsert to job_rankings table
```

**Why this order?** Groq's free tier is 6000 TPM / 30 RPM. Scoring 500 jobs locally first reduces Groq calls to ≤50 — well within free tier limits.

**Skill matching** is done deterministically in Python (no LLM): exact match, substring match, bigram match, and a 20+ alias map (`aws ↔ amazon web services`, `sklearn ↔ scikit-learn`, etc). Groq is only used for the qualitative one-sentence fit summary.

### ML Scorer (optional fine-tuning)

By default the scorer uses cosine similarity on `all-MiniLM-L6-v2` embeddings. To fine-tune a custom relevance scorer:

```bash
cd ml
pip install -r requirements.txt

python generate_dataset.py          # generates 600 synthetic training triplets via Groq
python train_scorer.py --push-to-hub YOUR_HF_USERNAME/neongrad-relevance-scorer
python evaluate_scorer.py           # verify Pearson > 0.85
```

Then set `SCORER_MODEL_ID=YOUR_HF_USERNAME/neongrad-relevance-scorer` in `backend/.env` and restart the backend.

---

## Build Phases

- **Phase 1** ✅ Foundation — scaffold, auth, CV parsing (PDF/DOCX), Adzuna job discovery
- **Phase 2** ✅ Ranking engine — LangGraph pipeline, sentence-transformer scoring, gap analysis dashboard
- **Phase 3** 🔲 Application pipeline — tailoring agent with judge loop, streaming SSE, Kanban tracker, PDF export
- **Phase 4** 🔲 Interview prep + analytics
- **Phase 5** 🔲 Polish + deploy + beta users

---

_Built by Hossein Masjedi · Next.js · FastAPI · LangGraph · Groq · Supabase · sentence-transformers_
