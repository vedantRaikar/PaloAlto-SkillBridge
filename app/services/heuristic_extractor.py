import re
import json
from pathlib import Path
from typing import List, Set
from app.core.config import settings
from app.models.graph import ExtractionResult, Node, Link

class HeuristicExtractor:
    def __init__(self):
        self.skills_map = self._load_skills()

    def _load_skills(self) -> dict:
        if settings.SKILLS_LIBRARY_PATH.exists():
            with open(settings.SKILLS_LIBRARY_PATH) as f:
                data = json.load(f)
            return {s['id']: s for s in data.get('skills', [])}
        return {}

    def _create_pattern(self, skill_id: str, aliases: List[str]) -> str:
        names = [skill_id] + aliases
        return r'\b(' + '|'.join(re.escape(n) for n in names) + r')\b'

    def extract_skills(self, text: str) -> Set[str]:
        text_lower = text.lower()
        found = set()
        
        for skill_id, skill_data in self.skills_map.items():
            pattern = self._create_pattern(skill_id, skill_data.get('aliases', []))
            if re.search(pattern, text_lower, re.IGNORECASE):
                found.add(skill_id)
        
        return found

    def extract(self, title: str, description: str) -> ExtractionResult:
        combined_text = f"{title} {description}"
        matched_skills = self.extract_skills(combined_text)
        
        nodes = []
        links = []
        
        for skill in matched_skills:
            skill_data = self.skills_map.get(skill, {})
            nodes.append(Node(
                id=skill,
                type="skill",
                category=skill_data.get('category', 'unknown'),
                aliases=skill_data.get('aliases', [])
            ))
            links.append(Link(
                source=title.lower().replace(" ", "_"),
                target=skill,
                type="REQUIRES"
            ))
        
        return ExtractionResult(
            nodes=nodes,
            links=links,
            success=len(nodes) > 0,
            method="heuristic"
        )

    def add_skill(self, skill_id: str, category: str = None, aliases: List[str] = None):
        if skill_id not in self.skills_map:
            self.skills_map[skill_id] = {
                "id": skill_id,
                "category": category or "unknown",
                "aliases": aliases or []
            }
            
            with open(settings.SKILLS_LIBRARY_PATH) as f:
                data = json.load(f)
            
            data['skills'].append(self.skills_map[skill_id])
            
            with open(settings.SKILLS_LIBRARY_PATH, 'w') as f:
                json.dump(data, f, indent=2)
