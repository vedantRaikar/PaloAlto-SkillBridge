import httpx
import asyncio
import time
from typing import Optional, List, Dict, Tuple
from functools import lru_cache
from langchain_groq import ChatGroq
from langchain_core.prompts import PromptTemplate
from langchain_core.output_parsers import JsonOutputParser
from pydantic import BaseModel, Field
from app.services.resolver import SkillResolver
from app.core.config import settings

GITHUB_API = "https://api.github.com"
CACHE_TTL_SECONDS = 300

LANGUAGE_TO_SKILL_PROMPT = PromptTemplate.from_template('''
Given a list of programming languages/technologies found in a GitHub profile, map them to skill names.

Languages found: {languages}

Return ONLY valid JSON:
{{
  "skill_mappings": [
    {{
      "language": "python",
      "skill_id": "python",
      "category": "programming"
    }}
  ],
  "top_skills": ["skill1", "skill2", ...]
}}

JSON Response:
''')

REPO_ANALYSIS_PROMPT = PromptTemplate.from_template('''
Analyze this repository information and identify the technologies, frameworks, and skills it uses.

Repository name: {repo_name}
Description: {description}
Languages used: {languages}

Return ONLY valid JSON:
{{
  "technologies": ["react", "django", "docker", ...],
  "frameworks": ["express", "flask", ...],
  "infrastructure": ["aws", "kubernetes", ...],
  "databases": ["postgresql", "mongodb", ...],
  "skills": ["skill1", "skill2", ...]
}}

JSON Response:
''')


class GitHubCache:
    _cache: Dict[str, Tuple[float, Dict]] = {}

    @classmethod
    def get(cls, key: str) -> Optional[Dict]:
        if key in cls._cache:
            timestamp, data = cls._cache[key]
            if time.time() - timestamp < CACHE_TTL_SECONDS:
                return data
            del cls._cache[key]
        return None

    @classmethod
    def set(cls, key: str, data: Dict):
        cls._cache[key] = (time.time(), data)

    @classmethod
    def clear(cls):
        cls._cache.clear()


