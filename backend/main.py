import json, logging, os, re, traceback
from concurrent.futures import ThreadPoolExecutor, TimeoutError as FutureTimeout
from io import BytesIO
from typing import Any, Dict, List, Optional
from dotenv import load_dotenv
from fastapi import FastAPI, File, Form, UploadFile, Request
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from pypdf import PdfReader
from question_bank import QUESTION_BANK
import random

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
load_dotenv(os.path.join(BASE_DIR, '.env'))
MODEL_ORDER = list(dict.fromkeys([m for m in [os.getenv('GROQ_MODEL'), 'openai/gpt-oss-20b', 'openai/gpt-oss-120b', 'qwen/qwen3.8-27b'] if m]))
ACTIVE_MODEL = None
LLM_POOL = ThreadPoolExecutor(max_workers=4)
logger = logging.getLogger(__name__)
app = FastAPI(title='SkillBridge API')
app.add_middleware(CORSMiddleware, allow_origins=['*'], allow_credentials=False, allow_methods=['*'], allow_headers=['*'])
try:
    from groq import Groq
    client = Groq(api_key=os.getenv('GROQ_API_KEY')) if os.getenv('GROQ_API_KEY') else None
except Exception:
    logger.exception('Failed to initialize Groq client')
    client = None

logger.info('SkillBridge LLM active model: %s', os.getenv('GROQ_MODEL') or MODEL_ORDER[0])

@app.exception_handler(Exception)
async def unexpected_error_handler(request: Request, exc: Exception):
    logger.error('Unhandled API exception for %s %s\n%s', request.method, request.url.path, traceback.format_exc())
    path=request.url.path
    fallback={'detail':'Request could not be completed'}
    if path.endswith('/health'): fallback={'status':'ok'}
    elif path.endswith('/resume/parse'): fallback={'name':'Student','skills':[],'missing_skills':[],'match_score':0}
    elif path.endswith('/test/generate'): fallback={'questions':build_bank_fallback(['Python'])}
    elif path.endswith('/test/submit'): fallback={'score':0,'per_skill':{}}
    elif path.endswith('/interview/next'): fallback={'reply':'Could you tell me more about your experience?', 'done':False}
    elif path.endswith('/interview/score'): fallback={'technical':0,'hr':0,'soft_skills':0,'feedback':'Complete a few answers to receive feedback.'}
    elif path.endswith('/readiness'): fallback=readiness_fallback(0,0,{},[])
    elif path.endswith('/jobs') and request.method=='GET': fallback=[]
    elif path.endswith('/candidates'): fallback=[]
    elif path.endswith('/batch-gaps'): fallback=[]
    return JSONResponse(status_code=200,content=fallback)

def _valid_payload(value: Any, validator: Optional[Any]) -> bool:
    return isinstance(value, dict) and (validator(value) if validator else True)

def llm_json(system: str, prompt: str, fallback: Dict[str, Any], validator: Optional[Any] = None) -> Dict[str, Any]:
    """Call Groq with bounded retries, route validation and a cached working model."""
    global ACTIVE_MODEL
    if not client:
        return fallback
    models = ([ACTIVE_MODEL] if ACTIVE_MODEL else []) + [m for m in MODEL_ORDER if m != ACTIVE_MODEL]
    for model in models:
        future = None
        try:
            future = LLM_POOL.submit(client.chat.completions.create, model=model, temperature=0.2, max_tokens=4000, timeout=20,
                messages=[{'role':'system','content':system},{'role':'user','content':prompt}])
            response = future.result(timeout=20)
            content = response.choices[0].message.content
            if not isinstance(content, str) or not content.strip():
                raise ValueError('LLM returned empty message content')
            raw = re.sub(r'^\s*```(?:json)?\s*', '', content, flags=re.I)
            raw = re.sub(r'\s*```\s*$', '', raw).strip()
            starts = [i for i in (raw.find('{'), raw.find('[')) if i >= 0]
            end = max(raw.rfind('}'), raw.rfind(']'))
            if starts and end > min(starts):
                raw = raw[min(starts):end + 1]
            parsed = json.loads(raw)
            if not _valid_payload(parsed, validator):
                raise ValueError('LLM JSON failed route contract validation')
            ACTIVE_MODEL = model
            logger.info('LLM request succeeded using model %s', model)
            return parsed
        except Exception:
            if isinstance(__import__('sys').exc_info()[1], FutureTimeout) and future is not None:
                future.cancel()
            logger.error('LLM request failed using model %s\n%s', model, traceback.format_exc())
    return fallback

