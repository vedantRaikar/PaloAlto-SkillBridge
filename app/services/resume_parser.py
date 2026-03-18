import re
from pathlib import Path
from typing import Optional, Dict, List
from app.services.extraction_pipeline import ExtractionPipeline
from app.services.resolver import SkillResolver

class ResumeParser:
    def __init__(self):
        self.resolver = SkillResolver()
        self.extraction_pipeline = ExtractionPipeline()

    def extract_text_from_pdf(self, file_path: str) -> str:
        try:
            from PyPDF2 import PdfReader
            reader = PdfReader(file_path)
            text = ""
            for page in reader.pages:
                text += page.extract_text() or ""
            return text
        except Exception as e:
            return f"Error reading PDF: {str(e)}"

    def extract_text_from_docx(self, file_path: str) -> str:
        try:
            from docx import Document
            doc = Document(file_path)
            text = ""
            for para in doc.paragraphs:
                text += para.text + "\n"
            return text
        except Exception as e:
            return f"Error reading DOCX: {str(e)}"

    def extract_text(self, file_path: str) -> str:
        path = Path(file_path)
        extension = path.suffix.lower()
        
        if extension == '.pdf':
            return self.extract_text_from_pdf(file_path)
        elif extension in ['.docx', '.doc']:
            return self.extract_text_from_docx(file_path)
        else:
            return f"Unsupported file format: {extension}"

    def extract_sections(self, text: str) -> Dict[str, str]:
        sections = {
            "header": "",
            "summary": "",
            "experience": "",
            "education": "",
            "skills": "",
            "other": ""
        }
        
        lines = text.split('\n')
        current_section = "other"
        section_keywords = {
            "summary": ["summary", "objective", "profile", "about"],
            "experience": ["experience", "employment", "work history", "professional experience"],
            "education": ["education", "academic", "degree", "university", "college"],
            "skills": ["skills", "technologies", "technical skills", "competencies"],
        }
        
        header_pattern = r'^[A-Z][A-Z\s]+$|Contact|Phone|Email|LinkedIn'
        
        for line in lines:
            line_clean = line.strip()
            if not line_clean:
                continue
            
            if len(line_clean) < 100 and re.match(header_pattern, line_clean):
                current_section = "header"
            else:
                for section, keywords in section_keywords.items():
                    if any(kw.lower() in line_clean.lower() for kw in keywords):
                        current_section = section
                        break
                
                sections[current_section] += line_clean + "\n"
        
        for key in sections:
            sections[key] = sections[key].strip()
        
        return sections

    def extract_skills_from_text(self, text: str) -> List[str]:
        import json
        
        result = self.extraction_pipeline.extract_sync("Resume Skills", text)
        extraction = result.get("extraction_result", {})
        
        if extraction and hasattr(extraction, 'nodes'):
            skills = [n.id for n in extraction.nodes if n.type == "skill"]
            return skills
        
        if isinstance(extraction, dict):
            skills = [n.get('id') for n in extraction.get('nodes', []) if n.get('type') == 'skill']
            return skills
        
        return []

    def extract_name(self, text: str) -> Optional[str]:
        lines = text.split('\n')
        for line in lines[:5]:
            line_clean = line.strip()
            if line_clean and len(line_clean) < 50 and len(line_clean.split()) <= 4:
                if not any(char.isdigit() for char in line_clean):
                    if re.match(r'^[A-Z][a-z]+(\s+[A-Z][a-z]+)+$', line_clean):
                        return line_clean
        return None

    def extract_contact(self, text: str) -> Dict[str, str]:
        contact = {}
        
        email_pattern = r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b'
        emails = re.findall(email_pattern, text)
        if emails:
            contact["email"] = emails[0]
        
        phone_pattern = r'(\+?1?\s*[-.]?\s*)?(\(?\d{3}\)?[-.\s]?)?\d{3}[-.\s]?\d{4}'
        phones = re.findall(phone_pattern, text)
        if phones:
            contact["phone"] = ''.join(filter(str.isdigit, phones[0][0] + phones[0][1] + phones[0][2]))
        
        linkedin_pattern = r'linkedin\.com/in/([a-zA-Z0-9-]+)'
        linkedin = re.findall(linkedin_pattern, text, re.IGNORECASE)
        if linkedin:
            contact["linkedin"] = linkedin[0]
        
        github_pattern = r'github\.com/([a-zA-Z0-9-]+)'
        github = re.findall(github_pattern, text, re.IGNORECASE)
        if github:
            contact["github"] = github[0]
        
        return contact

    def parse_resume(self, file_path: str) -> Dict:
        text = self.extract_text(file_path)
        
        if text.startswith("Error"):
            return {
                "success": False,
                "error": text
            }
        
        sections = self.extract_sections(text)
        raw_skills = self.extract_skills_from_text(sections.get("skills", "") + " " + sections.get("experience", ""))
        resolved_skills = list(set(self.resolver.resolve_all_skills(raw_skills).values()))
        resolved_skills = [s for s in resolved_skills if s]
        
        return {
            "success": True,
            "name": self.extract_name(text),
            "contact": self.extract_contact(text),
            "sections": sections,
            "raw_skills": raw_skills,
            "resolved_skills": resolved_skills,
            "summary": sections.get("summary", "")[:500],
            "experience_years": self._estimate_years(sections.get("experience", ""))
        }

    def _estimate_years(self, experience_text: str) -> Optional[int]:
        year_pattern = r'(19|20)\d{2}'
        years = re.findall(year_pattern, experience_text)
        if len(years) >= 2:
            years_int = [int(y) for y in years]
            return max(years_int) - min(years_int)
        return None

    def parse_resume_bytes(self, content: bytes, filename: str, temp_dir: str = "/tmp") -> Dict:
        import tempfile
        import os
        
        suffix = Path(filename).suffix.lower()
        with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp:
            tmp.write(content)
            tmp_path = tmp.name
        
        try:
            return self.parse_resume(tmp_path)
        finally:
            if os.path.exists(tmp_path):
                os.unlink(tmp_path)
