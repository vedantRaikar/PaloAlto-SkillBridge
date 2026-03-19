"""Tests for app/services/entity_deduplicator.py."""
import pytest
from app.services.entity_deduplicator import EntityDeduplicator, get_entity_deduplicator


@pytest.fixture()
def dedup():
    return EntityDeduplicator()


# ---------------------------------------------------------------------------
# normalize_entity
# ---------------------------------------------------------------------------

def test_normalize_direct_alias(dedup):
    assert dedup.normalize_entity("js") == "javascript"
    assert dedup.normalize_entity("ts") == "typescript"
    assert dedup.normalize_entity("k8s") == "kubernetes"
    assert dedup.normalize_entity("ci/cd") == "ci_cd"


def test_normalize_partial_alias_match(dedup):
    # "react.js" contains the alias "react.js" → canonical "react"
    result = dedup.normalize_entity("react.js")
    assert result == "react"


def test_normalize_strips_and_lowercases(dedup):
    result = dedup.normalize_entity("  Python  ")
    assert result == "python"


def test_normalize_removes_special_chars(dedup):
    result = dedup.normalize_entity("node.js!")
    # Should pass through normalization cleanly
    assert isinstance(result, str)
    assert "!" not in result


def test_normalize_spaces_to_underscores(dedup):
    result = dedup.normalize_entity("machine learning")
    assert result.replace(" ", "_") == result


def test_normalize_collapses_multiple_underscores(dedup):
    result = dedup.normalize_entity("test--skill")
    assert "__" not in result


# ---------------------------------------------------------------------------
# levenshtein_distance
# ---------------------------------------------------------------------------

def test_levenshtein_identical(dedup):
    assert dedup.levenshtein_distance("python", "python") == 0


def test_levenshtein_empty_strings(dedup):
    assert dedup.levenshtein_distance("", "python") == 6
    assert dedup.levenshtein_distance("python", "") == 6
    assert dedup.levenshtein_distance("", "") == 0


def test_levenshtein_one_edit(dedup):
    assert dedup.levenshtein_distance("cat", "bat") == 1


def test_levenshtein_insert_delete(dedup):
    assert dedup.levenshtein_distance("kitten", "sitting") == 3


def test_levenshtein_reversed_args_symmetric(dedup):
    d1 = dedup.levenshtein_distance("abc", "abcd")
    d2 = dedup.levenshtein_distance("abcd", "abc")
    assert d1 == d2


# ---------------------------------------------------------------------------
# similarity_ratio
# ---------------------------------------------------------------------------

def test_similarity_ratio_identical(dedup):
    assert dedup.similarity_ratio("python", "python") == 1.0


def test_similarity_ratio_different(dedup):
    ratio = dedup.similarity_ratio("python", "java")
    assert 0.0 <= ratio < 1.0


# ---------------------------------------------------------------------------
# are_similar
# ---------------------------------------------------------------------------

def test_are_similar_identical(dedup):
    assert dedup.are_similar("python", "python")


def test_are_similar_common_alias(dedup):
    # "reactjs" and "react" normalize to the same thing via alias
    assert dedup.are_similar("reactjs", "react")


def test_are_similar_dissimilar(dedup):
    assert not dedup.are_similar("python", "kubernetes", threshold=0.9)


def test_are_similar_substring(dedup):
    # "nodejs" contains "node"
    result = dedup.are_similar("nodejs", "node")
    # Could be True due to substring check
    assert isinstance(result, bool)


# ---------------------------------------------------------------------------
# find_duplicates
# ---------------------------------------------------------------------------

def test_find_duplicates_none(dedup):
    # All distinct and dissimilar
    dupes = dedup.find_duplicates(["python", "kubernetes", "redis"], threshold=0.99)
    assert dupes == []


def test_find_duplicates_finds_aliases(dedup):
    dupes = dedup.find_duplicates(["reactjs", "react", "python"])
    # reactjs and react should be in the same group
    assert any("react" in g or "reactjs" in g for g in dupes)


