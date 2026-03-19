"""Tests for app/models/profile.py – Pydantic model definitions."""
import pytest
from app.models.profile import (
    ProfileSource,
    ContactInfo,
    GitHubProfile,
    ResumeProfile,
    UserProfile,
    ProfileMergeRequest,
)


# ---------------------------------------------------------------------------
# ProfileSource enum
# ---------------------------------------------------------------------------

def test_profile_source_values():
    assert ProfileSource.RESUME == "resume"
    assert ProfileSource.GITHUB == "github"
    assert ProfileSource.MANUAL == "manual"
    assert ProfileSource.MERGED == "merged"


# ---------------------------------------------------------------------------
# ContactInfo
# ---------------------------------------------------------------------------

def test_contact_info_all_none_by_default():
    ci = ContactInfo()
    assert ci.email is None
    assert ci.phone is None
    assert ci.linkedin is None
    assert ci.github is None


def test_contact_info_with_values():
    ci = ContactInfo(email="test@example.com", phone="1234567890", linkedin="johndoe", github="johndoe")
    assert ci.email == "test@example.com"
    assert ci.github == "johndoe"


# ---------------------------------------------------------------------------
# GitHubProfile
# ---------------------------------------------------------------------------

def test_github_profile_defaults():
    gp = GitHubProfile(username="octocat")
    assert gp.username == "octocat"
    assert gp.followers == 0
    assert gp.public_repos == 0
    assert gp.languages == {}
    assert gp.top_skills == []
    assert gp.repos == []


def test_github_profile_with_data():
    gp = GitHubProfile(
        username="dev",
        name="Dev User",
        bio="I code",
        followers=100,
        public_repos=20,
        languages={"Python": 70.5, "JavaScript": 29.5},
        top_skills=["python", "react"],
        repos=[{"name": "project1"}],
    )
    assert gp.name == "Dev User"
    assert gp.followers == 100
    assert "Python" in gp.languages
    assert "python" in gp.top_skills


# ---------------------------------------------------------------------------
# ResumeProfile
# ---------------------------------------------------------------------------

def test_resume_profile_defaults():
    rp = ResumeProfile()
    assert rp.name is None
    assert rp.skills == []
    assert rp.experience_years is None


def test_resume_profile_with_data():
    rp = ResumeProfile(
        name="Jane Doe",
        summary="Experienced developer",
        skills=["python", "django"],
        experience_years=5,
        contact=ContactInfo(email="jane@example.com"),
    )
    assert rp.name == "Jane Doe"
    assert "python" in rp.skills
    assert rp.experience_years == 5


# ---------------------------------------------------------------------------
# UserProfile
# ---------------------------------------------------------------------------

def test_user_profile_minimal():
    up = UserProfile(id="user1", name="Alice")
    assert up.id == "user1"
    assert up.name == "Alice"
    assert up.sources == []
    assert up.skills == []
    assert up.github is None
    assert up.resume is None
    assert up.experience_years is None
    assert up.readiness_scores == {}


def test_user_profile_full():
    contact = ContactInfo(email="alice@example.com", github="alice")
    github = GitHubProfile(username="alice", top_skills=["python"])
    up = UserProfile(
        id="alice1",
        name="Alice",
        sources=[ProfileSource.GITHUB, ProfileSource.RESUME],
        skills=["python", "docker"],
        github=github,
        contact=contact,
        experience_years=3,
        readiness_scores={"backend_developer": 0.75},
    )
    assert "python" in up.skills
    assert ProfileSource.GITHUB in up.sources
    assert up.github.username == "alice"
    assert up.readiness_scores["backend_developer"] == 0.75


def test_user_profile_serialization():
    up = UserProfile(
        id="u1",
        name="Bob",
        sources=[ProfileSource.MANUAL],
        skills=["javascript"],
        contact=ContactInfo(email="bob@example.com"),
    )
    d = up.model_dump()
    assert d["id"] == "u1"
    assert "javascript" in d["skills"]
    assert d["contact"]["email"] == "bob@example.com"


# ---------------------------------------------------------------------------
# ProfileMergeRequest
# ---------------------------------------------------------------------------

def test_profile_merge_request_minimal():
    req = ProfileMergeRequest(user_id="u1")
    assert req.user_id == "u1"
    assert req.github_username is None
    assert req.resume_base64 is None
    assert req.resume_filename is None
    assert req.additional_skills == []


def test_profile_merge_request_full():
    req = ProfileMergeRequest(
        user_id="u2",
        github_username="dev",
        resume_base64="base64data",
        resume_filename="resume.pdf",
        additional_skills=["python", "aws"],
    )
    assert req.github_username == "dev"
    assert "python" in req.additional_skills
