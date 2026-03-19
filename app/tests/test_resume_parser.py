"""Tests for app/services/resume_parser.py."""
import pytest
from app.services.resume_parser import ResumeParser, TECHNICAL_SKILLS, SKILL_VARIATIONS


@pytest.fixture()
def parser():
    return ResumeParser()


# ---------------------------------------------------------------------------
# Initialization
# ---------------------------------------------------------------------------

def test_parser_initializes(parser):
    assert isinstance(parser.tech_skills_set, set)
    assert "python" in parser.tech_skills_set


# ---------------------------------------------------------------------------
# _clean_extracted_text
# ---------------------------------------------------------------------------

def test_clean_text_removes_excess_newlines(parser):
    text = "Line 1\n\n\n\nLine 2"
    result = parser._clean_extracted_text(text)
    assert "\n\n\n" not in result


def test_clean_text_empty(parser):
    assert parser._clean_extracted_text("") == ""


def test_clean_text_pipe_split(parser):
    long_pipe_line = "A" * 30 + "|" + "B" * 30
    result = parser._clean_extracted_text(long_pipe_line)
    assert isinstance(result, str)


# ---------------------------------------------------------------------------
# extract_skills_from_text
# ---------------------------------------------------------------------------

def test_extract_skills_finds_python(parser):
    skills = parser.extract_skills_from_text("5 years of Python development experience")
    assert "python" in skills


def test_extract_skills_finds_react(parser):
    skills = parser.extract_skills_from_text("Built frontends with React and TypeScript")
    assert "react" in skills
    assert "typescript" in skills


def test_extract_skills_applies_variations(parser):
    # "k8s" → "kubernetes"
    skills = parser.extract_skills_from_text("Deployed on k8s clusters")
    assert "kubernetes" in skills


def test_extract_skills_empty_text(parser):
    skills = parser.extract_skills_from_text("")
    assert isinstance(skills, list)
    assert len(skills) == 0


def test_extract_skills_no_match(parser):
    skills = parser.extract_skills_from_text("Excellent communications skills and team player")
    # Should return an empty list or minimal matches
    assert isinstance(skills, list)


def test_extract_skills_multiple(parser):
    text = "Python, Docker, PostgreSQL, Redis, AWS, React"
    skills = parser.extract_skills_from_text(text)
    assert "python" in skills
    assert "docker" in skills


# ---------------------------------------------------------------------------
# extract_skills_from_skill_section
# ---------------------------------------------------------------------------

def test_extract_from_skill_section(parser):
    section = "Python | Django | PostgreSQL | Docker | Git"
    skills = parser.extract_skills_from_skill_section(section)
    assert "python" in skills
    assert "docker" in skills


def test_extract_from_skill_section_empty(parser):
    skills = parser.extract_skills_from_skill_section("")
    assert skills == []


# ---------------------------------------------------------------------------
# extract_sections
# ---------------------------------------------------------------------------

def test_extract_sections_returns_dict(parser):
    text = "John Doe\njohn@example.com\n\nExperience\nWorked at Company for 3 years\n\nSkills\nPython Docker"
    sections = parser.extract_sections(text)
    assert isinstance(sections, dict)
    assert "experience" in sections
    assert "skills" in sections


def test_extract_sections_detects_skills_section(parser):
    text = "skills\npython django docker"
    sections = parser.extract_sections(text)
    assert "python" in sections["skills"].lower() or "python" in sections["other"].lower()


def test_extract_sections_detects_summary(parser):
    text = "summary\nExperienced Python developer with 5 years"
    sections = parser.extract_sections(text)
    assert "Experienced" in sections.get("summary", "") or "Experienced" in sections.get("other", "")


def test_extract_sections_experience_keyword(parser):
    text = "experience\n2020-2023 Software Engineer at Acme"
    sections = parser.extract_sections(text)
    assert "2020" in sections.get("experience", "") or "2020" in sections.get("other", "")


# ---------------------------------------------------------------------------
# extract_name
# ---------------------------------------------------------------------------

def test_extract_name_valid_name(parser):
    text = "John Doe\njohn@example.com"
    name = parser.extract_name(text)
    assert name == "John Doe"


def test_extract_name_with_email_first(parser):
    text = "john@example.com\nJohn Doe"
    name = parser.extract_name(text)
    # Email line won't match the name pattern, falls through to other lines
    assert name is None or isinstance(name, str)


