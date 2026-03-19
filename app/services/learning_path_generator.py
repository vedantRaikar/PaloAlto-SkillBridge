"""
Learning Path Generator
=======================
Generates ordered learning paths using graph shortest path and prerequisites.
"""

from typing import List, Dict, Set, Optional, Tuple
from app.services.graph_manager import GraphManager
from app.services.knowledge_sources.onet_integration import SKILL_TO_COURSES, SKILL_ALIASES

# Define skill prerequisites based on domain knowledge
# Format: skill -> [skills that should be learned first]
SKILL_PREREQUISITES: Dict[str, List[str]] = {
    # Programming fundamentals
    "html": [],
    "css": ["html"],
    "javascript": ["html", "css"],
    "typescript": ["javascript"],
    "python": [],
    "java": [],
    "sql": [],
    
    # Web frameworks
    "react": ["javascript", "html", "css"],
    "vue": ["javascript", "html", "css"],
    "angular": ["typescript", "javascript", "html", "css"],
    "django": ["python"],
    "flask": ["python"],
    "express": ["javascript", "nodejs"],
    "nodejs": ["javascript"],
    
    # Backend
    "api": ["python", "java", "javascript"],
    "rest_api": ["api"],
    "graphql": ["api"],
    
    # Databases
    "databases": ["sql"],
    "postgresql": ["sql"],
    "mongodb": ["databases"],
    "redis": ["databases"],
    
    # DevOps & Cloud
    "git": [],
    "docker": ["linux"],
    "kubernetes": ["docker", "linux"],
    "aws": ["linux", "networking"],
    "azure": ["cloud", "powershell"],
    "terraform": ["aws", "cloud"],
    
    # Data
    "machine_learning": ["python", "statistics", "sql"],
    "data_science": ["python", "sql", "statistics"],
    "deep_learning": ["machine_learning", "python"],
    
    # Security
    "security": ["networking", "linux"],
    "penetration_testing": ["security", "networking"],
}

# Skill categories for grouping
SKILL_CATEGORIES: Dict[str, str] = {
    "programming": ["python", "java", "javascript", "typescript", "golang", "rust", "c"],
    "frontend": ["html", "css", "react", "vue", "angular", "sass", "webpack"],
    "backend": ["api", "rest_api", "graphql", "nodejs", "express", "django", "flask"],
    "database": ["sql", "postgresql", "mysql", "mongodb", "redis", "databases"],
    "devops": ["git", "docker", "kubernetes", "ci_cd", "linux", "ansible"],
    "cloud": ["aws", "azure", "gcp", "terraform", "cloud_architecture"],
    "data": ["sql", "machine_learning", "data_science", "statistics", "pandas"],
    "security": ["security", "penetration_testing", "network_security"],
}

# Difficulty levels for skills
SKILL_LEVELS: Dict[str, str] = {
    "beginner": ["html", "css", "git", "python", "javascript", "sql", "linux"],
    "intermediate": ["react", "docker", "api", "postgresql", "aws", "nodejs"],
    "advanced": ["kubernetes", "machine_learning", "security", "system_design"],
}


