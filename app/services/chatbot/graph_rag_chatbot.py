"""
Graph RAG Chatbot Service
========================
A Retrieval-Augmented Generation (RAG) chatbot that uses the knowledge graph
to answer questions about skills, careers, learning paths, and certifications.
"""

from typing import List, Dict, Optional, Tuple
from langchain_groq import ChatGroq
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain_core.messages import HumanMessage, AIMessage, SystemMessage
from langchain_core.output_parsers import StrOutputParser
from app.core.config import settings
from app.services.graph_manager import GraphManager
from app.services.knowledge_sources.onet_integration import get_skill_mapper, get_onet_knowledge, SKILL_TO_COURSES


SYSTEM_PROMPT = """You are a helpful career and learning advisor for SkillBridge. Your role is to help users:

1. Understand what skills they need for different careers
2. Find learning resources (courses, certifications) for skills
3. Plan their learning path from current skills to target roles
4. Compare different technologies or frameworks
5. Get recommendations for improving their resume/career

You have access to a comprehensive knowledge graph containing:
- Tech occupations (software developer, data scientist, DevOps engineer, etc.)
- Skills required for each occupation
- Courses and certifications for skills
- Relationships between skills (prerequisites, related skills)

When answering questions:
- Be specific and actionable
- Suggest concrete courses or certifications when appropriate
- Use the knowledge graph data to back your answers
- If you don't have specific information, say so honestly
- Focus on helping users advance their careers

Always be encouraging and supportive while being honest about gaps in knowledge."""

GRAPH_CONTEXT_PROMPT = """Based on the user's question, I've retrieved the following information from the knowledge graph:

**Relevant Occupations:**
{occupations}

**Relevant Skills:**
{skills}

**Skill Relationships:**
{skill_relations}

**Available Courses:**
{courses}

**Available Certifications:**
{certifications}

Use this information to answer the user's question accurately and helpfully."""


