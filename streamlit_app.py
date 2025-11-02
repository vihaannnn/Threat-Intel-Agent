import streamlit as st
import asyncio
import sys
import os
from pathlib import Path
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Check for OpenAI API key from environment
OPENAI_KEY = os.getenv("OPENAI_API_KEY")

# Add project root to path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from client.llm_agent_dynamic import mcp_agent

# Duke University Blue color scheme
DUKE_BLUE = "#012169"
DUKE_LIGHT_BLUE = "#339898"
DUKE_GRAY = "#E5E5E5"
ACCENT_COLOR = "#00539B"

# Page configuration
st.set_page_config(
    page_title="Security Assistant",
    page_icon="🤖",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom CSS for Duke branding
st.markdown(f"""
    <style>
    /* Main theme colors */
    .stApp {{
        background-color: #f8f9fa;
    }}
    
    /* Sidebar styling */
    [data-testid="stSidebar"] {{
        background: linear-gradient(180deg, {DUKE_BLUE} 0%, {ACCENT_COLOR} 100%);
        padding-top: 2rem;
    }}
    
    /* Sidebar content container */
    [data-testid="stSidebar"] > div:first-child {{
        padding: 1rem 1.5rem;
    }}
    
    /* Make sidebar text readable */
    [data-testid="stSidebar"] .element-container {{
        color: #FFFFFF !important;
    }}
    
    [data-testid="stSidebar"] h1,
    [data-testid="stSidebar"] h2,
    [data-testid="stSidebar"] h3 {{
        color: #FFFFFF !important;
        font-weight: 600 !important;
        margin-bottom: 1rem !important;
    }}
    
    /* Force white color for markdown headers in sidebar */
    [data-testid="stSidebar"] .stMarkdown h1,
    [data-testid="stSidebar"] .stMarkdown h2,
    [data-testid="stSidebar"] .stMarkdown h3 {{
        color: #FFFFFF !important;
    }}
    
    [data-testid="stSidebar"] .stMarkdown {{
        color: #FFFFFF !important;
    }}
    
    [data-testid="stSidebar"] p {{
        color: #E8E8E8 !important;
        line-height: 1.6 !important;
    }}
    
    [data-testid="stSidebar"] label {{
        color: #FFFFFF !important;
        font-weight: 500 !important;
    }}
    
    /* Sidebar dividers */
    [data-testid="stSidebar"] hr {{
        border-color: rgba(255, 255, 255, 0.2) !important;
        margin: 1.5rem 0 !important;
    }}
    
    /* BRUTE FORCE - Make ALL SVGs in sidebar white */
    [data-testid="stSidebar"] svg,
    [data-testid="stSidebar"] svg path,
    [data-testid="stSidebar"] svg circle,
    [data-testid="stSidebar"] svg rect,
    [data-testid="stSidebar"] svg line,
    [data-testid="stSidebar"] svg polyline,
    [data-testid="stSidebar"] svg polygon {{
        fill: #FFFFFF !important;
        stroke: #FFFFFF !important;
        color: #FFFFFF !important;
    }}
    
    [data-testid="stSidebar"] button,
    [data-testid="stSidebar"] button *,
    button[kind="header"],
    button[kind="header"] *,
    [data-testid="collapsedControl"],
    [data-testid="collapsedControl"] *,
    [data-testid="stSidebarCollapseButton"],
    [data-testid="stSidebarCollapseButton"] *,
    [data-testid="baseButton-header"],
    [data-testid="baseButton-header"] * {{
        color: #FFFFFF !important;
    }}
    
    [data-testid="stSidebar"] button svg,
    [data-testid="stSidebar"] button svg *,
    button[kind="header"] svg,
    button[kind="header"] svg * {{
        fill: #FFFFFF !important;
        stroke: #FFFFFF !important;
        color: #FFFFFF !important;
    }}
    
    /* Success/Error boxes in sidebar - Fixed */
    [data-testid="stSidebar"] [data-testid="stNotification"] {{
        background-color: transparent !important;
        border: none !important;
    }}
    
    [data-testid="stSidebar"] [data-testid="stNotificationContentSuccess"] {{
        background-color: rgba(76, 175, 80, 0.2) !important;
        border: 1px solid rgba(76, 175, 80, 0.4) !important;
        border-radius: 8px !important;
        color: #FFFFFF !important;
    }}
    
    [data-testid="stSidebar"] [data-testid="stNotificationContentError"] {{
        background-color: rgba(244, 67, 54, 0.2) !important;
        border: 1px solid rgba(244, 67, 54, 0.4) !important;
        border-radius: 8px !important;
        color: #FFFFFF !important;
    }}
    
    [data-testid="stSidebar"] [data-testid="stNotificationContentWarning"] {{
        background-color: rgba(255, 193, 7, 0.2) !important;
        border: 1px solid rgba(255, 193, 7, 0.4) !important;
        border-radius: 8px !important;
        color: #FFFFFF !important;
    }}
    
    [data-testid="stSidebar"] .stSuccess,
    [data-testid="stSidebar"] .stError,
    [data-testid="stSidebar"] .stWarning {{
        background-color: transparent !important;
    }}
    
    [data-testid="stSidebar"] .stSuccess > div,
    [data-testid="stSidebar"] .stError > div,
    [data-testid="stSidebar"] .stWarning > div {{
        background-color: rgba(255, 255, 255, 0.1) !important;
        border: 1px solid rgba(255, 255, 255, 0.3) !important;
        border-radius: 8px !important;
        color: #FFFFFF !important;
    }}
    
    /* Sidebar buttons */
    [data-testid="stSidebar"] .stButton > button {{
        background-color: rgba(255, 255, 255, 0.1) !important;
        color: #FFFFFF !important;
        border: 1px solid rgba(255, 255, 255, 0.3) !important;
        border-radius: 8px !important;
        padding: 0.6rem 1rem !important;
        font-weight: 500 !important;
        transition: all 0.3s ease !important;
        width: 100% !important;
        text-align: left !important;
    }}
    
    [data-testid="stSidebar"] .stButton > button:hover {{
        background-color: rgba(255, 255, 255, 0.2) !important;
        border-color: rgba(255, 255, 255, 0.5) !important;
        transform: translateX(4px);
    }}
    
    /* Chat messages */
    .stChatMessage {{
        background-color: white;
        border-radius: 10px;
        padding: 15px;
        margin: 10px 0;
        box-shadow: 0 2px 4px rgba(0,0,0,0.1);
    }}
    
    /* User message - Duke Blue */
    [data-testid="stChatMessageContent"][data-message-type="user"] {{
        background-color: {DUKE_BLUE} !important;
        color: white !important;
    }}
    
    /* Assistant message - Light background */
    [data-testid="stChatMessageContent"][data-message-type="assistant"] {{
        background-color: {DUKE_GRAY} !important;
        color: #000000 !important;
    }}
    
    /* Header styling */
    h1 {{
        color: {DUKE_BLUE};
        font-weight: 700;
    }}
    
    /* Button styling */
    .stButton > button {{
        background-color: {DUKE_BLUE};
        color: white;
        border: none;
        border-radius: 5px;
        padding: 10px 24px;
        font-weight: 600;
    }}
    
    .stButton > button:hover {{
        background-color: {DUKE_LIGHT_BLUE};
    }}
    
    /* Input fields */
    .stTextInput > div > div > input {{
        border: 2px solid {DUKE_BLUE};
        border-radius: 5px;
    }}
    
    /* Success/Info boxes */
    .stSuccess {{
        background-color: {DUKE_LIGHT_BLUE};
        color: white;
    }}
    </style>
""", unsafe_allow_html=True)

# Initialize session state
if "messages" not in st.session_state:
    st.session_state.messages = []

# Sidebar for configuration
with st.sidebar:
    # Header with icon
    st.markdown("""
        <div style='text-align: center; padding: 1rem 0 1.5rem 0;'>
            <div style='font-size: 3rem; margin-bottom: 0.5rem;'>🛡️</div>
            <h2 style='margin: 0; font-size: 1.3rem; font-weight: 600;'>Threat Intelligence Agent</h2>
        </div>
    """, unsafe_allow_html=True)
    
    st.markdown("---")
    
    # About section with styling
    st.markdown("### 📚 About")
    st.markdown("""
    <div style='background: rgba(255, 255, 255, 0.08); border-radius: 10px; padding: 1rem; margin: 0.5rem 0;'>
        <p style='margin: 0; font-size: 0.9rem; line-height: 1.6;'>
            This Agent provides tools for <strong>web searches</strong>, <strong>vulnerability analysis</strong>, 
            and <strong>CVE lookups</strong>. Designed for easy extensibility and ideal for automating 
            threat intelligence workflows.
        </p>
    </div>
    """, unsafe_allow_html=True)
    
    st.markdown("---")
    
    # API Status section
    st.markdown("### 🔑 API Status")
    if OPENAI_KEY:
        st.success("✓ API Key Configured")
    else:
        st.error("✗ API Key Missing")
        st.warning("Set OPENAI_API_KEY in .env")
    
    st.markdown("---")
    
    # Example queries with better spacing
    st.markdown("### 💡 Example Queries")
    st.markdown("<div style='margin-bottom: 0.5rem;'></div>", unsafe_allow_html=True)
    
    


    example_queries = [
        ("🔍", "Are there any known vulnerabilities specific to machines running both Windows Server 2022 and Docker with privileged containers enabled?"),
        ("🔍", "What is the risk of running Active Directory on a server that also hosts Kubernetes and exposed Redis?"),
        ("🔍", "Which vulnerabilities could impact cross-zone authentication if both OpenLDAP and Active Directory are used for federated login in segmented VLANs?"),
    ]
    
    for i, (icon, query) in enumerate(example_queries):
        if st.button(f"{icon} {query}", key=f"example_{i}", use_container_width=True):
            st.session_state.example_query = query
    
    st.markdown("---")
    
    # Clear chat button with icon
    if st.button("🗑️ Clear Chat History", use_container_width=True):
        st.session_state.messages = []
        st.rerun()
    

# Main chat interface
st.title("🛡️ Threat Intelligence Agent")
st.markdown("Ask me about vulnerabilities, security issues, and remediation strategies.")

# Check if API key is configured
if not OPENAI_KEY:
    st.error("⚠️ **Configuration Required**")
    st.warning("""
    The OPENAI_API_KEY environment variable is not set. 
    
    Please add your API key to the `.env` file:
    ```
    OPENAI_API_KEY=sk-your-api-key-here
    ```
    
    Then restart the application.
    """)
    st.stop()

# Display chat messages
for message in st.session_state.messages:
    with st.chat_message(message["role"]):
        st.markdown(message["content"])

# Handle example query clicks
if "example_query" in st.session_state:
    example_query = st.session_state.example_query
    del st.session_state.example_query
    
    # Add to messages
    st.session_state.messages.append({"role": "user", "content": example_query})
    
    # Display user message
    with st.chat_message("user"):
        st.markdown(example_query)
    
    # Get response
    with st.chat_message("assistant"):
        with st.spinner("Thinking..."):
            try:
                # Run the agent directly without capturing stdout
                result = asyncio.run(mcp_agent(example_query))
                
                # Check if we got a result
                if result:
                    response = str(result)
                else:
                    response = "I encountered an issue processing your request. Please try again."
                
                st.markdown(response)
                
            except Exception as e:
                import traceback
                error_details = traceback.format_exc()
                response = f"❌ Error: {str(e)}\n\nPlease check your configuration and try again."
                st.error(response)
                # Print full error to console for debugging
                print(f"Full error details:\n{error_details}")
    
        st.session_state.messages.append({"role": "assistant", "content": response})
    
    st.rerun()

# Chat input
if prompt := st.chat_input("Ask me about security vulnerabilities..."):
    # Add user message
    st.session_state.messages.append({"role": "user", "content": prompt})
    
    # Display user message
    with st.chat_message("user"):
        st.markdown(prompt)
    
    # Get assistant response
    with st.chat_message("assistant"):
        with st.spinner("Analyzing your query..."):
            try:
                # Run the agent directly without capturing stdout
                result = asyncio.run(mcp_agent(prompt))
                
                # Check if we got a result
                if result:
                    response = str(result)
                else:
                    response = "I encountered an issue processing your request. Please try again."
                
                st.markdown(response)
                
            except Exception as e:
                import traceback
                error_details = traceback.format_exc()
                response = f"❌ Error: {str(e)}\n\nPlease check your configuration and connection."
                st.error(response)
                # Print full error to console for debugging
                print(f"Full error details:\n{error_details}")
        
        st.session_state.messages.append({"role": "assistant", "content": response})