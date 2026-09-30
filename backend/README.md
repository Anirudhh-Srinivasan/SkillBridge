# SkillBridge backend

Copy `.env.example` to `.env` and add `GROQ_API_KEY` for live Llama responses. Fallbacks keep the demo working without it.

```bash
pip install -r requirements.txt
uvicorn main:app --reload --port 8000
```
