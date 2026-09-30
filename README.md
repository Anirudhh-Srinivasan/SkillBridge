# SkillBridge

AI skill mapping portal connecting students, industry, and faculty. The student flow maps resume evidence to skills, assessments, interviews, and readiness; company and faculty dashboards use the same FastAPI service.

## Requirements and installation

- Python 3.10 or newer
- Node.js and npm

Install backend dependencies from the repository root:

```bash
pip install -r backend/requirements.txt
```

Install each frontend's dependencies:

```bash
cd frontend-student && npm install && cd ..
cd frontend-dashboards && npm install && cd ..
```

Create `backend/.env` with your Groq key to enable generated interview/test content. The backend selects and caches a working chat model automatically:

```dotenv
GROQ_API_KEY=your_key_here
```

The model preference order is `GROQ_MODEL` when set, then `openai/gpt-oss-20b`, `openai/gpt-oss-120b`, and `qwen/qwen3.8-27b`. The local `.env` is ignored by Git; never commit your key.

The backend also supports deterministic fallback behavior if no key is configured. Each frontend has a `.env` configured for the local API at `http://localhost:8000/api`, with mock data disabled. To preview mock data, open the app with `?mock=1`.

## Run all services

From the repository root:

```bash
./run_all.sh
```

Press Ctrl+C to stop the backend and both frontends. Services use these ports:

- Backend: `8000`
- Student app: `5173`
- Company and faculty dashboards: `5174`

`run_all.sh` first frees ports 8000, 5173, and 5174, then starts all services. Both frontends use the live API by default. To preview mock data, set `VITE_USE_MOCK=true` in the frontend environment or open either app with `?mock=1`.

For the demo flow and sample resume, see [`demo/DEMO_SCRIPT.md`](demo/DEMO_SCRIPT.md) and [`demo/sample_resume.txt`](demo/sample_resume.txt).
