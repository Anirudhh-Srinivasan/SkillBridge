PROJECT: SkillBridge - AI skill mapping portal (student <-> industry <-> faculty)
Base URL: http://localhost:8000/api (CORS open for all origins)
Frontends read it from VITE_API_URL

POST /resume/parse (multipart: file, target_role)
 -> {name, skills:[str], missing_skills:[str], match_score:int}
POST /test/generate {skills:[str]}
 -> {questions:[{id, question, options:[4 str], answer_index, skill}]}
POST /test/submit {answers:[{id, selected}], questions:[...]}
 -> {score:int, per_skill:{skill:int}}
POST /interview/next {type:"technical"|"hr", target_role, history:[{role:"user"|"assistant", content}]}
 -> {reply:str, done:bool}
POST /interview/score {history:[...], target_role}
 -> {technical:int, hr:int, soft_skills:int, feedback:str}
POST /readiness {match_score, test_score, interview:{technical,hr,soft_skills}, missing_skills:[str]}
 -> {readiness_score:int, skill_gaps:[{skill, level:int}], learning_path:[{step, resource}]}
GET /jobs -> [{id, company, role, required_skills:[str]}]
POST /jobs {company, role, required_skills} -> job
GET /candidates?job_id= -> [{id, name, skills:[str], readiness_score, match_score}] sorted desc by match_score
GET /faculty/batch-gaps -> [{skill, gap_percent:int}]

Folders: /backend (port 8000), /frontend-student (5173), /frontend-dashboards (5174)
Only edit files inside YOUR folder.
