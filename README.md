# Fair LLM Monitor

Bias-mitigated AI chat with a live fairness monitoring dashboard. Chat with an LLM while toxicity, stereotype, and refusal disparity metrics are measured and visualized in real time.

## Pages

| Route | Description |
|---|---|
| `/` | Landing page with links |
| `/chat` | Chat interface with streaming and settings panel |
| `/dashboard` | Live fairness metrics: charts, table, disparity alerts |

---

## Quick Start (Local)

### 1 — Backend

```bash
# Create and activate a virtual environment
python -m venv .venv
.venv\Scripts\activate        # Windows
# source .venv/bin/activate   # macOS/Linux

# Install dependencies
pip install -r requirements.txt

# Copy and configure environment
cp .env.example .env
# Edit .env — set LLM_API_KEY and SALT

# Start the backend (port 8000)
uvicorn backend.main:app --reload
```

### 2 — Frontend

```bash
# Install Node dependencies
npm install

# Create frontend env file
echo "NEXT_PUBLIC_API_URL=http://localhost:8000" > .env.local

# Start the dev server (port 3000)
npm run dev
```

Open http://localhost:3000.

---

## Deploy to Vercel (Frontend) + Render (Backend)

### Backend → Render

1. Push this repo to GitHub.
2. Go to [Render.com](https://render.com) → **New Web Service** → connect your repo.
3. Render will auto-detect `render.yaml`. Set these **Secret Env Vars** in the Render dashboard:
   - `LLM_API_KEY` — your OpenAI or Anthropic key
   - `SALT` — a random 32-character string
   - `CORS_ORIGINS` — your Vercel frontend URL (e.g. `https://fair-llm.vercel.app`)

### Frontend → Vercel

1. Go to [Vercel.com](https://vercel.com) → **Import** your GitHub repo.
2. Vercel auto-detects Next.js. Add one **Environment Variable** in the Vercel dashboard:
   - `NEXT_PUBLIC_API_URL` — your Render backend URL (e.g. `https://fair-llm-backend.onrender.com`)
3. Deploy.

> **Tip:** Update `vercel.json` → `rewrites[0].destination` to your actual Render URL to enable API proxying (removes CORS complexity entirely).

---

## Environment Variables

### Backend (`.env`)

| Variable | Default | Description |
|---|---|---|
| `LLM_PROVIDER` | `openai` | `openai` or `anthropic` |
| `LLM_API_KEY` | *(required)* | Your LLM provider API key |
| `LLM_MODEL` | `gpt-4o-mini` | Model name |
| `SALT` | *(required in prod)* | Secret for hashing user IDs |
| `DATABASE_URL` | SQLite | Use Postgres URL in prod |
| `CORS_ORIGINS` | `http://localhost:3000` | Frontend origin(s) |
| `APP_ENV` | `local` | `local` / `production` |
| `REDIS_URL` | *(optional)* | Omit to run without async queue |

### Frontend (`.env.local`)

| Variable | Description |
|---|---|
| `NEXT_PUBLIC_API_URL` | Backend API origin URL |

---

## Tech Stack

| Layer | Tech |
|---|---|
| Frontend | Next.js 14, TailwindCSS, TanStack Query, Recharts |
| Backend | FastAPI, async SQLAlchemy, structlog, slowapi |
| LLM | OpenAI / Anthropic (configurable) |
| Database | SQLite (local) / Postgres (production) |
| Deployment | Vercel (frontend) + Render (backend) |
