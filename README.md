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
├── frontend/   # Next.js app
├── backend/    # FastAPI app
├── ml/         # Model training scripts
└── supabase/   # DB migrations
```

## Getting Started

### Prerequisites

- A Supabase project
- Adzuna API key (free tier)
- Groq API key (free tier)

---

### Option A — Docker (recommended)

Runs the full stack in one command. No Python or Node setup required.

```bash
# 1. Create a root .env file with your public keys
cp .env.example .env  # fill in NEXT_PUBLIC_SUPABASE_URL, NEXT_PUBLIC_SUPABASE_ANON_KEY, NEXT_PUBLIC_API_URL

# 2. Add your secret keys to backend/.env
cp backend/.env.example backend/.env  # fill in SUPABASE_SERVICE_ROLE_KEY, GROQ_API_KEY, ADZUNA_APP_ID, ADZUNA_API_KEY

# 3. Start everything
docker compose up --build
```

- Frontend → http://localhost:3001
- Backend → http://localhost:8000

---

### Option B — Local dev (hot reload)

Requires Node.js 18+ and Python 3.11+.

**Backend**
```bash
cd backend
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env  # fill in your keys
uvicorn main:app --reload
```

**Frontend**
```bash
cd frontend
npm install
cp .env.local.example .env.local  # fill in your keys
npm run dev
```

---

### Database

Apply the migration once in the Supabase SQL editor:

```
supabase/migrations/001_initial_schema.sql
```

## Build Phases

- **Phase 1** ✅ Foundation — scaffold, auth, CV parsing, Adzuna integration
- **Phase 2** 🔲 Ranking engine — fine-tune scorer, LangGraph ranking agent, dashboard
- **Phase 3** 🔲 Application pipeline — tailoring agent, streaming SSE
- **Phase 4** 🔲 Interview prep + analytics
- **Phase 5** 🔲 Polish + deploy + beta users

---

_Built by Hossein Masjedi · Stack: Next.js · FastAPI · LangGraph · Groq · Supabase · sentence-transformers_
