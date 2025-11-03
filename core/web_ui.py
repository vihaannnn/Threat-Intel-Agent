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
import sys
from pathlib import Path

# Add project root to path for imports
_project_root = Path(__file__).parent.parent
if str(_project_root) not in sys.path:
    sys.path.insert(0, str(_project_root))

from utils.config import OPENAI_KEY, VALID_API_KEY
from tools.rag_tool import OSVRAGTool, ExtractedEntities
from tools.web_search import WebSearchTool
from core.llm import get_llm_provider
from core.risk_scorer import get_risk_scorer

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("SecurityAnalysis")

# Page configuration
st.set_page_config(
    page_title="Security Analysis Interface - Threat Intelligence Agent",
    layout="wide",
    initial_sidebar_state="expanded",
    page_icon="🔒"
)

# Duke University Theme CSS - Similar to Threat Intelligence Agent Design
st.markdown("""
<style>
    /* Duke University Blue Colors - Matching Image Scheme */
    :root {
        --duke-blue: #012169;
        --duke-blue-dark: #001144;
        --duke-blue-sidebar: #012169;
        --duke-blue-light: #4A90E2;
        --duke-blue-accent: #6BA3D6;
        --duke-white: #FFFFFF;
        --duke-gray-dark: #2C2C2C;
        --duke-gray-light: #F5F5F5;
        --duke-gray-text: #666666;
        --duke-text: #333333;
    }
    
    /* Main background - White */
    .stApp {
        background-color: var(--duke-white) !important;
    }
    
    .main .block-container {
        background-color: var(--duke-white) !important;
        padding-top: 2rem;
    }
    
    /* Sidebar styling - Dark Blue */
    section[data-testid="stSidebar"] {
        background-color: var(--duke-blue-sidebar) !important;
    }
    
    .css-1d391kg {
        background-color: var(--duke-blue-sidebar) !important;
    }
    
    .css-1lcbmhc {
        background-color: var(--duke-blue-sidebar) !important;
    }
    
    /* Sidebar text - White */
    .css-1lcbmhc .css-1n76uvr {
        color: var(--duke-white) !important;
        font-weight: 700 !important;
    }
    
    section[data-testid="stSidebar"] p,
    section[data-testid="stSidebar"] span,
    section[data-testid="stSidebar"] div,
    section[data-testid="stSidebar"] label {
        color: var(--duke-white) !important;
    }
    
    /* Sidebar help text/tooltips - White */
    section[data-testid="stSidebar"] [data-testid="stTooltip"],
    section[data-testid="stSidebar"] .stTooltip,
    section[data-testid="stSidebar"] [data-baseweb="tooltip"],
    section[data-testid="stSidebar"] [class*="tooltip"],
    section[data-testid="stSidebar"] .tooltip {
        color: var(--duke-white) !important;
        background-color: rgba(1, 33, 105, 0.95) !important;
        border: 1px solid rgba(255, 255, 255, 0.3) !important;
    }
    
    /* Sidebar help icon tooltip text */
    section[data-testid="stSidebar"] div[role="tooltip"],
    section[data-testid="stSidebar"] .st-help-tooltip,
    section[data-testid="stSidebar"] [data-testid="tooltip"] p,
    section[data-testid="stSidebar"] [data-testid="tooltip"] div {
        color: var(--duke-white) !important;
    }
    
    /* Sidebar dividers - Light */
    section[data-testid="stSidebar"] hr {
        border-color: rgba(255, 255, 255, 0.3) !important;
    }
    
    /* Make all text elements in sidebar white */
    section[data-testid="stSidebar"] * {
        color: var(--duke-white) !important;
    }
    
    /* Exception for input fields - they need dark text */
    section[data-testid="stSidebar"] input,
    section[data-testid="stSidebar"] textarea {
        color: var(--duke-text) !important;
        background-color: var(--duke-white) !important;
    }
    
    /* Main header styling - Clean white background with sticky positioning */
    .main-header {
        background: var(--duke-white) !important;
        padding: 1.5rem 2rem;
        border-radius: 10px;
        margin-bottom: 1.5rem;
        border-left: 5px solid var(--duke-blue);
        box-shadow: 0 2px 8px rgba(1, 33, 105, 0.1);
        position: sticky !important;
        top: 0 !important;
        z-index: 1000 !important;
        backdrop-filter: blur(10px) !important;
        background-color: rgba(255, 255, 255, 0.98) !important;
    }
    
    /* Ensure header stays at top when scrolling */
    .stApp > header {
        position: sticky !important;
        top: 0 !important;
        z-index: 999 !important;
    }
    
    .duke-logo-text {
        color: var(--duke-blue) !important;
        font-size: 0.85rem;
        font-weight: 700;
        letter-spacing: 1.2px;
        margin-bottom: 0.5rem;
        text-transform: uppercase;
    }
    
    .main-header h1 {
        color: var(--duke-blue) !important;
        font-weight: 700 !important;
        margin: 0 !important;
        padding: 0 !important;
        border: none !important;
        font-size: 2rem !important;
    }
    
    /* Title styling - Dark blue on white */
    h1 {
        color: var(--duke-blue) !important;
        font-weight: 700 !important;
        border-bottom: 3px solid var(--duke-blue-accent) !important;
        padding-bottom: 0.5rem !important;
    }
    
    /* Button styling - Dark gray/blue */
    .stButton > button {
        background-color: var(--duke-blue) !important;
        color: var(--duke-white) !important;
        border: none !important;
        border-radius: 6px !important;
        font-weight: 600 !important;
        transition: all 0.3s ease !important;
        padding: 0.5rem 1.5rem !important;
    }
    
    .stButton > button:hover {
        background-color: var(--duke-blue-dark) !important;
        transform: translateY(-2px);
        box-shadow: 0 4px 12px rgba(1, 33, 105, 0.3) !important;
    }
    
    /* Input field styling - Light borders on white */
    .stTextInput > div > div > input {
        border: 2px solid #E0E0E0 !important;
        border-radius: 6px !important;
        background-color: var(--duke-white) !important;
        color: var(--duke-text) !important;
    }
    
    .stTextInput > div > div > input:focus {
        border-color: var(--duke-blue-accent) !important;
        box-shadow: 0 0 0 3px rgba(1, 33, 105, 0.1) !important;
    }
    
    .stTextArea > div > div > textarea {
        border: 2px solid #E0E0E0 !important;
        border-radius: 6px !important;
        background-color: var(--duke-white) !important;
        color: var(--duke-text) !important;
    }
    
    .stTextArea > div > div > textarea:focus {
        border-color: var(--duke-blue-accent) !important;
        box-shadow: 0 0 0 3px rgba(1, 33, 105, 0.1) !important;
    }
    
    /* Chat input styling - Dark gray footer */
    .stChatInputContainer {
        background-color: var(--duke-gray-dark) !important;
        border-top: 2px solid var(--duke-gray-dark) !important;
        padding: 1rem !important;
    }
    
    .stChatInputContainer input {
        background-color: #404040 !important;
        color: var(--duke-white) !important;
        border: none !important;
    }
    
    /* Info boxes - Light blue accent */
    .stInfo {
        border-left: 4px solid var(--duke-blue-accent) !important;
        background-color: #E8F0F8 !important;
        color: var(--duke-text) !important;
    }
    
    /* Expander styling */
    .streamlit-expanderHeader {
        color: var(--duke-blue) !important;
        font-weight: 600 !important;
        background-color: var(--duke-gray-light) !important;
    }
    
    /* Links */
    a {
        color: var(--duke-blue) !important;
    }
    
    a:hover {
        color: var(--duke-blue-light) !important;
    }
    
    /* Divider styling */
    hr {
        border-color: #E0E0E0 !important;
        opacity: 0.5 !important;
    }
    
    /* Text readability - Dark text on white */
    .main p, .main span, .main div {
        color: var(--duke-text) !important;
    }
    
    .main .stMarkdown {
        color: var(--duke-text) !important;
    }
    
    /* Make all markdown text dark and readable */
    .stMarkdown {
        color: var(--duke-text) !important;
    }
    
    .stMarkdown p {
        color: var(--duke-text) !important;
    }
    
    .stMarkdown strong {
        color: var(--duke-text) !important;
    }
    
    /* Specific styling for description text */
    .main .stMarkdown p,
    .main .stMarkdown strong {
        color: var(--duke-text) !important;
        font-size: 1rem !important;
    }
    
    /* Chat messages - readable on white */
    .stChatMessage {
        background-color: var(--duke-white) !important;
    }
    
    .stChatMessage p {
        color: var(--duke-text) !important;
    }
    
    /* Ensure all text elements in main area are readable */
    [data-testid="stMarkdownContainer"] p,
    [data-testid="stMarkdownContainer"] strong {
        color: var(--duke-text) !important;
    }
    
    /* Tooltip styling - make help text readable */
    [data-baseweb="popover"] {
        background-color: rgba(1, 33, 105, 0.95) !important;
        color: var(--duke-white) !important;
        border: 1px solid rgba(255, 255, 255, 0.3) !important;
    }
    
    [data-baseweb="popover"] p,
    [data-baseweb="popover"] div,
    [data-baseweb="popover"] span {
        color: var(--duke-white) !important;
    }
    
    /* Specific styling for Streamlit tooltips */
    div[role="tooltip"],
    .stTooltip,
    [data-testid="stTooltip"],
    [data-testid="stHelpTooltip"] {
        background-color: rgba(1, 33, 105, 0.95) !important;
        color: var(--duke-white) !important;
        border: 1px solid rgba(255, 255, 255, 0.3) !important;
    }
    
    /* Make sure all tooltip content is white */
    div[role="tooltip"] *,
    .stTooltip *,
    [data-testid="stTooltip"] *,
    [data-testid="stHelpTooltip"] * {
        color: var(--duke-white) !important;
    }
    
    /* Input field labels in sidebar - white */
    section[data-testid="stSidebar"] label {
        color: var(--duke-white) !important;
    }
    
    /* Make sidebar input labels white */
    section[data-testid="stSidebar"] [class*="label"],
    section[data-testid="stSidebar"] [class*="Label"] {
        color: var(--duke-white) !important;
    }
</style>
""", unsafe_allow_html=True)

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
    # Duke University Header - Light Theme with Sticky Positioning
    st.markdown("""
    <div class="main-header">
        <div class="duke-logo-text">Duke University</div>
        <h1>Threat Intelligence Assistant</h1>
    </div>
    """, unsafe_allow_html=True)
    
    st.markdown('<p style="color: #333333; font-size: 1.1rem; margin: 0.5rem 0;"><strong>Security risk analysis and remediation guidance</strong></p>', unsafe_allow_html=True)
    st.markdown('<p style="color: #333333; font-size: 1rem; margin: 0.5rem 0;">Query vulnerabilities, security risks, CVE details, and infrastructure analysis</p>', unsafe_allow_html=True)
    
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
        st.markdown("""
        <div style="padding: 0.5rem 0; margin-bottom: 1rem; border-bottom: 2px solid rgba(255, 255, 255, 0.3);">
            <h3 style="color: white; margin: 0; font-weight: 700;">Infrastructure Context</h3>
        </div>
        """, unsafe_allow_html=True)
        st.markdown('<p style="color: white; margin: 0.5rem 0;">Provide details about your infrastructure for better analysis</p>', unsafe_allow_html=True)
        
        # API Status Section
        st.divider()
        st.markdown("""
        <div style="padding: 0.5rem 0; margin-bottom: 1rem; border-bottom: 2px solid rgba(255, 255, 255, 0.3);">
            <h3 style="color: white; margin: 0; font-weight: 700;">API Status</h3>
        </div>
        """, unsafe_allow_html=True)
        
        # Check API key status
        from utils.config import OPENAI_KEY, SERPER_API_KEY
        api_configured = bool(OPENAI_KEY and OPENAI_KEY.strip())
        serper_configured = bool(SERPER_API_KEY and SERPER_API_KEY.strip())
        
        # Display API Key status
        if api_configured:
            st.markdown("""
            <div style="background-color: #4CAF50; color: white; padding: 0.5rem 1rem; border-radius: 6px; margin: 0.5rem 0; display: flex; align-items: center; gap: 0.5rem;">
                <span style="font-size: 1.2rem;">✓</span>
                <span style="font-weight: 600;">API Key Configured</span>
            </div>
            """, unsafe_allow_html=True)
        else:
            st.markdown("""
            <div style="background-color: #FF9800; color: white; padding: 0.5rem 1rem; border-radius: 6px; margin: 0.5rem 0; display: flex; align-items: center; gap: 0.5rem;">
                <span style="font-size: 1.2rem;">⚠</span>
                <span style="font-weight: 600;">API Key Not Configured</span>
            </div>
            """, unsafe_allow_html=True)
        
        # Display Serper API status (optional)
        if serper_configured:
            st.markdown("""
            <div style="background-color: #4CAF50; color: white; padding: 0.4rem 1rem; border-radius: 6px; margin: 0.3rem 0; display: flex; align-items: center; gap: 0.5rem;">
                <span style="font-size: 1rem;">✓</span>
                <span style="font-size: 0.9rem;">Serper API Configured</span>
            </div>
            """, unsafe_allow_html=True)
        else:
            st.markdown("""
            <div style="background-color: #757575; color: white; padding: 0.4rem 1rem; border-radius: 6px; margin: 0.3rem 0; display: flex; align-items: center; gap: 0.5rem;">
                <span style="font-size: 1rem;">-</span>
                <span style="font-size: 0.9rem;">Using DuckDuckGo Search</span>
            </div>
            """, unsafe_allow_html=True)
        
        st.divider()
        
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
        st.markdown('<p style="color: white; font-weight: bold; font-size: 1rem; margin: 0.5rem 0;">Example Questions:</p>', unsafe_allow_html=True)
        st.markdown('<p style="color: white; margin: 0.3rem 0;">- What vulnerabilities affect Python 3.11?</p>', unsafe_allow_html=True)
        st.markdown('<p style="color: white; margin: 0.3rem 0;">- Analyze CVE-2024-12345 for my infrastructure</p>', unsafe_allow_html=True)
        st.markdown('<p style="color: white; margin: 0.3rem 0;">- What are the risks of using Express.js 4.18?</p>', unsafe_allow_html=True)
        st.markdown('<p style="color: white; margin: 0.3rem 0;">- Find remote code execution vulnerabilities in my stack</p>', unsafe_allow_html=True)
    
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
