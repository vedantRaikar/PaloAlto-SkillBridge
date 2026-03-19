# SkillBridge Design Documentation

## 1. Purpose and Vision
SkillBridge is an AI-powered career navigation platform that helps users understand their current skill profile, compare it with target roles, and get actionable recommendations for learning resources and certifications.

The system is designed to solve three core problems:
- Skill visibility: Users often do not know what skills they already have in a structured form.
- Gap clarity: Users struggle to map current capabilities to role requirements.
- Learning direction: Users need prioritized, practical recommendations instead of generic content.

## 2. High-Level System Design

### 2.1 Architecture Overview
SkillBridge follows a client-server architecture with clear separation of concerns:
- Frontend application for user interactions and workflow orchestration.
- Backend API for profile processing, extraction, graph operations, and recommendation generation.
- Knowledge Graph layer for relationship-aware skill, role, course, and certification mapping.
- Data files and caches for fast retrieval and fallback behavior.

### 2.2 Three-Layer Architecture
SkillBridge follows a three-layer architecture to keep the system modular, scalable, and easy to maintain.

Layer 1: Presentation Layer (User Interaction)
- What it contains:
   - Next.js pages and React components
   - Client-side state management (Zustand)
   - API client integration (Axios)
- What it does:
   - Collects user input (profile links, resumes, role selection)
   - Triggers backend API calls
   - Displays analysis outputs such as readiness, skill gaps, learning path, courses, and certifications

Layer 2: Application Layer (Business Logic and APIs)
- What it contains:
   - FastAPI route handlers grouped by domain (profile, extraction, roadmap, courses, jobs, chatbot)
   - Service modules such as Gap Analyzer, Learning Path Generator, Profile Builder, and Resource Manager
- What it does:
   - Validates and orchestrates requests
   - Runs extraction, matching, and recommendation workflows
   - Applies algorithms such as semantic matching, topological sorting, and shortest-path optimization
   - Coordinates fallbacks when preferred data sources are unavailable

Layer 3: Data and Knowledge Layer (Graph and Resource Backbone)
- What it contains:
   - Knowledge graph managed through NetworkX
   - JSON-backed stores (knowledge graph, skills library, courses, certifications, pending review)
   - External knowledge sources (O*NET, Wikidata SPARQL, provider resources)
- What it does:
   - Stores relationships among users, roles, skills, courses, and certifications
   - Serves graph queries used by the gap and roadmap engines
   - Caches discovered resources for performance and resilience

How the three layers work together
1. The Presentation Layer sends a user action to the Application Layer.
2. The Application Layer executes business logic and algorithmic analysis.
3. The Application Layer reads and writes graph/resource data through the Data and Knowledge Layer.
4. The processed result is returned to the Presentation Layer for visualization.

This separation ensures UI flexibility, cleaner service design, and a future-ready path for scaling storage and compute independently.

### 2.3 Core Data Flow
1. Input ingestion:
   - User provides GitHub profile, resume, job descriptions, or manual entries.
2. Skill extraction:
   - NLP and LLM-assisted extraction identifies entities (skills, tools, domains, roles).
3. Profile synthesis:
   - Extracted entities are normalized and merged into a user profile.
4. Gap analysis:
   - User profile is compared against role expectations from the knowledge base.
5. Recommendation generation:
   - Missing skills are mapped to courses and certifications.
6. Presentation:
   - Frontend pages display readiness metrics, gap details, and learning paths.

## 3. Technical Stack

### 3.1 Frontend
- Framework: Next.js (App Router), React, TypeScript
- UI and state: Tailwind CSS, Zustand, Radix UI primitives
- Charts and visualization: Recharts
- API communication: Axios

Why this stack:
- Strong developer velocity with component-driven architecture.
- Reliable TypeScript developer experience for safer UI logic.
- Good balance between performance, maintainability, and UI flexibility.

