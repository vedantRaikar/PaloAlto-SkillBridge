import re
import json
from typing import List, Dict, Set, Tuple, Optional
from collections import defaultdict
from difflib import SequenceMatcher
from app.core.config import settings

class EntityDeduplicator:
    def __init__(self):
        self.skills_map = self._load_skills()
        self.normalization_rules = self._get_normalization_rules()

    def _load_skills(self) -> dict:
        if settings.SKILLS_LIBRARY_PATH.exists():
            with open(settings.SKILLS_LIBRARY_PATH) as f:
                data = json.load(f)
            return {s['id']: s for s in data.get('skills', [])}
        return {}

    def _get_normalization_rules(self) -> dict:
        return {
            'js': 'javascript',
            'ts': 'typescript',
            'py': 'python',
            'react.js': 'react',
            'reactjs': 'react',
            'node.js': 'nodejs',
            'nodejs': 'nodejs',
            'postgres': 'postgresql',
            'postgres': 'postgresql',
            'mongo': 'mongodb',
            'mongodb': 'mongodb',
            'k8s': 'kubernetes',
            'kube': 'kubernetes',
            'tf': 'terraform',
            'aws': 'aws',
            'gcp': 'gcp',
            'ml': 'machine_learning',
            'ai': 'artificial_intelligence',
            'dl': 'deep_learning',
            'nlp': 'natural_language_processing',
            'cv': 'computer_vision',
            'sql': 'sql',
            'nosql': 'nosql',
            'ci/cd': 'ci_cd',
            'cicd': 'ci_cd',
            'html/css': 'html_css',
            'html5': 'html_css',
            'css3': 'html_css',
            'rest api': 'rest_api',
            'restful': 'rest_api',
            'graphql': 'graphql',
            'testing': 'testing',
            'tdd': 'testing',
        }

    def normalize_entity(self, entity: str) -> str:
        entity_lower = entity.lower().strip()
        
        if entity_lower in self.normalization_rules:
            return self.normalization_rules[entity_lower]
        
        for alias, canonical in self.normalization_rules.items():
            if alias in entity_lower or entity_lower in alias:
                return canonical
        
        normalized = entity_lower.replace(' ', '_').replace('-', '_')
        normalized = re.sub(r'[^\w_]', '', normalized)
        normalized = re.sub(r'_+', '_', normalized)
        normalized = normalized.strip('_')
        
        return normalized

    def levenshtein_distance(self, s1: str, s2: str) -> int:
        if len(s1) < len(s2):
            return self.levenshtein_distance(s2, s1)
        
        if len(s2) == 0:
            return len(s1)
        
        previous_row = range(len(s2) + 1)
        for i, c1 in enumerate(s1):
            current_row = [i + 1]
            for j, c2 in enumerate(s2):
                insertions = previous_row[j + 1] + 1
                deletions = current_row[j] + 1
                substitutions = previous_row[j] + (c1 != c2)
                current_row.append(min(insertions, deletions, substitutions))
            previous_row = current_row
        
        return previous_row[-1]

    def similarity_ratio(self, s1: str, s2: str) -> float:
        return SequenceMatcher(None, s1.lower(), s2.lower()).ratio()

    def are_similar(self, entity1: str, entity2: str, threshold: float = 0.8) -> bool:
        norm1 = self.normalize_entity(entity1)
        norm2 = self.normalize_entity(entity2)
        
        if norm1 == norm2:
            return True
        
        if norm1 in norm2 or norm2 in norm1:
            return True
        
        if len(norm1) > 2 and len(norm2) > 2:
            distance = self.levenshtein_distance(norm1, norm2)
            max_len = max(len(norm1), len(norm2))
            similarity = 1 - (distance / max_len)
            if similarity >= threshold:
                return True
        
        ratio = self.similarity_ratio(norm1, norm2)
        if ratio >= threshold:
            return True
        
        return False

    def find_duplicates(self, entities: List[str], threshold: float = 0.8) -> List[List[str]]:
        duplicates = []
        used = set()
        
        for i, entity1 in enumerate(entities):
            if i in used:
                continue
            
            group = [entity1]
            used.add(i)
            
            for j, entity2 in enumerate(entities):
                if j in used:
                    continue
                
                if self.are_similar(entity1, entity2, threshold):
                    group.append(entity2)
                    used.add(j)
            
            if len(group) > 1:
                duplicates.append(group)
        
        return duplicates

    def deduplicate_entities(self, entities: List[str], threshold: float = 0.8) -> Tuple[List[str], Dict[str, str]]:
        duplicates = self.find_duplicates(entities, threshold)
        
        canonical_map = {}
        for group in duplicates:
            canonical = self._select_canonical(group)
            for entity in group:
                if entity != canonical:
                    canonical_map[entity] = canonical
        
        deduplicated = []
        seen = set()
        
        for entity in entities:
            if entity in canonical_map:
                canonical = canonical_map[entity]
                if canonical not in seen:
                    deduplicated.append(canonical)
                    seen.add(canonical)
            else:
                if entity not in seen:
                    deduplicated.append(entity)
                    seen.add(entity)
        
        return deduplicated, canonical_map

    def _select_canonical(self, entities: List[str]) -> str:
        for entity in entities:
            normalized = self.normalize_entity(entity)
            if normalized in self.skills_map:
                return normalized
        
        for entity in entities:
            if entity in self.skills_map:
                return entity
        
        return max(entities, key=lambda e: len(e))

    def merge_skill_metadata(self, skill1_data: Dict, skill2_data: Dict) -> Dict:
        merged = skill1_data.copy()
        
        if 'aliases' not in merged:
            merged['aliases'] = []
        
        if 'aliases' in skill2_data:
            for alias in skill2_data['aliases']:
                if alias.lower() not in [a.lower() for a in merged['aliases']]:
                    merged['aliases'].append(alias)
        
        if 'category' not in merged or merged['category'] == 'unknown':
            if 'category' in skill2_data and skill2_data['category'] != 'unknown':
                merged['category'] = skill2_data['category']
        
        for key in ['metadata', 'description', 'resources']:
            if key in skill2_data and key not in merged:
                merged[key] = skill2_data[key]
        
        return merged

    def optimize_entity_set(self, entities: List[Dict]) -> Tuple[List[Dict], Dict]:
        entity_ids = [e.get('id', e.get('name', '')) for e in entities]
        entity_map = {e.get('id', e.get('name')): e for e in entities}
        
        deduplicated_ids, canonical_map = self.deduplicate_entities(entity_ids)
        
        optimized = []
        for entity_id in deduplicated_ids:
            if entity_id in entity_map:
                entity = entity_map[entity_id].copy()
                entity['id'] = entity_id
                optimized.append(entity)
        
        for old_id, new_id in canonical_map.items():
            if old_id in entity_map and new_id not in entity_map:
                merged = self.merge_skill_metadata(entity_map[new_id], entity_map[old_id])
                entity_map[new_id] = merged
        
        return optimized, canonical_map

    def find_skill_aliases(self, skill_id: str) -> List[str]:
        if skill_id in self.skills_map:
            return self.skills_map[skill_id].get('aliases', [])
        return []

    def add_alias(self, skill_id: str, alias: str) -> bool:
        if skill_id not in self.skills_map:
            return False
        
        if 'aliases' not in self.skills_map[skill_id]:
            self.skills_map[skill_id]['aliases'] = []
        
        normalized_alias = self.normalize_entity(alias)
        
        if normalized_alias in self.skills_map:
            return False
        
        for existing_alias in self.skills_map[skill_id]['aliases']:
            if self.normalize_entity(existing_alias) == normalized_alias:
                return False
        
        self.skills_map[skill_id]['aliases'].append(alias)
        
        self._save_skills()
        return True

    def _save_skills(self):
        skills_list = list(self.skills_map.values())
        data = {'skills': skills_list}
        
        with open(settings.SKILLS_LIBRARY_PATH, 'w') as f:
            json.dump(data, f, indent=2)

    def suggest_canonical_form(self, entity: str) -> Optional[str]:
        normalized = self.normalize_entity(entity)
        
        if normalized in self.skills_map:
            return normalized
        
        for skill_id, skill_data in self.skills_map.items():
            if 'aliases' in skill_data:
                for alias in skill_data['aliases']:
                    if self.normalize_entity(alias) == normalized:
                        return skill_id
        
        return None


_entity_deduplicator = None

def get_entity_deduplicator() -> EntityDeduplicator:
    global _entity_deduplicator
    if _entity_deduplicator is None:
        _entity_deduplicator = EntityDeduplicator()
    return _entity_deduplicator
