# SkillBridge: two-minute demo

Open these pages in separate tabs:

- Student app: http://localhost:5173
- Company and faculty dashboards: http://localhost:5174

## Student flow (about 90 seconds)

1. At the student landing page, confirm the tagline **“Verified skills, not just resumes”**.
2. Choose `demo/sample_resume.txt` and leave **backend developer** selected. Click **Analyze my profile**.
3. Point out the extracted skills and the missing skills. Click **Start skill assessment**.
4. Answer the 10 questions by clicking any option. The demo accepts any selection and computes a score.
5. In the interview, enter these three answers when prompted:
   - “I measured API latency and improved a SQL query with targeted tests.”
   - “First I reproduced the error, then added validation and deployed a safe fix.”
   - “For example, the endpoint handled 20 percent more requests after caching.”
6. After the third technical response, the interview switches to HR. Enter:
   - “I clarified the disagreement, shared the evidence, and agreed on a plan with my teammate.”
   - “I asked for feedback, practiced the weak area, and used it in the next project.”
   - “I want to contribute reliable backend APIs and learn from the team.”
7. After three HR responses, show the interview score, readiness score, skill-gap chart, and learning path.

## Company and faculty views (about 30 seconds)

8. Click **Company & faculty dashboards** in the student header, or open http://localhost:5174.
9. On **Industry**, show the seeded candidate ranking, skill matches, and scores. Click a candidate for details.
10. Click **Academia** in the dashboard sidebar to show cohort skill gaps, workshop suggestions, readiness distribution, and seeded students.
11. Use **Student app** in the dashboard sidebar to return to the student flow.

## Runtime

From the repository root, `./run_all.sh` starts the backend on port 8000, student app on 5173, and dashboard on 5174. The backend uses deterministic fallbacks whenever Groq is missing, slow, rate-limited, or returns an invalid response.
