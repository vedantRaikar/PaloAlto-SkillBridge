"""
Pytest Configuration and Fixtures
=================================
Shared fixtures and configuration for tests.
"""

import pytest
import sys
from pathlib import Path

# Add app directory to path
app_path = Path(__file__).parent.parent
sys.path.insert(0, str(app_path))


@pytest.fixture
def sample_user_skills():
    """Sample user skills for testing."""
    return ["python", "git", "javascript"]


@pytest.fixture
def sample_role_skills():
    """Sample role skills for testing."""
    return ["python", "docker", "kubernetes", "linux", "ci_cd"]


@pytest.fixture
def devops_skills():
    """DevOps engineer skills."""
    return {
        "role": "devops_engineer",
        "required": ["linux", "docker", "kubernetes", "ci_cd", "scripting", "monitoring"],
        "user_has": ["python", "git"]
    }


@pytest.fixture
def frontend_skills():
    """Frontend developer skills."""
    return {
        "role": "frontend_developer",
        "required": ["html", "css", "javascript", "react", "typescript"],
        "user_has": ["javascript", "html"]
    }


@pytest.fixture
def backend_skills():
    """Backend developer skills."""
    return {
        "role": "backend_developer",
        "required": ["python", "sql", "api", "git", "databases"],
        "user_has": ["python", "sql"]
    }


@pytest.fixture
def mock_graph_manager():
    """Mock graph manager for testing."""
    from unittest.mock import MagicMock
    
    mock = MagicMock()
    mock.get_role_skills.return_value = ["python", "docker", "kubernetes"]
    mock.get_user_skills.return_value = ["python"]
    mock.get_all_roles.return_value = [
        {"id": "devops", "title": "DevOps Engineer"},
        {"id": "frontend", "title": "Frontend Developer"}
    ]
    return mock


@pytest.fixture
def skill_impact_scores():
    """Skill impact scores for testing."""
    return {
        "python": 9,
        "javascript": 9,
        "docker": 9,
        "kubernetes": 8,
        "aws": 9,
        "sql": 9,
        "git": 8,
        "linux": 7,
    }


@pytest.fixture
def skill_prerequisites():
    """Sample skill prerequisites for testing."""
    return {
        "kubernetes": ["docker", "linux"],
        "docker": ["linux"],
        "react": ["javascript", "html", "css"],
        "machine_learning": ["python", "statistics"],
        "deep_learning": ["machine_learning", "python"],
    }


@pytest.fixture
def fast_track_courses():
    """Sample fast track courses for testing."""
    return {
        "docker": [
            ("Docker Tutorial", "freecodecamp", 5, True),
            ("Docker Curriculum", "docker", 8, True),
        ],
        "kubernetes": [
            ("K8s Basics", "kubernetes.io", 5, True),
        ],
        "python": [
            ("Python Basics", "freecodecamp", 10, True),
        ],
    }
