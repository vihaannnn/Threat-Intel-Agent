"""
Security Analysis Interface for Threat Intelligence Agent
Interactive interface for security risk analysis and remediation recommendations
"""

import streamlit as st
import asyncio
import json
import logging
from datetime import datetime
from typing import Dict, Any, List, Optional
import re

# Import our components
from utils.config import OPENAI_KEY, VALID_API_KEY
from tools.rag_tool import OSVRAGTool, ExtractedEntities
from tools.web_search import WebSearchTool
from utils.llm import get_llm_provider
from utils.risk_scorer import get_risk_scorer

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("SecurityAnalysis")

# Page configuration
st.set_page_config(
    page_title="Security Analysis Interface - Threat Intelligence Agent",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Initialize session state
if "messages" not in st.session_state:
    st.session_state.messages = []
if "infrastructure_context" not in st.session_state:
    st.session_state.infrastructure_context = {
        "os_versions": [],
        "services": [],
        "packages": [],
        "assets": [],
        "network_info": ""
    }

# Initialize components
@st.cache_resource
def initialize_components():
    """Initialize RAG tool and other components"""
    try:
        rag_tool = OSVRAGTool(openai_api_key=OPENAI_KEY)
        web_search = WebSearchTool()
        llm_provider = get_llm_provider()
        risk_scorer = get_risk_scorer()
        return rag_tool, web_search, llm_provider, risk_scorer
    except Exception as e:
        st.error(f"Failed to initialize components: {e}")
        return None, None, None, None

def extract_cve_ids(text: str) -> List[str]:
    """Extract CVE IDs from text"""
    cve_pattern = r'CVE-\d{4}-\d{4,7}'
    ghsa_pattern = r'GHSA-[a-z0-9]{4}-[a-z0-9]{4}-[a-z0-9]{4}'
    cves = re.findall(cve_pattern, text, re.IGNORECASE)
    ghsas = re.findall(ghsa_pattern, text, re.IGNORECASE)
    return cves + ghsas

def extract_ecosystems(text: str) -> List[str]:
    """Extract ecosystem mentions from text"""
    ecosystem_map = {
        "python": "PyPI",
        "pypi": "PyPI",
        "npm": "npm",
        "node": "npm",
        "node.js": "npm",
        "java": "Maven",
        "maven": "Maven",
        "go": "Go",
        "golang": "Go",
        "debian": "Debian",
        "ubuntu": "Debian",
        "linux": "Debian"
    }
    
    ecosystems = []
    text_lower = text.lower()
    for keyword, ecosystem in ecosystem_map.items():
        if keyword in text_lower:
            if ecosystem not in ecosystems:
                ecosystems.append(ecosystem)
    return ecosystems

async def analyze_infrastructure_and_search(
    rag_tool: OSVRAGTool,
    llm_provider,
    query: str,
    infrastructure_context: Dict[str, Any]
) -> Dict[str, Any]:
    """Analyze query and search for relevant vulnerabilities"""
    
    # Extract CVE IDs if mentioned
    cve_ids = extract_cve_ids(query)
    
    # Extract ecosystems from query and context
    ecosystems = extract_ecosystems(query)
    if infrastructure_context.get("packages"):
        for pkg in infrastructure_context["packages"]:
            pkg_ecosystems = extract_ecosystems(str(pkg))
            ecosystems.extend(pkg_ecosystems)
    
    # Remove duplicates
    ecosystems = list(set(ecosystems))
    
    # If CVE IDs are mentioned, fetch them directly
    vuln_data = []
    if cve_ids:
        for cve_id in cve_ids[:3]:  # Limit to 3 CVEs
            try:
                vuln = await rag_tool.get_vulnerability_by_id(cve_id)
                if vuln:
                    vuln_data.append(vuln)
            except Exception as e:
                logger.error(f"Error fetching {cve_id}: {e}")
    
    # Perform semantic search
    entities = ExtractedEntities(
        ecosystems=ecosystems if ecosystems else None,
        query_text=query
    )
    
    try:
        search_results = await rag_tool.search_vulnerabilities(
            query=query,
            entities=entities,
            limit=10,
            use_hybrid=True,
            use_reranking=True
        )
    except Exception as e:
        logger.error(f"Search error: {e}")
        search_results = {"results": [], "total_found": 0}
    
    # Combine CVE-specific results with search results
    all_results = vuln_data + search_results.get("results", [])
    
    return {
        "vulnerabilities": all_results,
        "cve_ids": cve_ids,
        "ecosystems": ecosystems,
        "search_results": search_results
    }

async def generate_analysis_response(
    llm_provider,
    query: str,
    infrastructure_context: Dict[str, Any],
    vulnerability_data: Dict[str, Any],
    conversation_history: List[Dict[str, str]]
) -> str:
    """Generate analysis response using LLM"""
    
    # Build context from infrastructure
    infra_context_text = ""
    if infrastructure_context.get("os_versions"):
        infra_context_text += f"OS Versions: {', '.join(infrastructure_context['os_versions'])}\n"
    if infrastructure_context.get("services"):
        infra_context_text += f"Services: {', '.join(infrastructure_context['services'])}\n"
    if infrastructure_context.get("packages"):
        infra_context_text += f"Packages: {', '.join(map(str, infrastructure_context['packages']))}\n"
    if infrastructure_context.get("network_info"):
        infra_context_text += f"Network Info: {infrastructure_context['network_info']}\n"
    
    # Format vulnerability data
    vuln_summary = ""
    if vulnerability_data.get("vulnerabilities"):
        vuln_summary = "\n\nFound Vulnerabilities:\n"
        for i, vuln in enumerate(vulnerability_data["vulnerabilities"][:5], 1):
            vuln_id = vuln.get("id", "Unknown")
            summary = vuln.get("content", "")[:200] + "..." if len(vuln.get("content", "")) > 200 else vuln.get("content", "")
            severity = vuln.get("severity", [])
            vuln_summary += f"\n{i}. {vuln_id}\n"
            vuln_summary += f"   Summary: {summary}\n"
            if severity:
                vuln_summary += f"   Severity: {severity[0].get('score', 'N/A') if severity else 'N/A'}\n"
    
    # Build conversation history context
    history_context = ""
    if conversation_history:
        history_context = "\n\nPrevious conversation:\n"
        for msg in conversation_history[-3:]:  # Last 3 messages
            role = msg.get("role", "unknown")
            content = msg.get("content", "")[:100]
            history_context += f"{role}: {content}\n"
    
    # Create system prompt
    system_prompt = """You are a security analyst specialized in threat intelligence and vulnerability analysis.

Your role is to:
1. Analyze security questions and infrastructure details
2. Identify vulnerabilities affecting the organization
3. Provide clear, actionable remediation recommendations
4. Explain security risks in accessible language

Always be:
- Clear and concise
- Action-oriented (provide specific remediation steps)
- Risk-aware (prioritize critical vulnerabilities)
- Context-aware (consider the organization's infrastructure)

Format your responses in a professional, helpful manner. Use bullet points for recommendations.
"""
    
    # Build user prompt
    user_prompt = f"""User Question: {query}

{infra_context_text}

{vuln_summary}

{history_context}

Please provide a comprehensive answer that:
1. Addresses the user's question directly
2. Explains any relevant vulnerabilities found
3. Provides specific remediation steps if vulnerabilities are identified
4. Considers the infrastructure context provided
5. Mentions any CVEs or security issues relevant to their setup

Be clear and professional. If vulnerabilities are found, explain the risk and how to fix them."""
    
    # Generate response
    try:
        response = await llm_provider.chat_completion(
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt}
            ],
            temperature=0.7,
            max_tokens=1500
        )
        return response
    except Exception as e:
        logger.error(f"LLM error: {e}")
        return f"I apologize, but I encountered an error generating a response. Please try again. Error: {str(e)}"

