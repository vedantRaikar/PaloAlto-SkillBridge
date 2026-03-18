import json
from typing import Optional, List, Dict
from app.core.config import settings
from app.services.heuristic_extractor import HeuristicExtractor

class SkillResolver:
    _instance = None
    _embeddings_model = None
    _skills_cache: Optional[List[str]] = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    def __init__(self):
        if SkillResolver._skills_cache is None:
            self._load_skills_cache()

    def _load_skills_cache(self):
        if settings.SKILLS_LIBRARY_PATH.exists():
            with open(settings.SKILLS_LIBRARY_PATH) as f:
                data = json.load(f)
            SkillResolver._skills_cache = [s['id'] for s in data.get('skills', [])]
        else:
            SkillResolver._skills_cache = []

    def resolve_skill(self, user_skill: str) -> Optional[str]:
        user_skill_lower = user_skill.lower().strip()
        skills = SkillResolver._skills_cache or []

        for skill in skills:
            if skill == user_skill_lower:
                return skill
            if skill in user_skill_lower or user_skill_lower in skill:
                return skill

        heuristic = HeuristicExtractor()
        matched = heuristic.extract_skills(user_skill)
        if matched:
            return list(matched)[0]

        return self._fuzzy_resolve(user_skill_lower, skills)

    def _fuzzy_resolve(self, user_skill: str, skills: List[str]) -> Optional[str]:
        import re
        
        user_clean = re.sub(r'[^\w]', '', user_skill)
        
        for skill in skills:
            skill_clean = re.sub(r'[^\w]', '', skill.lower())
            if user_clean == skill_clean:
                return skill
            
            if user_clean in skill_clean or skill_clean in user_clean:
                if len(user_clean) >= 2 and len(skill_clean) >= 2:
                    return skill

        return None

    def resolve_all_skills(self, user_skills: List[str]) -> Dict[str, Optional[str]]:
        resolved = {}
        for skill in user_skills:
            resolved[skill] = self.resolve_skill(skill)
        return resolved

    def add_alias(self, skill_id: str, alias: str):
        if not settings.SKILLS_LIBRARY_PATH.exists():
            return

        with open(settings.SKILLS_LIBRARY_PATH) as f:
            data = json.load(f)

        for skill in data.get('skills', []):
            if skill['id'] == skill_id:
                if 'aliases' not in skill:
                    skill['aliases'] = []
                if alias.lower() not in [a.lower() for a in skill['aliases']]:
                    skill['aliases'].append(alias.lower())
                break

        with open(settings.SKILLS_LIBRARY_PATH, 'w') as f:
            json.dump(data, f, indent=2)

        SkillResolver._skills_cache = None
        self._load_skills_cache()