def file_text(data: bytes, name: str) -> str:
    if name.lower().endswith('.pdf'):
        try: return '\n'.join(p.extract_text() or '' for p in PdfReader(BytesIO(data)).pages)
        except Exception: return ''
    return data.decode('utf-8', errors='ignore')

ROLE_SKILLS = {'software':['Python','JavaScript','SQL','Git','REST APIs','React'], 'data':['Python','SQL','Pandas','Statistics','Machine Learning','Excel'], 'frontend':['JavaScript','React','HTML','CSS','Git','REST APIs'], 'backend':['Python','FastAPI','SQL','REST APIs','Docker','Git']}
def required(role):
    return next((v for k,v in ROLE_SKILLS.items() if k in role.lower()), ROLE_SKILLS['software'])

TECH_SKILLS = [
    'Python','JavaScript','TypeScript','Java','C','C++','C#','Go','Rust','Ruby','PHP','Kotlin','Swift','Scala','R','Bash','PowerShell',
    'HTML','CSS','Sass','Tailwind CSS','Bootstrap','React','Next.js','Vue','Angular','Svelte','Node.js','Express','FastAPI','Django','Flask','Spring Boot','ASP.NET',
    'REST APIs','GraphQL','WebSockets','SQL','PostgreSQL','MySQL','SQLite','MongoDB','Redis','DynamoDB','Cassandra','Elasticsearch','Oracle','Microsoft SQL Server',
    'Git','GitHub','GitLab','Docker','Kubernetes','Terraform','Ansible','Jenkins','GitHub Actions','CI/CD','Linux','Nginx','AWS','Azure','Google Cloud','Serverless',
    'Pandas','NumPy','SciPy','scikit-learn','TensorFlow','PyTorch','Keras','Machine Learning','Deep Learning','NLP','Computer Vision','Statistics','Data Analysis','Data Visualization','Tableau','Power BI','Apache Spark','Airflow',
    'Data Structures','Algorithms','Object-Oriented Programming','Microservices','System Design','Agile','Unit Testing','Pytest','Jest','Selenium','Playwright','Figma','Firebase','Supabase','Kafka','RabbitMQ','Prometheus','Grafana'
]

ROLE_REQUIREMENTS = {
    'backend developer': ['Python','SQL','REST APIs','Git','Docker','FastAPI'],
    'backend engineer': ['Python','SQL','REST APIs','Git','Docker','FastAPI'],
    'frontend developer': ['JavaScript','TypeScript','React','HTML','CSS','Git'],
    'frontend engineer': ['JavaScript','TypeScript','React','HTML','CSS','Git'],
    'full stack developer': ['JavaScript','TypeScript','React','Node.js','SQL','Git'],
    'full-stack developer': ['JavaScript','TypeScript','React','Node.js','SQL','Git'],
    'data analyst': ['SQL','Python','Pandas','Statistics','Data Visualization','Excel'],
    'data scientist': ['Python','SQL','Pandas','scikit-learn','Statistics','Machine Learning'],
    'machine learning engineer': ['Python','SQL','Machine Learning','scikit-learn','PyTorch','Docker'],
    'ml engineer': ['Python','SQL','Machine Learning','scikit-learn','PyTorch','Docker'],
    'devops engineer': ['Linux','Docker','Kubernetes','AWS','CI/CD','Terraform'],
    'software engineer': ['Python','JavaScript','SQL','Git','Data Structures','REST APIs'],
}

def required_for_role(role: str) -> List[str]:
    key = role.strip().lower()
    if key in ROLE_REQUIREMENTS:
        return ROLE_REQUIREMENTS[key]
    for role_key, skills in ROLE_REQUIREMENTS.items():
        if role_key in key or key in role_key:
            return skills
    return ROLE_REQUIREMENTS['software engineer']

