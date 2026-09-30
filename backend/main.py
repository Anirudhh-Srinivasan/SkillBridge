import json, logging, os, re
from io import BytesIO
from typing import Any, Dict, List, Optional
from dotenv import load_dotenv
from fastapi import FastAPI, File, Form, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from pypdf import PdfReader

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
load_dotenv(os.path.join(BASE_DIR, '.env'))
GROQ_MODEL = os.getenv('GROQ_MODEL', 'llama-3.3-70b-versatile')
logger = logging.getLogger(__name__)
app = FastAPI(title='SkillBridge API')
app.add_middleware(CORSMiddleware, allow_origins=['*'], allow_credentials=False, allow_methods=['*'], allow_headers=['*'])
try:
    from groq import Groq
    client = Groq(api_key=os.getenv('GROQ_API_KEY')) if os.getenv('GROQ_API_KEY') else None
except Exception:
    logger.exception('Failed to initialize Groq client')
    client = None

logger.info('GROQ_API_KEY loaded: %s', bool(os.getenv('GROQ_API_KEY')))

def llm_json(system: str, prompt: str, fallback: Dict[str, Any]) -> Dict[str, Any]:
    if not client: return fallback
    try:
        r = client.chat.completions.create(model=GROQ_MODEL, temperature=0.2, response_format={'type':'json_object'}, messages=[{'role':'system','content':system},{'role':'user','content':prompt}])
        raw = r.choices[0].message.content.strip()
        raw = re.sub(r'^```(?:json)?\s*', '', raw, flags=re.I)
        raw = re.sub(r'\s*```$', '', raw).strip()
        return json.loads(raw)
    except Exception:
        logger.exception('Groq LLM call or JSON parsing failed; returning fallback')
        return fallback

def file_text(data: bytes, name: str) -> str:
    if name.lower().endswith('.pdf'):
        try: return '\n'.join(p.extract_text() or '' for p in PdfReader(BytesIO(data)).pages)
        except Exception: return ''
    return data.decode('utf-8', errors='ignore')

ROLE_SKILLS = {'software':['Python','JavaScript','SQL','Git','REST APIs','React'], 'data':['Python','SQL','Pandas','Statistics','Machine Learning','Excel'], 'frontend':['JavaScript','React','HTML','CSS','Git','REST APIs'], 'backend':['Python','FastAPI','SQL','REST APIs','Docker','Git']}
def required(role):
    return next((v for k,v in ROLE_SKILLS.items() if k in role.lower()), ROLE_SKILLS['software'])

@app.get('/api/health')
def health(): return {'status':'ok'}

@app.post('/api/resume/parse')
async def parse_resume(file: UploadFile = File(...), target_role: str = Form(...)):
    text = file_text(await file.read(), file.filename or 'resume.txt')
    known = ['Python','JavaScript','Java','SQL','React','FastAPI','Git','HTML','CSS','Pandas','Machine Learning','Docker','Excel','REST APIs','Statistics']
    skills = [s for s in known if re.search(r'\b'+re.escape(s)+r'\b', text, re.I)]
    name_match = re.search(r'(?im)^name\s*[:\-]\s*(.+)$', text)
    fallback = {'name': name_match.group(1).strip() if name_match else 'Student', 'skills': skills}
    parsed = llm_json('Extract only JSON with name and skills array.', text[:10000], fallback)
    skills = [str(x) for x in parsed.get('skills', skills)] if isinstance(parsed.get('skills', skills), list) else skills
    needed = required(target_role); have = {x.lower() for x in skills}; missing = [x for x in needed if x.lower() not in have]
    return {'name':str(parsed.get('name', fallback['name'])),'skills':skills,'missing_skills':missing,'match_score':round(100*(len(needed)-len(missing))/len(needed))}

class TestGenerate(BaseModel): skills: List[str]
class TestSubmit(BaseModel): answers: List[Dict[str,Any]]; questions: List[Dict[str,Any]]
class InterviewNext(BaseModel): type: str; target_role: str; history: List[Dict[str,str]] = []
class InterviewScore(BaseModel): history: List[Dict[str,str]]; target_role: str
class Readiness(BaseModel): match_score: int; test_score: int; interview: Dict[str,int]; missing_skills: List[str]
class Job(BaseModel): company: str; role: str; required_skills: List[str]

@app.post('/api/test/generate')
def generate_test(b: TestGenerate):
    ss=b.skills or ['Python']; qs=[{'id':i+1,'question':f'Which statement best describes {ss[i%len(ss)]}?','options':[f'Core {ss[i%len(ss)]} concept','A database brand','A hardware part','An unrelated protocol'],'answer_index':0,'skill':ss[i%len(ss)]} for i in range(10)]
    r=llm_json('Return JSON with exactly 10 MCQs, each with id, question, four options, answer_index, skill.',str(ss),{'questions':qs}); return {'questions':r.get('questions',qs)[:10]}