### 3.2 Backend
- Framework: FastAPI
- Language and typing: Python 3.10+, Pydantic v2
- Graph operations: NetworkX
- HTTP and integrations: httpx
- NLP and semantic support: spaCy, sentence-transformers
- LLM integration: LangChain + Groq

Why this stack:
- FastAPI provides high throughput, clear request validation, and auto-generated docs.
- Python ecosystem is strong for NLP, embeddings, and experimentation.
- NetworkX allows fast iteration for graph-centric recommendation logic.

### 3.3 Data and Storage
- Persistent graph-like data in JSON files for portability and simplicity.
- Knowledge base and learning resources stored under data/.
- Runtime cache files for discovered resources.

Current storage model is optimized for development speed and transparent inspection.

## 4. Core Design Components

### 4.1 Extraction and Entity Pipeline
Responsibility:
- Parse and extract structured entities from unstructured input.

Design notes:
- Multi-strategy extraction approach to improve robustness:
  - LLM extraction for richer semantic understanding.
  - NLP heuristics and fallback logic for reliability.
- Queue-based processing for background extraction and retry behavior.

### 4.2 Knowledge Graph Management
Responsibility:
- Model relationships across users, skills, roles, resources, and certifications.

Design notes:
- Graph nodes represent entities (skills, roles, courses, certifications).
- Graph edges encode relationships (requires, teaches, related_to, etc.).
- Graph supports traversal-based insights for gap and progression analysis.

Why we chose a knowledge graph-based approach:
- Relationship-first problem fit:
   - SkillBridge is fundamentally a relationship problem (user -> skills -> role requirements -> courses/certifications).
   - A graph models these links directly instead of forcing them into rigid table joins.
- Better recommendation explainability:
   - We can explain recommendations through explicit paths, for example:
      - "Role requires X"
      - "You have Y"
      - "Course Z teaches missing skill X"
   - This increases user trust compared to black-box outputs.
- Natural support for path-based algorithms:
   - Core logic (prerequisite ordering, shortest-path optimization, related-skill expansion) maps naturally to graph traversal.
   - This aligns well with the Dijkstra and topological ordering logic already used in the system.
- Easier incremental knowledge growth:
   - New roles, skills, courses, and certifications can be added as nodes/edges without schema redesign.
   - This is useful for evolving taxonomies and dynamic external sources.
- Robust fallback behavior:
   - Graph-first retrieval allows reuse of previously discovered resources.
   - If external APIs are slow/unavailable, existing graph relationships still support recommendations.

Trade-off acknowledged:
- For very large scale and high-concurrency workloads, graph persistence should evolve beyond JSON-backed storage.
- The current choice optimizes development speed and explainability, with a clear migration path to a production graph/database stack.

### 4.3 Gap Analysis Engine
Responsibility:
- Compute matched and missing skills for target roles.
- Calculate readiness and confidence indicators.

Design notes:
- Uses taxonomy mappings and semantic matching for tolerant comparison.
- Designed to support both direct and inferred skill alignments.

### 4.4 Learning and Certification Recommendation Layer
Responsibility:
- Map missing skills to practical resources.

Recent design improvement:
- Dynamic recommendation path introduced with external knowledge discovery.
- Wikidata SPARQL integration is used to supplement static mappings.
- TTL-based caching ensures recommendations refresh periodically while preserving performance.

Benefits:
- Reduces repetition from static-only recommendations.
- Improves coverage for new or less common skills.
- Maintains graceful fallback if external source is unavailable.

## 5. Algorithms Used

This section summarizes the major algorithms currently used in SkillBridge and how each contributes to system behavior.

### 5.1 Dijkstra's Shortest Path (Learning Path Optimization)
Purpose:
- Find a minimum-time skill acquisition path for users moving from current skills to target-role skills.

Where it is used:
- Optimized learning path generation module.

