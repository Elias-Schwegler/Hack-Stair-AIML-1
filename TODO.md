# TODO — Suggested fixes and tasks

This file collects the suggested repository fixes and actionable steps so contributors can pick tasks and mark progress.

NOTE: I ran a quick audit and found import-path fragility, Docker entrypoint ambiguity, and missing helper files (`.env.example`, `.dockerignore`). Below are prioritized tasks with concrete steps and acceptance criteria.

---

## 1) Fix package imports (HIGH)

Problem
- Several modules manipulate `sys.path` or use top-level imports like `from services...`. This causes ModuleNotFoundError when running the package as a module (`python -m backend.main`) or via `uvicorn backend.main:app`.

Steps
- Replace top-level imports with package-relative imports. Example in `backend/main.py`:
  - Change `from services.azure_openai_service import AzureOpenAIService`
    to `from .services.azure_openai_service import AzureOpenAIService`
- Remove `sys.path.append('.')` / `sys.path.insert(...)` where not strictly necessary.
- Scan `backend/services/*.py`, `frontend/*.py` and `location-tools/*` for similar patterns and fix them.

Commands / checks
- After edits, run:
  ```powershell
  cd <repo-root>
  python -m backend.main
  # and
  uvicorn backend.main:app --reload
  ```

Acceptance criteria
- `python -m backend.main` starts without ModuleNotFoundError.
- `uvicorn backend.main:app` runs and serves `/health` and `/docs`.

---

## 2) Unify Docker Entrypoint & docker-compose (MEDIUM)

Problem
- The repository contains multiple possible entrypoints (`frontend.chat_server_mcp` vs `backend.main`). `Dockerfile` currently starts `frontend.chat_server_mcp`. This is OK if that module fully exposes the API and imports the backend properly, but it's fragile.

Steps
- Decide which module should be the canonical API entrypoint (recommendation: `backend.main` for a dedicated API).
- Update `Dockerfile` CMD and `docker-compose.yml` service (`backend`) to launch `uvicorn backend.main:app --host 0.0.0.0 --port 8000`.
- If `frontend.chat_server_mcp` remains the entrypoint, ensure it does not rely on sys.path hacks — prefer package-relative imports.

Commands / checks
- Build & run:
  ```powershell
  docker compose build
  docker compose up -d
  docker compose logs -f
  ```
- Verify endpoints:
  - http://localhost:8000/health
  - http://localhost:8000/docs

Acceptance criteria
- Backend container starts and `/health` returns success.
- Frontend static server (nginx) serves `index.html` at http://localhost:8080.

---

## 3) Add `.env.example` and `.dockerignore` (LOW)

Problem
- There's no `.env.example`, other contributors might not know which env vars are required. Docker build context includes all files and may be large.

Steps
- Create `.env.example` at repo root with keys (empty values) matching `.env` variables used in the code:
  - AZURE_OPENAI_API_KEY=
  - AZURE_OPENAI_ENDPOINT=
  - AZURE_OPENAI_API_VERSION=
  - AZURE_SEARCH_ENDPOINT=
  - AZURE_SEARCH_KEY=
  - AZURE_SEARCH_INDEX_NAME=
  - EMBEDDING_MODEL=
  - CHAT_MODEL=
  - AZURE_OPENAI_DEPLOYMENT_NAME=
- Create `.dockerignore` to exclude `.git`, `.venv`, `node_modules`, `__pycache__`, `data/` (if large), etc.

Commands
- No runtime commands; just create files and commit.

Acceptance criteria
- `.env.example` and `.dockerignore` exist in repo.

---

## 4) Improve `/health` endpoint (LOW)

Problem
- `/health` currently reports `azure_openai: connected` unconditionally. This can be misleading.

Steps
- Implement simple checks:
  - If AZURE_OPENAI_API_KEY is set, perform a lightweight client check or return `configured`.
  - For Azure Search, attempt a small search and reflect status.
- Fall back to `unknown` gracefully when keys are missing.

Acceptance criteria
- `/health` returns a JSON object indicating actual status or `not_configured` when keys are absent.

---

## 5) Optional: Add `.dockerignore` and optimize Dockerfiles (LOW)

Ideas
- Use a smaller final runtime image and multi-stage builds (build deps separately). Current Dockerfile is acceptable for development; for production consider multi-stage wheel build.
- Add `.dockerignore` to minimize context during `docker build`.

---

If you want, I can apply items 1 and 3 automatically now (imports fixes + add `.env.example` and `.dockerignore`) and open a follow-up PR suggestion. Reply with which tasks you want me to apply (1, 2, 3, 4, 5 or any combination). I will then implement them and run quick checks.