def extract_resume_fallback(text: str, target_role: str) -> Dict[str, Any]:
    lines = [line.strip() for line in text.splitlines() if line.strip()]
    name = lines[0] if lines else 'Student'
    name = re.sub(r'^(?:name\s*[:\-]\s*)', '', name, flags=re.I).strip() or 'Student'
    found = []
    for skill in TECH_SKILLS:
        pattern = r'(?<![\w+#.])' + re.escape(skill) + r'(?![\w+#.])'
        if re.search(pattern, text, re.I):
            found.append(skill)
    present = {skill.casefold() for skill in found}
    needed = required_for_role(target_role)
    missing = [skill for skill in needed if skill.casefold() not in present]
    return {'name': name, 'skills': found, 'missing_skills': missing,
            'match_score': round(100 * (len(needed) - len(missing)) / len(needed)) if needed else 0}

@app.get('/api/health')
def health(): return {'status':'ok'}

def _resume_valid(x): return isinstance(x.get('name'), str) and isinstance(x.get('skills'), list) and all(isinstance(v,str) for v in x['skills'])
def _questions_valid(x):
    qs=x.get('questions')
    return isinstance(qs,list) and len(qs)==10 and all(isinstance(q,dict) and isinstance(q.get('id'),(int,str)) and isinstance(q.get('question'),str) and isinstance(q.get('skill'),str) and isinstance(q.get('options'),list) and len(q['options'])==4 and all(isinstance(o,str) for o in q['options']) and isinstance(q.get('answer_index'),int) and 0<=q['answer_index']<4 for q in qs)
def _next_valid(x): return isinstance(x.get('reply'),str) and bool(x['reply'].strip()) and isinstance(x.get('done'),bool)
def _score_valid(x): return all(isinstance(x.get(k),int) and 0<=x[k]<=100 for k in ('technical','hr','soft_skills')) and isinstance(x.get('feedback'),str)

@app.post('/api/resume/parse')
async def parse_resume(file: UploadFile = File(...), target_role: str = Form(...)):
    text = file_text(await file.read(), file.filename or 'resume.txt')
    fallback = extract_resume_fallback(text, target_role)
    parsed = llm_json('Extract only JSON with name and skills array.', text[:10000], {'name':fallback['name'],'skills':fallback['skills']}, _resume_valid)
    # Keep the deterministic role comparison and use LLM extraction only when it
    # returned a valid skill list; the fallback path always uses the keyword bank.
    skills = [str(x) for x in parsed.get('skills', fallback['skills'])] if isinstance(parsed.get('skills', fallback['skills']), list) else fallback['skills']
    if parsed is not None and parsed.get('skills') is not None:
        present = {skill.casefold() for skill in skills}
        needed = required_for_role(target_role)
        missing = [skill for skill in needed if skill.casefold() not in present]
        score = round(100 * (len(needed)-len(missing))/len(needed)) if needed else 0
        return {'name':str(parsed.get('name',fallback['name'])),'skills':skills,'missing_skills':missing,'match_score':score}
    return fallback

class TestGenerate(BaseModel): skills: List[str]
class TestSubmit(BaseModel): answers: List[Dict[str,Any]]; questions: List[Dict[str,Any]]
class InterviewNext(BaseModel): type: str; target_role: str; history: List[Dict[str,str]] = []
class InterviewScore(BaseModel): history: List[Dict[str,str]]; target_role: str
class Readiness(BaseModel): match_score: int; test_score: int; interview: Dict[str,int]; missing_skills: List[str]
class Job(BaseModel): company: str; role: str; required_skills: List[str]

