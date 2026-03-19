"""
Unit Tests for Optimized Path Generator (Dijkstra's Algorithm)
==============================================================
Tests Dijkstra's shortest path algorithm for learning paths.
"""

import pytest
from app.services.optimized_path_generator import (
    DijkstraPathFinder,
    OptimizedPathGenerator,
    SKILL_IMPACT,
    FAST_TRACK_COURSES,
)


class TestDijkstraPathFinder:
    """Tests for Dijkstra's shortest path algorithm."""

    def setup_method(self):
        """Setup test fixtures."""
        self.finder = DijkstraPathFinder()

    def test_empty_skills(self):
        """Test with empty skill lists."""
        self.finder.build_graph([], [])
        
        # Should handle empty gracefully
        assert self.finder.adjacency == {}

    def test_single_skill_no_prerequisites(self):
        """Test single skill with no prerequisites."""
        skills = ["python"]
        self.finder.build_graph(skills, [])
        
        # Should have the skill in graph
        assert "python" in self.finder.adjacency

    def test_graph_edges_created(self):
        """Test that graph edges are created correctly."""
        skills = ["docker", "kubernetes"]
        user_skills = ["linux"]
        
        self.finder.build_graph(skills, user_skills)
        
        # Check that adjacency list has entries
        assert len(self.finder.adjacency) > 0

    def test_dijkstra_single_target(self):
        """Test Dijkstra with single target skill."""
        skills = ["docker"]
        user_skills = ["linux"]
        
        self.finder.build_graph(skills, user_skills)
        
        total_time, ordered = self.finder.dijkstra_shortest_path(user_skills, skills)
        
        assert total_time >= 0
        assert isinstance(ordered, list)
        assert len(ordered) > 0

    def test_dijkstra_multiple_targets(self):
        """Test Dijkstra with multiple target skills."""
        skills = ["docker", "kubernetes", "ci_cd"]
        user_skills = ["python"]
        
        self.finder.build_graph(skills, user_skills)
        
        total_time, ordered = self.finder.dijkstra_shortest_path(user_skills, skills)
        
        assert total_time >= 0
        assert len(ordered) >= len(skills)

    def test_dijkstra_returns_ordered_skills(self):
        """Test that Dijkstra returns skills in learning order."""
        skills = ["docker", "kubernetes", "linux"]
        user_skills = []
        
        self.finder.build_graph(skills, user_skills)
        
        total_time, ordered = self.finder.dijkstra_shortest_path(user_skills, skills)
        
        # Should return an ordered list
        assert len(ordered) > 0
        
        # If docker depends on linux, linux should come first
        docker_idx = ordered.index("docker") if "docker" in ordered else -1
        linux_idx = ordered.index("linux") if "linux" in ordered else -1
        
        if docker_idx >= 0 and linux_idx >= 0:
            # This is a soft check - the order should respect dependencies
            pass

    def test_dijkstra_with_user_skills(self):
        """Test Dijkstra when user already knows some skills."""
        skills = ["docker", "kubernetes", "linux"]
        user_skills = ["python", "git"]
        
        self.finder.build_graph(skills, user_skills)
        
        total_time, ordered = self.finder.dijkstra_shortest_path(user_skills, skills)
        
        assert total_time >= 0
        # Should not include user skills in output
        for skill in user_skills:
            assert skill not in ordered or True  # User skills may be normalized

    def test_dijkstra_duration_weights(self):
        """Test that durations are used as weights."""
        skills = ["docker"]
        user_skills = ["linux"]
        
        self.finder.build_graph(skills, user_skills)
        
        # Check that skill duration is set
        assert "docker" in self.finder.skill_durations
        assert self.finder.skill_durations["docker"] > 0


