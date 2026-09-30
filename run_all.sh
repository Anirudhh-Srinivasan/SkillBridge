#!/usr/bin/env bash
set -Eeuo pipefail

pids=()
cleanup() {
  trap - INT TERM EXIT
  for pid in "${pids[@]}"; do kill "$pid" 2>/dev/null || true; done
  for pid in "${pids[@]}"; do wait "$pid" 2>/dev/null || true; done
}
trap cleanup INT TERM EXIT

(cd backend && exec uvicorn main:app --host 0.0.0.0 --port 8000) & pids+=("$!")
(cd frontend-student && exec npm run dev -- --host 0.0.0.0) & pids+=("$!")
(cd frontend-dashboards && exec npm run dev -- --host 0.0.0.0) & pids+=("$!")

wait -n "${pids[@]}"
