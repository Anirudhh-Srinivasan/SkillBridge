#!/usr/bin/env bash
set -Eeuo pipefail

pids=()
for port in 8000 5173 5174; do
  if command -v fuser >/dev/null 2>&1; then fuser -k "${port}/tcp" 2>/dev/null || true; fi
done
cleanup() {
  trap - INT TERM EXIT
  for pid in "${pids[@]}"; do kill "$pid" 2>/dev/null || true; done
  for pid in "${pids[@]}"; do wait "$pid" 2>/dev/null || true; done
}
trap cleanup INT TERM EXIT

echo "Backend: http://localhost:8000"
echo "Student: http://localhost:5173"
echo "Dashboards: http://localhost:5174"

(cd backend && exec uvicorn main:app --host 0.0.0.0 --port 8000) & pids+=("$!")
(cd frontend-student && exec npm run dev -- --host 0.0.0.0) & pids+=("$!")
(cd frontend-dashboards && exec npm run dev -- --host 0.0.0.0) & pids+=("$!")

wait -n "${pids[@]}"
