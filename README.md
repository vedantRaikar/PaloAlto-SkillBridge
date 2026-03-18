# Skill-Bridge Navigator

AI-powered career guidance system using Knowledge Graphs. Bridge the gap between your current skills and your dream career.

## Architecture

```
┌─────────────────┐     ┌─────────────────┐
│  Frontend       │     │  Backend API    │
│  (Next.js)      │────▶│  (FastAPI)      │
│  :3000          │     │  :8000          │
└─────────────────┘     └────────┬────────┘
                                 │
                        ┌────────▼────────┐
                        │  Knowledge Graph │
                        │  (NetworkX+JSON)│
                        └─────────────────┘
```

## Tech Stack

| Layer | Technology |
|-------|------------|
| Frontend | Next.js 14, React, Tailwind CSS, Recharts |
| Backend | Python 3.10+, FastAPI, NetworkX |
| LLM | Groq (Llama 3.1 - Free Tier) |
| NLP | spaCy (Local) |

## Prerequisites

- **Python 3.10+**
- **Node.js 18+** (for frontend)
- **npm or yarn**

## Quick Start

### 1. Clone & Setup Backend

```bash
cd SkillBridge

# Create virtual environment
python -m venv .venv

# Activate (Linux/Mac)
source .venv/bin/activate

# Activate (Windows)
.venv\Scripts\activate

# Install dependencies
pip install -e .

# Download spaCy model
python -m spacy download en_core_web_md
```

### 2. Setup Environment

```bash
# Create .env file
cat > .env << 'EOF'
GROQ_API_KEY=gsk_your_key_here
EOF

# Get free API key: https://console.groq.com/keys
```

### 3. Run Backend

```bash
# In one terminal
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

Backend runs at: http://localhost:8000

API docs at: http://localhost:8000/docs

### 4. Run Frontend

```bash
# In another terminal
cd frontend

# Install dependencies
npm install

# Run development server
npm run dev
```

Frontend runs at: http://localhost:3000

---

## Project Structure

```
SkillBridge/
├── app/                          # Python Backend
│   ├── api/routes/               # API endpoints
│   │   ├── extraction.py         # LLM extraction
│   │   ├── profile.py            # GitHub/Resume parsing
│   │   ├── roadmap.py            # Gap analysis & roadmaps
│   │   └── ingestion.py          # Manual data entry
│   ├── models/                   # Pydantic schemas
│   │   ├── graph.py              # Node, Link, Graph
│   │   ├── profile.py            # User profiles
│   │   └── user.py               # Skill gaps, roadmaps
│   ├── services/                 # Business logic
│   │   ├── graph_manager.py      # NetworkX wrapper
│   │   ├── gap_analyzer.py       # Skill gap calculation
│   │   ├── roadmap_generator.py  # Learning paths
│   │   ├── entity_extractor.py   # Groq LLM extraction
│   │   ├── heuristic_extractor.py # Regex fallback
│   │   ├── nlp_extractor.py      # spaCy extraction
│   │   ├── github_analyzer.py    # GitHub API
│   │   ├── resume_parser.py      # PDF/DOCX parsing
│   │   ├── profile_builder.py    # Profile orchestration
│   │   ├── task_queue.py         # Background tasks
│   │   └── pending_queue.py      # Human-in-loop queue
│   └── core/
│       └── config.py             # Settings
├── data/                         # Data files
│   ├── knowledge_graph.json      # Graph storage
│   ├── skills_library.json        # 50+ skills
│   └── pending_review.json        # Failed extractions
├── frontend/                     # Next.js Frontend
│   ├── src/app/                  # Pages
│   │   ├── page.tsx              # Dashboard
│   │   ├── profile/page.tsx      # Profile builder
│   │   ├── analyze/page.tsx      # Gap analysis
│   │   └── roadmap/page.tsx     # Learning roadmap
│   ├── src/components/           # UI components
│   └── src/lib/                  # API client, types
└── pyproject.toml
```

---

## API Endpoints

### Profile Management
| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/api/v1/profile/github` | Analyze GitHub profile |
| POST | `/api/v1/profile/resume` | Upload & parse resume |
| POST | `/api/v1/profile/merge` | Merge multiple sources |
| GET | `/api/v1/profile/{id}` | Get user profile |
| GET | `/api/v1/profile/{id}/readiness` | Get readiness scores |

### Roadmap & Analysis
| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/v1/roadmap/roles` | List all career paths |
| GET | `/api/v1/roadmap/{user}/{role}/gap-analysis` | Analyze skill gaps |
| GET | `/api/v1/roadmap/{user}/{role}/roadmap` | Get learning roadmap |

### Extraction (LLM)
| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/api/v1/extraction/job` | Extract from job description |
| POST | `/api/v1/extraction/job/background` | Background extraction |
| GET | `/api/v1/extraction/pending` | Pending review items |
| GET | `/api/v1/extraction/tasks` | Background task status |

---

## Usage Examples

### Build Profile from GitHub

```bash
curl -X POST http://localhost:8000/api/v1/profile/github \
  -H "Content-Type: application/json" \
  -d '{"github_username": "your-username"}'
```

### Analyze Skill Gap

```bash
curl http://localhost:8000/api/v1/roadmap/github_your-username/fullstack_developer/gap-analysis
```

### Get Learning Roadmap

```bash
curl http://localhost:8000/api/v1/roadmap/github_your-username/fullstack_developer/roadmap
```

---

## How It Works

### 1. Build Profile
- Connect GitHub → Extract programming languages
- Upload Resume → Extract skills via LLM
- Manual Entry → Add skills directly

### 2. Analyze Gap
- System compares your skills to role requirements
- Calculates readiness percentage
- Identifies missing skills

### 3. Generate Roadmap
- Maps missing skills to courses
- Creates week-by-week learning plan
- Provides milestones and resources

### 4. Ingest Knowledge
- Add job descriptions → LLM extracts skills
- Add courses → Links to skills
- Fallback to regex if LLM unavailable

---

## Environment Variables

| Variable | Required | Description |
|----------|----------|-------------|
| `GROQ_API_KEY` | Yes | Free from console.groq.com |
| `NEXT_PUBLIC_API_URL` | No | Frontend API URL (default: http://localhost:8000/api/v1) |

---

## Troubleshooting

### spaCy model not found
```bash
python -m spacy download en_core_web_md
```

### Frontend can't reach backend
```bash
# CORS is enabled by default
# Make sure backend runs on port 8000
uvicorn app.main:app --reload --port 8000
```

### LLM extraction fails
- Check `GROQ_API_KEY` is set correctly
- System falls back to heuristic (regex) extraction
- Failed extractions saved to `data/pending_review.json`

---

## Development

### Run Tests
```bash
# Backend
pytest

# Frontend
cd frontend
npm run test
```

### Lint
```bash
# Backend
ruff check app/

# Frontend
cd frontend
npm run lint
```

---

## License

MIT License