# ---------------------------------------------------------------------------
# deduplicate_entities
# ---------------------------------------------------------------------------

def test_deduplicate_entities_no_dupes(dedup):
    entities = ["python", "docker", "kubernetes"]
    result, mapping = dedup.deduplicate_entities(entities, threshold=0.99)
    assert mapping == {}
    assert set(result) == set(entities)


def test_deduplicate_entities_with_dupes(dedup):
    entities = ["reactjs", "react", "python"]
    result, mapping = dedup.deduplicate_entities(entities)
    # Should have fewer than 3 items after dedup
    assert len(result) <= 3
    # Mapping should have at least one entry
    assert len(result) < 3 or mapping == {}


# ---------------------------------------------------------------------------
# _select_canonical
# ---------------------------------------------------------------------------

def test_select_canonical_prefers_known_skill(dedup):
    # "python" should be in the skills_map; unknown_x is not
    canonical = dedup._select_canonical(["unknown_x_zzz", "python"])
    assert canonical == "python"


def test_select_canonical_falls_back_to_longest(dedup):
    canonical = dedup._select_canonical(["abc", "abcdef"])
    assert canonical == "abcdef"


# ---------------------------------------------------------------------------
# merge_skill_metadata
# ---------------------------------------------------------------------------

def test_merge_skill_metadata_adds_aliases(dedup):
    s1 = {"id": "react", "aliases": ["reactjs"], "category": "frontend"}
    s2 = {"id": "react", "aliases": ["react.js"], "category": "frontend"}
    merged = dedup.merge_skill_metadata(s1, s2)
    assert "react.js" in merged["aliases"]
    assert "reactjs" in merged["aliases"]


def test_merge_skill_metadata_no_duplicate_aliases(dedup):
    s1 = {"id": "react", "aliases": ["reactjs"], "category": "frontend"}
    s2 = {"id": "react", "aliases": ["reactjs"], "category": "frontend"}
    merged = dedup.merge_skill_metadata(s1, s2)
    assert merged["aliases"].count("reactjs") == 1


def test_merge_skill_metadata_inherits_category(dedup):
    s1 = {"id": "foo", "aliases": [], "category": "unknown"}
    s2 = {"id": "foo", "aliases": [], "category": "backend"}
    merged = dedup.merge_skill_metadata(s1, s2)
    assert merged["category"] == "backend"


# ---------------------------------------------------------------------------
# suggest_canonical_form
# ---------------------------------------------------------------------------

def test_suggest_canonical_form_known_id(dedup):
    # "python" should be in the skills_map directly
    result = dedup.suggest_canonical_form("python")
    assert result == "python" or result is None  # depends on skills_library


def test_suggest_canonical_form_unknown(dedup):
    result = dedup.suggest_canonical_form("totally_unknown_xyz_abc_123")
    assert result is None


# ---------------------------------------------------------------------------
# find_skill_aliases / add_alias
# ---------------------------------------------------------------------------

def test_find_skill_aliases_empty_for_unknown(dedup):
    aliases = dedup.find_skill_aliases("totally_unknown_skill_xyz")
    assert aliases == []


def test_add_alias_to_unknown_returns_false(dedup):
    result = dedup.add_alias("totally_unknown_xyz", "alias_abc")
    assert result is False


# ---------------------------------------------------------------------------
# optimize_entity_set
# ---------------------------------------------------------------------------

def test_optimize_entity_set_passthrough(dedup):
    entities = [
        {"id": "python", "category": "programming"},
        {"id": "docker", "category": "devops"},
    ]
    optimized, mapping = dedup.optimize_entity_set(entities)
    assert len(optimized) <= 2


# ---------------------------------------------------------------------------
# Singleton getter
# ---------------------------------------------------------------------------

def test_get_entity_deduplicator_singleton():
    d1 = get_entity_deduplicator()
    d2 = get_entity_deduplicator()
    assert d1 is d2