@app.post('/api/test/submit')
def submit_test(b: TestSubmit):
    totals={}
    for q in b.questions:
        a=next((x.get('selected') for x in b.answers if x.get('id')==q.get('id')),None); totals.setdefault(str(q.get('skill','General')),[]).append(int(a==q.get('answer_index')))
    per={k:round(100*sum(v)/len(v)) for k,v in totals.items()}; return {'score':round(sum(per.values())/len(per)) if per else 0,'per_skill':per}

@app.post('/api/interview/next')
def interview_next(b: InterviewNext):
    n=sum(x.get('role')=='user' for x in b.history)
    qs=['Tell me about a project relevant to '+b.target_role+'.','How did you debug a difficult issue?','Explain a key design decision.','How do you handle conflicting deadlines?','Why should a team choose you?'] if b.type=='technical' else ['Tell me about yourself.','Describe a time you handled feedback.','How do you collaborate?','Tell me about a failure and what you learned.','Why this role?']
    fallback={'reply':qs[n] if n<5 else 'That completes the interview.','done':n>=5}
    result=llm_json('Return a JSON object with reply (one concise interview question) and done (boolean). Tailor it to the interview type and target role, use the history to avoid repeating questions, and set done=true only after five candidate answers.',json.dumps({'type':b.type,'target_role':b.target_role,'history':b.history}),fallback)
    return {'reply':str(result.get('reply',fallback['reply'])),'done':bool(result.get('done',fallback['done']))}

@app.post('/api/interview/score')
def interview_score(b: InterviewScore):
    base=min(95,45+10*sum(x.get('role')=='user' for x in b.history)); f={'technical':base,'hr':base,'soft_skills':min(95,base+3),'feedback':'Good structure and relevant examples; add measurable outcomes.'}; r=llm_json('Return JSON technical, hr, soft_skills integers 0-100 and short feedback.',str(b.history),f); return {k:r.get(k,f[k]) for k in f}

@app.post('/api/readiness')
def readiness(b: Readiness):
    iv=sum(b.interview.get(k,0) for k in ['technical','hr','soft_skills'])/3; score=round(b.match_score*.35+b.test_score*.3+iv*.35); gaps=[{'skill':s,'level':max(20,100-min(score,80))} for s in b.missing_skills]; path=[{'step':f'Master {s}','resource':f'Guided {s} fundamentals and hands-on exercises'} for s in b.missing_skills[:4]]
    extras=['Build a portfolio project','Take a timed assessment','Practice mock interviews','Apply to matched roles']; path += [{'step':x,'resource':'SkillBridge recommended practice plan'} for x in extras[:max(0,4-len(path))]]; return {'readiness_score':score,'skill_gaps':gaps,'learning_path':path[:5]}

jobs=[{'id':'job-1','company':'TCS','role':'Software Engineer','required_skills':['Python','SQL','Git']},{'id':'job-2','company':'Infosys','role':'Frontend Developer','required_skills':['JavaScript','React','HTML','CSS']},{'id':'job-3','company':'Razorpay','role':'Backend Engineer','required_skills':['Python','FastAPI','SQL','Docker']},{'id':'job-4','company':'Deloitte','role':'Data Analyst','required_skills':['Python','SQL','Excel','Statistics']},{'id':'job-5','company':'Wipro','role':'Graduate Engineer','required_skills':['Java','SQL','Git']}]
names=['Aarav Sharma','Ananya Iyer','Rohan Verma','Diya Nair','Arjun Rao','Meera Singh','Kabir Shah','Ishita Patel','Vivek Kumar','Saanvi Das','Aditya Menon','Tara Kapoor','Nikhil Jain','Pooja Reddy','Karan Gupta']
candidates_data=[{'id':f'cand-{i+1}','name':n,'skills':['Python','SQL','Git'] if i%3==0 else (['JavaScript','React','HTML'] if i%3==1 else ['Python','Pandas','Statistics']),'readiness_score':62+(i*7)%35,'match_score':58+(i*11)%43} for i,n in enumerate(names)]
gaps=[{'skill':s,'gap_percent':p} for s,p in [('SQL',42),('Communication',38),('Data Structures',55),('React',47),('System Design',63),('Python',29),('Git',34),('Statistics',51)]]
@app.get('/api/jobs')
def get_jobs(): return jobs
@app.post('/api/jobs')
def add_job(b: Job):
    x={'id':f'job-{len(jobs)+1}',**b.model_dump()}; jobs.append(x); return x
@app.get('/api/candidates')
def get_candidates(job_id: Optional[str]=None): return sorted(candidates_data,key=lambda x:x['match_score'],reverse=True)
@app.get('/api/faculty/batch-gaps')
def faculty_gaps(): return gaps
