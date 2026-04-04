"""
Fast-Track Learning Path Generator
=================================
Generates the fastest path to job readiness by prioritizing:
1. Essential skills only (minimum viable skillset)
2. Fastest courses (short duration, free options)
3. Highest impact skills first
"""

import re
from typing import List, Dict, Set, Optional, Tuple
import networkx as nx
from langchain_core.output_parsers import StrOutputParser
from langchain_core.prompts import PromptTemplate
from langchain_groq import ChatGroq
from app.core.config import settings
from app.services.knowledge_sources.onet_integration import SKILL_TO_COURSES, SKILL_ALIASES, get_skill_mapper
from app.services.learning_path_generator import SKILL_PREREQUISITES, SKILL_LEVELS, SKILL_CATEGORIES

DEFAULT_WEEKLY_STUDY_HOURS = 20.0
MAX_LLM_SKILL_HOURS = 120.0

# Community-estimated learning hours per skill (based on Coursera/bootcamp curricula,
# freeCodeCamp syllabi, and developer community surveys).
# These are the edge weights written into the knowledge graph for Dijkstra path-finding.
SKILL_DURATION_ESTIMATES: Dict[str, float] = {
    # Foundations / tools (quick wins)
    "git": 8.0, "github": 6.0,
    "linux": 20.0, "bash": 10.0, "scripting": 10.0,

    # Languages
    "python": 30.0, "javascript": 40.0, "typescript": 20.0,
    "java": 50.0, "golang": 35.0, "go": 35.0, "scala": 40.0,
    "r": 25.0, "rust": 45.0, "c": 40.0, "cpp": 45.0,

    # Web / frontend
    "html": 15.0, "css": 20.0,
    "react": 25.0, "vue": 20.0, "angular": 30.0, "next_js": 20.0,

    # Backend / frameworks
    "django": 20.0, "flask": 12.0, "fastapi": 12.0,
    "express": 15.0, "nodejs": 20.0, "node_js": 20.0,
    "api": 12.0, "rest": 10.0, "rest_api": 10.0, "graphql": 15.0,

    # Databases
    "sql": 15.0, "postgresql": 15.0, "postgres": 15.0,
    "mysql": 15.0, "mongodb": 12.0, "mongo": 12.0,
    "redis": 8.0, "elasticsearch": 15.0,

    # Cloud / DevOps
    "docker": 12.0, "kubernetes": 20.0,
    "aws": 25.0, "azure": 25.0, "gcp": 25.0,
    "terraform": 18.0, "ansible": 15.0,
    "ci_cd": 10.0, "jenkins": 10.0,

    # Data / AI / ML
    "pandas": 15.0, "numpy": 10.0, "sql": 15.0,
    "machine_learning": 45.0, "ml": 45.0,
    "deep_learning": 50.0, "neural_networks": 45.0,
    "data_science": 40.0, "data_analysis": 25.0,
    "statistics": 30.0,
    "tensorflow": 25.0, "pytorch": 25.0,
    "natural_language_processing": 40.0, "nlp": 40.0,
    "llms": 30.0, "embeddings": 20.0,
    "huggingface": 20.0, "transformers": 25.0,
    "computer_vision": 35.0, "opencv": 20.0,
    "ai": 30.0, "foundation_models": 25.0,
    "stt": 20.0, "tts": 20.0, "emotion_detection": 25.0,

    # Security
    "security": 30.0, "cybersecurity": 35.0,
    "network_security": 30.0, "penetration_testing": 40.0,

    # Architecture / methodology
    "microservices": 20.0, "microservice": 20.0,
    "scalable_microservices": 25.0,
    "software_architecture": 30.0, "system_design": 35.0,
    "algorithm_design": 30.0,
    "backend_infrastructure": 25.0,
    "kafka": 15.0, "rabbitmq": 12.0,
    "agile": 8.0, "testing": 12.0,
}

# Category-level fallback when an individual skill is not in SKILL_DURATION_ESTIMATES
CATEGORY_DURATION_ESTIMATES: Dict[str, float] = {
    "frontend": 20.0,
    "backend": 25.0,
    "devops": 18.0,
    "cloud": 25.0,
    "database": 15.0,
    "ai": 35.0,
    "data": 30.0,
    "security": 30.0,
    "programming": 35.0,
    "tools": 10.0,
    "methodology": 12.0,
}