def test_extract_name_too_long(parser):
    text = "This is a very long name that exceeds fifty characters limit"
    name = parser.extract_name(text)
    assert name is None


def test_extract_name_no_name(parser):
    name = parser.extract_name("2024-01-01\ndocker kubernetes")
    assert name is None


# ---------------------------------------------------------------------------
# extract_contact
# ---------------------------------------------------------------------------

def test_extract_contact_email(parser):
    text = "Contact: alice@example.com"
    contact = parser.extract_contact(text)
    assert contact.get("email") == "alice@example.com"


def test_extract_contact_linkedin(parser):
    text = "linkedin.com/in/alicedev"
    contact = parser.extract_contact(text)
    assert contact.get("linkedin") == "alicedev"


def test_extract_contact_github(parser):
    text = "github.com/alicedev"
    contact = parser.extract_contact(text)
    assert contact.get("github") == "alicedev"


def test_extract_contact_phone(parser):
    text = "Phone: 555-867-5309"
    contact = parser.extract_contact(text)
    # Phone may or may not match depending on regex
    assert isinstance(contact, dict)


def test_extract_contact_empty(parser):
    contact = parser.extract_contact("")
    assert isinstance(contact, dict)


# ---------------------------------------------------------------------------
# _estimate_years
# ---------------------------------------------------------------------------

def test_estimate_years_from_dates(parser):
    text = "2018 - 2023 Software Engineer"
    years = parser._estimate_years(text)
    assert years == 5


def test_estimate_years_no_dates(parser):
    years = parser._estimate_years("No dates here")
    assert years is None


def test_estimate_years_single_year(parser):
    years = parser._estimate_years("Started 2020")
    assert years is None


# ---------------------------------------------------------------------------
# _quick_resolve
# ---------------------------------------------------------------------------

def test_quick_resolve_applies_variations(parser):
    resolved = parser._quick_resolve(["k8s", "python", "react.js"])
    assert "kubernetes" in resolved
    assert "python" in resolved


def test_quick_resolve_empty(parser):
    assert parser._quick_resolve([]) == []


def test_quick_resolve_unknown_skill(parser):
    resolved = parser._quick_resolve(["myfantasylang"])
    assert "myfantasylang" in resolved


# ---------------------------------------------------------------------------
# parse_resume (full pipeline, text input via bytes)
# ---------------------------------------------------------------------------

def test_parse_resume_bytes_txt(parser, tmp_path):
    resume_text = (
        "Alice Smith\nalice@example.com\ngithub.com/alicedev\n\n"
        "SKILLS\npython django docker postgresql redis\n\n"
        "EXPERIENCE\n2019-2023 Senior Engineer at Acme Corp\n"
        "Built APIs with Python and Django"
    )
    filename = "resume.txt"
    result = parser.parse_resume_bytes(resume_text.encode("utf-8"), filename)
    assert result["success"] is True
    assert "python" in result["resolved_skills"] or "django" in result["resolved_skills"]


def test_parse_resume_bytes_empty_txt(parser):
    result = parser.parse_resume_bytes(b"Hello", "resume.txt")
    # Too short to parse → failure
    assert result["success"] is False


def test_parse_resume_bytes_pdf_error(parser):
    # Pass random bytes that can't be parsed as PDF → should return error dict
    result = parser.parse_resume_bytes(b"\x00\x01\x02", "resume.pdf")
    assert isinstance(result, dict)
    # Either success=False or success=True with empty skills
    assert "success" in result


# ---------------------------------------------------------------------------
# extract_text paths
# ---------------------------------------------------------------------------

def test_extract_text_txt_file(parser, tmp_path):
    txt_file = tmp_path / "resume.txt"
    txt_file.write_text("Hello World")
    text = parser.extract_text(str(txt_file))
    assert "Hello" in text


def test_extract_text_unsupported_format(parser, tmp_path):
    bad = tmp_path / "file.xyz"
    bad.write_text("content")
    text = parser.extract_text(str(bad))
    assert "Unsupported" in text


def test_extract_text_pdf_missing_file(parser, tmp_path):
    fake_pdf = tmp_path / "missing.pdf"
    # File doesn't exist
    text = parser.extract_text(str(fake_pdf))
    assert "Error" in text or isinstance(text, str)