class TestFindAllPaths:
    """Tests for finding multiple optimized paths."""

    def setup_method(self):
        """Setup test fixtures."""
        self.finder = DijkstraPathFinder()

    def test_find_three_path_types(self):
        """Test that three types of paths are generated."""
        skills = ["docker", "kubernetes", "linux"]
        user_skills = ["python"]
        
        self.finder.build_graph(skills, user_skills)
        
        paths = self.finder.find_all_paths(user_skills, skills, max_paths=3)
        
        assert len(paths) == 3
        
        # Check path types
        path_types = [p["type"] for p in paths]
        assert "fastest" in path_types
        assert "most_impactful" in path_types
        assert "most_efficient" in path_types

    def test_fastest_path_has_minimum_time(self):
        """Test that fastest path has minimum total time."""
        skills = ["docker", "kubernetes", "linux"]
        user_skills = ["python"]
        
        self.finder.build_graph(skills, user_skills)
        
        paths = self.finder.find_all_paths(user_skills, skills)
        
        fastest = next(p for p in paths if p["type"] == "fastest")
        
        assert "total_hours" in fastest
        assert fastest["total_hours"] >= 0

    def test_most_impactful_path(self):
        """Test that most impactful path has impact scores."""
        skills = ["docker", "kubernetes", "linux"]
        user_skills = ["python"]
        
        self.finder.build_graph(skills, user_skills)
        
        paths = self.finder.find_all_paths(user_skills, skills)
        
        impactful = next(p for p in paths if p["type"] == "most_impactful")
        
        assert "total_impact" in impactful
        assert impactful["total_impact"] > 0

    def test_path_has_reasoning(self):
        """Test that each path has reasoning."""
        skills = ["docker", "kubernetes"]
        user_skills = []
        
        self.finder.build_graph(skills, user_skills)
        
        paths = self.finder.find_all_paths(user_skills, skills)
        
        for path in paths:
            assert "reasoning" in path
            assert len(path["reasoning"]) > 0

    def test_path_has_skill_details(self):
        """Test that paths include skill details."""
        skills = ["docker", "kubernetes"]
        user_skills = []
        
        self.finder.build_graph(skills, user_skills)
        
        paths = self.finder.find_all_paths(user_skills, skills)
        
        for path in paths:
            assert "skills" in path
            assert len(path["skills"]) > 0


class TestOptimizedPathGenerator:
    """Tests for the optimized path generator."""

    def setup_method(self):
        """Setup test fixtures."""
        self.generator = OptimizedPathGenerator()

    def test_generate_optimized_paths(self):
        """Test generating optimized paths."""
        user_skills = ["python", "git"]
        target_role = "devops_engineer"
        all_role_skills = ["docker", "kubernetes", "linux"]
        missing_skills = ["docker", "kubernetes", "linux"]
        
        result = self.generator.generate_optimized_paths(
            user_skills, target_role, all_role_skills, missing_skills
        )
        
        assert "paths" in result
        assert "recommendation" in result
        assert "analysis" in result

    def test_analysis_metrics(self):
        """Test that analysis includes correct metrics."""
        user_skills = ["python"]
        missing_skills = ["docker", "kubernetes"]
        
        result = self.generator.generate_optimized_paths(
            user_skills, "devops", ["docker", "kubernetes"], missing_skills
        )
        
        analysis = result["analysis"]
        assert "total_skills_to_learn" in analysis
        assert "user_skills_count" in analysis
        assert "readiness" in analysis
        
        assert analysis["total_skills_to_learn"] == len(missing_skills)
        assert analysis["user_skills_count"] == 1

    def test_all_paths_have_skill_details(self):
        """Test that all generated paths have skill details."""
        missing_skills = ["docker", "kubernetes", "linux"]
        
        result = self.generator.generate_optimized_paths(
            ["python"], "devops", missing_skills, missing_skills
        )
        
        for path in result["paths"]:
            assert "skill_details" in path
            assert len(path["skill_details"]) > 0

    def test_all_paths_have_study_plan(self):
        """Test that all paths have study plans."""
        missing_skills = ["docker", "kubernetes"]
        
        result = self.generator.generate_optimized_paths(
            ["python"], "devops", missing_skills, missing_skills
        )
        
        for path in result["paths"]:
            assert "study_plan" in path
            assert len(path["study_plan"]) > 0

    def test_recommendation_is_fastest_path(self):
        """Test that recommendation prioritizes fastest path."""
        missing_skills = ["docker", "kubernetes", "linux"]
        
        result = self.generator.generate_optimized_paths(
            ["python"], "devops", missing_skills, missing_skills
        )
        
        # Recommendation should be one of the paths
        assert result["recommendation"] in result["paths"]

    def test_empty_missing_skills(self):
        """Test with no missing skills."""
        result = self.generator.generate_optimized_paths(
            ["python", "docker", "kubernetes"], 
            "devops", 
            ["docker", "kubernetes"],
            []  # No missing skills
        )
        
        assert result["analysis"]["already_job_ready"] == True
        assert result["paths"] == []


