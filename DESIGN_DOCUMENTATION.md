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
   - External knowledge sources (O*NET, DuckDuckGo live discovery, provider resources)
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
- Uses a multi-tier matching cascade for tolerant skill comparison.
- Designed to support both direct and inferred skill alignments.

How the matching cascade works:

The gap analyzer compares each required role skill against every user skill using a four-tier strategy. It stops at the first tier that produces a match:

| Tier | Strategy | Description | Cost |
|------|----------|-------------|------|
| 1 | Exact normalized match | Lowercase, underscore-normalize, then string equality check | O(1) set lookup |
| 2 | Alias map lookup | Bidirectional dictionary check against curated SKILL_ALIASES | O(1) |
| 3 | Graph-based SimRank | Structural similarity from shared roles, courses, and domains in the knowledge graph | O(1) cache lookup |
| 4 | Semantic embedding similarity | Sentence-transformer cosine similarity with threshold >= 0.75 | O(d) where d = 384 |

Performance optimizations:
- A pre-built normalized skill set enables O(1) exact lookups before the cascade runs.
- All match results are memoized in a bidirectional cache so each unique pair is computed at most once.
- SimRank scores are precomputed at startup over the full knowledge graph.
- Sentence-transformer canonical embeddings are precomputed at startup; only new user-skill embeddings are computed at request time.

Readiness calculation:
- Readiness = |matched_skills| / |required_skills|, representing a 0–1 ratio of how many target-role skills the user already possesses.

Resource mapping for gaps:
- Each missing skill is mapped to courses and certifications through a cached lookup chain: in-memory cache → knowledge graph query → web discovery fallback → graph persistence for future reuse.

### 4.4 Learning and Certification Recommendation Layer
Responsibility:
- Map missing skills to practical resources.

Recent design improvement:
- Dynamic recommendation path introduced with external knowledge discovery.
- DuckDuckGo-based live course discovery is used to supplement static mappings.
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
- Gap analysis (Tier 4 fallback), skill linking, and fallback skill mapping.

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

### 5.10 SimRank — Graph-Based Skill Similarity
Purpose:
- Compute structural similarity between skills based on their shared relationships in the knowledge graph, not their textual names.
- Catch domain relationships that text embeddings miss — for example, "Docker" and "Kubernetes" are similar because DevOps roles require both and the same courses teach them.

Where it is used:
- Gap analysis engine (Tier 3, between alias lookup and semantic embeddings).

How it works in SkillBridge:
1. A skill-only projection graph is built from the full knowledge graph. Two skills are connected if they share a common non-skill neighbor (a role that requires both, a course that teaches both, or a domain they both belong to). The edge weight equals the number of shared neighbors.
2. Iterative SimRank runs over this projected graph:
   - sim(a, a) = 1
   - sim(a, b) = (C / (|N(a)| × |N(b)|)) × Σ sim(N_i(a), N_j(b))
   - Where C is the decay factor (default 0.8) and N(x) are the neighbors of x.
3. The algorithm iterates a fixed number of rounds (default 5). Convergence is fast because the projected graph is typically sparse.
4. Only pairs with similarity above the threshold (default 0.3) are stored.
5. All scores are precomputed at startup and cached; runtime lookups are O(1).

Why chosen:
- Captures co-occurrence patterns that are invisible to text-based methods.
- Leverages the existing knowledge graph — no additional data sources needed.
- Complements semantic embedding similarity: embeddings handle name-level synonyms ("ML" ↔ "Machine Learning"), SimRank handles structural synonyms ("React" ↔ "Angular" via shared front-end courses/roles).
- Precomputed at startup so it adds zero latency to request-time matching.

Trade-off acknowledged:
- SimRank quality depends on graph density. A sparse graph with few courses and roles produces fewer useful similarity pairs.
- As the graph grows, computation cost increases quadratically with the number of skill nodes. For very large graphs (10K+ skills), approximate SimRank or random-walk methods would be needed.

## 6. AI Failure and Fallback Architecture

One of the core reliability concerns in SkillBridge is that several key workflows depend on services that can fail — the Groq LLM, spaCy NLP models, and external data sources like O\*NET. Rather than letting a single failure cascade into a broken user experience, the system is designed to degrade gracefully at every layer. If the smartest strategy does not work, something simpler takes over, and the user still gets a useful result.

