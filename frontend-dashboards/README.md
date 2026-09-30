# SkillBridge dashboards

Company and faculty dashboards for SkillBridge, built with React, Vite, Tailwind CSS, React Router, and Recharts.

## Run locally

```bash
npm install
npm run dev
```

The dashboard runs on [http://localhost:5174](http://localhost:5174).

Copy `.env.example` to `.env` to configure the API:

```env
VITE_API_URL=http://localhost:8000/api
VITE_USE_MOCK=true
```

Mock mode is enabled by default and can be disabled with `VITE_USE_MOCK=false`. The mock data mirrors the endpoint shapes in the root `API_CONTRACT.md`; mock mode includes five roles, fifteen Indian student candidates, and eight batch skill gaps. The company view supports job creation, candidate filtering, CSV export, candidate details, and local shortlisting. The faculty view shows skill gaps, generated workshop suggestions, and readiness distribution.

## API endpoints used

- `GET /jobs`
- `POST /jobs`
- `GET /candidates?job_id=...`
- `GET /faculty/batch-gaps`

