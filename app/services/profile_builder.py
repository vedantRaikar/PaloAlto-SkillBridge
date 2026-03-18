import base64
import uuid
from typing import Optional, List, Dict
from app.models.profile import UserProfile, ProfileSource, GitHubProfile, ResumeProfile, ContactInfo
from app.services.github_analyzer import GitHubAnalyzer, GitHubCache
from app.services.resume_parser import ResumeParser
from app.services.resolver import SkillResolver
from app.services.graph_manager import GraphManager
from app.models.graph import Node, LinkType, NodeType

class ProfileBuilder:
    def __init__(self):
        self.github_analyzer = GitHubAnalyzer()
        self.resume_parser = ResumeParser()
        self.resolver = SkillResolver()
        self.graph_manager = GraphManager()

    async def build_from_github_async(self, username: str) -> Optional[UserProfile]:
        analysis = await self.github_analyzer.analyze_profile_async(username)
        
        if "error" in analysis:
            return None

        github_profile = GitHubProfile(
            username=username,
            name=analysis.get("name"),
            bio=analysis.get("bio"),
            followers=analysis.get("followers", 0),
            public_repos=analysis.get("public_repos", 0),
            languages=analysis.get("languages", {}),
            top_skills=analysis.get("top_skills", []),
            repos=analysis.get("repos", [])
        )

        user_id = f"github_{username}"
        contact = ContactInfo(github=username)

        return UserProfile(
            id=user_id,
            name=analysis.get("name") or username,
            sources=[ProfileSource.GITHUB],
            skills=analysis.get("top_skills", []),
            github=github_profile,
            contact=contact
        )

    def build_from_github(self, username: str) -> Optional[UserProfile]:
        analysis = self.github_analyzer.analyze_sync(username)
        
        if "error" in analysis:
            return None

        github_profile = GitHubProfile(
            username=username,
            name=analysis.get("name"),
            bio=analysis.get("bio"),
            followers=analysis.get("followers", 0),
            public_repos=analysis.get("public_repos", 0),
            languages=analysis.get("languages", {}),
            top_skills=analysis.get("top_skills", []),
            repos=analysis.get("repos", [])
        )

        user_id = f"github_{username}"
        contact = ContactInfo(github=username)

        return UserProfile(
            id=user_id,
            name=analysis.get("name") or username,
            sources=[ProfileSource.GITHUB],
            skills=analysis.get("top_skills", []),
            github=github_profile,
            contact=contact
        )

    def build_from_resume(self, file_content: bytes, filename: str, user_id: Optional[str] = None) -> UserProfile:
        resume_data = self.resume_parser.parse_resume_bytes(file_content, filename)
        
        if not resume_data.get("success"):
            raise ValueError(resume_data.get("error", "Failed to parse resume"))

        contact = ContactInfo(
            email=resume_data.get("contact", {}).get("email"),
            phone=resume_data.get("contact", {}).get("phone"),
            linkedin=resume_data.get("contact", {}).get("linkedin"),
            github=resume_data.get("contact", {}).get("github")
        )

        resume_profile = ResumeProfile(
            name=resume_data.get("name"),
            contact=contact,
            summary=resume_data.get("summary"),
            skills=resume_data.get("resolved_skills", []),
            experience_years=resume_data.get("experience_years")
        )

        final_user_id = user_id or f"resume_{uuid.uuid4().hex[:8]}"
        final_name = resume_data.get("name") or "Unknown User"

        return UserProfile(
            id=final_user_id,
            name=final_name,
            sources=[ProfileSource.RESUME],
            skills=resume_data.get("resolved_skills", []),
            resume=resume_profile,
            contact=contact,
            experience_years=resume_data.get("experience_years")
        )

    def merge_profiles(self, profiles: List[UserProfile]) -> UserProfile:
        all_skills = set()
        for profile in profiles:
            all_skills.update(profile.skills)

        github_profile = None
        resume_profile = None
        merged_contact = ContactInfo()
        merged_name = "Unknown User"
        experience_years = None

        for profile in profiles:
            if profile.name and profile.name != "Unknown User":
                merged_name = profile.name
            if profile.github:
                github_profile = profile.github
            if profile.resume:
                resume_profile = profile.resume
            if profile.contact:
                if profile.contact.email:
                    merged_contact.email = profile.contact.email
                if profile.contact.phone:
                    merged_contact.phone = profile.contact.phone
                if profile.contact.linkedin:
                    merged_contact.linkedin = profile.contact.linkedin
                if profile.contact.github:
                    merged_contact.github = profile.contact.github
            if profile.experience_years:
                experience_years = max(experience_years or 0, profile.experience_years)

        merged_sources = list(set().union(*[set(p.sources) for p in profiles]))
        merged_sources.append(ProfileSource.MERGED)

        return UserProfile(
            id=f"merged_{uuid.uuid4().hex[:8]}",
            name=merged_name,
            sources=merged_sources,
            skills=list(all_skills),
            github=github_profile,
            resume=resume_profile,
            contact=merged_contact,
            experience_years=experience_years
        )

    def save_to_graph(self, profile: UserProfile):
        user_node = Node(
            id=profile.id,
            type=NodeType.USER,
            title=profile.name,
            metadata={
                "github": profile.contact.github,
                "email": profile.contact.email,
                "experience_years": profile.experience_years,
                "sources": [s.value for s in profile.sources]
            }
        )
        
        if not self.graph_manager.get_node(profile.id):
            self.graph_manager.add_node(user_node)
        
        for skill in profile.skills:
            if self.graph_manager.get_node(skill):
                if not self.graph_manager.graph.has_edge(profile.id, skill):
                    self.graph_manager.add_edge(profile.id, skill, LinkType.HAS_SKILL)

        self.graph_manager.save_graph()

    def calculate_readiness(self, profile: UserProfile, target_roles: List[str]) -> Dict[str, float]:
        from app.services.gap_analyzer import GapAnalyzer
        
        gap_analyzer = GapAnalyzer()
        readiness = {}
        
        for role in target_roles:
            score = gap_analyzer.calculate_readiness_score(profile.id, role)
            readiness[role] = score
        
        profile.readiness_scores = readiness
        return readiness

    def clear_github_cache(self):
        GitHubCache.clear()
