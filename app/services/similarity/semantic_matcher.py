"""
Semantic Skill Matcher
======================
Uses sentence embeddings to match skills based on semantic similarity.
This is more accurate than string matching as it understands that:
- "Python programming" and "Python" are the same skill
- "ML" and "Machine Learning" are the same concept
- "React.js" and "React" are the same framework
"""

import numpy as np
from typing import List, Dict, Optional, Set, Tuple
from functools import lru_cache
import re
from app.core.logger import get_logger


logger = get_logger(__name__)


class SemanticSkillMatcher:
    """
    Matches skills using semantic similarity with sentence embeddings.
    Falls back to exact matching and alias matching if embeddings fail.
    """
    
    DEFAULT_SIMILARITY_THRESHOLD = 0.75
    
    def __init__(self, model_name: str = "all-MiniLM-L6-v2", threshold: float = 0.75):
        self.threshold = threshold
        self._model = None
        self._model_name = model_name
        self._embedding_cache: Dict[str, np.ndarray] = {}
        
        self._canonical_skills: Set[str] = set()
        self._skill_embeddings: Dict[str, np.ndarray] = {}
        
        self._initialize_canonical_skills()
    
    def _initialize_canonical_skills(self):
        """Initialize the set of canonical skill names"""
        from app.services.knowledge_sources.onet_integration import SKILL_TO_COURSES, SKILL_ALIASES
        
        for skill in SKILL_TO_COURSES.keys():
            self._canonical_skills.add(skill.lower())
        
        for canonical, aliases in SKILL_ALIASES.items():
            self._canonical_skills.add(canonical.lower())
            for alias in aliases:
                self._canonical_skills.add(alias.lower())
    
    @property
    def model(self):
        """Lazy load the embedding model"""
        if self._model is None:
            try:
                from sentence_transformers import SentenceTransformer
                logger.info("Loading sentence-transformer model '%s'...", self._model_name)
                self._model = SentenceTransformer(self._model_name)
                logger.info("Model '%s' loaded successfully", self._model_name)
                self._precompute_embeddings()
            except Exception as e:
                logger.warning("Could not load embedding model: %s", e)
                return None
        return self._model

    def warmup(self):
        """Eagerly load model and precompute embeddings so first request is fast."""
        _ = self.model
    
    def _precompute_embeddings(self):
        """Pre-compute embeddings for all canonical skills"""
        if self.model is None:
            return
        
        skills_list = list(self._canonical_skills)
        embeddings = self.model.encode(skills_list, show_progress_bar=False)
        
        for skill, embedding in zip(skills_list, embeddings):
            self._skill_embeddings[skill] = embedding
    
    def _normalize_skill(self, skill: str) -> str:
        """Normalize skill name for consistent comparison"""
        skill = skill.lower().strip()
        skill = re.sub(r'[_\-\.]', ' ', skill)
        skill = re.sub(r'\s+', ' ', skill)
        return skill
    
    def get_embedding(self, skill: str) -> Optional[np.ndarray]:
        """Get embedding for a skill, with caching"""
        normalized = self._normalize_skill(skill)
        
        if normalized in self._embedding_cache:
            return self._embedding_cache[normalized]
        
        if self.model is None:
            return None
        
        try:
            embedding = self.model.encode([normalized])[0]
            self._embedding_cache[normalized] = embedding
            return embedding
        except Exception as e:
            logger.exception("Error getting embedding for '%s'", skill)
            return None
    
    def cosine_similarity(self, emb1: np.ndarray, emb2: np.ndarray) -> float:
        """Calculate cosine similarity between two embeddings"""
        dot_product = np.dot(emb1, emb2)
        norm1 = np.linalg.norm(emb1)
        norm2 = np.linalg.norm(emb2)
        if norm1 == 0 or norm2 == 0:
            return 0.0
        return float(dot_product / (norm1 * norm2))
    
    def find_similar_skills(self, skill: str, threshold: Optional[float] = None) -> List[Tuple[str, float]]:
        """
        Find skills similar to the given skill.
        Returns list of (skill_name, similarity_score) tuples.
        """
        threshold = threshold or self.threshold
        
        skill_emb = self.get_embedding(skill)
        if skill_emb is None:
            return []
        
        similarities = []
        for canonical, emb in self._skill_embeddings.items():
            score = self.cosine_similarity(skill_emb, emb)
            if score >= threshold:
                similarities.append((canonical, score))
        
        similarities.sort(key=lambda x: x[1], reverse=True)
        return similarities
    
    def skills_match(self, skill1: str, skill2: str, threshold: Optional[float] = None) -> bool:
        """
        Check if two skills match semantically.
        Uses multiple strategies for best accuracy:
        1. Exact match (after normalization)
        2. Substring match (for common patterns like "react" in "reactjs")
        3. Semantic similarity (embedding-based)
        4. Alias match
        """
        threshold = threshold or self.threshold
        
        s1 = self._normalize_skill(skill1)
        s2 = self._normalize_skill(skill2)
        
        if s1 == s2:
            return True
        
        if self._substring_match(s1, s2):
            return True
        
        if self._alias_match(skill1, skill2):
            return True
        
        skill_emb1 = self.get_embedding(skill1)
        skill_emb2 = self.get_embedding(skill2)
        
        if skill_emb1 is not None and skill_emb2 is not None:
            score = self.cosine_similarity(skill_emb1, skill_emb2)
            return score >= threshold
        
        return False
    
    def _substring_match(self, s1: str, s2: str) -> bool:
        """Check for common substring matches that are valid
        
        Only matches if:
        - Words are identical (handled by exact match)
        - One word is a prefix of another AND the longer word is an extended version
          (e.g., "react" in "reactjs" is valid, "script" in "javascript" is NOT)
        """
        words1 = set(s1.split())
        words2 = set(s2.split())
        
        if words1 == words2:
            return True
        
        if len(words1) == 1 and len(words2) == 1:
            word1 = list(words1)[0]
            word2 = list(words2)[0]
            
            len1, len2 = len(word1), len(word2)
            
            if len1 < 4 or len2 < 4:
                return False
            
            shorter, longer = (word1, word2) if len1 < len2 else (word2, word1)
            
            if longer.startswith(shorter + "js") or longer.startswith(shorter + "."):
                return True
            
            if longer.endswith("script") or longer.endswith("scripting"):
                return False
            
            if shorter in longer and len(shorter) >= 5:
                return True
            
            return False
        
        return False
    
    def _alias_match(self, skill1: str, skill2: str) -> bool:
        """Check if skills match via alias mapping"""
        from app.services.knowledge_sources.onet_integration import SKILL_ALIASES
        
        skill1_lower = skill1.lower()
        skill2_lower = skill2.lower()
        
        for canonical, aliases in SKILL_ALIASES.items():
            all_names = [canonical] + aliases
            if skill1_lower in [n.lower() for n in all_names] and skill2_lower in [n.lower() for n in all_names]:
                return True
        
        return False
    
    def get_canonical_skill(self, skill: str) -> Optional[str]:
        """
        Get the canonical name for a skill.
        Returns the most similar canonical skill name.
        """
        matches = self.find_similar_skills(skill, threshold=0.7)
        if matches:
            return matches[0][0]
        
        s1 = self._normalize_skill(skill)
        for canonical in self._canonical_skills:
            s2 = self._normalize_skill(canonical)
            if s1 == s2 or s1 in s2 or s2 in s1:
                return canonical
        
        return None
    
    def match_skill_list(self, user_skills: List[str], required_skills: List[str]) -> Tuple[List[str], List[str]]:
        """
        Match user skills to required skills.
        Returns (matched_skills, missing_skills).
        """
        matched = []
        missing = []
        
        user_skill_set = set(self._normalize_skill(s) for s in user_skills)
        
        for req_skill in required_skills:
            req_normalized = self._normalize_skill(req_skill)
            
            is_matched = False
            for user_skill in user_skills:
                if self.skills_match(user_skill, req_skill):
                    is_matched = True
                    break
            
            if is_matched:
                matched.append(req_skill)
            else:
                missing.append(req_skill)
        
        return matched, missing


_semantic_matcher: Optional[SemanticSkillMatcher] = None


def get_semantic_matcher() -> SemanticSkillMatcher:
    global _semantic_matcher
    if _semantic_matcher is None:
        _semantic_matcher = SemanticSkillMatcher()
    return _semantic_matcher
