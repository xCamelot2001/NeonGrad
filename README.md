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

- Node.js 18+
- Python 3.11+
- A Supabase project
- Adzuna API key (free tier)
- Groq API key (free tier)

### Backend

```bash
cd backend
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env  # fill in your keys
uvicorn main:app --reload
```

### Frontend

```bash
cd frontend
npm install
cp .env.local.example .env.local  # fill in your keys
npm run dev
```

### Database

Apply the migration in Supabase SQL editor:

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
