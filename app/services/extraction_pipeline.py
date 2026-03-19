import os
import re
from typing import List, Optional, Set, Dict, Any
from app.models.graph import ExtractionResult, Node, Link, NodeType
from app.services.entity_extractor import EntityExtractor
from app.services.heuristic_extractor import HeuristicExtractor
from app.services.nlp_extractor import NLPExtractor
from app.services.topic_extractor import get_topic_extractor
from app.services.entity_linker import get_entity_linker
from app.services.pending_queue import PendingQueue

TECH_TERMS = [
    'python', 'javascript', 'typescript', 'java', 'go', 'rust', 'ruby', 'c++', 'c#', 'csharp', 'php', 'swift', 'kotlin', 'scala', 'r', 'matlab', 'perl', 'haskell', 'elixir', 'clojure',
    'react', 'reactjs', 'vue', 'vuejs', 'angular', 'angularjs', 'svelte', 'nextjs', 'next.js', 'nuxt', 'nuxtjs', 'gatsby', 'remix',
    'nodejs', 'node.js', 'express', 'expressjs', 'fastapi', 'django', 'flask', 'rails', 'ruby on rails', 'spring', 'spring boot', 'asp.net', 'laravel', 'phoenix', 'gin',
    'aws', 'amazon web services', 'azure', 'microsoft azure', 'gcp', 'google cloud', 'google cloud platform', 'heroku', 'vercel', 'netlify', 'digitalocean', 'linode',
    'docker', 'kubernetes', 'k8s', 'helm', 'terraform', 'ansible', 'puppet', 'chef', 'jenkins', 'gitlab ci', 'github actions', 'circleci', 'travis', 'bitbucket',
    'postgresql', 'postgres', 'mysql', 'mariadb', 'mongodb', 'mongo', 'redis', 'elasticsearch', 'elastic', 'cassandra', 'dynamodb', 'sqlite', 'sql server', 'oracle', 'snowflake', 'bigquery',
    'git', 'github', 'gitlab', 'bitbucket', 'svn', 'mercurial',
    'graphql', 'rest', 'restful', 'grpc', 'websocket', 'socket.io', 'webhook', 'api', 'microservice', 'microservices',
    'html', 'css', 'sass', 'scss', 'less', 'tailwind', 'bootstrap', 'material ui', 'mui', 'chakra ui', 'styled-components',
    'tensorflow', 'pytorch', 'keras', 'scikit-learn', 'sklearn', 'pandas', 'numpy', 'scipy', 'ml', 'machine learning', 'deep learning', 'neural network', 'nlp', 'computer vision', 'ai', 'artificial intelligence', 'data science', 'data engineering',
    'linux', 'unix', 'bash', 'shell', 'zsh', 'powershell', 'windows server',
    'agile', 'scrum', 'kanban', 'jira', 'confluence', 'asana', 'trello', 'notion',
    'ci/cd', 'cicd', 'devops', 'devops engineer', 'sre', 'site reliability',
    'oauth', 'jwt', 'oauth2', 'ssl', 'tls', 'https', 'encryption', 'security', 'cybersecurity', 'penetration testing', 'owasp',
    'kafka', 'rabbitmq', 'sqs', 'sns', 'activemq', 'message queue', 'event driven',
    'spark', 'hadoop', 'hive', 'airflow', 'dbt', 'etl', 'data pipeline', 'data warehouse', 'data lake',
    'nginx', 'apache', 'caddy', 'load balancer', 'reverse proxy', 'cdn', 'cloudflare', 'akamai',
    'vpc', 'subnet', 'route53', 'cloudformation', 'cloudwatch', 'lambda', 'serverless', 'eks', 'eks', 'gke', 'aks', 'ecs', 'fargate',
    'vim', 'vscode', 'intellij', 'pycharm', 'webstorm', 'datagrip', 'postman', 'insomnia', 'swagger', 'openapi',
    'testing', 'tdd', 'bdd', 'unit test', 'integration test', 'e2e', 'end to end', 'selenium', 'cypress', 'playwright', 'jest', 'mocha', 'pytest', 'junit', 'testng',
    'mvc', 'mvvm', 'clean architecture', 'domain driven design', 'ddd', 'microservices architecture', 'event sourcing', 'cqrs',
    'tcp', 'udp', 'http', 'https', 'dns', 'dhcp', 'ssh', 'ftp', 'sftp', 'smtp', 'imap', 'pop3',
    'mongodb', 'mongoose', 'prisma', 'sequelize', 'typeorm', 'sqlalchemy', 'hibernate',
    'webpack', 'vite', 'esbuild', 'rollup', 'parcel', 'babel', 'typescript', 'eslint', 'prettier', 'husky', 'lint-staged',
    'nginx', 'apache', 'caddy', 'traefik', 'envoy', 'kong', 'apigee',
    'prometheus', 'grafana', 'datadog', 'new relic', 'sentry', 'elk', 'splunk', 'loki', 'tempo',
]