def build_bank_fallback(skills: List[str]) -> List[Dict[str, Any]]:
    """Select ten balanced bank questions, using nearby or general bank skills as needed."""
    requested = [str(skill).strip() for skill in skills if str(skill).strip()] or ['Python']
    bank_names = list(QUESTION_BANK)
    by_lower = {name.lower(): name for name in bank_names}
    canonical = []
    for skill in requested:
        # HTML and CSS are both represented by the combined HTML/CSS bank.
        key = skill.lower()
        if key in ('html', 'css'):
            match = 'HTML/CSS'
        else:
            match = by_lower.get(key)
        if match and match not in canonical:
            canonical.append(match)

    # Unknown skills borrow questions from the nearest bank topic where possible;
    # otherwise every bank skill is eligible as a balanced source.
    aliases = {
        'rust': 'Java', 'typescript': 'JavaScript', 'vue': 'React', 'angular': 'JavaScript',
        'postgresql': 'SQL', 'mysql': 'SQL', 'database': 'SQL', 'api': 'FastAPI',
        'backend': 'FastAPI', 'express': 'Node.js', 'containers': 'Docker',
        'algorithms': 'Data Structures', 'statistics': 'Machine Learning',
        'web development': 'HTML/CSS', 'css': 'HTML/CSS', 'html': 'HTML/CSS',
    }
    source_for = {}
    unsupported = []
    for skill in requested:
        key = skill.lower()
        source_for[skill] = by_lower.get(key) or (aliases.get(key) and by_lower.get(aliases[key]))
        if source_for[skill] is None:
            unsupported.append(skill)
    sources = list(dict.fromkeys(canonical + [source for source in source_for.values() if source]))
    if not sources:
        sources = bank_names[:]
    for index, skill in enumerate(unsupported):
        source_for[skill] = None

    # Divide ten slots as evenly as possible among requested skills. If a skill
    # has no direct bank, fill its allocation from the nearest available topic.
    selected = []
    used = {name: set() for name in bank_names}
    for index in range(10):
        requested_skill = requested[index % len(requested)]
        source = source_for.get(requested_skill)
        if source is None:
            source = bank_names[index % len(bank_names)]
        candidates = [q for q in QUESTION_BANK[source] if q['question'] not in used[source]]
        if not candidates:
            candidates = [q for bank_name in sources for q in QUESTION_BANK[bank_name]
                          if q['question'] not in used[bank_name]]
            if not candidates:
                candidates = [q for bank_name in bank_names for q in QUESTION_BANK[bank_name]]
        question = random.choice(candidates)
        actual_source = next(name for name in bank_names if question in QUESTION_BANK[name])
        used[actual_source].add(question['question'])
        selected.append({
            'id': len(selected) + 1,
            'question': question['question'],
            'options': list(question['options']),
            'answer_index': question['answer_index'],
            'skill': requested_skill if requested_skill not in unsupported else actual_source,
        })
    random.shuffle(selected)
    for index, question in enumerate(selected, start=1):
        question['id'] = index
    return selected

@app.post('/api/test/generate')
def generate_test(b: TestGenerate):
    qs=build_bank_fallback(b.skills)
    skills=b.skills or ['Python']
    r=llm_json('Return JSON with exactly 10 MCQs, each with id, question, four options, answer_index, skill.',str(skills),{'questions':qs}, _questions_valid); return {'questions':r['questions']}

@app.post('/api/test/submit')
def submit_test(b: TestSubmit):
    totals={}
    for q in b.questions:
        a=next((x.get('selected') for x in b.answers if x.get('id')==q.get('id')),None); totals.setdefault(str(q.get('skill','General')),[]).append(int(a==q.get('answer_index')))
    per={k:round(100*sum(v)/len(v)) for k,v in totals.items()}; return {'score':round(sum(per.values())/len(per)) if per else 0,'per_skill':per}

@app.post('/api/interview/next')
def interview_next(b: InterviewNext):
    fallback = interview_next_fallback(b.type, b.target_role, b.history)
    result=llm_json('Return a JSON object with reply (one concise interview question) and done (boolean). Tailor it to the interview type and target role, use the history to avoid repeating questions, and set done=true only after five candidate answers.',json.dumps({'type':b.type,'target_role':b.target_role,'history':b.history}),fallback, _next_valid)
    return {'reply':str(result.get('reply',fallback['reply'])),'done':bool(result.get('done',fallback['done']))}

TECH_INTERVIEW_BANK = [
    'How would you diagnose a slow request in a {role} system, and what measurements would you collect before changing it?',
    'How would you design a reliable interface between two parts of a {role} system when requests can fail or be retried?',
    'How would you test a {role} feature that depends on external data or services, including important edge cases?',
    'Describe a performance or reliability trade-off you would consider in a {role} system. How would you decide between the options?',
    'A {role} change works locally but fails after release. What steps would you take to isolate the cause and reduce user impact?',
]
HR_INTERVIEW_BANK = [
    'Tell me about a time you worked with a teammate whose approach differed from yours. How did you reach a good outcome?',
    'Describe a disagreement or conflict at work or on a project. What did you do, and what happened?',
    'What is one strength you rely on in a team, and what is one skill you are actively working to improve?',
    'Tell me about a time you received difficult feedback. How did you respond and what changed afterward?',
    'Why are you interested in this role, and what would you hope to contribute in your first few months?',
]

