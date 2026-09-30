// Toggle this locally or set VITE_USE_MOCK=false to connect to FastAPI.
export const USE_MOCK = import.meta.env.VITE_USE_MOCK !== undefined ? import.meta.env.VITE_USE_MOCK === 'true' : true
const BASE = import.meta.env.VITE_API_URL || 'http://localhost:8000/api'
const delay = (v) => new Promise(r => setTimeout(() => r(v), 450 + Math.random() * 400))
const questions = [
 ['React', 'Which hook stores component state?', ['useMemo','useState','useRef','useEffect'], 1], ['React', 'What does JSX compile to?', ['CSS','JavaScript calls','HTML','JSON'], 1], ['JavaScript', 'Which creates a block-scoped variable?', ['var','let','function','this'], 1], ['TypeScript', 'Why use TypeScript?', ['Runtime speed','Static type checks','Database access','Styling'], 1], ['CSS', 'Which layout is best for two dimensions?', ['Flexbox','Grid','Float','Inline'], 1], ['React', 'What key helps React track list items?', ['id prop','key prop','className','index only'], 1], ['JavaScript', 'What does async return?', ['Number','Promise','Array','Boolean'], 1], ['Git', 'Which command creates a branch?', ['git add','git branch','git push','git log'], 1], ['REST APIs', 'A successful creation usually returns?', ['200','201','404','500'], 1], ['React', 'What is a controlled input?', ['DOM-managed','State-managed','Read-only','A CSS input'], 1]
].map(([skill, question, options, answer_index], i) => ({ id: `q${i + 1}`, skill, question, options, answer_index }))
const mock = {
 parse: () => delay({ name:'Aarav Sharma', skills:['React','JavaScript','HTML','CSS','Git','REST APIs'], missing_skills:['TypeScript','Testing','System Design','Docker'], match_score:72 }),
 generate: () => delay({ questions }),
 submit: ({answers, questions: qs}) => { const score = Math.round(answers.filter(a => qs.find(q=>q.id===a.id)?.answer_index===a.selected).length / qs.length * 100); return delay({ score, per_skill:{ React:80, JavaScript:70, TypeScript:45, CSS:75, 'REST APIs':65 } }) },
 next: ({type, history}) => {
   const technical = ['Walk me through how React reconciliation improves rendering performance.','How would you structure state for a multi-step checkout?','Explain the difference between debounce and throttle.','How do you diagnose a slow API-backed page?','Design an error-handling strategy for a frontend app.']
   const hr = ['Tell me about a time you learned a difficult skill quickly.','How do you handle feedback on your work?','Describe a time you worked through a conflict with a teammate.','What kind of team environment helps you thrive?','Why does this role appeal to you?']
   const answers = history.filter(message => message.role === 'user').length
   const set = type === 'technical' ? technical : hr
   if (answers >= 5) return delay({ reply: `${type === 'technical' ? 'Technical' : 'HR'} round complete.`, done:true })
   return delay({ reply:set[answers], done:false })
 },
 score: () => delay({ technical:76, hr:84, soft_skills:81, feedback:'You communicate clearly and show strong practical reasoning. Strengthen TypeScript depth and system-design vocabulary before interviews.' }),
 readiness: ({match_score,test_score,interview,missing_skills}) => delay({ readiness_score:Math.round(match_score*.35+test_score*.3+((interview.technical+interview.hr+interview.soft_skills)/3)*.35), skill_gaps:missing_skills.map((skill,i)=>({skill,level:[75,64,58,42][i]||50})), learning_path:[{step:'Strengthen TypeScript foundations',resource:'TypeScript Handbook — Everyday Types'},{step:'Build a tested React feature',resource:'React Testing Library tutorial'},{step:'Practice scalable UI architecture',resource:'Frontend system design checklist'}] })
}
async function request(path, opts={}) { const r=await fetch(`${BASE}${path}`, { headers:{'Content-Type':'application/json',...(opts.headers||{})}, ...opts }); if(!r.ok) throw new Error((await r.text()) || 'Request failed'); return r.json() }
export const api = {
 parse: (file,target_role) => { if(USE_MOCK) return mock.parse(); const form=new FormData(); form.append('file',file); form.append('target_role',target_role); return fetch(`${BASE}/resume/parse`,{method:'POST',body:form}).then(async r=>{if(!r.ok) throw new Error(await r.text()); return r.json()}) },
 generate: (skills) => USE_MOCK ? mock.generate() : request('/test/generate',{method:'POST',body:JSON.stringify({skills})}),
 submit: (answers, questions) => USE_MOCK ? mock.submit({answers,questions}) : request('/test/submit',{method:'POST',body:JSON.stringify({answers,questions})}),
 next: (type,target_role,history) => USE_MOCK ? mock.next({type,history}) : request('/interview/next',{method:'POST',body:JSON.stringify({type,target_role,history})}),
 scoreInterview: (history,target_role) => USE_MOCK ? mock.score() : request('/interview/score',{method:'POST',body:JSON.stringify({history,target_role})}),
 readiness: (data) => USE_MOCK ? mock.readiness(data) : request('/readiness',{method:'POST',body:JSON.stringify(data)})
}
