import re
import json
from typing import List, Dict, Set, Optional
from collections import Counter
from langchain_groq import ChatGroq
from langchain_core.prompts import PromptTemplate
from langchain_core.output_parsers import JsonOutputParser
from pydantic import BaseModel, Field
from app.core.config import settings

SKILL_EXTRACTION_PROMPT = PromptTemplate.from_template('''
Analyze this job description and extract ALL technical skills, technologies, tools, and frameworks mentioned.

For each item:
- Programming languages
- Frameworks and libraries
- Cloud platforms and services
- Databases and data stores
- DevOps tools (CI/CD, containers, etc.)
- Any other technical skills

Return ONLY valid JSON:
{{
  "skills": [
    {{
      "id": "skill_name_in_snake_case",
      "name": "Skill Name",
      "category": "inferred_category"
    }}
  ]
}}

Job Title: {title}
Job Description: {description}

JSON Response:
''')

TOPIC_EXTRACTION_PROMPT = PromptTemplate.from_template('''
Analyze this job description and extract:
1. Tech domains/categories present
2. Implied skills not explicitly mentioned
3. Soft skills mentioned
4. Domain/industry context
5. Experience level

Return ONLY valid JSON:
{{
  "tech_categories": ["category1", "category2"],
  "implied_skills": ["skill1", "skill2"],
  "soft_skills": ["communication", "leadership"],
  "domain": "fintech|healthcare|ecommerce|saas|social|gaming|iot|data_engineering|other|none",
  "experience_level": "entry|mid|senior|expert|unknown"
}}

Job Title: {title}
Job Description: {description}

JSON Response:
''')

SOFT_SKILLS_PROMPT = PromptTemplate.from_template('''
From this job description, extract ALL soft skills and interpersonal abilities mentioned or implied.

Look for:
- Communication skills
- Leadership abilities
- Teamwork and collaboration
- Problem-solving skills
- Time management
- Adaptability and flexibility
- Creative thinking
- Any other human skills

Return ONLY valid JSON:
{{
  "soft_skills": ["skill1", "skill2", ...]
}}

Job Description: {description}

JSON Response:
''')

CERTIFICATION_EXTRACTION_PROMPT = PromptTemplate.from_template('''
From this job description, extract any certifications, credentials, or professional qualifications mentioned.

Look for:
- Cloud certifications (AWS, Azure, GCP)
- Security certifications
- Project management certifications
- Any other professional certifications

Return ONLY valid JSON:
{{
  "certifications": [
    {{
      "name": "Certification Name",
      "provider": "Provider (if mentioned)",
      "category": "cloud|security|project_management|general"
    }}
  ]
}}

Job Description: {description}

JSON Response:
''')

EXPERIENCE_LEVEL_PROMPT = PromptTemplate.from_template('''
Analyze this job description and determine the required experience level.

Consider:
- Years of experience mentioned
- Seniority indicators (lead, junior, mid, senior)
- Job title keywords
- Responsibility level

Return ONLY valid JSON:
{{
  "experience_level": "entry|mid|senior|expert|unknown",
  "years_min": 0,
  "years_max": 0,
  "reasoning": "brief explanation"
}}

Job Title: {title}
Job Description: {description}

JSON Response:
''')


