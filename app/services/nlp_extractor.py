import json
import re
from pathlib import Path
from typing import Optional, Set
from app.core.config import settings
from app.core.logger import get_logger
from app.models.graph import ExtractionResult, Node, Link

logger = get_logger(__name__)

class NLPExtractor:
    _spacy_model = None
    _skills_map: Optional[dict] = None

    def __init__(self):
        self._load_skills()

    def _load_skills(self) -> dict:
        if NLPExtractor._skills_map is None:
            if settings.SKILLS_LIBRARY_PATH.exists():
                with open(settings.SKILLS_LIBRARY_PATH) as f:
                    data = json.load(f)
                NLPExtractor._skills_map = {
                    s['id']: s for s in data.get('skills', [])
                }
            else:
                NLPExtractor._skills_map = {}
        return NLPExtractor._skills_map

    def _init_spacy(self):
        if NLPExtractor._spacy_model is None:
            try:
                import spacy
                NLPExtractor._spacy_model = spacy.load("en_core_web_md")
            except OSError:
                logger.warning("spaCy model 'en_core_web_md' not found. Run: python -m spacy download en_core_web_md")
                NLPExtractor._spacy_model = None

    def _extract_entities(self, text: str) -> Set[str]:
        self._init_spacy()
        
        if NLPExtractor._spacy_model is None:
            return set()

        doc = NLPExtractor._spacy_model(text)
        entities = set()

        for ent in doc.ents:
            if ent.label_ in ["PRODUCT", "ORG", "TECH"]:
                normalized = self._normalize_skill(ent.text)
                entities.add(normalized)

        for token in doc:
            if token.pos_ == "PROPN" and len(token.text) > 2:
                normalized = self._normalize_skill(token.text)
                entities.add(normalized)

        return entities

    def _normalize_skill(self, text: str) -> str:
        text = text.lower().strip()
        text = re.sub(r'\s+', '_', text)
        text = re.sub(r'[^\w_]', '', text)
        return text

    def _map_to_library(self, entities: Set[str]) -> dict:
        skills_map = self._load_skills()
        matched = {}

        for entity in entities:
            for skill_id, skill_data in skills_map.items():
                if self._matches_skill(entity, skill_id, skill_data):
                    matched[skill_id] = skill_data
                    break
                for alias in skill_data.get('aliases', []):
                    if self._matches_skill(entity, alias, {}):
                        matched[skill_id] = skill_data
                        break

        return matched

    def _matches_skill(self, text: str, skill_name: str, skill_data: dict) -> bool:
        text = text.lower()
        skill = skill_name.lower()
        
        if skill in text or text in skill:
            return True
        
        text_clean = re.sub(r'[^\w]', '', text)
        skill_clean = re.sub(r'[^\w]', '', skill)
        
        if text_clean == skill_clean:
            return True
            
        return False

    def extract(self, title: str, description: str, role_id: Optional[str] = None) -> ExtractionResult:
        combined = f"{title} {description}"
        entities = self._extract_entities(combined)
        matched_skills = self._map_to_library(entities)

        nodes = [
            Node(
                id=skill_id,
                type="skill",
                category=skill_data.get('category', 'unknown'),
                aliases=skill_data.get('aliases', [])
            )
            for skill_id, skill_data in matched_skills.items()
        ]

        links = []
        if role_id:
            for skill_id in matched_skills.keys():
                links.append(Link(
                    source=role_id,
                    target=skill_id,
                    type="REQUIRES"
                ))

        return ExtractionResult(
            nodes=nodes,
            links=links,
            success=len(nodes) > 0,
            method="nlp"
        )
