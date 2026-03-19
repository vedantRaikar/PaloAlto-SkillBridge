import re
import json
import asyncio
from typing import Dict, Any, Optional, List
from urllib.parse import urlparse, parse_qs
from datetime import datetime

import httpx


class LinkedInScraper:
    BASE_URL = "https://www.linkedin.com"
    USER_AGENT = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    
    HEADERS = {
        "User-Agent": USER_AGENT,
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
        "Accept-Language": "en-US,en;q=0.5",
        "Accept-Encoding": "gzip, deflate, br",
        "Connection": "keep-alive",
        "Upgrade-Insecure-Requests": "1",
        "Cache-Control": "max-age=0",
    }

    def __init__(self, timeout: int = 30):
        self.timeout = timeout
        self._session: Optional[httpx.AsyncClient] = None

    async def _get_session(self) -> httpx.AsyncClient:
        if self._session is None or self._session.is_closed:
            self._session = httpx.AsyncClient(
                timeout=self.timeout,
                headers=self.HEADERS,
                follow_redirects=True
            )
        return self._session

    def extract_job_id(self, url: str) -> Optional[str]:
        parsed = urlparse(url)
        
        if "linkedin.com/jobs/view" in url:
            match = re.search(r'/jobs/(\d+)', parsed.path)
            if match:
                return match.group(1)
        
        if "linkedin.com/jobs/posting" in url:
            match = re.search(r'/jobs/(\d+)', parsed.path)
            if match:
                return match.group(1)
        
        query_params = parse_qs(parsed.query)
        if "currentJobId" in query_params:
            return query_params["currentJobId"][0]
        if "jobId" in query_params:
            return query_params["jobId"][0]
        
        return None

    async def scrape_job(self, url: str) -> Dict[str, Any]:
        job_id = self.extract_job_id(url)
        
        if not job_id:
            return {
                "success": False,
                "error": "Could not extract job ID from URL"
            }

        methods_tried = []
        
        result = await self._try_method1_share_api(url, job_id)
        if result.get("success"):
            return result
        methods_tried.append("share_api")
        
        result = await self._try_method2_mobile(url, job_id)
        if result.get("success"):
            return result
        methods_tried.append("mobile")
        
        result = await self._try_method3_og_tags(url, job_id)
        if result.get("success"):
            return result
        methods_tried.append("og_tags")
        
        url_info = self._extract_from_url(url)
        if url_info.get("title"):
            return {
                "success": True,
                "job_id": job_id,
                "url": url,
                "title": url_info.get("title", "LinkedIn Job"),
                "company": url_info.get("company", ""),
                "description": url_info.get("description", ""),
                "location": url_info.get("location", ""),
                "source": "url_parsing",
                "note": "Limited info extracted from URL. Please paste full job description for better results."
            }
        
        return {
            "success": False,
            "error": "LinkedIn job pages require JavaScript rendering which is not supported.",
            "job_id": job_id,
            "url": url,
            "methods_tried": methods_tried,
            "suggestion": "Please paste the job description directly as text for best results."
        }

    async def _try_method1_share_api(self, url: str, job_id: str) -> Dict[str, Any]:
        try:
            share_url = f"https://www.linkedin.com/sharing/share-v2/?url={urlparse(url).path}"
            
            session = await self._get_session()
            response = await session.get(share_url)
            
            if response.status_code == 200:
                try:
                    data = response.json()
                    if data.get("data"):
                        job_data = data["data"]
                        return {
                            "success": True,
                            "job_id": job_id,
                            "url": url,
                            "title": job_data.get("title", ""),
                            "company": job_data.get("companyName", ""),
                            "description": job_data.get("description", ""),
                            "location": job_data.get("location", ""),
                        }
                except json.JSONDecodeError:
                    pass
        except Exception as e:
            print(f"Share API method failed: {e}")
        
        return {"success": False}

    async def _try_method2_mobile(self, url: str, job_id: str) -> Dict[str, Any]:
        try:
            mobile_url = url.replace("www.linkedin.com", "m.linkedin.com")
            
            session = await self._get_session()
            response = await session.get(mobile_url)
            html = response.text
            
            title = self._extract_from_meta(html, "og:title") or self._extract_title(html)
            company = self._extract_from_meta(html, "og:description")
            description = self._extract_description_from_mobile(html)
            
            if title and len(description) > 100:
                return {
                    "success": True,
                    "job_id": job_id,
                    "url": url,
                    "title": title,
                    "company": company or "",
                    "description": description,
                    "location": self._extract_location_from_mobile(html),
                }
        except Exception as e:
            print(f"Mobile method failed: {e}")
        
        return {"success": False}

    async def _try_method3_og_tags(self, url: str, job_id: str) -> Dict[str, Any]:
        try:
            session = await self._get_session()
            response = await session.get(url)
            html = response.text
            
            title = self._extract_from_meta(html, "og:title") or self._extract_title(html)
            description = self._extract_from_meta(html, "og:description") or ""
            site_name = self._extract_from_meta(html, "og:site_name")
            
            job_description = self._extract_description(html)
            
            if title:
                return {
                    "success": True,
                    "job_id": job_id,
                    "url": url,
                    "title": title,
                    "company": site_name or "",
                    "description": job_description or description,
                    "location": self._extract_location(html),
                }
        except Exception as e:
            print(f"OG tags method failed: {e}")
        
        return {"success": False}

    def _extract_from_meta(self, html: str, property: str) -> Optional[str]:
        patterns = [
            rf'<meta[^>]*(?:property|name)="{property}"[^>]*content="([^"]+)"',
            rf'<meta[^>]*content="([^"]+)"[^>]*(?:property|name)="{property}"',
        ]
        
        for pattern in patterns:
            match = re.search(pattern, html, re.IGNORECASE | re.DOTALL)
            if match:
                return match.group(1).strip()
        
        return None

    def _extract_title(self, html: str) -> str:
        patterns = [
            r'<h1[^>]*class="[^"]*top-card-layout[^"]*"[^>]*>([^<]+)</h1>',
            r'<h1[^>]*>([^<]+)</h1>',
            r'<title>([^<]+)</title>',
            r'"title"\s*:\s*"([^"]+)"',
        ]
        
        for pattern in patterns:
            match = re.search(pattern, html, re.IGNORECASE | re.DOTALL)
            if match:
                title = match.group(1).strip()
                title = re.sub(r'\s*[-|]\s*LinkedIn$', '', title)
                if title:
                    return title
        
        return ""

    def _extract_description_from_mobile(self, html: str) -> str:
        patterns = [
            r'<p[^>]*class="[^"]*description[^"]*"[^>]*>(.*?)</p>',
            r'"description"\s*:\s*"([^"]+)"',
            r'<div[^>]*class="[^"]*content[^"]*"[^>]*>(.*?)</div>',
        ]
        
        for pattern in patterns:
            match = re.search(pattern, html, re.IGNORECASE | re.DOTALL)
            if match:
                desc = self._clean_html(match.group(1))
                if len(desc) > 50:
                    return desc
        
        return ""

    def _extract_location_from_mobile(self, html: str) -> str:
        patterns = [
            r'"location"\s*:\s*"([^"]+)"',
            r'<span[^>]*class="[^"]*location[^"]*"[^>]*>([^<]+)</span>',
        ]
        
        for pattern in patterns:
            match = re.search(pattern, html, re.IGNORECASE)
            if match:
                return match.group(1).strip()
        
        return ""

    def _extract_from_url(self, url: str) -> Dict[str, str]:
        parsed = urlparse(url)
        path = parsed.path
        
        parts = path.strip('/').split('/')
        
        info = {"title": "", "company": "", "description": "", "location": ""}
        
        if "jobs" in parts:
            idx = parts.index("jobs")
            if idx + 2 < len(parts):
                company_slug = parts[idx + 1]
                title_slug = parts[idx + 2]
                
                company = company_slug.replace('-', ' ').title()
                title = title_slug.replace('-', ' ').title()
                
                info["company"] = company
                info["title"] = f"{title} at {company}"
        
        return info

    def _extract_description(self, html: str) -> str:
        patterns = [
            r'<div[^>]*class="[^"]*description[^"]*"[^>]*>(.*?)</div>',
            r'<div[^>]*id="job-details[^"]*"[^>]*>(.*?)</div>',
            r'"description"\s*:\s*"([^"]+)"',
            r'job-description[^>]*>(.*?)</div>',
        ]
        
        for pattern in patterns:
            match = re.search(pattern, html, re.IGNORECASE | re.DOTALL)
            if match:
                desc = self._clean_html(match.group(1))
                if len(desc) > 100:
                    return desc
        
        return ""

    def _extract_location(self, html: str) -> str:
        patterns = [
            r'bullet-feature[^>]*>.*?<span[^>]*>([^<]*location[^<]*)</span>',
            r'"jobLocation"\s*:\s*\{[^}]*"addressLocality"\s*:\s*"([^"]+)"',
            r'topcard__link--mock[^>]*>\s*([^<]+\s*[^<]+)</span>',
            r'"location"\s*:\s*"([^"]+)"',
        ]
        
        for pattern in patterns:
            match = re.search(pattern, html, re.IGNORECASE | re.DOTALL)
            if match:
                location = match.group(1).strip()
                if location and "location" not in location.lower():
                    return location
        
        return ""

    def _clean_html(self, text: str) -> str:
        text = re.sub(r'<script[^>]*>.*?</script>', '', text, flags=re.DOTALL | re.IGNORECASE)
        text = re.sub(r'<style[^>]*>.*?</style>', '', text, flags=re.DOTALL | re.IGNORECASE)
        text = re.sub(r'<[^>]+>', ' ', text)
        text = re.sub(r'\s+', ' ', text)
        text = re.sub(r'&nbsp;', ' ', text)
        text = re.sub(r'&amp;', '&', text)
        text = re.sub(r'&lt;', '<', text)
        text = re.sub(r'&gt;', '>', text)
        text = re.sub(r'&quot;', '"', text)
        text = text.strip()
        return text

    async def close(self):
        if self._session and not self._session.is_closed:
            await self._session.aclose()

    def __del__(self):
        if self._session and not self._session.is_closed:
            try:
                asyncio.get_event_loop()
            except RuntimeError:
                pass


_linkedin_scraper = None

def get_linkedin_scraper() -> LinkedInScraper:
    global _linkedin_scraper
    if _linkedin_scraper is None:
        _linkedin_scraper = LinkedInScraper()
    return _linkedin_scraper
