import streamlit as st
import asyncio
import sys
import os
from pathlib import Path
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Check for OpenAI API key BEFORE importing config
openai_key_from_env = os.getenv("OPENAI_API_KEY")

# Store the original env key for later use
original_env_key = openai_key_from_env

# If no API key in env, set a temporary one to avoid config.py error
if not openai_key_from_env:
    os.environ["OPENAI_API_KEY"] = "placeholder_will_be_set_by_user"
    original_env_key = None

# Add project root to path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

# Now safe to import - won't raise error
from client.llm_agent_dynamic import mcp_agent

# Duke University Blue color scheme
DUKE_BLUE = "#012169"
DUKE_LIGHT_BLUE = "#339898"
DUKE_GRAY = "#E5E5E5"

# Page configuration
st.set_page_config(
    page_title="Duke AI Chatbot",
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
        background-color: {DUKE_BLUE};
    }}
    
    /* Make sidebar text readable */
    [data-testid="stSidebar"] .element-container {{
        color: #000000 !important;
    }}
    
    [data-testid="stSidebar"] h3 {{
        color: #FFFFFF !important;
    }}
    
    [data-testid="stSidebar"] .stMarkdown {{
        color: #000000 !important;
    }}
    
    [data-testid="stSidebar"] p {{
        color: #FFFFFF !important;
    }}
    
    [data-testid="stSidebar"] label {{
        color: #FFFFFF !important;
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

if "show_api_key" not in st.session_state:
    st.session_state.show_api_key = False

# Track if API key was initially from environment (only set once)
if "initial_env_key_present" not in st.session_state:
    st.session_state.initial_env_key_present = bool(original_env_key and original_env_key != "placeholder_will_be_set_by_user")

# Track if user has interacted with the field
if "api_key_touched" not in st.session_state:
    st.session_state.api_key_touched = False

# Sidebar for configuration
with st.sidebar:
    st.markdown("### 🛡️ Duke Security Assistant")
    st.markdown("")
    
    # API Key configuration - ALWAYS show input field
    st.markdown("#### 🔑 API Configuration")
    
    # Show info ONLY if environment key was present initially
    if st.session_state.initial_env_key_present:
        st.info("ℹ️ API key detected in environment. You can override it below.")
    
    # Initialize session state for tracking user interaction
    if "api_key_touched" not in st.session_state:
        st.session_state.api_key_touched = False
    
    # API Key input - always visible and editable
    user_api_key = st.text_input(
        "OpenAI API Key",
        type="password" if not st.session_state.show_api_key else "default",
        key="api_input",
        placeholder="sk-...",
        help="Enter your OpenAI API key"
    )
    
    # Track if user has interacted with the field
    if user_api_key:  # Changed: only set to True if there's actual input
        st.session_state.api_key_touched = True
    
    # Determine which key to use
    if user_api_key and user_api_key.strip():
        # User entered a key - use it
        os.environ["OPENAI_API_KEY"] = user_api_key.strip()
        st.success("✓ Using API Key from input")
        has_valid_key = True
    elif st.session_state.api_key_touched and not user_api_key:
        # User touched the field but it's empty - don't fall back to env
        st.warning("⚠️ Please enter your OpenAI API Key")
        has_valid_key = False
    elif not st.session_state.api_key_touched and st.session_state.initial_env_key_present and original_env_key:
        # User hasn't touched field yet AND key was initially in env - use environment key
        os.environ["OPENAI_API_KEY"] = original_env_key
        st.success("✓ Using API Key from environment")
        has_valid_key = True
    else:
        # No key at all
        st.warning("⚠️ Please enter your OpenAI API Key")
        has_valid_key = False
    
    st.markdown("---")
    
    # Clear chat button
    if st.button("🗑️ Clear Chat History", use_container_width=True):
        st.session_state.messages = []
        st.rerun()
    
    st.markdown("---")
    
    # Example queries
    st.markdown("### 💡 Example Queries")
    example_queries = [
        "How do I remediate CVE-2025-59823?",
        "List recent npm vulnerabilities",
        "Show Python RCE vulnerabilities",
        "Find Java deserialization issues",
        "Debian kernel vulnerabilities",
        "Go module security issues"
    ]
    
    for i, query in enumerate(example_queries):
        if st.button(query, key=f"example_{i}", use_container_width=True):
            st.session_state.example_query = query
    
    st.markdown("---")
    st.markdown("### 📚 About")
    st.markdown("""
    This chatbot helps you:
    - Search for vulnerabilities
    - Get remediation advice
    - Analyze security issues
    - Find CVE information
    """)

# Main chat interface
st.title("🤖 Duke AI Security Assistant")
st.markdown("Ask me about vulnerabilities, security issues, and remediation strategies.")

# Display chat messages
for message in st.session_state.messages:
    with st.chat_message(message["role"]):
        st.markdown(message["content"])

# Handle example query clicks
if "example_query" in st.session_state:
    example_query = st.session_state.example_query
    del st.session_state.example_query
    
    # Check API key before processing
    if not has_valid_key:
        with st.chat_message("assistant"):
            st.error("⚠️ Please configure your OpenAI API key in the sidebar to use the chatbot.")
    else:
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