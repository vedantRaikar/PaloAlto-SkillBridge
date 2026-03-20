"""
Optimized Learning Path Generator
===============================
Uses Dijkstra's algorithm and graph shortest path for optimal learning routes.
"""

from typing import List, Dict, Set, Optional, Tuple
import heapq
from app.services.knowledge_sources.onet_integration import SKILL_TO_COURSES, SKILL_ALIASES, get_skill_mapper
from app.services.learning_path_generator import (
    SKILL_PREREQUISITES, 
    SKILL_LEVELS, 
    SKILL_CATEGORIES,
    LearningPathGenerator
)

# Skill impact scores (job market value 1-10)
SKILL_IMPACT = {
    "python": 9, "javascript": 9, "typescript": 8, "java": 8, "golang": 8,
    "html": 6, "css": 6, "react": 9, "vue": 7, "angular": 7,
    "api": 8, "rest_api": 8, "nodejs": 8, "express": 7, "django": 7, "flask": 7,
    "sql": 9, "postgresql": 7, "mongodb": 7, "redis": 6,
    "git": 8, "docker": 9, "kubernetes": 8, "aws": 9, "azure": 8, "gcp": 7,
    "linux": 7, "ci_cd": 7, "terraform": 7, "ansible": 6,
    "machine_learning": 9, "data_science": 9, "statistics": 7, "deep_learning": 8,
    "tensorflow": 8, "pytorch": 8, "pandas": 7,
    "security": 8, "network_security": 7,
    "agile": 6, "testing": 7, "debugging": 6, "code_review": 5,
    "scripting": 7, "monitoring": 6, "infrastructure_as_code": 7,
}

# Minimum viable skillset per role
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

# Fast-track courses with duration
FAST_TRACK_COURSES = {
    "python": [("Python Basics", "freecodecamp", 10, True), ("Automate Stuff", "automatetheboringstuff", 20, True)],
    "javascript": [("JS Crash Course", "freecodecamp", 8, True), ("JS.info", "javascript.info", 15, True)],
    "react": [("React Tutorial", "react.dev", 5, True), ("FCC React", "freecodecamp", 10, True)],
    "git": [("Git Crash Course", "freecodecamp", 4, True), ("Git Handbook", "github", 2, True)],
    "docker": [("Docker Tutorial", "freecodecamp", 5, True), ("Docker Curriculum", "docker", 8, True)],
    "kubernetes": [("K8s Basics", "kubernetes.io", 5, True), ("FCC K8s", "freecodecamp", 8, True)],
    "sql": [("SQL Tutorial", "freecodecamp", 6, True), ("SQLZoo", "sqlzoo", 5, True)],
    "linux": [("Linux Journey", "linuxjourney", 8, True), ("FCC Linux", "freecodecamp", 10, True)],
    "aws": [("AWS Cloud Practitioner", "aws", 6, True), ("AWS Training", "aws", 15, True)],
    "ci_cd": [("GitHub Actions", "github", 3, True), ("Jenkins Tutorial", "jenkins.io", 6, True)],
    "scripting": [("Bash Scripting", "freecodecamp", 5, True), ("Python Scripting", "freecodecamp", 6, True)],
    "api": [("REST API Tutorial", "restapitutorial", 6, True), ("API Design", "hackernoon", 4, True)],
    "machine_learning": [("Kaggle ML", "kaggle", 5, True), ("Stanford ML", "coursera", 40, False)],
}


class GraphNode:
    """Node for Dijkstra's algorithm."""
    def __init__(self, skill: str, distance: float = float('inf'), path: List[str] = None):
        self.skill = skill
        self.distance = distance
        self.path = path or []
    
    def __lt__(self, other):
        return self.distance < other.distance
    
    def __repr__(self):
        return f"GraphNode({self.skill}, dist={self.distance})"


