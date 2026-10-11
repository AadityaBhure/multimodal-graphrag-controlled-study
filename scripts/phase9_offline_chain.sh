#!/usr/bin/env bash
# Unattended offline Phase 9 chain: wait for the retrieval pool, then labels -> AR-01 training -> AR-02 calibration.
# It never touches validation/test, never calls Groq, and stops (non-zero) at the first failure.
set -euo pipefail
cd "$(dirname "$0")/.."
PY=.venv/Scripts/python.exe
export PYTHONDONTWRITEBYTECODE=1
echo "[chain] waiting for pool: $(date)"
until [ "$(ls artifacts/phase9/pool/graph | wc -l)" -ge 4404 ] && [ "$(ls artifacts/phase9/pool/text | wc -l)" -ge 4299 ] && [ "$(ls artifacts/phase9/pool/structured | wc -l)" -ge 840 ]; do sleep 30; done
sleep 30
echo "[chain] pool complete: $(date)"
$PY -I scripts/phase9_build_labels.py
echo "[chain] labels done: $(date)"
$PY -I scripts/phase9_calibrate_ar02.py
echo "[chain] AR-02 calibration done: $(date)"
$PY -I scripts/phase9_train_ar01.py 12
echo "[chain] AR-01 training done: $(date)"
