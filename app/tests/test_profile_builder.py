"""Tests for app/services/profile_builder.py."""
import pytest
from unittest.mock import MagicMock, AsyncMock, patch

from app.services.profile_builder import ProfileBuilder
from app.models.profile import UserProfile, ProfileSource, ContactInfo, GitHubProfile


def _make_profile(uid="user1", name="Alice", skills=None, source=ProfileSource.GITHUB):
    return UserProfile(
        id=uid,
        name=name,
        sources=[source],
        skills=skills or ["python"],
        contact=ContactInfo(email="alice@example.com", github="alice"),
    )


@pytest.fixture()
def builder():
    pb = ProfileBuilder()
    pb.github_analyzer = MagicMock()
    pb.resume_parser = MagicMock()
    pb.resolver = MagicMock()
    pb.graph_manager = MagicMock()
    pb.graph_manager.get_node.return_value = None
    pb.graph_manager.graph = MagicMock()
    pb.graph_manager.graph.has_edge.return_value = False
    pb.graph_manager.add_node = MagicMock()
    pb.graph_manager.add_edge = MagicMock()
    pb.graph_manager.save_graph = MagicMock()
    return pb


# ---------------------------------------------------------------------------
# build_from_github_async
# ---------------------------------------------------------------------------

@pytest.mark.anyio
async def test_build_from_github_async_success(builder):
    builder.github_analyzer.analyze_profile_async = AsyncMock(return_value={
        "name": "Alice",
        "bio": "Developer",
        "followers": 100,
        "public_repos": 10,
        "languages": {"Python": 5000},
        "top_skills": ["python", "docker"],
        "repos": [],
    })
    profile = await builder.build_from_github_async("alice")
    assert profile is not None
    assert profile.id == "github_alice"
    assert "python" in profile.skills


@pytest.mark.anyio
async def test_build_from_github_async_error(builder):
    builder.github_analyzer.analyze_profile_async = AsyncMock(return_value={"error": "Not found"})
    profile = await builder.build_from_github_async("nonexistent")
    assert profile is None


# ---------------------------------------------------------------------------
# build_from_github (sync)
# ---------------------------------------------------------------------------

def test_build_from_github_sync_success(builder):
    builder.github_analyzer.analyze_sync = MagicMock(return_value={
        "name": "Bob",
        "bio": "Engineer",
        "followers": 50,
        "public_repos": 5,
        "languages": {"JavaScript": 3000},
        "top_skills": ["javascript"],
        "repos": [],
    })
    profile = builder.build_from_github("bob")
    assert profile is not None
    assert profile.id == "github_bob"


def test_build_from_github_sync_error(builder):
    builder.github_analyzer.analyze_sync = MagicMock(return_value={"error": "Rate limited"})
    profile = builder.build_from_github("ratelimited")
    assert profile is None


# ---------------------------------------------------------------------------
# build_from_resume
# ---------------------------------------------------------------------------

def test_build_from_resume_success(builder):
    builder.resume_parser.parse_resume_bytes = MagicMock(return_value={
        "success": True,
        "name": "Carol",
        "contact": {"email": "carol@example.com", "phone": "123", "linkedin": "", "github": "carol"},
        "summary": "Experienced developer",
        "resolved_skills": ["python", "aws"],
        "experience_years": 5,
    })
    profile = builder.build_from_resume(b"fake pdf content", "resume.pdf")
    assert profile is not None
    assert "python" in profile.skills
    assert profile.name == "Carol"


def test_build_from_resume_failure(builder):
    builder.resume_parser.parse_resume_bytes = MagicMock(return_value={
        "success": False,
        "error": "Invalid file",
    })
    with pytest.raises(ValueError, match="Invalid file"):
        builder.build_from_resume(b"garbage", "file.pdf")