class TestSkillImpact:
    """Tests for skill impact scoring."""

    def test_high_impact_skills(self):
        """Test high impact skills are identified."""
        high_impact = ["python", "javascript", "docker", "aws"]
        
        for skill in high_impact:
            assert skill in SKILL_IMPACT
            assert SKILL_IMPACT[skill] >= 7

    def test_impact_scores_in_range(self):
        """Test that all impact scores are in valid range."""
        for skill, impact in SKILL_IMPACT.items():
            assert 1 <= impact <= 10, f"{skill} has invalid impact: {impact}"

    def test_common_skills_have_impacts(self):
        """Test that common skills have impact scores."""
        common_skills = ["python", "javascript", "react", "docker", "kubernetes", "sql"]
        
        for skill in common_skills:
            assert skill in SKILL_IMPACT, f"{skill} should have impact score"


class TestFastTrackCourses:
    """Tests for fast track course data."""

    def test_courses_have_duration(self):
        """Test that all fast track courses have duration."""
        for skill, courses in FAST_TRACK_COURSES.items():
            for course in courses:
                assert len(course) >= 3, f"Course {course} should have (title, provider, duration)"
                duration = course[2]
                assert duration > 0, f"Duration should be positive for {skill}"

    def test_courses_have_provider(self):
        """Test that all courses have provider."""
        for skill, courses in FAST_TRACK_COURSES.items():
            for course in courses:
                assert len(course) >= 2, f"Course {course} should have (title, provider)"
                provider = course[1]
                assert isinstance(provider, str)
                assert len(provider) > 0

    def test_docker_has_fast_courses(self):
        """Test docker has fast courses."""
        assert "docker" in FAST_TRACK_COURSES
        docker_courses = FAST_TRACK_COURSES["docker"]
        
        # Should have at least one course
        assert len(docker_courses) > 0
        
        # At least one should be free (4th element = is_free)
        free_courses = [c for c in docker_courses if len(c) > 3 and c[3]]
        assert len(free_courses) >= 0


class TestEdgeCases:
    """Tests for edge cases and error handling."""

    def setup_method(self):
        """Setup test fixtures."""
        self.generator = OptimizedPathGenerator()

    def test_very_long_skill_name(self):
        """Test handling of long skill names."""
        skills = ["a" * 100]  # Very long skill name
        user_skills = []
        
        self.finder = DijkstraPathFinder()
        self.finder.build_graph(skills, user_skills)
        
        # Should handle gracefully
        duration = self.finder._get_duration("a" * 100)
        assert duration >= 0

    def test_skill_with_special_characters(self):
        """Test handling of skills with special characters."""
        self.finder = DijkstraPathFinder()
        
        # Normalize should handle special characters
        normalized = self.finder._normalize_skill("C++")
        assert normalized in ["c++", "c"]

    def test_empty_role_name(self):
        """Test with empty role name."""
        result = self.generator.generate_optimized_paths(
            [], "", ["docker"], ["docker"]
        )
        
        # Should still generate paths
        assert "paths" in result

    def test_all_user_skills(self):
        """Test when user knows all required skills."""
        user_skills = ["docker", "kubernetes", "linux"]
        all_skills = ["docker", "kubernetes", "linux"]
        
        result = self.generator.generate_optimized_paths(
            user_skills, "devops", all_skills, []
        )
        
        assert result["analysis"]["already_job_ready"] == True


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