class GraphRAGChatbot:
    """
    RAG chatbot that uses the knowledge graph to answer career and learning questions.
    """
    
    def __init__(self):
        self._llm = None
        self._graph_manager = None
        self._skill_mapper = None
        self._onet_knowledge = None
        self._conversation_history: List[Dict] = []
    
    @property
    def llm(self):
        if self._llm is None:
            self._llm = ChatGroq(
                model="llama-3.1-8b-instant",
                api_key=settings.GROQ_API_KEY,
                temperature=0.7,
                max_tokens=1024,
            )
        return self._llm
    
    @property
    def graph_manager(self):
        if self._graph_manager is None:
            self._graph_manager = GraphManager()
        return self._graph_manager
    
    @property
    def skill_mapper(self):
        if self._skill_mapper is None:
            self._skill_mapper = get_skill_mapper()
        return self._skill_mapper
    
    @property
    def onet_knowledge(self):
        if self._onet_knowledge is None:
            self._onet_knowledge = get_onet_knowledge()
        return self._onet_knowledge
    
    def _classify_intent(self, question: str) -> str:
        """Classify the user's question intent"""
        question_lower = question.lower()
        
        intents = {
            "skill_path": ["how to become", "path to", "learning path", "how do i learn", "what skills do i need", "career path"],
            "course_recommendation": ["course", "learn", "tutorial", "where to learn", "best way to learn", "recommend"],
            "certification": ["certification", "certificate", "certify", "exam"],
            "skill_comparison": ["compare", "difference between", "vs", "versus", "which is better"],
            "occupation_info": ["job", "career", "role", "occupation", "profession", "salary", "demand"],
            "skill_info": ["what is", "explain", "tell me about", "overview of"],
        }
        
        for intent, keywords in intents.items():
            if any(kw in question_lower for kw in keywords):
                return intent
        
        return "general"
    
    def _extract_entities(self, question: str, conversation_history: Optional[List[Dict]] = None) -> Dict[str, List[str]]:
        """Extract relevant entities (skills, occupations) from the question"""
        entities = {
            "skills": [],
            "occupations": [],
            "technologies": [],
        }
        
        question_lower = question.lower()
        
        generic_refs = ["this role", "the role", "that role", "this job", "the job", "that job", "target role", "my goal", "my target"]
        has_generic_ref = any(ref in question_lower for ref in generic_refs)
        
        all_occupations = self.onet_knowledge.get_all_occupations()
        for occ in all_occupations:
            occ_title = occ.get("title", "").lower()
            occ_id = occ.get("id", "").replace("_", " ").lower()
            if occ_title in question_lower or occ_id in question_lower:
                entities["occupations"].append(occ_title)
            
            for skill in occ.get("skills", []):
                skill_name = skill.lower()
                if skill_name in question_lower:
                    entities["skills"].append(skill_name)
        
        known_skills = list(SKILL_TO_COURSES.keys())
        for skill in known_skills:
            if skill in question_lower:
                entities["skills"].append(skill)
        
        tech_keywords = ["python", "javascript", "react", "aws", "docker", "kubernetes", "sql", "java", "golang", "rust", "typescript"]
        for tech in tech_keywords:
            if tech in question_lower:
                entities["technologies"].append(tech)
        
        if has_generic_ref and conversation_history:
            history_entities = self._extract_entities_from_history(conversation_history)
            entities["occupations"].extend(history_entities["occupations"])
        
        entities["skills"] = list(set(entities["skills"]))
        entities["occupations"] = list(set(entities["occupations"]))
        
        return entities
    
    def _extract_entities_from_history(self, history: List[Dict]) -> Dict[str, List[str]]:
        """Extract entities from conversation history to maintain context"""
        entities = {
            "skills": [],
            "occupations": [],
            "technologies": [],
        }
        
        known_skills = list(SKILL_TO_COURSES.keys())
        
        for msg in history[-5:]:
            content = msg.get("user", "") or msg.get("assistant", "")
            content_lower = content.lower()
            
            for occ in self.onet_knowledge.get_all_occupations():
                occ_title = occ.get("title", "").lower()
                occ_id = occ.get("id", "").replace("_", " ").lower()
                if occ_title in content_lower or occ_id in content_lower:
                    entities["occupations"].append(occ_title)
            
            for skill in known_skills:
                if skill in content_lower:
                    entities["skills"].append(skill)
            
            tech_keywords = ["python", "javascript", "react", "aws", "docker", "kubernetes", "sql", "java", "golang", "rust", "typescript"]
            for tech in tech_keywords:
                if tech in content_lower:
                    entities["technologies"].append(tech)
        
        entities["skills"] = list(set(entities["skills"]))
        entities["occupations"] = list(set(entities["occupations"]))
        entities["technologies"] = list(set(entities["technologies"]))
        
        return entities
    
    def _get_context_for_question(self, question: str, conversation_history: Optional[List[Dict]] = None, selected_role: Optional[str] = None) -> Dict[str, any]:
        """Retrieve relevant context from the knowledge graph"""
        intent = self._classify_intent(question)
        entities = self._extract_entities(question, conversation_history)
        
        history_entities = self._extract_entities_from_history(conversation_history or [])
        entities["occupations"].extend(history_entities["occupations"])
        entities["skills"].extend(history_entities["skills"])
        entities["technologies"].extend(history_entities["technologies"])
        
        if selected_role:
            role_lower = selected_role.lower()
            role_normalized = role_lower.replace(" ", "_").replace("-", "_")
            
            all_occupations = self.onet_knowledge.get_all_occupations()
            for occ in all_occupations:
                occ_id = occ.get("id", "")
                occ_title = occ.get("title", "").lower()
                if role_normalized == occ_id or role_lower == occ_title or role_normalized in occ_id:
                    entities["occupations"].append(occ_title)
                    break
        
        entities["occupations"] = list(set(entities["occupations"]))
        entities["skills"] = list(set(entities["skills"]))
        entities["technologies"] = list(set(entities["technologies"]))
        
        context = {
            "intent": intent,
            "occupations": [],
            "skills": [],
            "skill_relations": [],
            "courses": [],
            "certifications": [],
        }
        
        for occupation in entities["occupations"]:
            occ_data = None
            for occ in self.onet_knowledge.get_all_occupations():
                if occ.get("title", "").lower() == occupation:
                    occ_data = occ
                    break
            
            if occ_data:
                context["occupations"].append({
                    "title": occ_data.get("title"),
                    "skills": occ_data.get("skills", []),
                    "tools": occ_data.get("tools", []),
                })
                
                for skill_name in occ_data.get("skills", []):
                    courses = self.skill_mapper.get_learning_path(skill_name)
                    if courses:
                        context["courses"].extend(courses[:2])
                    
                    certs = []
                    try:
                        from app.services.cert_discovery.service import get_certification_service
                        cert_service = get_certification_service()
                        certs = cert_service.get_by_skill(skill_name)[:2]
                    except:
                        pass
                    context["certifications"].extend([{"name": c.name, "provider": c.provider} for c in certs])
        
        for skill in entities["skills"] + entities["technologies"]:
            related = list(self.onet_knowledge.get_related_skills(skill))[:5]
            if related:
                context["skill_relations"].append({
                    "skill": skill,
                    "related": related
                })
            
            courses = self.skill_mapper.get_learning_path(skill)
            context["courses"].extend(courses[:2])
        
        for tech in entities["technologies"]:
            occupations = self.onet_knowledge.get_occupation_for_skill(tech)
            if occupations:
                occ_list = []
                for occ_id in occupations[:3]:
                    for occ in self.onet_knowledge.get_all_occupations():
                        if occ.get("id") == occ_id:
                            occ_list.append(occ.get("title"))
                context["occupations"].extend([{"title": t} for t in occ_list])
        
        context["occupations"] = context["occupations"][:5]
        context["courses"] = context["courses"][:10]
        context["certifications"] = context["certifications"][:5]
        
        return context
    
    def _format_context(self, context: Dict) -> str:
        """Format the context into a readable string for the prompt"""
        lines = []
        
        if context["occupations"]:
            lines.append("**Relevant Occupations:**")
            for occ in context["occupations"]:
                lines.append(f"- {occ.get('title', 'Unknown')}")
                if occ.get("skills"):
                    lines.append(f"  Required skills: {', '.join(occ['skills'][:5])}")
            lines.append("")
        
        if context["skills"]:
            lines.append("**Skills:**")
            for skill in set(context["skills"]):
                lines.append(f"- {skill}")
            lines.append("")
        
        if context["skill_relations"]:
            lines.append("**Skill Relationships:**")
            for rel in context["skill_relations"]:
                lines.append(f"- {rel['skill']} is related to: {', '.join(rel['related'][:3])}")
            lines.append("")
        
        if context["courses"]:
            lines.append("**Available Courses:**")
            seen = set()
            for course in context["courses"]:
                title = course.get("title", "")
                if title and title not in seen:
                    seen.add(title)
                    provider = course.get("provider", "Unknown")
                    free = "Free" if course.get("is_free") else "Paid"
                    lines.append(f"- {title} ({provider}, {free})")
            lines.append("")
        
        if context["certifications"]:
            lines.append("**Certifications:**")
            seen = set()
            for cert in context["certifications"]:
                name = cert.get("name", "")
                if name and name not in seen:
                    seen.add(name)
                    provider = cert.get("provider", "Unknown")
                    lines.append(f"- {name} ({provider})")
            lines.append("")
        
        return "\n".join(lines) if lines else "No specific information found in the knowledge graph for your question."
    
    def ask(self, question: str, conversation_history: Optional[List[Dict]] = None, selected_role: Optional[str] = None) -> Dict:
        """
        Answer a user question using Graph RAG.
        
        Returns:
            Dict with 'answer', 'context_used', and 'suggestions'
        """
        if not question.strip():
            return {
                "answer": "Please ask me a question about skills, careers, or learning resources.",
                "context_used": False,
                "suggestions": self._get_suggestions()
            }
        
        context = self._get_context_for_question(question, conversation_history, selected_role)
        formatted_context = self._format_context(context)
        
        history = conversation_history or []
        
        prompt = ChatPromptTemplate.from_messages([
            ("system", SYSTEM_PROMPT),
            ("system", GRAPH_CONTEXT_PROMPT),
            MessagesPlaceholder(variable_name="history"),
            ("human", "{question}"),
        ])
        
        chain = prompt | self.llm | StrOutputParser()
        
        try:
            answer = chain.invoke({
                "occupations": context["occupations"],
                "skills": context["skills"],
                "skill_relations": context["skill_relations"],
                "courses": context["courses"],
                "certifications": context["certifications"],
                "question": question,
                "history": [
                    HumanMessage(content=h["user"]) if h["role"] == "user" 
                    else AIMessage(content=h["assistant"])
                    for h in history[-5:]
                ]
            })
        except Exception as e:
            answer = f"I apologize, but I encountered an error processing your question. Please try again. (Error: {str(e)[:100]})"
        
        suggestions = self._generate_suggestions(question, context)
        
        return {
            "answer": answer,
            "context_used": context["context_used"] if "context_used" in context else (len(context["occupations"]) > 0 or len(context["courses"]) > 0),
            "intent": context["intent"],
            "suggestions": suggestions,
            "entities_found": {
                "skills": context["skills"],
                "occupations": [o.get("title") for o in context["occupations"]],
            }
        }
    
    def _get_suggestions(self) -> List[str]:
        """Get initial suggestions for the user"""
        return [
            "What skills do I need to become a software developer?",
            "How can I learn machine learning from scratch?",
            "What's the best AWS certification for beginners?",
            "Compare React vs Vue for frontend development",
            "What courses should I take to become a DevOps engineer?",
        ]
    
    def _generate_suggestions(self, question: str, context: Dict) -> List[str]:
        """Generate follow-up suggestions based on the question and context"""
        suggestions = []
        
        if context["occupations"]:
            suggestions.append(f"Tell me more about the {context['occupations'][0].get('title', 'selected role')} role")
        
        if context["skills"]:
            skill = context["skills"][0] if context["skills"] else "that skill"
            suggestions.append(f"What courses can help me learn {skill}?")
        
        if context["courses"]:
            suggestions.append("Can you recommend free courses?")
        
        if context["certifications"]:
            suggestions.append("Which certification is best for beginners?")
        
        suggestions.extend([
            "How long does it take to learn this?",
            "What are the job prospects?",
        ])
        
        return suggestions[:4]


_chatbot: Optional[GraphRAGChatbot] = None


def get_graph_rag_chatbot() -> GraphRAGChatbot:
    global _chatbot
    if _chatbot is None:
        _chatbot = GraphRAGChatbot()
    return _chatbot
