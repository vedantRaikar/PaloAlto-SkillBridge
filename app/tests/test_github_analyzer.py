"""Tests for app/services/github_analyzer.py."""
import time
import pytest
from unittest.mock import MagicMock, AsyncMock, patch

from app.services.github_analyzer import GitHubCache, GitHubAnalyzer


# ============================================================
# GitHubCache
# ============================================================

@pytest.fixture(autouse=True)
def clear_cache():
    GitHubCache.clear()
    yield
    GitHubCache.clear()


def test_cache_set_and_get():
    GitHubCache.set("user:alice", {"name": "Alice"})
    result = GitHubCache.get("user:alice")
    assert result == {"name": "Alice"}


def test_cache_miss():
    result = GitHubCache.get("user:nonexistent")
    assert result is None


def test_cache_expired():
    import app.services.github_analyzer as gha_mod
    old_ttl = gha_mod.CACHE_TTL_SECONDS
    try:
        gha_mod.CACHE_TTL_SECONDS = -1  # immediately expired
        GitHubCache.set("user:bob", {"name": "Bob"})
        result = GitHubCache.get("user:bob")
        assert result is None
    finally:
        gha_mod.CACHE_TTL_SECONDS = old_ttl


def test_cache_clear():
    GitHubCache.set("a", {"x": 1})
    GitHubCache.set("b", {"y": 2})
    GitHubCache.clear()
    assert GitHubCache.get("a") is None
    assert GitHubCache.get("b") is None


# ============================================================
# GitHubAnalyzer initialization
# ============================================================

def test_create_without_token():
    analyzer = GitHubAnalyzer()
    assert "Authorization" not in analyzer.headers


def test_create_with_token():
    analyzer = GitHubAnalyzer(token="test-token")
    assert "Authorization" in analyzer.headers
    assert analyzer.headers["Authorization"] == "token test-token"


def test_initialize_llm_no_key(monkeypatch):
    from app.core import config as cfg_module
    monkeypatch.setattr(cfg_module.settings, "GROQ_API_KEY", None)
    analyzer = GitHubAnalyzer()
    analyzer._initialize_llm()
    assert analyzer._llm is None


def test_initialize_llm_with_key(monkeypatch):
    monkeypatch.setattr("app.services.github_analyzer.ChatGroq", MagicMock())
    from app.core import config as cfg_module
    monkeypatch.setattr(cfg_module.settings, "GROQ_API_KEY", "fake-key")
    analyzer = GitHubAnalyzer()
    analyzer.api_key = "fake-key"
    analyzer._initialize_llm()
    assert analyzer._llm is not None


# ============================================================
# _fetch_with_client
# ============================================================

@pytest.mark.anyio
async def test_fetch_with_client_success():
    analyzer = GitHubAnalyzer()
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.json.return_value = {"login": "alice"}
    client = AsyncMock()
    client.get = AsyncMock(return_value=mock_response)
    result = await analyzer._fetch_with_client(client, "https://api.github.com/users/alice")
    assert result["success"] is True
    assert result["data"]["login"] == "alice"


@pytest.mark.anyio
async def test_fetch_with_client_not_found():
    analyzer = GitHubAnalyzer()
    mock_response = MagicMock()
    mock_response.status_code = 404
    client = AsyncMock()
    client.get = AsyncMock(return_value=mock_response)
    result = await analyzer._fetch_with_client(client, "https://api.github.com/users/nobody")
    assert result["success"] is False
    assert result["status"] == 404


@pytest.mark.anyio
async def test_fetch_with_client_network_error():
    analyzer = GitHubAnalyzer()
    client = AsyncMock()
    client.get = AsyncMock(side_effect=Exception("Connection refused"))
    result = await analyzer._fetch_with_client(client, "https://api.github.com/users/alice")
    assert result["success"] is False
    assert "error" in result


# ============================================================
# get_repos_languages_parallel
# ============================================================

@pytest.mark.anyio
async def test_get_repos_languages_parallel_empty():
    analyzer = GitHubAnalyzer()
    result = await analyzer.get_repos_languages_parallel("alice", [])
    assert result == {}


@pytest.mark.anyio
async def test_get_repos_languages_parallel_single_repo(monkeypatch):
    analyzer = GitHubAnalyzer()
    analyzer.get_repo_languages = AsyncMock(return_value={"Python": 5000})
    repos = [{"name": "my-repo"}]
    result = await analyzer.get_repos_languages_parallel("alice", repos)
    assert "Python" in result
    assert result["Python"] == 5000


@pytest.mark.anyio
async def test_get_repos_languages_parallel_merges(monkeypatch):
    analyzer = GitHubAnalyzer()
    analyzer.get_repo_languages = AsyncMock(side_effect=[
        {"Python": 2000},
        {"Python": 3000, "JavaScript": 1000},
    ])
    repos = [{"name": "repo1"}, {"name": "repo2"}]
    result = await analyzer.get_repos_languages_parallel("alice", repos)
    assert result["Python"] == 5000
    assert result["JavaScript"] == 1000


# ============================================================
# _map_languages_to_skills_llm (no LLM → returns input)
# ============================================================

@pytest.mark.anyio
async def test_map_languages_to_skills_no_llm(monkeypatch):
    from app.core import config as cfg_module
    monkeypatch.setattr(cfg_module.settings, "GROQ_API_KEY", None)
    analyzer = GitHubAnalyzer()
    result = await analyzer._map_languages_to_skills_llm(["Python", "JavaScript"])
    assert "Python" in result or "python" in result


@pytest.mark.anyio
async def test_map_languages_to_skills_empty(monkeypatch):
    from app.core import config as cfg_module
    monkeypatch.setattr(cfg_module.settings, "GROQ_API_KEY", None)
    analyzer = GitHubAnalyzer()
    result = await analyzer._map_languages_to_skills_llm([])
    assert result == []


# ============================================================
# Cache-based shortcuts in get_user, get_repos
# ============================================================

@pytest.mark.anyio
async def test_get_user_returns_cached():
    GitHubCache.set("user:alice", {"login": "alice", "name": "Alice"})
    analyzer = GitHubAnalyzer()
    result = await analyzer.get_user("alice")
    assert result is not None
    assert result["login"] == "alice"


@pytest.mark.anyio
async def test_get_repos_returns_cached():
    cached_repos = [{"name": "repo1"}, {"name": "repo2"}]
    GitHubCache.set("repos:bob", cached_repos)
    analyzer = GitHubAnalyzer()
    result = await analyzer.get_repos("bob")
    assert result == cached_repos
