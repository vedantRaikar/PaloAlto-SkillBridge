import json
import re
from typing import Optional, List, Dict, Set, Any
from langchain_groq import ChatGroq
from langchain_core.prompts import PromptTemplate
from langchain_core.output_parsers import JsonOutputParser
from pydantic import BaseModel
from app.core.config import settings

SKILL_NORMALIZATION_PROMPT = PromptTemplate.from_template('''
Analyze and normalize the skill name "{skill}".

Given this skill, return:
1. The canonical/standard name for this skill
2. The category it belongs to (programming, frontend, backend, cloud, database, ai, devops, tools, mobile, data, security, etc.)
3. Any related/alternative names or aliases
4. Whether this is a primary skill or a technology/framework

Return ONLY valid JSON:
{{
  "canonical_name": "react",
  "category": "frontend",
  "alternatives": ["reactjs", "react.js"],
  "is_primary": true,
  "related_skills": ["javascript", "typescript", "redux", "nextjs"]
}}

JSON Response:
''')

SKILL_RESOLUTION_PROMPT = PromptTemplate.from_template('''
Resolve skill variations to their canonical names.

Input skills: {skills}

For each skill, find the canonical name. Skills might be variations like:
- "react.js", "reactjs", "React" → "react"
- "postgres", "pg" → "postgresql"
- "k8s" → "kubernetes"
- "ml" → "machine learning"

Return ONLY valid JSON:
{{
  "resolved_skills": {{
    "react.js": "react",
    "reactjs": "react",
    "postgres": "postgresql"
  }},
  "unknown_skills": ["skill1", "skill2"],
  "skill_categories": {{
    "react": "frontend",
    "python": "programming"
  }}
}}

JSON Response:
''')

SKILL_ANALYSIS_PROMPT = PromptTemplate.from_template('''
Analyze the text and extract all technical skills mentioned.

Text: {text}

Extract skills for:
- Programming languages (Python, JavaScript, etc.)
- Frameworks (React, Django, etc.)
- Tools (Docker, Git, etc.)
- Cloud platforms (AWS, Azure, etc.)
- Databases (PostgreSQL, MongoDB, etc.)
- Concepts (CI/CD, DevOps, etc.)

Return ONLY valid JSON:
{{
  "extracted_skills": [
    {{
      "name": "python",
      "variation_found": "Python",
      "confidence": 1.0
    }}
  ],
  "skill_categories": {{
    "frontend": ["react", "typescript"],
    "backend": ["python", "postgresql"]
  }}
}}

JSON Response:
''')


class SkillNormalizationResult(BaseModel):
    canonical_name: str
    category: Optional[str]
    alternatives: List[str]
    is_primary: bool
    related_skills: List[str]


class SkillResolutionResult(BaseModel):
    resolved_skills: Dict[str, str]
    unknown_skills: List[str]
    skill_categories: Dict[str, str]


class SkillAnalysisResult(BaseModel):
    extracted_skills: List[Dict[str, Any]]
    skill_categories: Dict[str, List[str]]


