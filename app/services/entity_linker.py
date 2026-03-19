import json
import re
from typing import List, Dict, Set, Optional, Tuple
from langchain_groq import ChatGroq
from langchain_core.prompts import PromptTemplate
from langchain_core.output_parsers import JsonOutputParser
from app.core.config import settings
from app.services.graph_manager import GraphManager
from app.services.entity_deduplicator import get_entity_deduplicator
from app.models.graph import Node, Link, NodeType, LinkType

CATEGORY_INFERENCE_PROMPT = PromptTemplate.from_template('''
Given a skill or technology name, infer the most appropriate category for it.

Consider:
- What type of work does this skill relate to?
- Is it a programming language, framework, tool, platform, or concept?
- What domain does it belong to?

Skill: {skill_id}
Context (optional): {context}

Respond ONLY with the category name in lowercase (e.g., "programming", "frontend", "backend", "devops", "cloud", "database", "ai", "tools", "security", "mobile", "api", "architecture", "data", "infrastructure", "quality", or "unknown").
''')

SKILL_RELATIONSHIPS_PROMPT = PromptTemplate.from_template('''
Given a skill and its category, list other skills that are:
1. Commonly used together with this skill
2. Prerequisites (skills you should learn before this one)
3. Extensions (skills you can learn after mastering this one)

Respond in JSON format:
{{
  "related_skills": ["skill1", "skill2", ...],
  "prerequisites": ["skill_a", "skill_b", ...],
  "extensions": ["skill_x", "skill_y", ...]
}}

Skill: {skill_id}
Category: {category}

JSON Response:
''')