class DijkstraPathFinder:
    """
    Finds shortest learning paths using Dijkstra's algorithm.
    
    Graph Structure:
    - Nodes: Skills
    - Edges: Prerequisite relationships
    - Weights: Course duration (hours)
    """
    
    def __init__(self):
        self.adjacency: Dict[str, List[Tuple[str, float]]] = {}
        self.skill_durations: Dict[str, float] = {}
        self._duration_cache: Dict[str, float] = {}
        self.skill_mapper = get_skill_mapper()
        self._build_skill_map()
    
    def _build_skill_map(self):
        """Build skill alias mapping."""
        self.skill_map: Dict[str, Set[str]] = {}
        for skill, aliases in SKILL_ALIASES.items():
            self.skill_map[skill.lower()] = set(a.lower() for a in aliases)
            self.skill_map[skill.lower()].add(skill.lower())
    
    def _normalize_skill(self, skill: str) -> str:
        """Normalize skill name to canonical form."""
        return skill.lower().replace(" ", "_").replace("-", "_")
    
    def _get_duration(self, skill: str) -> float:
        """Get fastest course duration for a skill. Uses cached data to avoid live API calls."""
        skill_norm = self._normalize_skill(skill)

        if skill_norm in self._duration_cache:
            return self._duration_cache[skill_norm]

        duration = self._compute_duration(skill_norm)
        self._duration_cache[skill_norm] = duration
        return duration

    def _compute_duration(self, skill_norm: str) -> float:
        """Compute duration from static/cached sources (no live API calls)."""
        if skill_norm in FAST_TRACK_COURSES:
            return min(c[2] for c in FAST_TRACK_COURSES[skill_norm])

        if skill_norm in SKILL_TO_COURSES:
            courses = SKILL_TO_COURSES[skill_norm]
            if courses:
                return min(c.get("duration_hours", 20) for c in courses)

        cached_courses = self.skill_mapper.get_learning_path(skill_norm, refresh_live=False)
        if cached_courses:
            return min(c.get("duration_hours", 20) for c in cached_courses)
        
        return 20.0
    
    def _get_prerequisites(self, skill: str) -> List[str]:
        """Get direct prerequisites for a skill."""
        skill_norm = self._normalize_skill(skill)
        return SKILL_PREREQUISITES.get(skill_norm, [])
    
    def build_graph(self, skills: List[str], user_skills: List[str]):
        """Build prerequisite graph with duration weights.
        
        Edge direction: prerequisite -> dependent_skill
        Weight: duration of the dependent skill (time to learn after prerequisites)
        """
        self.adjacency.clear()
        self.skill_durations.clear()
        
        user_skill_set = set(self._normalize_skill(s) for s in user_skills)
        all_skills = set(self._normalize_skill(s) for s in skills)
        
        for skill in all_skills:
            self.adjacency[skill] = []
            self.skill_durations[skill] = self._get_duration(skill)
        
        for skill in all_skills:
            skill_duration = self._get_duration(skill)
            
            for prereq in self._get_prerequisites(skill):
                prereq_norm = self._normalize_skill(prereq)
                if prereq_norm in all_skills:
                    if prereq_norm not in self.adjacency:
                        self.adjacency[prereq_norm] = []
                        self.skill_durations[prereq_norm] = self._get_duration(prereq_norm)
                    self.adjacency[prereq_norm].append((skill, skill_duration))
    
    def dijkstra_shortest_path(
        self, 
        start_skills: List[str], 
        target_skills: List[str]
    ) -> Tuple[float, List[str]]:
        """
        Find minimum-time path from any start skill to all target skills.
        
        Uses Dijkstra's algorithm with skill duration as edge weight.
        
        Args:
            start_skills: Skills user already has
            target_skills: Skills user wants to learn
            
        Returns:
            (total_time, ordered_skills)
        """
        start_set = set(self._normalize_skill(s) for s in start_skills)
        target_set = set(self._normalize_skill(s) for s in target_skills)
        all_nodes = set(self.adjacency.keys()) | target_set
        
        distances: Dict[str, float] = {s: 0.0 for s in start_set}
        predecessors: Dict[str, Optional[str]] = {s: None for s in start_set}
        
        for node in all_nodes:
            if node not in distances:
                distances[node] = float('inf')
            if node not in predecessors:
                predecessors[node] = None
        
        pq = [(0.0, s) for s in start_set]
        visited: Set[str] = set()
        
        while pq:
            current_dist, current = heapq.heappop(pq)
            
            if current in visited:
                continue
            visited.add(current)
            
            if current in target_set:
                target_set.remove(current)
                if not target_set:
                    break
            
            for neighbor, weight in self.adjacency.get(current, []):
                if neighbor in visited:
                    continue
                
                new_dist = current_dist + weight
                if new_dist < distances[neighbor]:
                    distances[neighbor] = new_dist
                    predecessors[neighbor] = current
                    heapq.heappush(pq, (new_dist, neighbor))
        
        total_time = sum(
            self.skill_durations.get(self._normalize_skill(s), 20)
            for s in target_skills
        )
        
        ordered = self._reconstruct_order(target_skills, predecessors)
        
        return total_time, ordered
    
    def _reconstruct_order(
        self, 
        target_skills: List[str], 
        predecessors: Dict[str, Optional[str]]
    ) -> List[str]:
        """Reconstruct ordered skill list from predecessors."""
        ordered = []
        visited = set()
        
        def visit(skill: str):
            skill_norm = self._normalize_skill(skill)
            if skill_norm in visited:
                return
            visited.add(skill_norm)
            
            pred = predecessors.get(skill_norm)
            if pred:
                visit(pred)
            
            ordered.append(skill)
        
        for skill in target_skills:
            visit(skill)
        
        return ordered
    
    def find_all_paths(
        self,
        start_skills: List[str],
        target_skills: List[str],
        max_paths: int = 3
    ) -> List[Dict]:
        """
        Find multiple optimal paths with different trade-offs.
        
        Returns paths with different optimization criteria:
        - Fastest (minimum time)
        - Most impactful (highest skill impact)
        - Most efficient (impact per hour)
        """
        paths = []
        
        time, ordered_time = self.dijkstra_shortest_path(start_skills, target_skills)
        total_impact_all = sum(SKILL_IMPACT.get(self._normalize_skill(s), 5) for s in target_skills)
        
        paths.append({
            "type": "fastest",
            "criteria": "minimum_time",
            "total_hours": time,
            "total_weeks": round(time / 15, 1),
            "total_impact": total_impact_all,
            "skills": ordered_time,
            "reasoning": f"Optimized for speed: {round(time, 1)} hours total"
        })
        
        impact_ordered = sorted(
            target_skills, 
            key=lambda s: SKILL_IMPACT.get(self._normalize_skill(s), 5),
            reverse=True
        )
        total_impact = sum(SKILL_IMPACT.get(self._normalize_skill(s), 5) for s in target_skills)
        impact_time = sum(self._get_duration(s) for s in impact_ordered)
        
        paths.append({
            "type": "most_impactful",
            "criteria": "job_market_value",
            "total_impact": total_impact,
            "total_hours": impact_time,
            "total_weeks": round(impact_time / 15, 1),
            "skills": impact_ordered,
            "reasoning": f"Highest impact skills first: {total_impact} total market value"
        })
        
        efficiency = []
        for skill in target_skills:
            skill_norm = self._normalize_skill(skill)
            impact = SKILL_IMPACT.get(skill_norm, 5)
            duration = self._get_duration(skill)
            efficiency.append((skill, impact / max(duration, 1), impact, duration))
        
        efficiency.sort(key=lambda x: x[1], reverse=True)
        efficient_ordered = [s[0] for s in efficiency]
        efficient_time = sum(s[3] for s in efficiency)
        efficient_impact = sum(s[2] for s in efficiency)
        
        paths.append({
            "type": "most_efficient",
            "criteria": "impact_per_hour",
            "total_hours": efficient_time,
            "total_weeks": round(efficient_time / 15, 1),
            "total_impact": efficient_impact,
            "skills": efficient_ordered,
            "reasoning": f"Best impact per hour: {round(efficient_time, 1)} hours for all skills"
        })
        
        return paths


