
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
uv run pytest app/tests -q --tb=short --cov=app

# Frontend quality checks (no dedicated test script configured)
cd frontend
npm run lint
```

AI Disclosure:
- Did you use an AI assistant (Copilot, ChatGPT, etc.)? (Yes/No)
	- Yes (OpenCode / Github Copilot)

- How did you verify the suggestions?
	- I ran focused tests after each change to validate the modified module behavior.
  - I ran the full backend suite to ensure there were no regressions:
    uv run pytest app/tests -q --tb=short --cov=app
  - I confirmed key integration paths (course discovery, learning resources, and API startup) by running targeted   tests and checking pass/fail results.
  - I manually reviewed changed files to ensure fallbacks, caching behavior, and error handling matched intended logic.
  - I validated runtime behavior with a demo script for dynamic recommendations and checked that fallback logic worked when external sources were unavailable.
  - I only kept changes that passed tests and produced expected output in the app flow.


- Give one example of a suggestion you rejected or changed:
	- I rejected relying only on static hardcoded skill-to-course mappings. I changed the design to include dynamic discovery (DuckDuckGo/fallback chain) for better coverage.
  - I rejected relying only on static hardcoded skill-to-course mappings. I changed the design to include dynamic discovery (DuckDuckGo/fallback chain) for better coverage.
  - I rejected leaving print-based error handling in services. I switched to centralized structured logging for better debugging and observability.
  - rejected keeping venv/pip-style setup in the README because my workflow uses uv. I updated commands to uv sync and uv run 
  - I rejected using a test command that assumes a frontend test script exists (npm run test) since it was not configured. I changed it to npm run lint for a valid quality check.

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
	- Introduce Email Service and Report Service using Kafka
	- Optimize the code written by AI (Find and Implement optimisation Gaps)

- Known limitations
	- Dynamic external sources can vary in quality and response time.
	- JSON-backed graph is not ideal for concurrent high-write workloads.
	- Frontend currently lacks a dedicated automated test command/script.
