# SkillBridge — Student Portal

The student-facing AI readiness flow: resume analysis, a generated skills test, technical + HR mock interviews, and a printable readiness report.

## Run

```bash
npm install
npm run dev
```

It runs at `http://localhost:5173`. Copy `.env.example` to `.env` to override settings.

`VITE_USE_MOCK=true` (the default) provides a complete realistic demo without the API. Set it to `false` to use the FastAPI backend at `VITE_API_URL` (defaults to `http://localhost:8000/api`).