class SkillResolver:
    _instance = None
    _llm = None
    _skills_cache: Optional[List[str]] = None
    _category_cache: Dict[str, str] = {}

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    def __init__(self):
        if SkillResolver._skills_cache is None:
            self._load_skills_cache()
        self._initialize_llm()

    def _initialize_llm(self):
        if SkillResolver._llm is None and settings.GROQ_API_KEY:
            try:
                SkillResolver._llm = ChatGroq(
                    api_key=settings.GROQ_API_KEY,
                    model="llama-3.1-8b-instant",
                    temperature=0.1,
                    max_tokens=2048
                )
            except Exception:
                SkillResolver._llm = None

    def _load_skills_cache(self):
        if settings.SKILLS_LIBRARY_PATH.exists():
            try:
                with open(settings.SKILLS_LIBRARY_PATH) as f:
                    data = json.load(f)
                SkillResolver._skills_cache = [s['id'] for s in data.get('skills', [])]
            except Exception:
                SkillResolver._skills_cache = []
        else:
            SkillResolver._skills_cache = []

    def _normalize_skill_llm(self, skill: str) -> SkillNormalizationResult:
        if not SkillResolver._llm:
            return SkillNormalizationResult(
                canonical_name=skill.lower().replace(" ", "_"),
                category=None,
                alternatives=[],
                is_primary=True,
                related_skills=[]
            )
        
        try:
            chain = SKILL_NORMALIZATION_PROMPT | SkillResolver._llm | JsonOutputParser()
            result = chain.invoke({"skill": skill})
            return SkillNormalizationResult(**result)
        except Exception:
            return SkillNormalizationResult(
                canonical_name=skill.lower().replace(" ", "_"),
                category=None,
                alternatives=[],
                is_primary=True,
                related_skills=[]
            )

    def _resolve_skills_llm(self, skills: List[str]) -> SkillResolutionResult:
        if not SkillResolver._llm:
            resolved = {s: s.lower().replace(" ", "_") for s in skills}
            return SkillResolutionResult(
                resolved_skills=resolved,
                unknown_skills=[],
                skill_categories={}
            )
        
        try:
            chain = SKILL_RESOLUTION_PROMPT | SkillResolver._llm | JsonOutputParser()
            result = chain.invoke({"skills": ", ".join(skills)})
            return SkillResolutionResult(**result)
        except Exception:
            resolved = {s: s.lower().replace(" ", "_") for s in skills}
            return SkillResolutionResult(
                resolved_skills=resolved,
                unknown_skills=[],
                skill_categories={}
            )

    def _analyze_skills_llm(self, text: str) -> SkillAnalysisResult:
        if not SkillResolver._llm:
            return SkillAnalysisResult(extracted_skills=[], skill_categories={})
        
        try:
            chain = SKILL_ANALYSIS_PROMPT | SkillResolver._llm | JsonOutputParser()
            result = chain.invoke({"text": text})
            return SkillAnalysisResult(**result)
        except Exception:
            return SkillAnalysisResult(extracted_skills=[], skill_categories={})

    def resolve_skill_llm(self, skill: str) -> str:
        normalized = self._normalize_skill_llm(skill)
        return normalized.canonical_name

    def resolve_skill(self, skill: str) -> str:
        if SkillResolver._llm:
            normalized = self._normalize_skill_llm(skill)
            return normalized.canonical_name
        return skill.lower().replace(" ", "_")

    def resolve_all_skills_llm(self, skills: List[str]) -> Dict[str, str]:
        result = self._resolve_skills_llm(skills)
        
        resolved = {}
        for original, canonical in result.resolved_skills.items():
            resolved[original] = canonical
        
        for skill in result.unknown_skills:
            if skill not in resolved:
                resolved[skill] = skill.lower().replace(" ", "_")
        
        return resolved

    def resolve_all_skills(self, skills: List[str]) -> Dict[str, str]:
        return self.resolve_all_skills_llm(skills)

    def analyze_text_skills(self, text: str) -> List[str]:
        result = self._analyze_skills_llm(text)
        return [s["name"] for s in result.extracted_skills]

    def get_skill_category(self, skill: str) -> Optional[str]:
        if skill in SkillResolver._category_cache:
            return SkillResolver._category_cache[skill]
        if SkillResolver._llm:
            normalized = self._normalize_skill_llm(skill)
            if normalized.category:
                SkillResolver._category_cache[skill] = normalized.category
                return normalized.category
        return None

    def get_skill_category_llm(self, skill: str) -> Optional[str]:
        normalized = self._normalize_skill_llm(skill)
        if normalized.category:
            SkillResolver._category_cache[skill] = normalized.category
            return normalized.category
        return None

    def suggest_related_skills(self, skill: str, max_suggestions: int = 5) -> List[str]:
        if SkillResolver._llm:
            normalized = self._normalize_skill_llm(skill)
            return normalized.related_skills[:max_suggestions]
        return []

    def suggest_related_skills_llm(self, skill: str, max_suggestions: int = 5) -> List[str]:
        normalized = self._normalize_skill_llm(skill)
        return normalized.related_skills[:max_suggestions]

    def get_skill_metadata(self, skill: str) -> Dict[str, Any]:
        normalized = self._normalize_skill_llm(skill)
        return {
            "canonical_name": normalized.canonical_name,
            "category": normalized.category,
            "alternatives": normalized.alternatives,
            "is_primary": normalized.is_primary,
            "related_skills": normalized.related_skills
        }

    def add_skill(self, skill_id: str, category: str = None, aliases: List[str] = None):
        if not settings.SKILLS_LIBRARY_PATH.exists():
            return

        try:
            with open(settings.SKILLS_LIBRARY_PATH) as f:
                data = json.load(f)

            for skill in data.get('skills', []):
                if skill['id'] == skill_id:
                    return

            new_skill = {
                'id': skill_id,
                'category': category,
                'aliases': aliases or []
            }
            data.setdefault('skills', []).append(new_skill)

            with open(settings.SKILLS_LIBRARY_PATH, 'w') as f:
                json.dump(data, f, indent=2)

            if SkillResolver._skills_cache is None:
                SkillResolver._skills_cache = []
            SkillResolver._skills_cache.append(skill_id)
        except Exception:
            pass

    def add_alias(self, skill_id: str, alias: str):
        if not settings.SKILLS_LIBRARY_PATH.exists():
            return

        try:
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
        except Exception:
            pass


_skill_resolver: Optional[SkillResolver] = None


def get_skill_resolver() -> SkillResolver:
    global _skill_resolver
    if _skill_resolver is None:
        _skill_resolver = SkillResolver()
    return _skill_resolver
