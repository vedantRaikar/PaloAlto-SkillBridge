import re
from typing import Optional, Dict, Any
from urllib.parse import urlparse
from app.services.linkedin_scraper import LinkedInScraper

class JobIngestionService:
    def __init__(self):
        self.linkedin_scraper = LinkedInScraper()

    def is_linkedin_url(self, text: str) -> bool:
        text = text.strip()
        linkedin_patterns = [
            r'https?://(?:www\.)?linkedin\.com/jobs/',
            r'https?://(?:www\.)?linkedin\.com/job/',
        ]
        return any(re.match(pattern, text, re.IGNORECASE) for pattern in linkedin_patterns)

    def is_url(self, text: str) -> bool:
        url_pattern = re.compile(
            r'^https?://'
            r'(?:(?:[A-Z0-9](?:[A-Z0-9-]{0,61}[A-Z0-9])?\.)+[A-Z]{2,6}\.?|'
            r'localhost|'
            r'\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3})'
            r'(?::\d+)?'
            r'(?:/?|[/?]\S+)$', re.IGNORECASE)
        return bool(url_pattern.match(text.strip()))

    def detect_input_type(self, input_text: str) -> str:
        input_text = input_text.strip()
        if self.is_linkedin_url(input_text):
            return "linkedin_url"
        if self.is_url(input_text):
            return "generic_url"
        return "raw_text"

    async def ingest(self, input_data: str | Dict[str, Any]) -> Dict[str, Any]:
        if isinstance(input_data, dict):
            input_text = input_data.get("url") or input_data.get("text", "")
        else:
            input_text = input_data

        input_text = input_text.strip()
        input_type = self.detect_input_type(input_text)

        if input_type == "linkedin_url":
            return await self._ingest_linkedin(input_text)
        elif input_type == "generic_url":
            return {
                "success": False,
                "error": "Unsupported URL type. Please use a LinkedIn job URL or paste the job description directly.",
                "input_type": input_type
            }
        else:
            return self._ingest_raw_text(input_text)

    async def _ingest_linkedin(self, url: str) -> Dict[str, Any]:
        try:
            job_data = await self.linkedin_scraper.scrape_job(url)
            
            if job_data.get("success"):
                return {
                    "success": True,
                    "input_type": "linkedin_url",
                    "source": "linkedin",
                    "url": url,
                    "data": {
                        "title": job_data.get("title", "Unknown Title"),
                        "company": job_data.get("company", "Unknown Company"),
                        "description": job_data.get("description", ""),
                        "location": job_data.get("location", ""),
                        "experience_level": job_data.get("experience_level", ""),
                        "employment_type": job_data.get("employment_type", ""),
                        "industries": job_data.get("industries", []),
                        "skills": job_data.get("skills", []),
                        "posted_date": job_data.get("posted_date", ""),
                        "applicants": job_data.get("applicants", ""),
                    },
                    "raw_html_preview": job_data.get("raw_preview", "")[:500] if job_data.get("raw_preview") else ""
                }
            else:
                return {
                    "success": False,
                    "error": job_data.get("error", "LinkedIn uses JavaScript to render content. Simple scraping cannot extract job data."),
                    "input_type": "linkedin_url",
                    "suggestion": "Please paste the job description directly as text instead."
                }
        except Exception as e:
            return {
                "success": False,
                "error": f"LinkedIn scraping failed: {str(e)}",
                "input_type": "linkedin_url",
                "suggestion": "Please try pasting the job description directly as text instead."
            }

    def _ingest_raw_text(self, text: str) -> Dict[str, Any]:
        if len(text) < 50:
            return {
                "success": False,
                "error": "Job description too short. Please provide a more detailed description.",
                "input_type": "raw_text"
            }

        extracted = self._extract_structured_fields(text)

        return {
            "success": True,
            "input_type": "raw_text",
            "source": "manual",
            "data": {
                "title": extracted.get("title", "Job Position"),
                "company": extracted.get("company", "Company"),
                "description": text,
                "location": extracted.get("location", ""),
                "experience_level": extracted.get("experience_level", ""),
                "employment_type": extracted.get("employment_type", ""),
                "industries": extracted.get("industries", []),
                "skills": [],
            }
        }

    def _extract_structured_fields(self, text: str) -> Dict[str, Any]:
        result = {
            "title": "",
            "company": "",
            "location": "",
            "experience_level": "",
            "employment_type": "",
            "industries": []
        }

        lines = text.split('\n')
        if lines:
            first_line = lines[0].strip()
            if len(first_line) < 100:
                result["title"] = first_line
            else:
                words = first_line.split()
                result["title"] = ' '.join(words[:10])

        patterns = {
            "company": [
                r'(?:at|@|with|Company:?)\s+([A-Z][A-Za-z0-9\s&]+?)(?:\s*[-|]|$)',
                r'Company:\s*([^\n]+)',
                r'\*\*Company:\*\*\s*([^\n]+)',
            ],
            "location": [
                r'(?:Location|Remote|Hybrid):\s*([^\n]+)',
                r'in\s+([A-Z][a-z]+(?:\s*,\s*[A-Z]{2})?)',
            ],
            "experience_level": [
                r'(?:Experience|Level):\s*([^\n]+)',
                r'((?:Senior|Sr\.|Junior|Jr\.|Mid|Lead|Principal|Entry).*?(?:level|engineer|developer|role))',
            ],
            "employment_type": [
                r'(?:Employment|Type|Job)\s*(?:Type)?:\s*([^\n]+)',
                r'((?:Full-time|Part-time|Contract|Freelance))',
            ]
        }

        text_lower = text.lower()

        for field, field_patterns in patterns.items():
            for pattern in field_patterns:
                match = re.search(pattern, text, re.IGNORECASE)
                if match:
                    try:
                        result[field] = match.group(1).strip()
                        break
                    except IndexError:
                        continue

        return result

    def validate_job_data(self, job_data: Dict[str, Any]) -> Dict[str, Any]:
        issues = []
        
        if not job_data.get("title"):
            issues.append("Missing job title")
        
        if not job_data.get("description"):
            issues.append("Missing job description")
        elif len(job_data["description"]) < 100:
            issues.append("Job description is too short (minimum 100 characters)")

        return {
            "valid": len(issues) == 0,
            "issues": issues
        }

    def normalize_job_for_extraction(self, job_data: Dict[str, Any]) -> Dict[str, str]:
        title = job_data.get("title", "")
        description = job_data.get("description", "")
        
        company = job_data.get("company", "")
        if company:
            description = f"{title} at {company}\n\n{description}"

        location = job_data.get("location", "")
        if location:
            description = f"{description}\n\nLocation: {location}"

        experience = job_data.get("experience_level", "")
        if experience:
            description = f"{description}\n\nExperience Level: {experience}"

        employment_type = job_data.get("employment_type", "")
        if employment_type:
            description = f"{description}\n\nEmployment Type: {employment_type}"

        return {
            "title": title,
            "description": description
        }


_job_ingestion_service = None

def get_job_ingestion_service() -> JobIngestionService:
    global _job_ingestion_service
    if _job_ingestion_service is None:
        _job_ingestion_service = JobIngestionService()
    return _job_ingestion_service