COMMON_WORDS = {
    'the', 'and', 'for', 'are', 'but', 'not', 'you', 'all', 'can', 'her', 'was', 'one', 'our', 'out', 'day', 'get', 'has', 'him', 'his', 'how', 'its', 'may', 'new', 'now', 'old', 'see', 'two', 'way', 'who', 'boy', 'did', 'own', 'say', 'she', 'too', 'use', 'able', 'back', 'been', 'call', 'come', 'each', 'find', 'give', 'good', 'help', 'here', 'just', 'know', 'like', 'look', 'make', 'more', 'most', 'much', 'need', 'over', 'part', 'such', 'take', 'than', 'them', 'then', 'they', 'this', 'time', 'turn', 'well', 'work', 'year', 'also', 'any', 'because', 'between', 'both', 'company', 'development', 'experience', 'from', 'have', 'help', 'including', 'information', 'into', 'less', 'level', 'like', 'long', 'looking', 'more', 'must', 'need', 'only', 'other', 'people', 'position', 'required', 'role', 'same', 'service', 'should', 'skills', 'team', 'technical', 'they', 'those', 'through', 'using', 'what', 'when', 'where', 'which', 'while', 'with', 'within', 'would', 'required', 'preferred', 'plus', 'strong', 'working', 'years', 'experience', 'plus', 'etc', 'e.g.', 'i.e.', 'like', 'etc', 'including', 'knowledge', 'understanding', 'familiarity', 'proficiency', 'expertise', 'ability', 'capable', 'experience', 'exposure', 'familiar', 'proficient', 'experienced', 'skilled'
}


class DynamicSkillExtractor:
    def __init__(self):
        self.tech_terms_set = set(TECH_TERMS)
        self.common_words_set = COMMON_WORDS
    
    def extract_all_skills(self, text: str) -> Set[str]:
        text_lower = text.lower()
        found_skills = set()
        
        for term in self.tech_terms_set:
            if term in text_lower:
                normalized = term.replace(' ', '_').replace('.', '_')
                found_skills.add(normalized)
        
        words = re.findall(r'\b[a-z][a-z0-9+#-]*\b', text_lower)
        
        for i, word in enumerate(words):
            if len(word) < 3 or word in self.common_words_set:
                continue
            
            if word in self.tech_terms_set:
                found_skills.add(word)
                continue
            
            if i > 0 and words[i-1] in self.tech_terms_set:
                combined = f"{words[i-1]}_{word}"
                if combined in self.tech_terms_set:
                    found_skills.add(combined)
            
            if i < len(words) - 1 and words[i+1] in self.tech_terms_set:
                combined = f"{word}_{words[i+1]}"
                if combined in self.tech_terms_set:
                    found_skills.add(combined)
        
        camel_case = re.findall(r'\b[A-Z][a-z]+(?:[A-Z][a-z]+)+\b', text)
        for match in camel_case:
            normalized = match.replace(' ', '_').lower()
            found_skills.add(normalized)
        
        version_patterns = re.findall(r'\b([a-z][a-z0-9+-]*)[._]?v?(\d+(?:\.\d+)*)\b', text_lower)
        for base, version in version_patterns:
            if base in self.tech_terms_set:
                found_skills.add(base)
        
        framework_tools = re.findall(r'\b([A-Z][a-z]+(?:\s+[A-Z][a-z]+)*)\b', text)
        for match in framework_tools:
            if len(match) > 3:
                normalized = match.lower().replace(' ', '_')
                if normalized in self.tech_terms_set or any(t in normalized for t in ['js', 'ts', 'sql', 'api', 'aws', 'gcp', 'sql']):
                    found_skills.add(normalized)
        
        found_skills.discard('')
        found_skills.discard(' ')
        
        return found_skills