DURATION_ESTIMATE_PROMPT = PromptTemplate.from_template('''
Estimate the minimum-viable job-readiness learning time in hours for this skill.

Skill: {skill}
Target role context: {target_role}

Rules:
- Return ONLY a number (hours), no words.
- Use realistic self-study pacing for an average learner.
- Target entry-level productivity, not deep interview mastery.
- Keep the estimate between 2 and 120.

Hours:
''')

# Skill impact scores (job market value 1-10)
SKILL_IMPACT = {
    # Programming languages (high impact)
    "python": 9, "javascript": 9, "typescript": 8, "java": 8, "golang": 8,
    # Web
    "html": 6, "css": 6, "react": 9, "vue": 7, "angular": 7,
    # Backend
    "api": 8, "rest_api": 8, "nodejs": 8, "express": 7, "django": 7, "flask": 7,
    # Database
    "sql": 9, "postgresql": 7, "mongodb": 7, "redis": 6,
    # DevOps & Cloud
    "git": 8, "docker": 9, "kubernetes": 8, "aws": 9, "azure": 8, "gcp": 7,
    "linux": 7, "ci_cd": 7, "terraform": 7, "ansible": 6,
    # Data & AI
    "machine_learning": 9, "data_science": 9, "statistics": 7, "deep_learning": 8,
    "tensorflow": 8, "pytorch": 8, "pandas": 7, "sql": 9,
    # Soft skills & methodology
    "agile": 6, "testing": 7, "debugging": 6, "code_review": 5,
    # Security
    "security": 8, "network_security": 7,
}

# Minimum viable skillset per role (essential skills only)
ROLE_MINIMUM_SKILLS = {
    "software_developer": ["programming", "git", "testing", "debugging", "code_review"],
    "frontend_developer": ["html", "css", "javascript", "react", "git"],
    "backend_developer": ["python", "sql", "api", "git", "databases"],
    "full_stack_developer": ["html", "css", "javascript", "react", "python", "sql", "api"],
    "data_scientist": ["python", "sql", "machine_learning", "statistics", "data_analysis"],
    "data_engineer": ["sql", "python", "etl", "data_warehousing", "spark"],
    "devops_engineer": ["linux", "docker", "git", "ci_cd", "scripting", "kubernetes"],
    "cloud_engineer": ["cloud_computing", "aws", "docker", "kubernetes", "terraform"],
    "machine_learning_engineer": ["python", "machine_learning", "deep_learning", "tensorflow", "mlops"],
    "cybersecurity_analyst": ["security", "network_security", "linux", "penetration_testing"],
}

# Fast-track courses (prioritized by: free > short > high rating)
# Format: skill -> [(course_title, provider, duration_hours, is_free), ...]
FAST_TRACK_COURSES = {
    "python": [
        ("freeCodeCamp Python", "freecodecamp", 30, True),
        ("Automate the Boring Stuff", "automatetheboringstuff", 20, True),
        ("Python Crash Course", "freecodecamp", 10, True),
    ],
    "javascript": [
        ("freeCodeCamp JavaScript", "freecodecamp", 50, True),
        ("JavaScript.info", "javascript.info", 15, True),
        ("Eloquent JavaScript", "eloquentjavascript", 20, True),
    ],
    "react": [
        ("React.dev Tutorial", "react.dev", 20, True),
        ("freeCodeCamp React", "freecodecamp", 40, True),
    ],
    "git": [
        ("Git Crash Course", "freecodecamp", 8, True),
        ("Git Handbook", "github", 2, True),
        ("Git Immersion", "gitimmersion", 8, True),
    ],
    "docker": [
        ("Docker Tutorial", "freecodecamp", 10, True),
        ("Docker Curriculum", "docker", 8, True),
        ("Play with Docker", "play-with-docker", 5, True),
    ],
    "kubernetes": [
        ("Kubernetes Basics", "kubernetes.io", 10, True),
        ("freeCodeCamp K8s", "freecodecamp", 15, True),
        ("K8s by Example", "kubernetes.io", 5, True),
    ],
    "sql": [
        ("SQL Tutorial", "freecodecamp", 12, True),
        ("SQLZoo", "sqlzoo", 10, True),
        ("Select Star SQL", "selectstarsql", 8, True),
    ],
    "linux": [
        ("Linux Server Course", "freecodecamp", 15, True),
        ("Linux Journey", "linuxjourney", 12, True),
        ("Linux Basics", "linuxfoundation", 8, True),
    ],
    "aws": [
        ("AWS Cloud Practitioner", "aws", 10, True),
        ("AWS Training", "aws", 20, True),
    ],
    "html": [
        ("Responsive Web Design", "freecodecamp", 40, True),
    ],
    "css": [
        ("CSS Tutorial", "freecodecamp", 20, True),
    ],
    "machine_learning": [
        ("Kaggle ML Course", "kaggle", 10, True),
        ("Stanford ML Course", "coursera", 60, False),
        ("Fast.ai", "fast.ai", 40, True),
    ],
    "ci_cd": [
        ("GitHub Actions", "github", 5, True),
        ("Jenkins Tutorial", "jenkins.io", 8, True),
    ],
    "scripting": [
        ("Bash Scripting", "freecodecamp", 8, True),
        ("Python Scripting", "freecodecamp", 10, True),
    ],
    "api": [
        ("REST API Tutorial", "restapitutorial", 10, True),
        ("API Design Guide", "hackernoon", 5, True),
    ],
}