def interview_next_fallback(interview_type: str, target_role: str, history: List[Dict[str, str]]) -> Dict[str, Any]:
    # The frontend marks the technical-to-HR transition in the shared transcript.
    # Count HR answers from that marker while retaining the full transcript for scoring.
    round_start = max((i for i, message in enumerate(history)
                       if message.get('role') == 'assistant' and 'Technical round complete' in message.get('content', '')), default=-1)
    answered = sum(message.get('role') == 'user' for message in history[round_start + 1:])
    if answered >= 5:
        return {'reply':'Thank you for walking me through your examples. That completes our interview.', 'done':True}
    latest_answer = next((str(message.get('content','')).strip() for message in reversed(history)
                         if message.get('role') == 'user' and str(message.get('content','')).strip()), '')
    if interview_type.lower() == 'technical':
        role = target_role.lower()
        if 'ml' in role or 'machine learning' in role:
            label = 'machine learning'
        elif 'full stack' in role or 'full-stack' in role:
            label = 'full-stack application'
        elif 'frontend' in role or 'front-end' in role:
            label = 'frontend application'
        elif 'backend' in role or 'back-end' in role:
            label = 'backend service'
        elif 'data' in role:
            label = 'data platform'
        elif 'devops' in role or 'operations' in role:
            label = 'DevOps environment'
        else:
            label = target_role
        question = TECH_INTERVIEW_BANK[answered].format(role=label)
    else:
        question = HR_INTERVIEW_BANK[answered]
    reaction = ''
    if latest_answer:
        reaction = 'Thanks for explaining that. ' if len(latest_answer.split()) > 12 else 'I appreciate that. '
    return {'reply': reaction + question, 'done':False}

@app.post('/api/interview/score')
def interview_score(b: InterviewScore):
    fallback = score_interview_fallback(b.history, b.target_role)
    r=llm_json('Return JSON technical, hr, soft_skills integers 0-100 and 2-3 sentence feedback grounded in the interview history.',str({'target_role':b.target_role,'history':b.history}),fallback, _score_valid)
    return {k:r.get(k,fallback[k]) for k in fallback}

def score_interview_fallback(history: List[Dict[str, str]], target_role: str) -> Dict[str, Any]:
    answers = [str(message.get('content','')).strip() for message in history if message.get('role') == 'user' and str(message.get('content','')).strip()]
    joined = ' '.join(answers)
    words = re.findall(r"[A-Za-z0-9+#.]+", joined.lower())
    technical_terms = ['api','database','sql','python','javascript','react','docker','cloud','model','training','validation','pipeline','latency','cache','test','deploy','deployment','algorithm','query','endpoint','service','frontend','backend','metric','security','error','performance','data','schema','git','kubernetes']
    technical_hits = sum(bool(re.search(r'(?<!\w)'+re.escape(term)+r'(?!\w)', joined, re.I)) for term in technical_terms)
    structure_hits = sum(bool(re.search(r'\b(?:because|for example|for instance|first|then|finally|result|therefore|so that|measured|improved|reduced|increased)\b', answer, re.I)) for answer in answers)
    number_hits = sum(bool(re.search(r'\b\d+(?:\.\d+)?%?\b', answer)) for answer in answers)
    length_score = min(100, 35 + round(min(len(words), 220) * 0.27))
    coverage = min(100, 38 + 13 * len(answers))
    technical = round(max(0, min(100, 0.48*length_score + 0.36*min(100,technical_hits*12) + 0.16*coverage)))
    hr = round(max(0, min(100, 0.43*length_score + 0.34*min(100,structure_hits*22) + 0.23*min(100,number_hits*30))))
    soft = round(max(0, min(100, 0.38*length_score + 0.38*min(100,structure_hits*22) + 0.24*coverage)))
    lowered = joined.lower()
    strengths = []
    if technical_hits:
        matched = [term for term in technical_terms if re.search(r'(?<!\w)'+re.escape(term)+r'(?!\w)', joined, re.I)]
        strengths.append('You grounded your answers in technical details such as ' + ', '.join(matched[:3]))
    if structure_hits:
        strengths.append('You explained your reasoning with examples or cause and effect')
    if number_hits:
        strengths.append('You included measurable outcomes')
    if not strengths:
        strengths.append('You completed ' + str(len(answers)) + ' answer' + ('' if len(answers)==1 else 's'))
    gaps = []
    if not structure_hits:
        gaps.append('add a concrete example and explain the result')
    if not number_hits:
        gaps.append('include a number or specific impact where possible')
    if not technical_hits:
        gaps.append('name the tools, trade-offs, or technical steps you used')
    if len(strengths) > 1:
        first = strengths[0].rstrip('.') + '; ' + strengths[1][0].lower() + strengths[1][1:] + '.'
    else:
        first = strengths[0].rstrip('.') + '.'
    second = ('To strengthen your responses, ' + ' and '.join(gaps[:2]) + '.') if gaps else 'Keep linking your decisions to their impact and the role.'
    return {'technical':technical,'hr':hr,'soft_skills':soft,'feedback':first+' '+second}