This section walks through how each component handles that reality.

### 6.1 The Core Principle

The guiding idea is simple: always try the best approach, but never depend on it exclusively. Throughout the codebase, this looks like:

- Missing API keys are detected at startup so LLM paths silently disable themselves before any request is made — no runtime surprises.
- LLM exceptions are caught per-call, so a single bad response does not abort a larger workflow.
- Every AI-dependent method returns a well-typed empty result rather than `None` or an exception, so downstream code does not need special error-handling logic.
- Fallback events are logged, so failures are observable without disrupting the user-facing response.

### 6.2 Extraction Pipeline — The Clearest Example

The `ExtractionPipeline` is where the fallback architecture is most explicit. When a job description or resume comes in, the system runs three tiers in sequence and stops as soon as one of them produces usable output.

**Tier 1 — LLM extraction with NLP reinforcement**

This is the preferred path. `EntityExtractor` sends the text to the Groq LLM to extract skill entities with semantic understanding. `TopicExtractor`, also LLM-powered, identifies broader topics, implied skills, domains, and certifications. Alongside both of these, the `NLPExtractor` runs spaCy's named-entity recognition to independently identify entities from the text using trained linguistic models.

If the Groq API key is not configured, the two LLM extractors return empty results immediately, but the `NLPExtractor` continues on its own. Any exception thrown by any individual extractor is caught in isolation — the others are not affected. Tier 1 is considered successful if at least one skill node is extracted from any of these sources combined.

**Tier 2 — NLP-based fallback**

If Tier 1 produces nothing, the system falls back to `NLPExtractor` running independently, combined with `DynamicSkillExtractor` — a pure regex and keyword matcher running against a hardcoded list of over 150 common technology terms. There is no LLM call at this stage. The NLP model handles natural language structure, while the keyword matcher covers common technology names that appear verbatim. This tier handles the majority of cases where LLM output is unavailable or empty.

**Tier 3 — Human review queue**

If both Tier 1 and Tier 2 come back empty, the system does not return an error. Instead, it quietly adds the job to the pending review queue via `PendingQueue.add()`, returns a `pending_item_id` to the caller so the item can be tracked, and marks the response with `fallback_triggered=True`. A human reviewer can then handle the case manually.

### 6.3 Skill Resolver

`SkillResolver` uses the LLM to canonicalize skill name variants — mapping something like "pg" to "postgresql" or "k8s" to "kubernetes". If the Groq API key is missing, the LLM client is set to `None` at initialization and all resolver methods skip the LLM call entirely from that point forward.

When the LLM is unavailable or throws an exception, the resolver falls back to simple string normalization: lowercasing the skill name and replacing spaces with underscores. This keeps downstream matching functional — exact string comparisons still work — but the system loses its ability to recognize semantic equivalences between different names for the same technology.

### 6.4 Entity Linker

`EntityLinker` uses the LLM to figure out what category a skill belongs to and what its relationships are to other skills. To avoid unnecessary LLM calls, it checks an in-memory cache first — if the skill was seen before, the cached result is returned immediately.

If the cache misses, it checks the pre-loaded `skills_map` from the skills library JSON, which often already contains category information. Only if that also comes up empty does it call the LLM. If the LLM fails for any reason, it falls back to returning `"unknown"` for categories and empty lists for relationships, both of which are cached so the LLM is not retried for the same skill again in the same session. There is also a synchronous variant, `infer_skill_category_sync`, that never calls the LLM at all — it only checks the cache and the skills map, making it safe to call in tight loops.

### 6.5 Topic Extractor

`TopicExtractor` is responsible for pulling structured information out of job descriptions — things like technology categories, implied skills, soft skills, and certification mentions. It wraps four separate LLM calls, each following the same pattern.

First, it checks an in-memory cache. If the same text was processed recently, the cached structured result is returned without touching the LLM. If the API key is not set, it returns a typed empty object straight away. If the LLM call fails, it again returns a structured empty default — not `None`, but a properly typed object like `{tech_categories: [], implied_skills: [], domain: "none", experience_level: "unknown"}`. This means downstream code never has to check for null; it just gets an empty but valid result.

