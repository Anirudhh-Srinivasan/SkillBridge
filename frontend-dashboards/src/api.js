const API_BASE = import.meta.env.VITE_API_URL || 'http://localhost:8000/api'
const queryMock = new URLSearchParams(window.location.search).get('mock') === '1'
export const USE_MOCK = queryMock || import.meta.env.VITE_USE_MOCK === 'true'

const jobsMock = [
  { id: 'job-1', company: 'Razorpay', role: 'Frontend Engineer', required_skills: ['React', 'JavaScript', 'TypeScript', 'CSS', 'Accessibility'] },
  { id: 'job-2', company: 'Freshworks', role: 'Backend Engineer', required_skills: ['Python', 'FastAPI', 'PostgreSQL', 'Docker', 'Redis'] },
  { id: 'job-3', company: 'Zepto', role: 'Data Analyst', required_skills: ['SQL', 'Python', 'Statistics', 'Tableau', 'Communication'] },
  { id: 'job-4', company: 'Zoho', role: 'Product Designer', required_skills: ['Figma', 'UX Research', 'Prototyping', 'Design Systems', 'Communication'] },
  { id: 'job-5', company: 'PhonePe', role: 'Machine Learning Engineer', required_skills: ['Python', 'Machine Learning', 'TensorFlow', 'SQL', 'Statistics'] },
]

const candidatesMock = [
  ['Aarav Sharma', ['React','JavaScript','TypeScript','CSS','Accessibility','Git'], 94, 91],
  ['Ananya Iyer', ['React','JavaScript','CSS','Figma','Git','Communication'], 89, 86],
  ['Vihaan Patel', ['React','JavaScript','TypeScript','CSS','Node.js'], 85, 83],
  ['Diya Reddy', ['React','JavaScript','CSS','Accessibility','HTML'], 82, 80],
  ['Arjun Nair', ['JavaScript','React','TypeScript','CSS','Testing'], 79, 77],
  ['Meera Krishnan', ['Python','FastAPI','PostgreSQL','Docker','Redis','Git'], 96, 93],
  ['Aditya Verma', ['Python','FastAPI','PostgreSQL','Docker','AWS'], 88, 87],
  ['Ishita Singh', ['Python','PostgreSQL','Redis','Docker','Java'], 84, 82],
  ['Kabir Das', ['Python','FastAPI','PostgreSQL','Linux','Git'], 78, 79],
  ['Saanvi Rao', ['Python','FastAPI','Docker','Redis','Communication'], 73, 76],
  ['Reyansh Gupta', ['SQL','Python','Statistics','Tableau','Excel','Communication'], 92, 90],
  ['Aadhya Menon', ['SQL','Python','Statistics','Tableau','Power BI'], 87, 85],
  ['Vivaan Joshi', ['SQL','Python','Excel','Tableau','Storytelling'], 81, 81],
  ['Myra Kulkarni', ['SQL','Statistics','Python','Communication','Excel'], 76, 78],
  ['Atharv Shah', ['SQL','Python','Tableau','Statistics','Data viz'], 71, 74],
]
const candidates = candidatesMock.map(([name, skills, readiness_score, match_score], i) => ({ id: `stu-${String(i + 1).padStart(3, '0')}`, name, skills, readiness_score, match_score }))
const gapsMock = [
  { skill: 'System design', gap_percent: 78 }, { skill: 'Communication', gap_percent: 69 },
  { skill: 'Cloud fundamentals', gap_percent: 63 }, { skill: 'SQL optimization', gap_percent: 57 },
  { skill: 'Problem solving', gap_percent: 49 }, { skill: 'Testing & QA', gap_percent: 43 },
  { skill: 'Data structures', gap_percent: 36 }, { skill: 'Version control', gap_percent: 24 },
]

const delay = (ms = 220) => new Promise(resolve => setTimeout(resolve, ms))
async function request(path, options) {
  const response = await fetch(`${API_BASE}${path}`, { headers: { 'Content-Type': 'application/json', ...options?.headers }, ...options })
  if (!response.ok) throw new Error(`Request failed (${response.status})`)
  return response.json()
}

export async function getJobs() { if (USE_MOCK) { await delay(); return jobsMock } return request('/jobs') }
export async function getCandidates(jobId) {
  if (!jobId) return []
  if (USE_MOCK) {
    await delay()
    const job = jobsMock.find(item => item.id === jobId) || jobsMock[0]
    const relevant = candidates.filter(person => person.skills.some(skill => job.required_skills.includes(skill)) || jobId === 'job-4' || jobId === 'job-5')
    return relevant.map(person => {
      const overlap = person.skills.filter(skill => job.required_skills.includes(skill)).length
      const match_score = Math.min(99, Math.round((overlap / job.required_skills.length) * 72 + person.match_score * 0.28))
      return { ...person, match_score }
    }).sort((a, b) => b.match_score - a.match_score)
  }
  return request(`/candidates?job_id=${encodeURIComponent(jobId)}`)
}
export async function getBatchGaps() { if (USE_MOCK) { await delay(); return gapsMock } return request('/faculty/batch-gaps') }
export async function postJob(payload) {
  if (USE_MOCK) { await delay(350); const job = { id: `job-${Date.now()}`, ...payload }; jobsMock.unshift(job); return job }
  return request('/jobs', { method: 'POST', body: JSON.stringify(payload) })
}