class OptimizedPathGenerator:
    """
    Generates optimized learning paths using graph algorithms.
    """
    
    def __init__(self):
        self.path_finder = DijkstraPathFinder()
        self.skill_mapper = get_skill_mapper()
        self._course_cache: Dict[str, List[Dict]] = {}
    
    def generate_optimized_paths(
        self,
        user_skills: List[str],
        target_role: str,
        all_role_skills: List[str],
        missing_skills: List[str]
    ) -> Dict:
        """
        Generate multiple optimized paths using Dijkstra's algorithm.
        
        Returns:
            {
                "paths": [path1, path2, path3],
                "recommendation": best_path,
                "analysis": {...}
            }
        """
        if not missing_skills:
            return {
                "paths": [],
                "recommendation": None,
                "analysis": {
                    "total_skills_to_learn": 0,
                    "already_job_ready": True
                }
            }
        
        self.path_finder.build_graph(missing_skills, user_skills)
        
        paths = self.path_finder.find_all_paths(
            start_skills=user_skills,
            target_skills=missing_skills,
            max_paths=3
        )
        
        for path in paths:
            path["skill_details"] = []
            for skill in path["skills"]:
                skill_norm = self.path_finder._normalize_skill(skill)
                path["skill_details"].append({
                    "skill": skill,
                    "duration_hours": self.path_finder._get_duration(skill),
                    "impact_score": SKILL_IMPACT.get(skill_norm, 5),
                    "prerequisites": self.path_finder._get_prerequisites(skill),
                    "courses": self._get_courses(skill)
                })
            
            path["study_plan"] = self._create_study_plan(path)
        
        fastest = min(paths, key=lambda p: p["total_hours"])
        most_impactful = max(paths, key=lambda p: p["total_impact"])
        
        recommendation = fastest
        if fastest["total_hours"] <= most_impactful["total_hours"] * 1.5:
            recommendation = fastest
        
        return {
            "paths": paths,
            "recommendation": recommendation,
            "fastest_path": fastest,
            "most_impactful_path": most_impactful,
            "analysis": {
                "total_skills_to_learn": len(missing_skills),
                "total_role_skills": len(all_role_skills),
                "user_skills_count": len(user_skills),
                "readiness": round(len(user_skills) / len(all_role_skills) * 100, 1) if all_role_skills else 0
            }
        }
    
    def _get_courses(self, skill: str) -> List[Dict]:
        """Get courses for a skill (cached per session)."""
        skill_norm = self.path_finder._normalize_skill(skill)

        if skill_norm in self._course_cache:
            return self._course_cache[skill_norm]

        cached_courses = self.skill_mapper.get_learning_path(skill_norm, refresh_live=False)
        if cached_courses:
            self._course_cache[skill_norm] = cached_courses[:3]
            return cached_courses[:3]

        courses = []
        if skill_norm in FAST_TRACK_COURSES:
            for title, provider, duration, is_free in FAST_TRACK_COURSES[skill_norm]:
                courses.append({
                    "title": title,
                    "provider": provider,
                    "duration_hours": duration,
                    "is_free": is_free,
                    "url": self._get_url(provider, skill)
                })
        
        if skill_norm in SKILL_TO_COURSES and len(courses) < 2:
            for c in SKILL_TO_COURSES[skill_norm][:2]:
                if {"title": c.get("title")} not in [{"title": x["title"]} for x in courses]:
                    courses.append(c)

        result = courses[:3]
        self._course_cache[skill_norm] = result
        return result
    
    def _get_url(self, provider: str, skill: str) -> str:
        """Get course URL."""
        urls = {
            "freecodecamp": f"https://www.freecodecamp.org/learn/",
            "kubernetes.io": "https://kubernetes.io/docs/tutorials/",
            "react.dev": "https://react.dev/learn",
            "aws": "https://explore.skillbuilder.aws/",
            "github": "https://github.com/skills",
            "kaggle": "https://www.kaggle.com/learn",
        }
        return urls.get(provider.lower(), f"https://www.google.com/search?q=learn+{skill}")
    
    def _create_study_plan(self, path: Dict) -> List[Dict]:
        """Create week-by-week study plan."""
        plan = []
        current_week = 1
        hours_per_week = 15
        week_hours = 0
        
        for skill_data in path.get("skill_details", []):
            skill_hours = skill_data["duration_hours"]
            
            if week_hours + skill_hours <= hours_per_week:
                plan.append({
                    "week": current_week,
                    "topic": f"Learn {skill_data['skill']}",
                    "hours": skill_hours,
                    "skill": skill_data["skill"],
                    "courses": [c.get("title") for c in skill_data.get("courses", [])[:1]]
                })
                week_hours += skill_hours
                
                if week_hours >= hours_per_week:
                    current_week += 1
                    week_hours = 0
            else:
                remaining = hours_per_week - week_hours
                if remaining > 0:
                    plan.append({
                        "week": current_week,
                        "topic": f"Start {skill_data['skill']}",
                        "hours": remaining,
                        "skill": skill_data["skill"],
                        "courses": []
                    })
                
                current_week += 1
                weeks_needed = int((skill_hours - remaining + hours_per_week - 1) // hours_per_week)
                
                for w in range(max(1, weeks_needed)):
                    h = min(hours_per_week, skill_hours - remaining - w * hours_per_week)
                    if h > 0:
                        plan.append({
                            "week": current_week,
                            "topic": f"{'Continue' if w > 0 else 'Continue'} {skill_data['skill']}",
                            "hours": max(0, h),
                            "skill": skill_data["skill"],
                            "courses": []
                        })
                        current_week += 1
                
                week_hours = 0
        
        return plan


_optimized_generator: Optional[OptimizedPathGenerator] = None


def get_optimized_path_generator() -> OptimizedPathGenerator:
    global _optimized_generator
    if _optimized_generator is None:
        _optimized_generator = OptimizedPathGenerator()
    return _optimized_generator