How it works in SkillBridge:
- Skills are modeled as graph nodes.
- Prerequisite relations are modeled as directed edges.
- Edge weight approximates learning time from course duration.
- Dijkstra computes the least-cost route over this weighted prerequisite graph.

Why chosen:
- Handles weighted graphs well.
- Produces deterministic, interpretable paths.
- Efficient for current graph size.

### 5.2 Topological Sort with Dependency Resolution
Purpose:
- Create a valid learning order where prerequisites are learned before dependent skills.

Where it is used:
- Base learning path generator and phase planner.

How it works in SkillBridge:
- Missing skills are treated as nodes in a dependency graph.
- The algorithm repeatedly selects learnable skills whose prerequisites are already satisfied or outside the remaining set.
- Skills are grouped into foundation/intermediate/advanced phases after ordering.

Why chosen:
- Natural fit for prerequisite-driven learning.
- Easy to explain to users as a staged roadmap.

### 5.3 Recursive Transitive Closure for Prerequisites
Purpose:
- Identify all indirect prerequisites for a target skill, not only direct ones.

Where it is used:
- Prerequisite expansion in learning path generation.

How it works in SkillBridge:
- Depth-first recursive traversal over prerequisite chains.
- Uses visited-set tracking to prevent repeated exploration and loops.

Why chosen:
- Lightweight and effective for hierarchical skill dependencies.

### 5.4 Semantic Similarity Matching (Embeddings + Cosine Similarity)
Purpose:
- Match skills with different wording but similar meaning (for example, "k8s" and "kubernetes").

Where it is used:
- Gap analysis, skill linking, and fallback skill mapping.

How it works in SkillBridge:
- Skills are embedded into vector space using sentence-transformer embeddings.
- Cosine similarity is computed between vectors.
- Matching uses threshold-based acceptance combined with alias and exact checks.

Why chosen:
- Improves recall beyond strict string matching.
- Handles realistic user input variation.

### 5.5 Jaccard Similarity for Token-Level Matching
Purpose:
- Provide a fast lexical fallback when embedding-based matching is unavailable or unnecessary.

Where it is used:
- Skill-to-skill similarity scoring in knowledge source matching.

How it works in SkillBridge:
- Converts skill phrases into token sets.
- Computes Jaccard score as intersection over union.
- Uses threshold to select best static mapping candidate.

Why chosen:
- Computationally cheap and interpretable.
- Useful as a deterministic fallback tier.

### 5.6 Levenshtein Distance and Sequence Similarity
Purpose:
- Detect near-duplicate entities and normalize noisy skill text.

Where it is used:
- Entity deduplication pipeline.

How it works in SkillBridge:
- Levenshtein edit distance measures character-level transformation cost.
- Sequence similarity ratio (difflib) provides an additional normalized similarity score.
- Combined thresholds decide whether entities are merged.

Why chosen:
- Robust against minor typos and naming variants.
- Improves knowledge graph consistency.

### 5.7 Rule-Based Normalization and Alias Canonicalization
Purpose:
- Convert shorthand and alternate names into canonical skill identifiers.

Where it is used:
- Entity extraction, deduplication, and gap comparison.

How it works in SkillBridge:
- Applies normalization rules (case folding, punctuation cleanup, underscore normalization).
- Uses alias dictionaries to map variants to canonical forms.

Why chosen:
- Fast and deterministic.
- Reduces false negatives before heavier semantic algorithms run.

### 5.8 Regex-Based Extraction and Parsing
Purpose:
- Extract useful signals from unstructured text and HTML in fallback mode.

Where it is used:
- Heuristic extraction pipeline and dynamic course discovery parsing.

How it works in SkillBridge:
- Pattern matching over job/resume text for skill phrases and structures.
- HTML anchor parsing for runtime-discovered course links.

Why chosen:
- Reliable fallback when LLM responses are unavailable or low confidence.
- Very fast for narrow extraction tasks.

### 5.9 Multi-Tier Fallback Selection Strategy
Purpose:
- Ensure the recommendation system remains available even if one source fails.