class LearningPathGenerator:
    """
    Generates ordered learning paths from missing skills to target role.
    Uses topological sorting and dependency resolution.
    """
    
    def __init__(self):
        self.graph_manager = GraphManager()
        self._build_skill_dependencies()
    
    def _build_skill_dependencies(self):
        """Build complete skill dependency graph from multiple sources."""
        self._prerequisites: Dict[str, Set[str]] = {}
        
        for skill, prereqs in SKILL_PREREQUISITES.items():
            self._prerequisites[skill] = set(prereqs)
        
        for skill, aliases in SKILL_ALIASES.items():
            for alias in aliases:
                if alias.lower() not in self._prerequisites:
                    self._prerequisites[alias.lower()] = set()
    
    def get_skill_level(self, skill: str) -> str:
        """Determine skill difficulty level."""
        skill_lower = skill.lower()
        
        for level, skills in SKILL_LEVELS.items():
            if skill_lower in skills:
                return level
        
        for category, skills in SKILL_CATEGORIES.items():
            if skill_lower in skills:
                if category in ["frontend", "database"]:
                    return "intermediate"
                elif category in ["devops", "cloud", "data"]:
                    return "advanced"
        
        return "intermediate"
    
    def get_skill_category(self, skill: str) -> str:
        """Get category for a skill."""
        skill_lower = skill.lower()
        
        for category, skills in SKILL_CATEGORIES.items():
            if skill_lower in skills:
                return category
        
        return "general"
    
    def get_prerequisites(self, skill: str) -> List[str]:
        """Get direct prerequisites for a skill."""
        skill_lower = skill.lower()
        return list(self._prerequisites.get(skill_lower, set()))
    
    def get_all_prerequisites(self, skill: str, visited: Optional[Set[str]] = None) -> List[str]:
        """Get all prerequisites recursively (transitive closure)."""
        if visited is None:
            visited = set()
        
        if skill in visited:
            return []
        
        visited.add(skill)
        all_prereqs = set()
        
        direct_prereqs = self.get_prerequisites(skill)
        for prereq in direct_prereqs:
            all_prereqs.add(prereq)
            all_prereqs.update(self.get_all_prerequisites(prereq, visited))
        
        return list(all_prereqs)
    
    def topological_sort_skills(self, skills: List[str]) -> List[str]:
        """
        Sort skills in learning order using topological sort.
        Skills with fewer/more important prerequisites come first.
        """
        skill_set = set(s.lower() for s in skills)
        result = []
        remaining = set(skill_set)
        
        def can_learn(skill: str) -> bool:
            prereqs = self.get_prerequisites(skill)
            return all(p.lower() in result or p.lower() not in remaining 
                      for p in prereqs if p.lower() in skill_set)
        
        max_iterations = len(skills) * 2
        iteration = 0
        
        while remaining and iteration < max_iterations:
            learnable = [s for s in remaining if can_learn(s)]
            
            if not learnable:
                remaining_list = list(remaining)
                result.extend(remaining_list)
                break
            
            learnable.sort(key=lambda s: len(self.get_prerequisites(s)))
            result.append(learnable[0])
            remaining.remove(learnable[0])
            iteration += 1
        
        return result
    
    def group_skills_by_phase(self, skills: List[str]) -> Dict[str, List[str]]:
        """
        Group skills into learning phases.
        Phase 1: Foundation (no prerequisites in missing list)
        Phase 2: Intermediate (prerequisites met)
        Phase 3: Advanced (final skills)
        """
        sorted_skills = self.topological_sort_skills(skills)
        
        phases = {
            "foundation": [],
            "intermediate": [],
            "advanced": [],
            "specialized": []
        }
        
        skill_set = set(s.lower() for s in skills)
        
        for skill in sorted_skills:
            prereqs = [p for p in self.get_prerequisites(skill) if p.lower() in skill_set]
            level = self.get_skill_level(skill)
            
            if level == "beginner" or not prereqs:
                phases["foundation"].append(skill)
            elif level == "intermediate":
                phases["intermediate"].append(skill)
            elif level == "advanced":
                phases["advanced"].append(skill)
            else:
                phases["specialized"].append(skill)
        
        for key in phases:
            phases[key] = list(dict.fromkeys(phases[key]))
        
        return phases
    
    def generate_learning_path(
        self, 
        missing_skills: List[str],
        user_skills: Optional[List[str]] = None
    ) -> Dict:
        """
        Generate a complete ordered learning path.
        
        Returns:
            {
                "ordered_skills": [...],  # Skills in learning order
                "phases": {...},           # Skills grouped by phase
                "prerequisites": {...},   # Prerequisites for each skill
                "estimated_time": {...},   # Time estimate per skill
            }
        """
        user_skills = user_skills or []
        user_skill_set = set(s.lower() for s in user_skills)
        
        all_skills_needed = set()
        for skill in missing_skills:
            all_skills_needed.add(skill.lower())
            all_skills_needed.update(self.get_all_prerequisites(skill))
        
        skill_to_learn = [s for s in all_skills_needed if s not in user_skill_set]
        
        ordered_skills = self.topological_sort_skills(skill_to_learn)
        phases = self.group_skills_by_phase(skill_to_learn)
        
        prerequisites = {}
        for skill in ordered_skills:
            prereqs = self.get_prerequisites(skill)
            if prereqs:
                prerequisites[skill] = [p for p in prereqs if p.lower() in skill_to_learn or p.lower() in user_skill_set]
        
        time_estimates = {
            "beginner": 14,
            "intermediate": 21,
            "advanced": 30,
            "specialized": 45
        }
        
        return {
            "ordered_skills": ordered_skills,
            "phases": phases,
            "prerequisites": prerequisites,
            "total_skills_to_learn": len(skill_to_learn),
            "estimated_days": sum(time_estimates.get(self.get_skill_level(s), 21) for s in skill_to_learn),
            "estimated_weeks": round(sum(time_estimates.get(self.get_skill_level(s), 21) for s in skill_to_learn) / 7, 1),
            "category_breakdown": self._get_category_breakdown(skill_to_learn)
        }
    
    def _get_category_breakdown(self, skills: List[str]) -> Dict[str, int]:
        """Get count of skills per category."""
        breakdown = {}
        for skill in skills:
            category = self.get_skill_category(skill)
            breakdown[category] = breakdown.get(category, 0) + 1
        return breakdown


_path_generator: Optional[LearningPathGenerator] = None


def get_learning_path_generator() -> LearningPathGenerator:
    global _path_generator
    if _path_generator is None:
        _path_generator = LearningPathGenerator()
    return _path_generator
