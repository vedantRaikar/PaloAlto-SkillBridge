"""
Fast-Track Learning Path Generator
=================================
Generates the fastest path to job readiness by prioritizing:
1. Essential skills only (minimum viable skillset)
2. Fastest courses (short duration, free options)
3. Highest impact skills first
"""

from typing import List, Dict, Set, Optional, Tuple
from app.services.knowledge_sources.onet_integration import SKILL_TO_COURSES, SKILL_ALIASES, get_skill_mapper
from app.services.learning_path_generator import SKILL_PREREQUISITES, SKILL_LEVELS, SKILL_CATEGORIES

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
        self._build_skill_map()
    
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
    
    def _get_course_duration(self, skill: str) -> int:
        """Get fastest course duration in hours."""
        skill_norm = self._normalize_skill(skill)

        runtime_courses = self._skill_mapper.get_learning_path(skill_norm, refresh_live=True)
        if runtime_courses:
            return min(c.get("duration_hours", 20) for c in runtime_courses)
        
        if skill_norm in FAST_TRACK_COURSES:
            courses = FAST_TRACK_COURSES[skill_norm]
            return min(c[2] for c in courses)
        
        if skill_norm in SKILL_TO_COURSES:
            courses = SKILL_TO_COURSES[skill_norm]
            if courses:
                return min(c.get("duration_hours", 20) for c in courses)
        
        return 20
    
    def _get_fastest_courses(self, skill: str, max_results: int = 2) -> List[Dict]:
        """Get fastest courses for a skill (prioritize free + short)."""
        skill_norm = self._normalize_skill(skill)
        runtime_courses = self._skill_mapper.get_learning_path(skill_norm, refresh_live=True)
        if runtime_courses:
            sorted_runtime = sorted(runtime_courses, key=lambda c: (
                0 if c.get("is_free") else 1,
                c.get("duration_hours", 20),
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
        Generate the fastest path to job readiness.
        
        Args:
            user_skills: Skills the user already has
            target_role: Target job role
            all_role_skills: All skills required for the role
            max_skills_to_learn: Maximum skills to include (default 5 for fast track)
        
        Returns:
            Dict with fast-track learning path
        """
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
        
        fast_track_skills = missing_minimum[:max_skills_to_learn]
        
        if len(fast_track_skills) < max_skills_to_learn:
            remaining = [
                s for s in missing_skills
                if s not in fast_track_skills and self._normalize_skill(s) not in user_skill_set
            ]
            for skill in remaining:
                if len(fast_track_skills) >= max_skills_to_learn:
                    break
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
        
        skill_data.sort(key=lambda x: x["priority"], reverse=True)
        
        total_hours = sum(s["duration_hours"] for s in skill_data)
        total_weeks = round(total_hours / 15, 1)
        
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
        """Create a week-by-week study plan."""
        plan = []
        current_week = 1
        hours_per_week = 15
        
        remaining_hours = 0
        
        for skill in skill_data:
            skill_hours = skill["duration_hours"]
            
            if remaining_hours > 0:
                plan.append({
                    "week": current_week,
                    "topic": f"Continue {skill['skill']}",
                    "hours": remaining_hours,
                    "skill": skill["skill"],
                })
                remaining_hours = 0
                current_week += 1
            
            if skill_hours <= hours_per_week:
                plan.append({
                    "week": current_week,
                    "topic": f"Learn {skill['skill']}",
                    "hours": skill_hours,
                    "skill": skill["skill"],
                    "courses": [c.get("title") for c in skill.get("courses", [])[:1]],
                })
                current_week += 1
            else:
                weeks_needed = (skill_hours + hours_per_week - 1) // hours_per_week
                for w in range(weeks_needed):
                    h = min(hours_per_week, skill_hours - w * hours_per_week)
                    plan.append({
                        "week": current_week,
                        "topic": f"{'Learn' if w == 0 else 'Continue'} {skill['skill']}" + (f" (part {w+1})" if weeks_needed > 1 else ""),
                        "hours": h,
                        "skill": skill["skill"],
                        "courses": [c.get("title") for c in skill.get("courses", [])[:1]] if w == 0 else [],
                    })
                    current_week += 1
        
        return plan


_fast_track_generator: Optional[FastTrackGenerator] = None


def get_fast_track_generator() -> FastTrackGenerator:
    global _fast_track_generator
    if _fast_track_generator is None:
        _fast_track_generator = FastTrackGenerator()
    return _fast_track_generator