class FastTrackGenerator:
    """
    Generates the fastest path to job readiness.
    
    Strategy:
    1. Identify minimum viable skills (essential skills only)
    2. Prioritize by: impact × speed (quick wins first)
    3. Select fastest courses (free + short duration)
    4. Skip nice-to-have skills for initial path
    """
    
    def __init__(self):
        self._skill_map: Dict[str, Set[str]] = {}
        self._skill_mapper = get_skill_mapper()
        self._duration_llm = None
        self._duration_cache: Dict[str, float] = {}
        self._build_skill_map()

    def _initialize_duration_llm(self):
        if self._duration_llm is None and settings.GROQ_API_KEY:
            self._duration_llm = ChatGroq(
                api_key=settings.GROQ_API_KEY,
                model="llama-3.1-8b-instant",
                temperature=0.0,
                max_tokens=32,
            )
    
    def _build_skill_map(self):
        """Build skill alias mapping for normalization."""
        for skill, aliases in SKILL_ALIASES.items():
            self._skill_map[skill.lower()] = set(a.lower() for a in aliases)
            self._skill_map[skill.lower()].add(skill.lower())
    
    def _normalize_skill(self, skill: str) -> str:
        """Normalize skill name."""
        return skill.lower().replace(" ", "_").replace("-", "_")
    
    def _get_skill_impact(self, skill: str) -> int:
        """Get job impact score (1-10)."""
        skill_norm = self._normalize_skill(skill)
        return SKILL_IMPACT.get(skill_norm, 5)
    
    def _safe_duration_hours(self, course: Dict, default: int = 20) -> int:
        """Normalize optional/non-numeric durations into a stable integer value."""
        value = course.get("duration_hours")
        if value in (None, ""):
            return default
        try:
            duration = float(value)
        except (TypeError, ValueError):
            return default
        if duration <= 0:
            return default
        return int(duration)

    def _estimate_duration_with_llm(self, skill: str, target_role: Optional[str] = None) -> Optional[float]:
        """Tier-1 estimate from LLM. Returns None on any failure."""
        self._initialize_duration_llm()
        if not self._duration_llm:
            return None

        skill_norm = self._normalize_skill(skill)
        cache_key = f"{skill_norm}|{self._normalize_skill(target_role or 'general')}"
        if cache_key in self._duration_cache:
            return self._duration_cache[cache_key]

        try:
            chain = DURATION_ESTIMATE_PROMPT | self._duration_llm | StrOutputParser()
            raw = chain.invoke({
                "skill": skill_norm.replace("_", " "),
                "target_role": (target_role or "general").replace("_", " "),
            })
            match = re.search(r"\d+(?:\.\d+)?", str(raw))
            if not match:
                return None

            hours = float(match.group(0))
            hours = max(2.0, min(MAX_LLM_SKILL_HOURS, hours))
            self._duration_cache[cache_key] = hours
            return hours
        except Exception:
            return None

    def estimate_total_hours_for_skills(
        self,
        skills: List[str],
        target_role: Optional[str] = None,
    ) -> int:
        """Estimate cumulative hours for a list of skills using the same duration stack."""
        total = 0.0
        for skill in skills:
            total += float(self._estimate_duration(skill, target_role))
        return int(round(total))

    def estimate_total_weeks_for_skills(
        self,
        skills: List[str],
        target_role: Optional[str] = None,
        weekly_hours: float = DEFAULT_WEEKLY_STUDY_HOURS,
    ) -> float:
        """Estimate weeks for skills using shared weekly pace assumptions."""
        total_hours = self.estimate_total_hours_for_skills(skills, target_role)
        return round(total_hours / max(weekly_hours, 1.0), 1)

    def _estimate_duration(self, skill: str, target_role: Optional[str] = None) -> float:
        """Community-estimated learning hours for a skill (used for graph edge weights).

        Tiers:
        1. LLM estimate (live)
        2. Skill-specific estimate from SKILL_DURATION_ESTIMATES
        3. Category-level estimate from CATEGORY_DURATION_ESTIMATES
        4. Hard fallback 20.0
        """
        skill_norm = self._normalize_skill(skill)

        llm_hours = self._estimate_duration_with_llm(skill_norm, target_role)
        if llm_hours is not None:
            return llm_hours

        if skill_norm in SKILL_DURATION_ESTIMATES:
            return SKILL_DURATION_ESTIMATES[skill_norm]
        for category, skills in SKILL_CATEGORIES.items():
            if skill_norm in [self._normalize_skill(s) for s in skills]:
                return float(CATEGORY_DURATION_ESTIMATES.get(category, 20.0))
        return 20.0

    def _get_course_duration(self, skill: str) -> int:
        """Get fastest course duration in hours for the API response field.

        Tiers:
        1. Live catalog: real (non-null, positive) duration_hours
        2. Community estimates (_estimate_duration)
        3. Hard fallback 20
        """
        skill_norm = self._normalize_skill(skill)

        runtime_courses = self._skill_mapper.get_learning_path(skill_norm, refresh_live=True)
        if runtime_courses:
            live_durations = [
                float(c["duration_hours"])
                for c in runtime_courses
                if c.get("duration_hours") not in (None, "")
                and float(c["duration_hours"]) > 0
            ]
            if live_durations:
                return int(min(live_durations))

        return int(self._estimate_duration(skill))

    def _order_skills_by_prerequisite_graph(
        self,
        user_skills: List[str],
        missing_skills: List[str],
        duration_map: Dict[str, float],
    ) -> List[Tuple[str, float]]:
        """Order missing skills by shortest-prerequisite-chain from user skills.

        Runs multi-source Dijkstra on the PREREQUISITE_FOR subgraph that was
        previously wired via GraphManager.populate_skill_prerequisites().
        Edge weight = community-estimated learning hours of the *target* skill.

        Skills closer to things the user already knows (shorter prerequisite chains)
        come first, naturally producing a dependency-respecting learning order.

        Returns:
            List of (skill, distance_hours) sorted ascending by distance.
        """
        from app.services.graph_manager import GraphManager

        gm = GraphManager()
        graph = gm.graph

        prereq_edges = [
            (u, v, data.get("weight", 20.0))
            for u, v, data in graph.edges(data=True)
            if data.get("type") == "PREREQUISITE_FOR"
        ]

        fallback = sorted(
            [(s, duration_map.get(self._normalize_skill(s), 20.0)) for s in missing_skills],
            key=lambda x: x[1],
        )

        if not prereq_edges:
            return fallback

        prereq_graph = nx.DiGraph()
        prereq_graph.add_weighted_edges_from(prereq_edges)

        sources = [
            self._normalize_skill(s)
            for s in user_skills
            if self._normalize_skill(s) in prereq_graph.nodes
        ]

        if not sources:
            return fallback

        try:
            dist_map = dict(
                nx.multi_source_dijkstra_path_length(prereq_graph, sources, weight="weight")
            )
        except Exception:
            return fallback

        result: List[Tuple[str, float]] = []
        for skill in missing_skills:
            skill_norm = self._normalize_skill(skill)
            dist = dist_map.get(skill_norm, duration_map.get(skill_norm, 20.0))
            result.append((skill, dist))

        result.sort(key=lambda x: x[1])
        return result
    
    def _get_fastest_courses(self, skill: str, max_results: int = 2) -> List[Dict]:
        """Get fastest courses for a skill (prioritize free + short)."""
        skill_norm = self._normalize_skill(skill)
        runtime_courses = self._skill_mapper.get_learning_path(skill_norm, refresh_live=True)
        if runtime_courses:
            sorted_runtime = sorted(runtime_courses, key=lambda c: (
                0 if c.get("is_free") else 1,
                self._safe_duration_hours(c),
            ))
            return sorted_runtime[:max_results]

        results = []
        
        if skill_norm in FAST_TRACK_COURSES:
            for title, provider, duration, is_free in FAST_TRACK_COURSES[skill_norm]:
                for course in SKILL_TO_COURSES.get(skill_norm, []):
                    if course.get("title", "").lower().replace(" ", "_") in title.lower():
                        results.append(course)
                        break
                else:
                    results.append({
                        "title": title,
                        "provider": provider,
                        "duration_hours": duration,
                        "level": "beginner",
                        "is_free": is_free,
                        "url": self._get_course_url(skill_norm, provider),
                        "description": f"Fast-track course for {skill}"
                    })
                if len(results) >= max_results:
                    break
        
        if not results and skill_norm in SKILL_TO_COURSES:
            courses = SKILL_TO_COURSES[skill_norm]
            sorted_courses = sorted(courses, key=lambda c: (
                0 if c.get("is_free") else 1,
                c.get("duration_hours", 20)
            ))
            results = sorted_courses[:max_results]
        
        return results
    
    def _get_course_url(self, skill: str, provider: str) -> str:
        """Get course URL for provider."""
        urls = {
            "freecodecamp": f"https://www.freecodecamp.org/news/search/?query={skill}",
            "kubernetes.io": "https://kubernetes.io/docs/tutorials/",
            "react.dev": "https://react.dev/learn",
            "aws": "https://explore.skillbuilder.aws/",
            "github": "https://github.com/skills",
            "kaggle": "https://www.kaggle.com/learn",
        }
        return urls.get(provider.lower(), f"https://www.google.com/search?q=learn+{skill}")
    
    def _get_minimum_skills(self, role: str, all_required: List[str]) -> List[str]:
        """Get minimum viable skillset for a role."""
        role_norm = self._normalize_skill(role)
        
        if role_norm in ROLE_MINIMUM_SKILLS:
            minimum = ROLE_MINIMUM_SKILLS[role_norm]
            return [s for s in minimum if s in all_required]
        
        skill_impacts = [(s, self._get_skill_impact(s)) for s in all_required]
        skill_impacts.sort(key=lambda x: x[1], reverse=True)
        
        top_skills = [s for s, _ in skill_impacts[:7]]
        return top_skills
    
    def _calculate_job_readiness_score(self, user_skills: List[str], target_skills: List[str]) -> float:
        """Calculate percentage of job readiness."""
        user_set = set(self._normalize_skill(s) for s in user_skills)
        target_set = set(self._normalize_skill(s) for s in target_skills)
        
        matched = len(user_set & target_set)
        total = len(target_set)
        
        if total == 0:
            return 0.0
        
        return round((matched / total) * 100, 1)
    
    def generate_fast_track(
        self,
        user_skills: List[str],
        target_role: str,
        all_role_skills: List[str],
        max_skills_to_learn: int = 5
    ) -> Dict:
        """
        Generate the fastest path to job readiness using graph-based Dijkstra ordering.

        Strategy:
        1. Build community-weighted prerequisite edges in the knowledge graph
        2. Run multi-source Dijkstra from user's existing skills
        3. Order missing skills by shortest prerequisite chain (quick-wins first)
        4. Pick top max_skills_to_learn skills and fetch their fastest courses

        Args:
            user_skills: Skills the user already has
            target_role: Target job role
            all_role_skills: All skills required for the role
            max_skills_to_learn: Maximum skills to include (default 5 for fast track)

        Returns:
            Dict with fast-track learning path
        """
        from app.services.graph_manager import GraphManager

        user_skill_set = set(self._normalize_skill(s) for s in user_skills)

        missing_skills = [
            s for s in all_role_skills
            if self._normalize_skill(s) not in user_skill_set
        ]

        minimum_skills = self._get_minimum_skills(target_role, all_role_skills)

        missing_minimum = [
            s for s in minimum_skills
            if self._normalize_skill(s) not in user_skill_set
        ]

        # 1. Build community duration map — used as Dijkstra edge weights
        duration_map: Dict[str, float] = {
            self._normalize_skill(s): self._estimate_duration(s, target_role)
            for s in all_role_skills
        }

        # 2. Build prereq lookup from the existing SKILL_PREREQUISITES catalogue
        prerequisites_map: Dict[str, List[str]] = {
            self._normalize_skill(s): [
                self._normalize_skill(p)
                for p in SKILL_PREREQUISITES.get(self._normalize_skill(s), [])
            ]
            for s in all_role_skills
        }

        # 3. Wire weighted PREREQUISITE_FOR edges into the knowledge graph
        gm = GraphManager()
        gm.populate_skill_prerequisites(all_role_skills, prerequisites_map, duration_map)

        # 4. Dijkstra-order missing skills: shortest prerequisite chain first
        missing_minimum_ordered = [
            s for s, _ in self._order_skills_by_prerequisite_graph(
                user_skills, missing_minimum, duration_map
            )
        ]
        missing_all_ordered = [
            s for s, _ in self._order_skills_by_prerequisite_graph(
                user_skills, missing_skills, duration_map
            )
        ]

        # 5. Fill fast-track list — preference: minimum skills first, then remaining
        fast_track_skills: List[str] = missing_minimum_ordered[:max_skills_to_learn]

        if len(fast_track_skills) < max_skills_to_learn:
            for skill in missing_all_ordered:
                if len(fast_track_skills) >= max_skills_to_learn:
                    break
                if skill not in fast_track_skills and self._normalize_skill(skill) not in user_skill_set:
                    fast_track_skills.append(skill)

        skill_data = []
        for skill in fast_track_skills:
            courses = self._get_fastest_courses(skill)
            duration = self._get_course_duration(skill)
            impact = self._get_skill_impact(skill)

            skill_data.append({
                "skill": skill,
                "impact_score": impact,
                "duration_hours": duration,
                "priority": impact / max(duration, 1),
                "courses": courses,
                "certifications": [],
            })

        # Preserve Dijkstra order — do NOT re-sort by priority here.
        # The prerequisite graph already puts "closest/cheapest" skills first.

        total_hours = sum(s["duration_hours"] for s in skill_data)
        total_weeks = round(total_hours / DEFAULT_WEEKLY_STUDY_HOURS, 1)

        current_readiness = self._calculate_job_readiness_score(
            user_skills, minimum_skills
        )
        after_readiness = self._calculate_job_readiness_score(
            user_skills + fast_track_skills, minimum_skills
        )

        return {
            "type": "fast_track",
            "target_role": target_role,
            "user_skills": user_skills,

            "minimum_skills": minimum_skills,
            "fast_track_skills": [s["skill"] for s in skill_data],

            "skill_details": skill_data,

            "current_readiness": current_readiness,
            "projected_readiness": after_readiness,

            "total_hours": total_hours,
            "total_weeks": total_weeks,

            "missing_skills": missing_skills,
            "nice_to_have_skills": [
                s for s in all_role_skills
                if s not in minimum_skills and self._normalize_skill(s) not in user_skill_set
            ],

            "study_plan": self._create_study_plan(skill_data),
        }
    
    def _create_study_plan(self, skill_data: List[Dict]) -> List[Dict]:
        """Create a compact skill-by-skill study plan.

        Keeps one entry per skill to avoid repetitive "part N" rows when a skill
        takes multiple weeks.
        """
        plan = []
        current_week = 1
        hours_per_week = int(DEFAULT_WEEKLY_STUDY_HOURS)

        for skill in skill_data:
            skill_hours = skill["duration_hours"]

            weeks_needed = max(1, (skill_hours + hours_per_week - 1) // hours_per_week)
            start_week = current_week
            end_week = current_week + weeks_needed - 1

            plan.append({
                "week": start_week,
                "end_week": end_week,
                "topic": f"Learn {skill['skill']}",
                "skill": skill["skill"],
                "hours": skill_hours,
                "hours_per_week": min(hours_per_week, skill_hours),
                "weeks_needed": weeks_needed,
                "courses": [c.get("title") for c in skill.get("courses", [])[:1]],
            })

            current_week = end_week + 1
        
        return plan


_fast_track_generator: Optional[FastTrackGenerator] = None


def get_fast_track_generator() -> FastTrackGenerator:
    global _fast_track_generator
    if _fast_track_generator is None:
        _fast_track_generator = FastTrackGenerator()
    return _fast_track_generator