@app.post('/api/readiness')
def readiness(b: Readiness):
    fallback=readiness_fallback(b.match_score, b.test_score, b.interview, b.missing_skills)
    prompt=json.dumps({'match_score':b.match_score,'test_score':b.test_score,'interview':b.interview,'missing_skills':b.missing_skills})
    def valid(x):
        return isinstance(x.get('readiness_score'),int) and 0<=x['readiness_score']<=100 and isinstance(x.get('skill_gaps'),list) and all(isinstance(g,dict) and isinstance(g.get('skill'),str) and isinstance(g.get('level'),int) for g in x['skill_gaps']) and isinstance(x.get('learning_path'),list) and all(isinstance(p,dict) and isinstance(p.get('step'),str) and isinstance(p.get('resource'),str) for p in x['learning_path'])
    return llm_json('Return JSON with readiness_score integer 0-100, skill_gaps array of {skill,level}, and learning_path array of {step,resource}.',prompt,fallback,valid)

RESOURCE_MAP = {
    'python': 'Python tutorial: https://docs.python.org/3/tutorial/',
    'javascript': 'JavaScript guide: https://developer.mozilla.org/en-US/docs/Web/JavaScript/Guide',
    'typescript': 'TypeScript handbook: https://www.typescriptlang.org/docs/handbook/intro.html',
    'react': 'React Learn: https://react.dev/learn',
    'html': 'freeCodeCamp Responsive Web Design: https://www.freecodecamp.org/learn/2022/responsive-web-design/',
    'css': 'MDN CSS: https://developer.mozilla.org/en-US/docs/Learn/CSS',
    'sql': 'SQLBolt interactive lessons: https://sqlbolt.com/',
    'git': 'Git book: https://git-scm.com/book/en/v2',
    'docker': 'Docker Get Started: https://docs.docker.com/get-started/',
    'fastapi': 'FastAPI tutorial: https://fastapi.tiangolo.com/tutorial/',
    'node.js': 'Node.js Learn: https://nodejs.org/en/learn',
    'java': 'Dev.java learning paths: https://dev.java/learn/',
    'machine learning': 'Google Machine Learning Crash Course: https://developers.google.com/machine-learning/crash-course',
    'data structures': 'VisuAlgo data structure visualizations: https://visualgo.net/en',
    'kubernetes': 'Kubernetes basics: https://kubernetes.io/docs/tutorials/kubernetes-basics/',
    'aws': 'AWS Skill Builder: https://skillbuilder.aws/',
    'linux': 'Linux Journey: https://linuxjourney.com/',
    'statistics': 'Khan Academy Statistics: https://www.khanacademy.org/math/statistics-probability',
    'pandas': 'Pandas getting started: https://pandas.pydata.org/docs/getting_started/',
    'rest apis': 'MDN HTTP overview: https://developer.mozilla.org/en-US/docs/Web/HTTP/Overview',
}

def readiness_fallback(match_score: int, test_score: int, interview: Dict[str, int], missing_skills: List[str]) -> Dict[str, Any]:
    interview_avg = sum(int(interview.get(key, 0)) for key in ('technical','hr','soft_skills')) / 3
    score = round(0.35*match_score + 0.30*test_score + 0.35*interview_avg)
    gaps = [{'skill':skill,'level':max(0,min(100,100-score))} for skill in missing_skills]
    path = []
    for skill in missing_skills[:5]:
        resource = RESOURCE_MAP.get(skill.casefold(), f'Search the {skill} learning path: https://roadmap.sh/ (choose the closest topic roadmap)')
        path.append({'step':f'Study {skill} fundamentals and practice a small task','resource':resource})
    return {'readiness_score':score,'skill_gaps':gaps,'learning_path':path}

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
