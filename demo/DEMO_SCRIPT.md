# Two-minute SkillBridge demo

**Opening line:** “verified skills, not just resumes”

1. **0:00–0:15 — Upload resume.** Open the student app at `http://localhost:5173`, choose `demo/sample_resume.txt`, select **Backend Developer**, and analyze the profile. Say that SkillBridge reads evidence from the resume and compares it with a target role.
2. **0:15–0:35 — Skills and gaps.** Point out detected skills such as Python, FastAPI, SQL, React, and Git, then the role gaps such as Docker and REST APIs. Explain that the match score is a starting signal.
3. **0:35–1:00 — Test.** Start the assessment, answer a couple of questions, and show that the assessment is scored per skill.
4. **1:00–1:25 — Interview.** Answer a technical prompt and an HR prompt. Mention that the follow-up uses the selected role and interview history.
5. **1:25–1:40 — Results.** Show readiness, the interview scorecard, skill gaps, and the suggested learning path.
6. **1:40–1:53 — Company dashboard.** Open `http://localhost:5174`; select an open role and show the candidate ranking, verified skills, and match/readiness scores.
7. **1:53–2:00 — Faculty view.** Open **Academia** to show cohort skill gaps, readiness distribution, and workshop ideas.

The backend can run without a `GROQ_API_KEY`; deterministic fallback responses keep the demo flowing. Add a valid key to enable Groq-generated responses.
