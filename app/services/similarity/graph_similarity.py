"""
Graph-Based Skill Similarity (SimRank)
======================================
Computes skill similarity based on structural relationships in the knowledge graph.
Two skills are similar if they share neighbors — i.e., they are required by the same
roles, taught by the same courses, belong to the same domain, or are prerequisites
for the same downstream skills.

This captures domain relationships that text embeddings miss:
- "Docker" and "Kubernetes" are similar because they co-occur in DevOps roles.
- "React" and "Angular" are similar because they're taught by front-end courses.
- "SQL" and "PostgreSQL" are similar because the same roles require both.

SimRank formula (iterative):
    sim(a, a) = 1
    sim(a, b) = C / (|In(a)| * |In(b)|) * Σ sim(In_i(a), In_j(b))

where In(x) are the in-neighbors of x and C is a decay factor (0 < C < 1).
"""

import networkx as nx
from typing import Dict, List, Optional, Set, Tuple
from app.core.logger import get_logger

logger = get_logger(__name__)


class GraphSkillSimilarity:
    """
    Computes and caches SimRank-based similarity scores between skill nodes
    in the knowledge graph.
    """

    def __init__(self, decay: float = 0.8, max_iterations: int = 5, threshold: float = 0.3):
        self._decay = decay
        self._max_iterations = max_iterations
        self._threshold = threshold
        self._sim_scores: Dict[Tuple[str, str], float] = {}
        self._skill_nodes: List[str] = []
        self._computed = False

    def compute(self, graph: nx.DiGraph):
        """
        Build a skill-only projection of the knowledge graph and run
        iterative SimRank over it.
        """
        self._skill_nodes = [
            n for n in graph.nodes()
            if graph.nodes[n].get("type") == "skill"
        ]

        if len(self._skill_nodes) < 2:
            logger.info("SimRank: fewer than 2 skill nodes, skipping computation")
            self._computed = True
            return

        # Build an undirected skill projection where two skills are linked
        # if they share a common neighbor of any type (role, course, domain, etc.).
        skill_set = set(self._skill_nodes)
        neighbor_to_skills: Dict[str, Set[str]] = {}

        for skill in self._skill_nodes:
            # Collect all non-skill neighbors (predecessors + successors)
            neighbors = set()
            for pred in graph.predecessors(skill):
                if pred not in skill_set:
                    neighbors.add(pred)
            for succ in graph.successors(skill):
                if succ not in skill_set:
                    neighbors.add(succ)

            for nbr in neighbors:
                neighbor_to_skills.setdefault(nbr, set()).add(skill)

        # Build a weighted skill-skill graph:
        # edge weight = number of shared non-skill neighbors.
        proj = nx.Graph()
        proj.add_nodes_from(self._skill_nodes)

        for _nbr, skills in neighbor_to_skills.items():
            skills_list = list(skills)
            for i in range(len(skills_list)):
                for j in range(i + 1, len(skills_list)):
                    a, b = skills_list[i], skills_list[j]
                    if proj.has_edge(a, b):
                        proj[a][b]["weight"] += 1
                    else:
                        proj.add_edge(a, b, weight=1)

        # Iterative SimRank on the projected graph
        n = len(self._skill_nodes)
        idx = {s: i for i, s in enumerate(self._skill_nodes)}

        # Initialize: sim(a, a) = 1, sim(a, b) = 0
        sim = [[1.0 if i == j else 0.0 for j in range(n)] for i in range(n)]

        for _iteration in range(self._max_iterations):
            new_sim = [[0.0] * n for _ in range(n)]
            for i in range(n):
                new_sim[i][i] = 1.0

            for i in range(n):
                ni = list(proj.neighbors(self._skill_nodes[i]))
                if not ni:
                    continue
                for j in range(i + 1, n):
                    nj = list(proj.neighbors(self._skill_nodes[j]))
                    if not nj:
                        continue

                    total = 0.0
                    for a in ni:
                        ai = idx[a]
                        for b in nj:
                            bi = idx[b]
                            total += sim[ai][bi]

                    score = (self._decay / (len(ni) * len(nj))) * total
                    new_sim[i][j] = score
                    new_sim[j][i] = score

            sim = new_sim

        # Store only above-threshold pairs
        for i in range(n):
            for j in range(i + 1, n):
                if sim[i][j] >= self._threshold:
                    key = self._cache_key(self._skill_nodes[i], self._skill_nodes[j])
                    self._sim_scores[key] = sim[i][j]

        self._computed = True
        logger.info(
            "SimRank computed: %d skill nodes, %d similar pairs (threshold=%.2f)",
            n, len(self._sim_scores), self._threshold,
        )

    @staticmethod
    def _cache_key(a: str, b: str) -> Tuple[str, str]:
        return (a, b) if a < b else (b, a)

    def similarity(self, skill1: str, skill2: str) -> float:
        """Return the SimRank similarity score between two skills (0.0–1.0)."""
        if skill1 == skill2:
            return 1.0
        key = self._cache_key(skill1, skill2)
        return self._sim_scores.get(key, 0.0)

    def skills_match(self, skill1: str, skill2: str, threshold: Optional[float] = None) -> bool:
        """Check if two skills are similar based on graph structure."""
        threshold = threshold or self._threshold
        return self.similarity(skill1, skill2) >= threshold

    def find_similar_skills(
        self, skill: str, threshold: Optional[float] = None
    ) -> List[Tuple[str, float]]:
        """Return all skills similar to the given skill, sorted by score descending."""
        threshold = threshold or self._threshold
        results = []
        for (a, b), score in self._sim_scores.items():
            if score < threshold:
                continue
            if a == skill:
                results.append((b, score))
            elif b == skill:
                results.append((a, score))
        results.sort(key=lambda x: x[1], reverse=True)
        return results

    @property
    def is_computed(self) -> bool:
        return self._computed


_graph_similarity: Optional[GraphSkillSimilarity] = None


def get_graph_similarity() -> GraphSkillSimilarity:
    """Singleton accessor for the graph similarity engine."""
    global _graph_similarity
    if _graph_similarity is None:
        _graph_similarity = GraphSkillSimilarity()
    return _graph_similarity
