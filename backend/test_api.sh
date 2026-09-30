#!/usr/bin/env bash
set -e
B=http://localhost:8000/api
curl -fsS "$B/health"; curl -fsS "$B/jobs"
curl -fsS -X POST "$B/jobs" -H 'Content-Type: application/json' -d '{"company":"DemoCo","role":"Intern","required_skills":["Python"]}'
curl -fsS "$B/candidates?job_id=job-1"; curl -fsS "$B/faculty/batch-gaps"
printf 'Name: Priya Sharma\nPython SQL Git' >/tmp/skillbridge-resume.txt
curl -fsS -X POST "$B/resume/parse" -F file=@/tmp/skillbridge-resume.txt -F target_role='Software Engineer'
curl -fsS -X POST "$B/test/generate" -H 'Content-Type: application/json' -d '{"skills":["Python","SQL"]}'
curl -fsS -X POST "$B/test/submit" -H 'Content-Type: application/json' -d '{"answers":[{"id":1,"selected":0}],"questions":[{"id":1,"answer_index":0,"skill":"Python"}]}'
curl -fsS -X POST "$B/interview/next" -H 'Content-Type: application/json' -d '{"type":"technical","target_role":"Backend Engineer","history":[]}'
curl -fsS -X POST "$B/interview/score" -H 'Content-Type: application/json' -d '{"history":[],"target_role":"Backend Engineer"}'
curl -fsS -X POST "$B/readiness" -H 'Content-Type: application/json' -d '{"match_score":70,"test_score":80,"interview":{"technical":75,"hr":80,"soft_skills":85},"missing_skills":["Docker"]}'
echo
