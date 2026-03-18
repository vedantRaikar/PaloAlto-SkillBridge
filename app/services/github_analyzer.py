import httpx
import asyncio
import time
from typing import Optional, List, Dict, Tuple
from functools import lru_cache
from app.services.resolver import SkillResolver

GITHUB_API = "https://api.github.com"
CACHE_TTL_SECONDS = 300

LANGUAGE_MAPPING = {
    "python": "python",
    "javascript": "javascript",
    "typescript": "typescript",
    "java": "java",
    "go": "go",
    "rust": "rust",
    "c++": "cpp",
    "c#": "csharp",
    "ruby": "ruby",
    "php": "php",
    "swift": "swift",
    "kotlin": "kotlin",
    "scala": "scala",
    "html": "html_css",
    "css": "html_css",
    "shell": "bash",
    "dockerfile": "docker",
}

PACKAGE_FILES = {
    "requirements.txt": "pip",
    "package.json": "npm",
    "Pipfile": "pip",
    "pyproject.toml": "pip",
    "go.mod": "go",
    "Cargo.toml": "rust",
    "Gemfile": "ruby",
    "composer.json": "php",
}


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
        self.headers = {
            "Accept": "application/vnd.github.v3+json"
        }
        if token:
            self.headers["Authorization"] = f"token {token}"

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
        resolved_skills = []
        for lang in top_languages:
            mapped = LANGUAGE_MAPPING.get(lang.lower(), lang.lower())
            resolved = self.resolver.resolve_skill(mapped)
            if resolved:
                resolved_skills.append(resolved)
            else:
                resolved_skills.append(mapped)

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