class ExtractionPipeline:
    def __init__(self, groq_api_key: Optional[str] = None):
        self.groq_api_key = groq_api_key or os.getenv("GROQ_API_KEY")
        self.entity_extractor = EntityExtractor(api_key=self.groq_api_key)
        self.heuristic_extractor = HeuristicExtractor()
        self.nlp_extractor = NLPExtractor()
        self.dynamic_extractor = DynamicSkillExtractor()
        self.pending_queue = PendingQueue()
        self.tiers_attempted: List[str] = []

    async def extract(self, title: str, description: str) -> dict:
        self.tiers_attempted = []
        role_id = self._normalize_id(title)
        combined_text = f"{title} {description}"

        result = await self._tier1_llm(title, description, role_id, combined_text)
        if result.success and result.nodes:
            result = await self._post_process_result(result, role_id)
            return self._build_response(result, "llm", False)

        result = await self._tier2_dynamic(title, description, role_id, combined_text)
        if result.success and result.nodes:
            result = await self._post_process_result(result, role_id)
            return self._build_response(result, "dynamic", False)

        return await self._tier3_human_loop(title, description)

    async def _tier1_llm(self, title: str, description: str, role_id: str, combined_text: str) -> ExtractionResult:
        self.tiers_attempted.append("llm")
        
        entity_result = await self.entity_extractor.extract(title, description)
        topic_extractor = get_topic_extractor(api_key=self.groq_api_key)
        topic_result = await topic_extractor.full_topic_extraction_llm(title, description, [])
        
        all_skills: Dict[str, Dict] = {}
        
        if entity_result.success and entity_result.nodes:
            for node in entity_result.nodes:
                if node.type == NodeType.SKILL:
                    all_skills[node.id] = {
                        'id': node.id,
                        'category': node.category,
                        'source': 'llm_extraction'
                    }
        
        for skill in topic_result.get('additional_skills', []):
            normalized = self._normalize_id(skill)
            if normalized and normalized not in all_skills:
                all_skills[normalized] = {
                    'id': normalized,
                    'category': None,
                    'source': 'llm_topic'
                }
        
        for skill in topic_result.get('implied_skills', []):
            normalized = self._normalize_id(skill)
            if normalized and normalized not in all_skills:
                all_skills[normalized] = {
                    'id': normalized,
                    'category': None,
                    'source': 'llm_implied'
                }
        
        llm_extracted_count = len(all_skills)
        
        dynamic_skills = self.dynamic_extractor.extract_all_skills(combined_text)
        for skill in dynamic_skills:
            if skill not in all_skills:
                all_skills[skill] = {
                    'id': skill,
                    'category': None,
                    'source': 'dynamic'
                }
        
        nodes = []
        links = []
        
        if all_skills:
            role_node = Node(id=role_id, type=NodeType.ROLE, title=title)
            nodes.append(role_node)
            
            for skill_id, skill_data in all_skills.items():
                nodes.append(Node(
                    id=skill_id,
                    type=NodeType.SKILL,
                    category=skill_data.get('category')
                ))
                links.append(Link(
                    source=role_id,
                    target=skill_id,
                    type="REQUIRES"
                ))
            
            if entity_result.links:
                links.extend(entity_result.links)
        elif entity_result.nodes:
            nodes = entity_result.nodes
            links = entity_result.links
        
        return ExtractionResult(
            nodes=nodes,
            links=links,
            success=len(nodes) > 0,
            method="llm"
        )

    async def _tier2_dynamic(self, title: str, description: str, role_id: str, combined_text: str) -> ExtractionResult:
        self.tiers_attempted.append("dynamic_fallback")
        
        found_skills = self.dynamic_extractor.extract_all_skills(combined_text)
        
        nodes = []
        if found_skills:
            role_node = Node(id=role_id, type=NodeType.ROLE, title=title)
            nodes.append(role_node)
            
            for skill in found_skills:
                nodes.append(Node(
                    id=skill,
                    type=NodeType.SKILL,
                    category=None
                ))
        
        links = []
        for node in nodes:
            if node.type == NodeType.SKILL:
                links.append(Link(
                    source=role_id,
                    target=node.id,
                    type="REQUIRES"
                ))
        
        return ExtractionResult(
            nodes=nodes,
            links=links,
            success=len(nodes) > 0,
            method="dynamic_fallback"
        )

    async def _tier3_human_loop(self, title: str, description: str) -> dict:
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

    async def _post_process_result(self, result: ExtractionResult, role_id: str) -> ExtractionResult:
        entity_linker = get_entity_linker(api_key=self.groq_api_key)
        
        for node in result.nodes:
            if node.type == NodeType.SKILL and not node.category:
                category = await entity_linker.infer_skill_category(node.id, role_id)
                node.category = category
        
        return result

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
        text = text.lower().strip()
        text = re.sub(r'[^\w\s-]', '', text)
        text = re.sub(r'[\s]+', '_', text)
        return text

    def extract_sync(self, title: str, description: str) -> dict:
        import asyncio
        import concurrent.futures
        try:
            loop = asyncio.get_running_loop()
            with concurrent.futures.ThreadPoolExecutor() as pool:
                future = pool.submit(asyncio.run, self.extract(title, description))
                return future.result(timeout=120)
        except RuntimeError:
            return asyncio.run(self.extract(title, description))