class GitHubAnalyzer:
    def __init__(self, token: Optional[str] = None, max_concurrent: int = 10):
        self.token = token
        self.resolver = SkillResolver()
        self.max_concurrent = max_concurrent
        self.api_key = settings.GROQ_API_KEY
        self._llm = None
        self._skill_mappings_cache: Dict[str, List[str]] = {}
        self.headers = {
            "Accept": "application/vnd.github.v3+json"
        }
        if token:
            self.headers["Authorization"] = f"token {token}"

    def _initialize_llm(self):
        if self._llm is None and self.api_key:
            self._llm = ChatGroq(
                api_key=self.api_key,
                model="llama-3.1-8b-instant",
                temperature=0.1,
                max_tokens=1024
            )

    async def _fetch_with_client(
        self,
        client: httpx.AsyncClient,
        url: str,
        params: Optional[Dict] = None
    ) -> Dict:
        try:
            response = await client.get(url, headers=self.headers, params=params, timeout=10.0)
            if response.status_code == 200:
                return {"success": True, "data": response.json()}
            return {"success": False, "status": response.status_code}
        except Exception as e:
            return {"success": False, "error": str(e)}

    async def get_user(self, username: str) -> Optional[Dict]:
        cached = GitHubCache.get(f"user:{username}")
        if cached:
            return cached

        async with httpx.AsyncClient() as client:
            result = await self._fetch_with_client(client, f"{GITHUB_API}/users/{username}")
            if result.get("success"):
                user_data = result["data"]
                GitHubCache.set(f"user:{username}", user_data)
                return user_data
            return None

    async def get_repos(self, username: str, limit: int = 30) -> List[Dict]:
        cached = GitHubCache.get(f"repos:{username}")
        if cached:
            return cached

        async with httpx.AsyncClient() as client:
            result = await self._fetch_with_client(
                client,
                f"{GITHUB_API}/users/{username}/repos",
                params={"sort": "updated", "per_page": limit}
            )
            if result.get("success"):
                repos_data = result["data"]
                GitHubCache.set(f"repos:{username}", repos_data)
                return repos_data
            return []

    async def get_repo_languages(self, owner: str, repo: str) -> Dict[str, int]:
        async with httpx.AsyncClient() as client:
            result = await self._fetch_with_client(
                client,
                f"{GITHUB_API}/repos/{owner}/{repo}/languages"
            )
            if result.get("success"):
                return result["data"]
            return {}

    async def get_repos_languages_parallel(
        self,
        owner: str,
        repos: List[Dict],
        max_concurrent: int = 10
    ) -> Dict[str, int]:
        if not repos:
            return {}

        semaphore = asyncio.Semaphore(max_concurrent)

        async def fetch_with_semaphore(repo: Dict) -> Dict[str, int]:
            async with semaphore:
                return await self.get_repo_languages(owner, repo['name'])

        tasks = [fetch_with_semaphore(repo) for repo in repos]
        results = await asyncio.gather(*tasks, return_exceptions=True)

        combined = {}
        for result in results:
            if isinstance(result, dict):
                for lang, bytes_count in result.items():
                    combined[lang] = combined.get(lang, 0) + bytes_count

        return combined

    async def _map_languages_to_skills_llm(self, languages: List[str]) -> List[str]:
        if not languages:
            return []
        
        cache_key = ','.join(sorted(languages))
        if cache_key in self._skill_mappings_cache:
            return self._skill_mappings_cache[cache_key]
        
        self._initialize_llm()
        if not self._llm:
            return languages
        
        try:
            class SkillMapping(BaseModel):
                language: str
                skill_id: str
                category: Optional[str] = None
            
            class LanguageMappings(BaseModel):
                skill_mappings: List[SkillMapping] = Field(default_factory=list)
                top_skills: List[str] = Field(default_factory=list)
            
            chain = LANGUAGE_TO_SKILL_PROMPT | self._llm | JsonOutputParser()
            result = await chain.ainvoke({"languages": ', '.join(languages)})
            
            top_skills = result.get("top_skills", [])
            self._skill_mappings_cache[cache_key] = top_skills
            return top_skills
        except Exception:
            return languages

    async def _analyze_repo_llm(self, repo_name: str, description: str, languages: List[str]) -> Dict:
        self._initialize_llm()
        if not self._llm:
            return {"skills": languages}
        
        try:
            chain = REPO_ANALYSIS_PROMPT | self._llm | JsonOutputParser()
            result = await chain.ainvoke({
                "repo_name": repo_name,
                "description": description or "",
                "languages": ', '.join(languages)
            })
            return result
        except Exception:
            return {"skills": languages}

    async def analyze_profile(self, username: str) -> Dict:
        user = await self.get_user(username)
        if not user:
            return {"error": "User not found", "username": username}

        repos = await self.get_repos(username)
        repos_to_analyze = repos[:10]

        language_counts = await self.get_repos_languages_parallel(
            user['login'],
            repos_to_analyze,
            self.max_concurrent
        )

        total_bytes = sum(language_counts.values())
        
        if total_bytes > 0:
            language_percentages = {
                lang: round(count / total_bytes, 2)
                for lang, count in language_counts.items()
            }
        else:
            language_percentages = {}

        top_languages = list(language_percentages.keys())[:5]
        
        top_skills = await self._map_languages_to_skills_llm(top_languages)
        
        resolved_skills = []
        for skill in top_skills:
            resolved = self.resolver.resolve_skill(skill)
            if resolved:
                resolved_skills.append(resolved)
            else:
                resolved_skills.append(skill)

        return {
            "username": username,
            "name": user.get("name"),
            "bio": user.get("bio"),
            "followers": user.get("followers", 0),
            "public_repos": user.get("public_repos", 0),
            "languages": language_percentages,
            "top_languages": top_languages,
            "top_skills": list(set(resolved_skills)),
            "total_repos_analyzed": len(repos_to_analyze),
            "repos": [
                {
                    "name": r['name'],
                    "language": r.get('language'),
                    "stars": r.get('stargazers_count', 0),
                    "url": r['html_url']
                }
                for r in repos_to_analyze
            ]
        }

    def analyze_sync(self, username: str) -> Dict:
        try:
            loop = asyncio.get_running_loop()
            import concurrent.futures
            with concurrent.futures.ThreadPoolExecutor() as pool:
                future = pool.submit(asyncio.run, self.analyze_profile(username))
                return future.result()
        except RuntimeError:
            return asyncio.run(self.analyze_profile(username))

    async def analyze_profile_async(self, username: str) -> Dict:
        return await self.analyze_profile(username)
