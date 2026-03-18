import os
from typing import List, Optional
from app.models.graph import ExtractionResult, Node, Link
from app.services.entity_extractor import EntityExtractor
from app.services.heuristic_extractor import HeuristicExtractor
from app.services.nlp_extractor import NLPExtractor
from app.services.pending_queue import PendingQueue

class ExtractionPipeline:
    def __init__(self, groq_api_key: Optional[str] = None):
        self.groq_api_key = groq_api_key or os.getenv("GROQ_API_KEY")
        self.entity_extractor = EntityExtractor(api_key=self.groq_api_key)
        self.heuristic_extractor = HeuristicExtractor()
        self.nlp_extractor = NLPExtractor()
        self.pending_queue = PendingQueue()
        self.tiers_attempted: List[str] = []

    async def extract(self, title: str, description: str) -> dict:
        self.tiers_attempted = []
        role_id = self._normalize_id(title)

        result = await self._tier1_llm(title, description)
        if result.success and result.nodes:
            return self._build_response(result, "llm", False)

        result = self._tier2_heuristic(title, description, role_id)
        if result.success and result.nodes:
            return self._build_response(result, "heuristic", False)

        result = self._tier3_nlp(title, description, role_id)
        if result.success and result.nodes:
            return self._build_response(result, "nlp", False)

        return self._tier4_human_loop(title, description)

    def _tier1_llm(self, title: str, description: str) -> ExtractionResult:
        self.tiers_attempted.append("llm")
        return self.entity_extractor.extract_sync(title, description)

    def _tier2_heuristic(self, title: str, description: str, role_id: str) -> ExtractionResult:
        self.tiers_attempted.append("heuristic")
        result = self.heuristic_extractor.extract(title, description)
        
        if role_id and result.nodes:
            links = [Link(source=role_id, target=n.id, type="REQUIRES") for n in result.nodes]
            result.links = links
            
            role_node = Node(id=role_id, type="role", title=title)
            result.nodes.insert(0, role_node)
        
        return result

    def _tier3_nlp(self, title: str, description: str, role_id: str) -> ExtractionResult:
        self.tiers_attempted.append("nlp")
        return self.nlp_extractor.extract(title, description, role_id)

    def _tier4_human_loop(self, title: str, description: str) -> dict:
        self.tiers_attempted.append("human_loop")
        
        item_id = self.pending_queue.add(
            title=title,
            description=description,
            item_type="job",
            error="All extraction tiers failed"
        )

        return {
            "extraction_result": ExtractionResult(
                nodes=[],
                links=[],
                success=False,
                method="none"
            ),
            "method_used": "none",
            "tiers_attempted": self.tiers_attempted,
            "fallback_triggered": True,
            "pending_item_id": item_id,
            "message": "Added to pending review queue for manual processing"
        }

    def _build_response(self, result: ExtractionResult, method: str, fallback: bool) -> dict:
        return {
            "extraction_result": result,
            "method_used": method,
            "tiers_attempted": self.tiers_attempted,
            "fallback_triggered": fallback,
            "nodes_count": len(result.nodes),
            "links_count": len(result.links)
        }

    def _normalize_id(self, text: str) -> str:
        import re
        text = text.lower().strip()
        text = re.sub(r'[^\w\s-]', '', text)
        text = re.sub(r'[\s]+', '_', text)
        return text

    def extract_sync(self, title: str, description: str) -> dict:
        import asyncio
        return asyncio.run(self.extract(title, description))
