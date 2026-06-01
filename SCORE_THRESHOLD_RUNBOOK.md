# SCORE_THRESHOLD Runbook

Use this when changing `SCORE_THRESHOLD` in `Backend/.env`.

## Why restart is required

- `SCORE_THRESHOLD` is read when backend starts from `routers/Resume_parsing/routers/config.py`.
- Changing `.env` does not update the running process automatically.

## Safe update procedure

1. Edit `Backend/.env`:
   - Example: `SCORE_THRESHOLD=10.0`
2. Restart backend server.
3. Call stage sync endpoint once:
   - `POST /api/resume/sync-stages`
4. Refresh recruiter pages:
   - Candidates
   - Resume Screening
   - Pipeline Overview

## Expected behavior after sync

- `score >= SCORE_THRESHOLD` -> `Applied`
- `score < SCORE_THRESHOLD` -> `Rejected`

## API / UI (single source of truth)

- Each row from `GET /api/resume/candidates` includes `threshold` (the current `SCORE_THRESHOLD` from `.env` at server start).
- `GET /api/resume/screening-config` returns `{ "score_threshold": <number> }` so the recruiter UI never assumes a fixed percentage (e.g. 25%) when a row omits `threshold`.

## Important notes

- Old records keep previous stage until sync runs.
- Duplicate resume screening attempts return an error and should not force candidate stage to `Rejected`.
- Frontend errors (network/API) should not force candidate stage to `Rejected`.