### 6.6 Chatbot

The chatbot is built in a way that intentionally limits how much of it depends on the LLM. Context assembly — querying the knowledge graph, looking up O\*NET data, finding relevant skills and certifications — is entirely deterministic and does not touch the LLM at all. No AI outage can disrupt this phase.

The LLM is only involved in the final step: synthesizing the assembled context into a natural language answer. If that call fails, the chatbot responds with a readable apology message that includes a truncated version of the error. If the input question is empty, the LLM call is skipped outright and the user gets a helpful prompt suggesting what to ask. Errors in individual context lookups, such as the certification lookup, cause that piece of context to simply be omitted rather than aborting the whole response.

### 6.7 Gap Analyzer

The gap analyzer has independent fallback chains for several of its responsibilities.

When looking up the skills required for a target role, it first checks the knowledge graph. If the graph has no data for that role, it falls back to querying the O\*NET API. If that also returns nothing, it defaults to an empty skill list.

For skill matching, it uses a four-tier cascade: exact normalized string comparison first, then bidirectional alias maps, then graph-based SimRank similarity (precomputed at startup), and finally the semantic embedding matcher as a last resort. Both SimRank and the semantic matcher are wrapped in try/except blocks, so if either is unavailable, matching falls through to the next tier or returns `False` rather than crashing.

For course and certification lookups, results for each skill are individually cached in memory. On a cache miss, the knowledge graph is queried, then external discovery services. Crucially, any exception for one skill is contained to that skill — the loop continues for all remaining skills rather than aborting early.

### 6.8 Course Discovery

`CourseAggregator` uses three tiers for course recommendations. It checks its in-memory cache first, which has a 24-hour TTL — if fresh results exist, they are returned immediately without any external call. On a cache miss, it runs a live DuckDuckGo-based discovery to find relevant learning resources. If live discovery returns nothing, it falls back to three hardcoded generic courses from freeCodeCamp and Coursera. This static result is also cached so repeated requests for the same skill do not keep hitting external sources unnecessarily.

`LearningResourceManager` takes a similar containment approach — any exception discovering resources for one skill results in an empty list for that skill, and the batch continues normally for the rest. Errors writing the results back to the graph are also silently swallowed, because a persistence failure should not surface as an API error.

### 6.9 Roadmap Generator

`RoadmapGenerator` uses the LLM to produce personalized learning milestones for each skill. If the LLM is unavailable or raises an exception, it returns a simple static set of three steps per skill — "Learn fundamentals", "Build projects", "Practice". Like the other components, milestone results are cached in memory, so repeated roadmap requests for the same skill set avoid redundant LLM calls entirely.

### 6.10 Summary

| Component | First Choice | If That Fails | Last Resort |
|---|---|---|---|
| Extraction Pipeline | Groq LLM + spaCy NER | spaCy NER + regex keyword matching | Human review queue |
| Skill Resolver | LLM canonicalization | Lowercase + underscore normalization | Identity mapping |
| Topic Extractor | LLM structured extraction | In-memory cache hit | Empty typed defaults |
| Entity Linker | LLM inference | `skills_map` lookup | `"unknown"` / empty relations |
| Chatbot | LLM answer synthesis | — | User-readable error message |
| Gap Analyzer (role skills) | Knowledge graph | O\*NET API | Empty skill list |
| Gap Analyzer (matching) | Exact string match | Alias map → SimRank | Semantic similarity (skipped on error) |
| Course Discovery | In-memory TTL cache | DuckDuckGo live discovery | Static hardcoded courses |
| Roadmap Generator | LLM milestone generation | In-memory cache hit | Static 3-step milestones per skill |

## 7. API Design Principles
The backend follows these API principles:
- Route grouping by domain (profile, extraction, courses, roadmap, jobs).
- Clear request/response schemas with validation.
- Predictable error shapes and status handling.
- Async-first endpoints where external I/O is involved.

This keeps the API easy to evolve and straightforward for frontend integration.

## 8. Non-Functional Considerations

### 8.1 Performance
- In-memory and file-based cache layers reduce repeated discovery calls.
- Structured fallback chain avoids hard failures under partial dependency outages.
- JSON graph structure keeps local development fast and debuggable.