class TopicExtractor:
    def __init__(self, api_key: Optional[str] = None):
        self.skills_map = self._load_skills()
        self.api_key = api_key or settings.GROQ_API_KEY
        self._llm = None
        self._cache: Dict[str, any] = {}

    def _initialize_llm(self):
        if self._llm is None and self.api_key:
            self._llm = ChatGroq(
                api_key=self.api_key,
                model="llama-3.1-8b-instant",
                temperature=0.1,
                max_tokens=2048
            )

    def _load_skills(self) -> dict:
        if settings.SKILLS_LIBRARY_PATH.exists():
            with open(settings.SKILLS_LIBRARY_PATH) as f:
                data = json.load(f)
            return {s['id']: s for s in data.get('skills', [])}
        return {}

    def _extract_words(self, text: str) -> List[str]:
        text_lower = text.lower()
        words = re.findall(r'\b[a-z][a-z0-9+-]*\b', text_lower)
        return list(set(words))

    def _normalize_skill_name(self, skill: str) -> str:
        skill_lower = skill.lower().strip()
        skill_lower = re.sub(r'[^\w\s-]', '', skill_lower)
        skill_lower = skill_lower.replace(' ', '_').replace('-', '_')
        skill_lower = re.sub(r'_+', '_', skill_lower)
        return skill_lower.strip('_')

    async def extract_skills_llm(self, title: str, description: str) -> List[Dict]:
        self._initialize_llm()
        
        cache_key = f"skills_{hash(title + description[:100])}"
        if cache_key in self._cache:
            return self._cache[cache_key]
        
        if not self._llm:
            return []
        
        try:
            from pydantic import BaseModel, Field
            class SkillItem(BaseModel):
                id: str
                name: str
                category: Optional[str] = None
            
            class SkillsOutput(BaseModel):
                skills: List[SkillItem] = Field(default_factory=list)
            
            chain = SKILL_EXTRACTION_PROMPT | self._llm | JsonOutputParser()
            result = await chain.ainvoke({
                "title": title,
                "description": description[:3000]
            })
            
            skills = result.get("skills", [])
            self._cache[cache_key] = skills
            return skills
        except Exception as e:
            return []

    async def extract_topics_llm(self, title: str, description: str) -> Dict:
        self._initialize_llm()
        
        cache_key = f"topics_{hash(title + description[:100])}"
        if cache_key in self._cache:
            return self._cache[cache_key]
        
        if not self._llm:
            return {
                'tech_categories': [],
                'implied_skills': [],
                'soft_skills': [],
                'domain': 'none',
                'experience_level': 'unknown'
            }
        
        try:
            chain = TOPIC_EXTRACTION_PROMPT | self._llm | JsonOutputParser()
            result = await chain.ainvoke({
                "title": title,
                "description": description[:2000]
            })
            
            self._cache[cache_key] = result
            return result
        except Exception:
            return {
                'tech_categories': [],
                'implied_skills': [],
                'soft_skills': [],
                'domain': 'none',
                'experience_level': 'unknown'
            }

    async def extract_soft_skills_llm(self, description: str) -> List[str]:
        self._initialize_llm()
        
        if not self._llm:
            return []
        
        try:
            chain = SOFT_SKILLS_PROMPT | self._llm | JsonOutputParser()
            result = await chain.ainvoke({"description": description[:2000]})
            return result.get("soft_skills", [])
        except Exception:
            return []

    async def extract_certifications_llm(self, description: str) -> List[Dict]:
        self._initialize_llm()
        
        if not self._llm:
            return []
        
        try:
            chain = CERTIFICATION_EXTRACTION_PROMPT | self._llm | JsonOutputParser()
            result = await chain.ainvoke({"description": description[:2000]})
            return result.get("certifications", [])
        except Exception:
            return []

    async def extract_experience_level_llm(self, title: str, description: str) -> Dict:
        self._initialize_llm()
        
        if not self._llm:
            return {'experience_level': 'unknown', 'years_min': 0, 'years_max': 0}
        
        try:
            chain = EXPERIENCE_LEVEL_PROMPT | self._llm | JsonOutputParser()
            result = await chain.ainvoke({
                "title": title,
                "description": description[:2000]
            })
            return result
        except Exception:
            return {'experience_level': 'unknown', 'years_min': 0, 'years_max': 0}

    def extract_topics(self, text: str) -> List[Dict]:
        return []

    def extract_implied_skills(self, found_skills: List[str]) -> List[str]:
        return []

    def extract_soft_skills(self, text: str) -> List[str]:
        return []

    def extract_certifications(self, text: str) -> List[str]:
        return []

    def extract_experience_level(self, text: str) -> Optional[str]:
        return None

    def extract_tools(self, text: str) -> List[str]:
        return []

    def full_topic_extraction(self, text: str, found_skills: List[str]) -> Dict:
        return {
            'topics': [],
            'implied_skills': [],
            'soft_skills': [],
            'certifications': [],
            'experience_level': 'unknown',
            'tools': [],
            'additional_skills': found_skills,
            'domain': 'none',
            'tech_categories': []
        }

    async def full_topic_extraction_llm(self, title: str, description: str, found_skills: List[str]) -> Dict:
        skills_result = await self.extract_skills_llm(title, description)
        topics_result = await self.extract_topics_llm(title, description)
        soft_skills = await self.extract_soft_skills_llm(description)
        certs = await self.extract_certifications_llm(description)
        exp_result = await self.extract_experience_level_llm(title, description)
        
        skill_ids = [s['id'] for s in skills_result if 'id' in s]
        all_skills = list(set(skill_ids + found_skills))
        
        return {
            'topics': [{'name': c, 'type': 'tech_category'} for c in topics_result.get('tech_categories', [])],
            'implied_skills': topics_result.get('implied_skills', []),
            'soft_skills': soft_skills,
            'certifications': certs,
            'experience_level': exp_result.get('experience_level', 'unknown'),
            'experience_years': {'min': exp_result.get('years_min', 0), 'max': exp_result.get('years_max', 0)},
            'tools': skill_ids,
            'additional_skills': all_skills,
            'domain': topics_result.get('domain', 'none'),
            'tech_categories': topics_result.get('tech_categories', []),
            'llm_skills': skills_result
        }


_topic_extractor = None

def get_topic_extractor(api_key: Optional[str] = None) -> TopicExtractor:
    global _topic_extractor
    if _topic_extractor is None:
        _topic_extractor = TopicExtractor(api_key=api_key)
    return _topic_extractor