def main():
    """Main security analysis application"""
    st.title("Security Analysis Interface")
    st.markdown("**Security risk analysis and remediation guidance**")
    st.markdown("Query vulnerabilities, security risks, CVE details, and infrastructure analysis")
    
    # Initialize components
    rag_tool, web_search, llm_provider, risk_scorer = initialize_components()
    
    if not rag_tool or not llm_provider:
        st.error("Failed to initialize components. Please check your configuration.")
        st.info("Make sure:")
        st.info("1. Your `.env` file contains `OPENAI_API_KEY`")
        st.info("2. Docker services (Qdrant) are running")
        st.info("3. Vector database is set up: `python data/setup_local_qdrant.py`")
        return
    
    # Sidebar for infrastructure context
    with st.sidebar:
        st.header("Infrastructure Context")
        st.markdown("Provide details about your infrastructure for better analysis")
        
        # OS Versions
        os_input = st.text_input(
            "OS Versions (comma-separated)",
            value=", ".join(st.session_state.infrastructure_context["os_versions"]),
            help="e.g., Ubuntu 22.04, Windows Server 2022"
        )
        if os_input:
            st.session_state.infrastructure_context["os_versions"] = [
                os.strip() for os in os_input.split(",") if os.strip()
            ]
        
        # Services
        services_input = st.text_input(
            "Services/Applications",
            value=", ".join(st.session_state.infrastructure_context["services"]),
            help="e.g., nginx, Apache, PostgreSQL"
        )
        if services_input:
            st.session_state.infrastructure_context["services"] = [
                s.strip() for s in services_input.split(",") if s.strip()
            ]
        
        # Packages
        packages_input = st.text_input(
            "Packages/Dependencies",
            value=", ".join(map(str, st.session_state.infrastructure_context["packages"])),
            help="e.g., python:requests:2.31.0, npm:express:4.18.0"
        )
        if packages_input:
            st.session_state.infrastructure_context["packages"] = [
                p.strip() for p in packages_input.split(",") if p.strip()
            ]
        
        # Network Info
        network_info = st.text_area(
            "Network Information",
            value=st.session_state.infrastructure_context["network_info"],
            help="e.g., Internet-exposed servers, internal network segments"
        )
        st.session_state.infrastructure_context["network_info"] = network_info
        
        # Clear context button
        if st.button("Clear Context"):
            st.session_state.infrastructure_context = {
                "os_versions": [],
                "services": [],
                "packages": [],
                "assets": [],
                "network_info": ""
            }
            st.rerun()
        
        st.divider()
        st.markdown("**Example Questions:**")
        st.markdown("- What vulnerabilities affect Python 3.11?")
        st.markdown("- Analyze CVE-2024-12345 for my infrastructure")
        st.markdown("- What are the risks of using Express.js 4.18?")
        st.markdown("- Find remote code execution vulnerabilities in my stack")
    
    # Display chat history
    for message in st.session_state.messages:
        with st.chat_message(message["role"]):
            st.markdown(message["content"])
            if message.get("vulnerabilities"):
                with st.expander("View Vulnerability Details"):
                    for vuln in message["vulnerabilities"][:3]:
                        st.markdown(f"**{vuln.get('id', 'Unknown')}**")
                        st.markdown(f"*{vuln.get('ecosystem', 'Unknown ecosystem')}*")
                        if vuln.get("severity"):
                            for sev in vuln["severity"]:
                                st.markdown(f"Severity: {sev.get('type', 'Unknown')} = {sev.get('score', 'N/A')}")
                        st.markdown(f"{vuln.get('content', '')[:200]}...")
                        st.divider()
    
    # Chat input
    if prompt := st.chat_input("Ask me about security vulnerabilities, CVEs, or infrastructure risks..."):
        # Add user message to chat history
        st.session_state.messages.append({"role": "user", "content": prompt})
        with st.chat_message("user"):
            st.markdown(prompt)
        
        # Generate response
        with st.chat_message("assistant"):
            with st.spinner("Analyzing security risks and searching vulnerabilities..."):
                try:
                    # Analyze infrastructure and search vulnerabilities
                    vulnerability_data = asyncio.run(
                        analyze_infrastructure_and_search(
                            rag_tool,
                            llm_provider,
                            prompt,
                            st.session_state.infrastructure_context
                        )
                    )
                    
                    # Generate analysis response
                    response = asyncio.run(
                        generate_analysis_response(
                            llm_provider,
                            prompt,
                            st.session_state.infrastructure_context,
                            vulnerability_data,
                            st.session_state.messages
                        )
                    )
                    
                    # Display response
                    st.markdown(response)
                    
                    # Show vulnerability details if found
                    if vulnerability_data.get("vulnerabilities"):
                        st.info(f"Found {len(vulnerability_data['vulnerabilities'])} relevant vulnerabilities")
                        with st.expander("View Vulnerability Details"):
                            for i, vuln in enumerate(vulnerability_data["vulnerabilities"][:5], 1):
                                st.markdown(f"### {i}. {vuln.get('id', 'Unknown')}")
                                st.markdown(f"**Ecosystem:** {vuln.get('ecosystem', 'Unknown')}")
                                if vuln.get("severity"):
                                    for sev in vuln["severity"]:
                                        st.markdown(f"**{sev.get('type', 'Severity')}:** {sev.get('score', 'N/A')}")
                                st.markdown(f"**Description:** {vuln.get('content', 'No description')[:300]}...")
                                if vuln.get("references"):
                                    st.markdown("**References:**")
                                    for ref in vuln["references"][:3]:
                                        if isinstance(ref, dict) and ref.get("url"):
                                            st.markdown(f"- [{ref['url']}]({ref['url']})")
                                st.divider()
                    
                    # Add assistant response to history
                    st.session_state.messages.append({
                        "role": "assistant",
                        "content": response,
                        "vulnerabilities": vulnerability_data.get("vulnerabilities", [])
                    })
                
                except Exception as e:
                    error_msg = f"Error: {str(e)}"
                    st.error(error_msg)
                    logger.error(f"Analysis error: {e}", exc_info=True)
                    st.session_state.messages.append({
                        "role": "assistant",
                        "content": error_msg
                    })

if __name__ == "__main__":
    main()