### 8.2 Reliability
- Multiple extraction paths improve resilience to model/service failures.
- Fallback recommendations available when dynamic sources are not reachable.

### 8.3 Maintainability
- Service-oriented backend modules separate responsibilities.
- Pydantic schemas keep contracts explicit.
- Test suite validates key user flows and regression-prone routes.

### 8.4 Test-Driven Development for AI-Assisted Changes
All AI-assisted code changes in SkillBridge are validated using a test-driven development (TDD) strategy:
1. **Identify scope:** Before accepting any AI suggestion, the affected modules and their existing test coverage are identified.
2. **Module-level validation:** Focused, module-level tests are run after each change to verify the modified behavior in isolation.
3. **Full regression suite:** The complete backend test suite (`pytest app/tests/`) is run to catch regressions across all services.
4. **Integration path checks:** Key integration paths (course discovery, learning resources, API startup, gap analysis) are validated through targeted test execution.
5. **Manual review:** Changed files are manually reviewed to confirm fallback behavior, caching correctness, and error handling logic.
6. **Runtime verification:** Runtime behavior is validated against demo scenarios and fallback-triggered paths.
7. **Gate:** Only changes that pass all tests and produce expected output in the application flow are committed.

This workflow ensures that AI-generated code is held to the same quality bar as manually written code, preventing regressions and maintaining system reliability.

### 8.5 Security and Compliance (Current and Planned)
Current:
- Input validation and structured parsing.
- Environment-based secret handling.

Planned:
- Stronger auth and RBAC for multi-user deployment.
- Audit logging for sensitive profile operations.
- Data retention and deletion controls.

## 9. Trade-Offs and Design Decisions

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

## 10. Future Enhancements

### 10.1 Data Layer and Skill-to-Course Mapping
- Build a dedicated base data layer:
  - Introduce a structured schema for skill, course, and certification nodes to enforce consistency across all ingestion sources.
  - Replace raw JSON-backed graph storage with a well-defined persistence model that supports versioning and schema migration.
- Improve skill-to-course mapping in the knowledge graph:
  - Enrich graph edges with weights representing relevance, prerequisite depth, and provider quality scores.
  - Curate and validate course-to-skill relationships to reduce false positives from dynamic discovery.
  - Support many-to-many mappings where a single course covers multiple skills and a single skill is taught by multiple courses.
- Add data quality tooling:
  - Automated consistency checks for orphan nodes, duplicate edges, and missing relationships.
  - Periodic reconciliation jobs to align cached discovery results with the canonical graph.

### 10.2 Data and Recommendation Quality
- Multi-source recommendation fusion:
  - Curated catalogs + provider APIs.
- Ranking model using:
  - Relevance, quality signals, learner outcomes, and user constraints.
- Personalized recommendation scoring:
  - Time budget, preferred providers, current level, and goals.

### 10.3 Platform and Scalability
- Move from JSON persistence to PostgreSQL + Neo4j graph DB and/or graph database.
- Add background workers for extraction and recommendation refresh jobs.
- Add distributed caching for production deployments.

### 10.4 Product Experience
- More explainable recommendations (why each course is suggested).
- Skill progression simulation and milestone planning.
- Side-by-side role comparison and what-if analysis.

### 10.5 Observability and Operations
- Structured telemetry for extraction success/failure rates.
- Latency dashboards for critical API paths.
- Alerting for integration failures and cache miss spikes.

### 10.6 Security and Governance
- OAuth-based login and scoped user sessions.
- Profile privacy controls and consent-aware data ingestion.
- Enterprise-friendly audit and policy controls.

## 11. Suggested Deployment Evolution

Current state is suitable for local and small-team usage. For production hardening:
1. Introduce managed database and object storage.
2. Add worker queue and scheduled refresh pipelines.
3. Add authentication and tenant-aware authorization.
4. Deploy frontend and backend with CI/CD and environment promotion.
5. Add end-to-end monitoring and incident response playbooks.

## 12. Conclusion
SkillBridge has a strong foundation: modular service design, graph-aware reasoning, and a practical hybrid recommendation strategy.

The immediate architecture is optimized for iteration speed and explainability, while the roadmap enables a clear path toward production-grade scalability, personalization, and reliability.





