# Security Chatbot - Quick Start Guide

## 🚀 Quick Start (One Command)

```bash
python run_all.py
```

This will:
1. ✅ Check if `.env` file exists (create it with `python setup_env.py` if needed)
2. ✅ Start Docker services (Qdrant + OpenSearch)
3. ✅ Launch the Streamlit chatbot interface

## 📋 First Time Setup

If this is your first time running:

### Step 1: Create `.env` file
```bash
python setup_env.py
```
This creates `.env` with your OpenAI API key already configured.

### Step 2: Set up Vector Database
```bash
python data/setup_local_qdrant.py
```
This will:
- Load vulnerability data from `osv_data/` and `extended_data/`
- Generate embeddings
- Store them in Qdrant

### Step 3: Run the Chatbot
```bash
python run_all.py
```

## 💬 Using the Chatbot

Once the Streamlit interface opens:

1. **Add Infrastructure Context** (sidebar):
   - OS Versions: e.g., "Ubuntu 22.04, Windows Server 2022"
   - Services: e.g., "nginx, Apache, PostgreSQL"
   - Packages: e.g., "python:requests:2.31.0, npm:express:4.18.0"
   - Network Info: e.g., "Internet-exposed servers"

2. **Ask Security Questions**:
   - "What vulnerabilities affect Python 3.11?"
   - "Analyze CVE-2024-12345 for my infrastructure"
   - "What are the risks of using Express.js 4.18?"
   - "Find remote code execution vulnerabilities in my stack"
   - "How do I remediate CVE-2024-59823?"

3. **Get Answers**:
   - The chatbot will search vulnerability databases
   - Analyze your infrastructure context
   - Provide remediation recommendations
   - Explain security risks

## 🎯 Features

- ✅ **Conversational Interface**: Chat naturally about security
- ✅ **Infrastructure Analysis**: Context-aware vulnerability detection
- ✅ **CVE Lookup**: Direct CVE/GHSA ID analysis
- ✅ **Remediation Guidance**: Actionable security recommendations
- ✅ **RAG-Powered**: Semantic search across vulnerability databases
- ✅ **Real-time Analysis**: Instant security risk assessment

## 🔧 Troubleshooting

### Error: "Missing OPENAI_API_KEY"
```bash
python setup_env.py
```

### Error: "Collection not found"
```bash
python data/setup_local_qdrant.py
```

### Error: "Connection refused" (Docker)
```bash
# Make sure Docker Desktop is running
docker ps
```

### Skip Docker services
```bash
python run_all.py --no-docker
```

## 📝 Example Conversations

**User:** "What vulnerabilities affect my Ubuntu 22.04 server running nginx?"

**Bot:** Analyzes your infrastructure, searches for Ubuntu/Debian vulnerabilities affecting nginx, provides specific CVEs and remediation steps.

**User:** "Tell me about CVE-2024-12345"

**Bot:** Fetches detailed CVE information, explains impact, provides remediation guidance.

**User:** "I'm using Python requests 2.31.0. Is it secure?"

**Bot:** Checks PyPI vulnerabilities, identifies any CVEs affecting that version, recommends updates.

## 🎉 Enjoy Your Security Chatbot!

The chatbot is now ready to help you analyze security risks and get remediation guidance.