class EntityLinker:
    def __init__(self, api_key: Optional[str] = None):
        self.gm = GraphManager()
        self.deduplicator = get_entity_deduplicator()
        self.skills_map = self._load_skills()
        self.api_key = api_key or settings.GROQ_API_KEY
        self._llm = None
        self._category_cache: Dict[str, str] = {}
        self._relationships_cache: Dict[str, Dict] = {}

    def _initialize_llm(self):
        if self._llm is None and self.api_key:
            self._llm = ChatGroq(
                api_key=self.api_key,
                model="llama-3.1-8b-instant",
                temperature=0.1,
                max_tokens=512
            )

    def _load_skills(self) -> dict:
        if settings.SKILLS_LIBRARY_PATH.exists():
            with open(settings.SKILLS_LIBRARY_PATH) as f:
                data = json.load(f)
            return {s['id']: s for s in data.get('skills', [])}
        return {}

    async def _infer_category_llm(self, skill_id: str, context: str = "") -> str:
        if skill_id in self._category_cache:
            return self._category_cache[skill_id]
        
        if skill_id in self.skills_map and self.skills_map[skill_id].get('category'):
            return self.skills_map[skill_id]['category']
        
        self._initialize_llm()
        if not self._llm:
            return "unknown"
        
        try:
            from langchain_core.output_parsers import StrOutputParser
            chain = CATEGORY_INFERENCE_PROMPT | self._llm | StrOutputParser()
            result = (await chain.ainvoke({"skill_id": skill_id, "context": context or ""})).strip().lower()
            
            self._category_cache[skill_id] = result
            return result
        except Exception:
            pass
        
        self._category_cache[skill_id] = "unknown"
        return "unknown"

    async def _infer_relationships_llm(self, skill_id: str, category: str) -> Dict[str, List[str]]:
        if skill_id in self._relationships_cache:
            return self._relationships_cache[skill_id]
        
        self._initialize_llm()
        result = {"related_skills": [], "prerequisites": [], "extensions": []}
        
        if not self._llm:
            return result
        
        try:
            chain = SKILL_RELATIONSHIPS_PROMPT | self._llm | JsonOutputParser()
            llm_result = await chain.ainvoke({"skill_id": skill_id, "category": category})
            result = {
                "related_skills": llm_result.get("related_skills", []),
                "prerequisites": llm_result.get("prerequisites", []),
                "extensions": llm_result.get("extensions", [])
            }
        except Exception:
            pass
        
        self._relationships_cache[skill_id] = result
        return result

    async def infer_skill_category(self, skill_id: str, context: str = "") -> str:
        return await self._infer_category_llm(skill_id, context)

    def infer_skill_category_sync(self, skill_id: str, context: str = "") -> str:
        if skill_id in self._category_cache:
            return self._category_cache[skill_id]
        if skill_id in self.skills_map and self.skills_map[skill_id].get('category'):
            return self.skills_map[skill_id]['category']
        return "unknown"

    async def infer_skill_relationships(self, skill_id: str, category: str = "") -> List[str]:
        if not category:
            category = await self.infer_skill_category(skill_id)
        result = await self._infer_relationships_llm(skill_id, category)
        return result.get("related_skills", []) + result.get("prerequisites", []) + result.get("extensions", [])

    def infer_skill_relationships_sync(self, skill_id: str) -> List[str]:
        if skill_id in self._relationships_cache:
            return self._relationships_cache[skill_id].get("related_skills", [])
        return []

    async def link_entity_to_graph(self, node: Node, context: str = "") -> List[Tuple[str, str, LinkType]]:
        links = []
        skill_id = node.id
        
        category = node.category or await self.infer_skill_category(skill_id, context)
        if category and node.type == NodeType.SKILL:
            category_node_id = f"category_{category}"
            if self.gm.get_node(category_node_id):
                links.append((category_node_id, skill_id, LinkType.PART_OF))
        
        related_skills = await self.infer_skill_relationships(skill_id, category)
        for related in related_skills:
            if self.gm.get_node(related):
                links.append((skill_id, related, LinkType.RELATED_TO))
        
        return links

    def link_entity_to_graph_sync(self, node: Node, context: str = "") -> List[Tuple[str, str, LinkType]]:
        links = []
        skill_id = node.id
        
        category = node.category or self.infer_skill_category_sync(skill_id)
        if category and node.type == NodeType.SKILL:
            category_node_id = f"category_{category}"
            if self.gm.get_node(category_node_id):
                links.append((category_node_id, skill_id, LinkType.PART_OF))
        
        return links

    def link_role_to_graph(self, role_id: str, skill_ids: List[str]) -> List[Tuple[str, str, LinkType]]:
        links = []
        
        for skill_id in skill_ids:
            if self.gm.get_node(skill_id):
                links.append((role_id, skill_id, LinkType.REQUIRES))
        
        return links

    def link_course_to_graph(self, course_id: str, skill_ids: List[str]) -> List[Tuple[str, str, LinkType]]:
        links = []
        
        for skill_id in skill_ids:
            if self.gm.get_node(skill_id):
                links.append((course_id, skill_id, LinkType.TEACHES))
        
        return links

    def link_user_to_graph(self, user_id: str, skill_ids: List[str]) -> List[Tuple[str, str, LinkType]]:
        links = []
        
        for skill_id in skill_ids:
            if self.gm.get_node(skill_id):
                links.append((user_id, skill_id, LinkType.HAS_SKILL))
        
        return links

    def resolve_skill_to_canonical(self, skill_id: str) -> str:
        canonical = self.deduplicator.suggest_canonical_form(skill_id)
        if canonical:
            return canonical
        
        normalized = self.deduplicator.normalize_entity(skill_id)
        if normalized in self.skills_map:
            return normalized
        
        return skill_id

    async def add_new_skill(self, skill_id: str, category: Optional[str] = None, aliases: Optional[List[str]] = None, context: str = "") -> Node:
        canonical_id = self.resolve_skill_to_canonical(skill_id)
        
        if canonical_id != skill_id:
            self.deduplicator.add_alias(canonical_id, skill_id)
        
        existing = self.gm.get_node(canonical_id)
        if existing:
            return Node(**existing)
        
        inferred_category = category or await self.infer_skill_category(canonical_id, context)
        
        node = Node(
            id=canonical_id,
            type=NodeType.SKILL,
            category=inferred_category,
            title=canonical_id.replace('_', ' ').title(),
            aliases=aliases or []
        )
        
        self.gm.add_node(node)
        
        links = await self.link_entity_to_graph(node, context)
        for source, target, link_type in links:
            if not self.gm.graph.has_edge(source, target):
                self.gm.add_edge(source, target, link_type)
        
        return node

    def add_new_role(self, role_id: str, skill_ids: List[str], metadata: Optional[Dict] = None) -> Node:
        existing = self.gm.get_node(role_id)
        if existing:
            return Node(**existing)
        
        node = Node(
            id=role_id,
            type=NodeType.ROLE,
            title=role_id.replace('_', ' ').title(),
            metadata=metadata or {}
        )
        
        self.gm.add_node(node)
        
        for skill_id in skill_ids:
            if not self.gm.get_node(skill_id):
                import asyncio
                try:
                    loop = asyncio.get_event_loop()
                    loop.run_until_complete(self.add_new_skill(skill_id))
                except RuntimeError:
                    asyncio.run(self.add_new_skill(skill_id))
        
        links = self.link_role_to_graph(role_id, skill_ids)
        for source, target, link_type in links:
            if not self.gm.graph.has_edge(source, target):
                self.gm.add_edge(source, target, link_type)
        
        return node

    def add_new_course(self, course_id: str, skill_ids: List[str], title: str, provider: Optional[str] = None) -> Node:
        existing = self.gm.get_node(course_id)
        if existing:
            return Node(**existing)
        
        node = Node(
            id=course_id,
            type=NodeType.COURSE,
            title=title,
            metadata={'provider': provider} if provider else {}
        )
        
        self.gm.add_node(node)
        
        for skill_id in skill_ids:
            if not self.gm.get_node(skill_id):
                import asyncio
                try:
                    loop = asyncio.get_event_loop()
                    loop.run_until_complete(self.add_new_skill(skill_id))
                except RuntimeError:
                    asyncio.run(self.add_new_skill(skill_id))
        
        links = self.link_course_to_graph(course_id, skill_ids)
        for source, target, link_type in links:
            if not self.gm.graph.has_edge(source, target):
                self.gm.add_edge(source, target, link_type)
        
        return node

    def batch_link_entities(self, nodes: List[Node]) -> List[Link]:
        all_links = []
        
        roles = [n for n in nodes if n.type == NodeType.ROLE]
        skills = [n for n in nodes if n.type == NodeType.SKILL]
        
        for role in roles:
            role_skill_ids = [s.id for s in skills]
            links = self.link_role_to_graph(role.id, role_skill_ids)
            all_links.extend(links)
        
        for skill in skills:
            links = self.link_entity_to_graph_sync(skill)
            all_links.extend(links)
        
        return [Link(source=s, target=t, type=lt) for s, t, lt in all_links]

    def suggest_related_entities(self, entity_id: str, max_results: int = 5) -> List[Dict]:
        suggestions = []
        
        if entity_id in self.skills_map:
            category = self.skills_map[entity_id].get('category')
            if category:
                category_skills = [
                    (sid, data) for sid, data in self.skills_map.items()
                    if data.get('category') == category and sid != entity_id
                ]
                for sid, data in category_skills[:max_results]:
                    if self.gm.get_node(sid):
                        suggestions.append({
                            'id': sid,
                            'relationship': 'same_category',
                            'category': category,
                            'title': data.get('title', sid.replace('_', ' ').title())
                        })
        
        return suggestions[:max_results]


_entity_linker = None

def get_entity_linker(api_key: Optional[str] = None) -> EntityLinker:
    global _entity_linker
    if _entity_linker is None:
        _entity_linker = EntityLinker(api_key=api_key)
    return _entity_linker
