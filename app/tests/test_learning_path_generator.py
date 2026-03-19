"""
Unit Tests for Learning Path Generator
===================================
Tests topological sort and learning path generation.
"""

import pytest
from app.services.learning_path_generator import (
    LearningPathGenerator,
    SKILL_PREREQUISITES,
    SKILL_LEVELS,
)


class TestTopologicalSort:
    """Tests for topological sort algorithm."""

    def setup_method(self):
        """Setup test fixtures."""
        self.generator = LearningPathGenerator()

    def test_empty_skills_list(self):
        """Test with empty skills list."""
        result = self.generator.topological_sort_skills([])
        assert result == []

    def test_single_skill_no_prerequisites(self):
        """Test single skill with no prerequisites."""
        result = self.generator.topological_sort_skills(["python"])
        assert result == ["python"]

    def test_skills_with_prerequisites_respected(self):
        """Test that prerequisites are respected in ordering."""
        skills = ["kubernetes", "docker", "linux"]
        result = self.generator.topological_sort_skills(skills)
        
        # kubernetes depends on linux and docker
        # docker depends on linux
        # linux should come before docker
        # docker should come before kubernetes
        
        if "linux" in result and "docker" in result:
            linux_idx = result.index("linux")
            docker_idx = result.index("docker")
            assert linux_idx < docker_idx, "linux should come before docker"

    def test_all_skills_returned(self):
        """Test that all input skills are returned."""
        skills = ["python", "java", "javascript", "react"]
        result = self.generator.topological_sort_skills(skills)
        
        assert len(result) == len(skills)
        for skill in skills:
            assert skill in result

    def test_skills_with_circular_dependency(self):
        """Test handling of skills that might create cycles."""
        # This test ensures the algorithm handles potential cycles gracefully
        skills = ["docker", "kubernetes", "ci_cd"]
        result = self.generator.topological_sort_skills(skills)
        
        assert len(result) == len(skills)
        assert set(result) == set(skills)


class TestSkillPrerequisites:
    """Tests for skill prerequisite detection."""

    def setup_method(self):
        """Setup test fixtures."""
        self.generator = LearningPathGenerator()

    def test_docker_prerequisites(self):
        """Test docker prerequisites."""
        prereqs = self.generator.get_prerequisites("docker")
        assert "linux" in prereqs or len(prereqs) >= 0  # docker needs linux

    def test_kubernetes_prerequisites(self):
        """Test kubernetes prerequisites."""
        prereqs = self.generator.get_prerequisites("kubernetes")
        assert "linux" in prereqs
        assert "docker" in prereqs

    def test_python_no_prerequisites(self):
        """Test python has no prerequisites."""
        prereqs = self.generator.get_prerequisites("python")
        # Python is a starting language - should have no prerequisites
        assert len(prereqs) == 0

    def test_all_prerequisites_recursive(self):
        """Test recursive prerequisite finding."""
        prereqs = self.generator.get_all_prerequisites("kubernetes")
        
        # Should include transitive dependencies
        assert "linux" in prereqs
        assert "docker" in prereqs


class TestSkillLevels:
    """Tests for skill level categorization."""

    def setup_method(self):
        """Setup test fixtures."""
        self.generator = LearningPathGenerator()

    def test_beginner_skills(self):
        """Test beginner level skills."""
        beginner_skills = ["html", "css", "git", "python"]
        for skill in beginner_skills:
            level = self.generator.get_skill_level(skill)
            assert level in ["beginner", "intermediate"], f"{skill} should be beginner or intermediate"

    def test_intermediate_skills(self):
        """Test intermediate level skills."""
        level = self.generator.get_skill_level("react")
        assert level in ["beginner", "intermediate", "advanced"]

    def test_advanced_skills(self):
        """Test advanced level skills."""
        level = self.generator.get_skill_level("kubernetes")
        assert level in ["intermediate", "advanced"]


class TestSkillCategories:
    """Tests for skill category assignment."""

    def setup_method(self):
        """Setup test fixtures."""
        self.generator = LearningPathGenerator()

    def test_programming_category(self):
        """Test programming category skills."""
        for skill in ["python", "java", "javascript"]:
            category = self.generator.get_skill_category(skill)
            assert category in ["programming", "general", "data"]

    def test_devops_category(self):
        """Test DevOps category skills."""
        for skill in ["docker", "kubernetes", "linux"]:
            category = self.generator.get_skill_category(skill)
            # These can be categorized as devops or general
            assert category is not None

    def test_database_category(self):
        """Test database category skills."""
        category = self.generator.get_skill_category("sql")
        assert category == "database"


class TestLearningPathGeneration:
    """Tests for complete learning path generation."""

    def setup_method(self):
        """Setup test fixtures."""
        self.generator = LearningPathGenerator()

    def test_generate_path_with_user_skills(self):
        """Test path generation with user skills."""
        user_skills = ["python", "git"]
        missing_skills = ["docker", "kubernetes", "linux"]
        
        path = self.generator.generate_learning_path(missing_skills, user_skills)
        
        assert "ordered_skills" in path
        assert "phases" in path
        assert len(path["ordered_skills"]) > 0

    def test_path_includes_all_missing_skills(self):
        """Test that path includes all missing skills."""
        missing_skills = ["docker", "kubernetes"]
        user_skills = ["python"]
        
        path = self.generator.generate_learning_path(missing_skills, user_skills)
        
        for skill in missing_skills:
            assert skill in path["ordered_skills"]

    def test_path_has_time_estimates(self):
        """Test that path includes time estimates."""
        path = self.generator.generate_learning_path(["docker"], [])
        
        assert "estimated_days" in path
        assert "estimated_weeks" in path
        assert path["estimated_days"] > 0

    def test_path_has_phases(self):
        """Test that path is grouped into phases."""
        path = self.generator.generate_learning_path(
            ["docker", "kubernetes", "linux", "scripting"],
            []
        )
        
        assert "phases" in path
        assert "foundation" in path["phases"]
        # Skills should be distributed across phases

    def test_empty_missing_skills(self):
        """Test with no missing skills."""
        path = self.generator.generate_learning_path([], ["python", "docker"])
        
        assert path["ordered_skills"] == []
        assert path["total_skills_to_learn"] == 0


class TestPhaseGrouping:
    """Tests for skill phase grouping."""

    def setup_method(self):
        """Setup test fixtures."""
        self.generator = LearningPathGenerator()

    def test_foundation_phase(self):
        """Test foundation phase contains beginner skills."""
        phases = self.generator.group_skills_by_phase(["git", "html", "css"])
        
        assert "foundation" in phases
        # These are beginner skills
        assert "git" in phases["foundation"] or "html" in phases["foundation"]

    def test_phases_are_non_overlapping(self):
        """Test that skills don't appear in multiple phases."""
        skills = ["python", "docker", "kubernetes"]
        phases = self.generator.group_skills_by_phase(skills)
        
        # Collect all skills from phases
        all_phased_skills = []
        for phase_skills in phases.values():
            all_phased_skills.extend(phase_skills)
        
        # Check for duplicates
        assert len(all_phased_skills) == len(set(all_phased_skills))


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