Where it is used:
- Course recommendation and knowledge lookup.

How it works in SkillBridge:
- Ordered strategy: dynamic external discovery -> cached resources -> static knowledge mappings -> semantic/token fallback.
- Returns the highest-quality available result for the current context.

Why chosen:
- Improves reliability and user experience.
- Prevents hard failures due to partial upstream outages.

## 6. API Design Principles
The backend follows these API principles:
- Route grouping by domain (profile, extraction, courses, roadmap, jobs).
- Clear request/response schemas with validation.
- Predictable error shapes and status handling.
- Async-first endpoints where external I/O is involved.

This keeps the API easy to evolve and straightforward for frontend integration.

## 7. Non-Functional Considerations

### 6.1 Performance
- In-memory and file-based cache layers reduce repeated discovery calls.
- Structured fallback chain avoids hard failures under partial dependency outages.
- JSON graph structure keeps local development fast and debuggable.

### 6.2 Reliability
- Multiple extraction paths improve resilience to model/service failures.
- Fallback recommendations available when dynamic sources are not reachable.

### 6.3 Maintainability
- Service-oriented backend modules separate responsibilities.
- Pydantic schemas keep contracts explicit.
- Test suite validates key user flows and regression-prone routes.

### 6.4 Security and Compliance (Current and Planned)
Current:
- Input validation and structured parsing.
- Environment-based secret handling.

Planned:
- Stronger auth and RBAC for multi-user deployment.
- Audit logging for sensitive profile operations.
- Data retention and deletion controls.

## 8. Trade-Offs and Design Decisions

### Decision 1: JSON-based data store instead of relational database
Pros:
- Rapid prototyping, low setup overhead, easy local portability.
Cons:
- Limited transactional guarantees and multi-writer safety.

### Decision 2: Graph-centric recommendation model
Pros:
- Natural fit for role-skill-resource relationships and path reasoning.
Cons:
- Additional complexity when scaling to very large graphs.

### Decision 3: Hybrid static + dynamic recommendation sources
Pros:
- Reliability from static data plus freshness from external sources.
Cons:
- Requires cache policy tuning and source quality checks.

## 9. Future Enhancements

### 8.1 Data and Recommendation Quality
- Multi-source recommendation fusion:
  - Wikidata + curated catalogs + provider APIs.
- Ranking model using:
  - Relevance, quality signals, learner outcomes, and user constraints.
- Personalized recommendation scoring:
  - Time budget, preferred providers, current level, and goals.

### 8.2 Platform and Scalability
- Move from JSON persistence to PostgreSQL and/or graph database.
- Add background workers for extraction and recommendation refresh jobs.
- Add distributed caching for production deployments.

### 8.3 Product Experience
- More explainable recommendations (why each course is suggested).
- Skill progression simulation and milestone planning.
- Side-by-side role comparison and what-if analysis.

### 8.4 Observability and Operations
- Structured telemetry for extraction success/failure rates.
- Latency dashboards for critical API paths.
- Alerting for integration failures and cache miss spikes.

### 8.5 Security and Governance
- OAuth-based login and scoped user sessions.
- Profile privacy controls and consent-aware data ingestion.
- Enterprise-friendly audit and policy controls.

## 10. Suggested Deployment Evolution

Current state is suitable for local and small-team usage. For production hardening:
1. Introduce managed database and object storage.
2. Add worker queue and scheduled refresh pipelines.
3. Add authentication and tenant-aware authorization.
4. Deploy frontend and backend with CI/CD and environment promotion.
5. Add end-to-end monitoring and incident response playbooks.

## 11. Conclusion
SkillBridge has a strong foundation: modular service design, graph-aware reasoning, and a practical hybrid recommendation strategy.

The immediate architecture is optimized for iteration speed and explainability, while the roadmap enables a clear path toward production-grade scalability, personalization, and reliability.