def test_build_from_resume_with_user_id(builder):
    builder.resume_parser.parse_resume_bytes = MagicMock(return_value={
        "success": True,
        "name": "Dan",
        "contact": {},
        "summary": "",
        "resolved_skills": ["java"],
        "experience_years": None,
    })
    profile = builder.build_from_resume(b"pdf", "cv.pdf", user_id="custom_user")
    assert profile.id == "custom_user"


# ---------------------------------------------------------------------------
# merge_profiles
# ---------------------------------------------------------------------------

def test_merge_profiles_two(builder):
    p1 = _make_profile("u1", "Alice", ["python"], ProfileSource.GITHUB)
    p2 = _make_profile("u2", "Unknown User", ["docker"], ProfileSource.RESUME)
    merged = builder.merge_profiles([p1, p2])
    assert "python" in merged.skills
    assert "docker" in merged.skills
    assert merged.name == "Alice"


def test_merge_profiles_uses_max_experience(builder):
    p1 = _make_profile("u1", "Alice", ["python"])
    p1.experience_years = 3
    p2 = _make_profile("u2", "Bob", ["java"])
    p2.experience_years = 5
    merged = builder.merge_profiles([p1, p2])
    assert merged.experience_years == 5


def test_merge_profiles_merges_contact(builder):
    p1 = _make_profile("u1", "Alice", ["python"])
    p1.contact = ContactInfo(email="alice@example.com")
    p2 = _make_profile("u2", "Alice", ["docker"])
    p2.contact = ContactInfo(phone="555-1234")
    merged = builder.merge_profiles([p1, p2])
    assert merged.contact.email == "alice@example.com"
    assert merged.contact.phone == "555-1234"


def test_merge_profiles_includes_merged_source(builder):
    p1 = _make_profile("u1", "Alice", ["python"])
    p2 = _make_profile("u2", "Bob", ["java"])
    merged = builder.merge_profiles([p1, p2])
    assert ProfileSource.MERGED in merged.sources


# ---------------------------------------------------------------------------
# save_to_graph
# ---------------------------------------------------------------------------

def test_save_to_graph_new_user(builder):
    profile = _make_profile("user_new", "NewUser", ["python"])
    profile.experience_years = 2
    builder.save_to_graph(profile)
    builder.graph_manager.add_node.assert_called_once()
    builder.graph_manager.save_graph.assert_called_once()


def test_save_to_graph_existing_user(builder):
    builder.graph_manager.get_node.return_value = {"type": "user"}
    profile = _make_profile("user_existing", "ExistingUser", ["python"])
    builder.save_to_graph(profile)
    # Should not add node again
    builder.graph_manager.add_node.assert_not_called()
    builder.graph_manager.save_graph.assert_called_once()


def test_save_to_graph_links_skills(builder):
    builder.graph_manager.get_node.side_effect = lambda nid: (
        None if nid == "user1" else {"type": "skill"}
    )
    profile = _make_profile("user1", "Alice", ["python", "docker"])
    builder.save_to_graph(profile)
    assert builder.graph_manager.add_edge.call_count == 2


# ---------------------------------------------------------------------------
# calculate_readiness
# ---------------------------------------------------------------------------

def test_calculate_readiness(builder, monkeypatch):
    import app.services.gap_analyzer as ga_mod
    mock_instance = MagicMock()
    mock_instance.calculate_readiness_score.return_value = 0.8
    monkeypatch.setattr(ga_mod, "GapAnalyzer", lambda: mock_instance)
    profile = _make_profile("u1", "Alice", ["python"])
    result = builder.calculate_readiness(profile, ["backend_dev"])
    assert isinstance(result, dict)
    assert result.get("backend_dev") == 0.8


# ---------------------------------------------------------------------------
# clear_github_cache
# ---------------------------------------------------------------------------

def test_clear_github_cache(builder):
    from app.services.github_analyzer import GitHubCache
    GitHubCache._cache["test"] = (0, {})
    builder.clear_github_cache()
    assert GitHubCache._cache == {}
