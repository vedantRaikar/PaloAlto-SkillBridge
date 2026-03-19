# README Template

Candidate Name: Gokuldas Vedant Raikar

Scenario Chosen: SkillBridge - AI-powered skill gap analysis and dynamic learning resource recommendation using a knowledge graph.

Estimated Time Spent: ~5 hours

Quick Start:
- Prerequisites:
	- Python 3.10+
	- Node.js 18+
	- `uv` installed (https://docs.astral.sh/uv/)
	- Groq API key in `.env` (`GROQ_API_KEY`)
- Run Commands:
```bash
# 1) Backend setup
uv sync
uv run python -m spacy download en_core_web_md

# 2) Run backend (from repo root)
uv run uvicorn app.main:app --reload --host 0.0.0.0 --port 8000

# 3) Frontend setup and run (new terminal)
cd frontend
npm install
npm run dev
```
- Test Commands:
```bash
# Backend tests
uv run pytest app\tests\ -q --tb=short

# Frontend quality checks (no dedicated test script configured)
cd frontend
npm run lint
```

AI Disclosure:
- Did you use an AI assistant (Copilot, ChatGPT, etc.)? (Yes/No)
	- Yes (OpenCode / Github Copilot)
- How did you verify the suggestions?
	- Ran targeted and full backend test suites after each significant code change.
	- Manually inspected changed modules and validated fallback behavior for dynamic recommendations.
	- Confirmed no regressions by running `486` tests successfully.
- Give one example of a suggestion you rejected or changed:
	- A cache refactor initially broke compatibility with tests that expected list-form cache entries.
	- I changed the implementation to support both old list format and new TTL dictionary format, then re-ran tests.

Tradeoffs & Prioritization:
- What did you cut to stay within the 4–6 hour limit?
	- Full database migration (stayed on JSON-backed graph storage).
	- Advanced frontend E2E test coverage.
	- Production-grade auth/RBAC and deployment hardening.
- What would you build next if you had more time?
	- Introduce PostgreSQL + graph persistence strategy for better scale.
	- Add recommendation ranking signals (freshness, user preference, quality metrics).
	- Add frontend integration tests and end-to-end observability dashboards.
  - Dockerize the application and create a docker-compose file for orchestration
  - Develope CI pipeline with PR and Main merge build
  - Will implement API Access control through Azure AD app roles 
  - Develope Integration Test cases via Postman and Running in Postman
- Known limitations
	- Dynamic external sources can vary in quality and response time.
	- JSON-backed graph is not ideal for concurrent high-write workloads.
	- Frontend currently lacks a dedicated automated test command/script.
