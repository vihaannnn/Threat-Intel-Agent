# Threat Intelligence Agent

## Overview

The Threat Intelligence Agent is a comprehensive security analysis platform designed to help organizations identify, assess, and remediate software vulnerabilities. The system provides an interactive interface for querying vulnerability databases, analyzing security risks, and generating actionable remediation recommendations.

The platform leverages vector search technology to efficiently query large vulnerability databases, natural language processing for intelligent query understanding, and risk scoring algorithms to prioritize security threats based on multiple factors including CVSS scores, EPSS probabilities, CISA KEV status, and asset criticality.

## System Architecture

The system consists of several key components:

- **Vector Database (Qdrant)**: Stores vulnerability data with semantic embeddings for efficient similarity search
- **Web Interface (Streamlit)**: Interactive user interface for security analysis and vulnerability queries
- **LLM Provider**: Supports both OpenAI API and local models for generating security analysis and recommendations
- **RAG Tool**: Retrieval-Augmented Generation system for querying vulnerability databases
- **Risk Scorer**: Multi-factor risk assessment engine combining CVSS, EPSS, KEV, and asset context
- **Web Search Integration**: Optional web search capabilities for real-time threat intelligence

## System Requirements

### Minimum Requirements

- **Operating System**: Windows 10/11, macOS 10.15+, or Linux (Ubuntu 20.04+)
- **Python**: Version 3.12 or higher
- **RAM**: 8GB minimum (16GB recommended)
- **Storage**: 5GB free disk space
- **Docker**: Docker Desktop or Docker Engine (for Qdrant vector database)
- **Internet Connection**: Required for API access and initial setup

### Software Dependencies

The following software must be installed on your system:

1. **Python 3.12+**: Download from [python.org](https://www.python.org/downloads/)
2. **Docker Desktop**: Download from [docker.com](https://www.docker.com/products/docker-desktop/)
3. **Git**: For cloning the repository (optional if downloading as ZIP)

### API Keys Required

- **OpenAI API Key** (Required): Obtain from [platform.openai.com](https://platform.openai.com/api-keys)
- **Serper API Key** (Optional): For enhanced web search capabilities from [serper.dev](https://serper.dev/)

## Installation

### Step 1: Clone or Download the Repository

If using Git:

```bash
git clone <repository-url>
cd Threat-Intel-Agent
```

Alternatively, download and extract the ZIP file to your desired location.

### Step 2: Create Python Virtual Environment

Navigate to the project directory and create a virtual environment:

**Windows:**
```powershell
python -m venv venv
.\venv\Scripts\activate
```

**macOS/Linux:**
```bash
python3 -m venv venv
source venv/bin/activate
```

### Step 3: Install Python Dependencies

Install all required Python packages:

```bash
pip install -r requirements.txt
```

Additionally, install the following packages that may not be in requirements.txt:

```bash
pip install streamlit keyring opensearch-py
```

**Note**: If you plan to use local LLM models instead of OpenAI, you may also need:

```bash
pip install transformers torch sentence-transformers
```

### Step 4: Install and Start Docker

1. Install Docker Desktop from [docker.com](https://www.docker.com/products/docker-desktop/)
2. Start Docker Desktop and ensure it is running
3. Verify Docker is working:

```bash
docker ps
```

### Step 5: Configure Environment Variables

Create a `.env` file in the project root directory. You can use the provided setup script:

```bash
python setup_env.py
```

The script will prompt you for your OpenAI API key. Alternatively, manually create a `.env` file based on `env.example`:

```env
# Required API Keys
OPENAI_API_KEY=sk-proj-your-key-here

# Optional API Keys
SERPER_API_KEY=your-serper-key-here

# Model Configuration
OPENAI_MODEL=gpt-4o-mini

# Server Configuration
MCP_API_KEY=demo123
LOG_LEVEL=INFO

# Local Model Configuration
PREFER_LOCAL_MODELS=false
PREFERRED_LOCAL_MODEL=llama-3.1-70b
```

### Step 6: Initialize the Vector Database

The system requires vulnerability data to be embedded and stored in Qdrant. Run the setup script from the project root directory:

```bash
python data/setup_local_qdrant.py
```

**Important**: Always run scripts from the project root directory, not from within the `core/` folder.

This script will:
- Connect to Qdrant (via Docker)
- Create the necessary collection
- Load vulnerability data from the `osv_data` directory
- Generate embeddings using OpenAI
- Store the data in the vector database

**Important**: This process requires:
- Docker running with Qdrant container
- Valid OpenAI API key in `.env` file
- Sufficient time for embedding generation (may take 10-30 minutes depending on data size)

If Qdrant is not running, the script will attempt to start it automatically. Otherwise, ensure Qdrant is running:

```bash
docker run -d --name qdrant-threat-intel -p 6333:6333 -p 6334:6334 -v $(pwd)/qdrant_storage:/qdrant/storage qdrant/qdrant:latest
```

## Running the Application

### Important: Working Directory

**Always run all commands from the project root directory** (where the `.env` file and `requirements.txt` are located). Do not run commands from within the `core/` folder.

To verify you're in the correct directory, you should see:
- `.env` file
- `requirements.txt`
- `core/` folder
- `data/` folder
- `tools/` folder

### Quick Start

The simplest way to run the application is using the main runner script:

```bash
python core/run_all.py
```

This script will:
1. Check system setup and configuration
2. Start Docker services (Qdrant and OpenSearch) if needed
3. Launch the Streamlit web interface
4. Open your default web browser automatically

### Command Line Options

The `core/run_all.py` script supports several options. Remember to run from the project root:

```bash
# Run with local model preference
python core/run_all.py --local

# Run without starting Docker services (use existing containers)
python core/run_all.py --no-docker

# Combine options
python core/run_all.py --local --no-docker
```

### Manual Service Startup

If you prefer to start services manually:

**Start Qdrant:**
```bash
docker run -d --name qdrant-threat-intel -p 6333:6333 -p 6334:6334 -v $(pwd)/qdrant_storage:/qdrant/storage qdrant/qdrant:latest
```

**Start OpenSearch (Optional):**
```bash
docker run -d --name opensearch-threat-intel -p 9200:9200 -p 9600:9600 -e discovery.type=single-node -e DISABLE_INSTALL_DEMO_CONFIG=true -e DISABLE_SECURITY_PLUGIN=true opensearchproject/opensearch:2.11.0
```

**Start Streamlit UI (from project root):**
```bash
streamlit run core/web_ui.py
```

**Important**: All commands should be run from the project root directory where the `.env` file is located.

### Accessing the Web Interface

Once the application is running:
1. The Streamlit interface will automatically open in your default web browser
2. If it doesn't open automatically, navigate to: `http://localhost:8501`
3. The interface provides:
   - Security analysis query interface
   - Vulnerability search capabilities
   - Risk assessment and scoring
   - Remediation recommendations

## Usage Guide

### Basic Operations

**Querying Vulnerabilities:**
1. Enter your security question or vulnerability query in the main interface
2. Specify infrastructure context if applicable (programming languages, frameworks, etc.)
3. Click "Analyze" to search the vulnerability database
4. Review results with risk scores and recommendations

**Searching by CVE:**
1. Use the vulnerability search feature
2. Enter a CVE identifier (e.g., CVE-2024-1234)
3. View detailed vulnerability information and affected packages

**Ecosystem Filtering:**
The system supports filtering by software ecosystems:
- npm (Node.js packages)
- PyPI (Python packages)
- Maven (Java packages)
- Go (Go modules)
- Debian (Debian/Ubuntu packages)

### Advanced Features

**Risk Scoring:**
The system calculates comprehensive risk scores based on:
- CVSS (Common Vulnerability Scoring System) scores
- EPSS (Exploit Prediction Scoring System) probabilities
- CISA KEV (Known Exploited Vulnerabilities) status
- Asset criticality and exposure
- Patch availability
- Exploit availability

**Local Model Support:**
To use local LLM models instead of OpenAI:
1. Set `PREFER_LOCAL_MODELS=true` in `.env`
2. Install required dependencies: `pip install transformers torch`
3. Configure preferred model: `PREFERRED_LOCAL_MODEL=mistral-7b`
4. Run with `--local` flag from project root: `python core/run_all.py --local`

**Web Search Integration:**
Enable web search for real-time threat intelligence:
1. Obtain Serper API key from [serper.dev](https://serper.dev/)
2. Add `SERPER_API_KEY=your-key` to `.env`
3. Web search will automatically be used when available

## Troubleshooting

### Common Issues

**Docker Not Running:**
- Error: "Docker is not running"
- Solution: Start Docker Desktop and ensure it's running before launching the application

**Qdrant Connection Failed:**
- Error: "Could not connect to Qdrant"
- Solution: 
  1. Verify Docker is running: `docker ps`
  2. Check Qdrant container: `docker ps | grep qdrant`
  3. Restart Qdrant: `docker restart qdrant-threat-intel`
  4. Verify port 6333 is not in use by another application

**Missing OpenAI API Key:**
- Error: "Missing OPENAI_API_KEY"
- Solution:
  1. Ensure `.env` file exists in project root
  2. Verify `OPENAI_API_KEY=sk-...` is set in `.env`
  3. Run `python setup_env.py` to reconfigure

**Collection Not Found:**
- Error: "Qdrant collection 'osv_vulnerabilities' not found"
- Solution: Run `python data/setup_local_qdrant.py` to initialize the database

**Import Errors:**
- Error: "ModuleNotFoundError"
- Solution:
  1. Ensure virtual environment is activated
  2. Reinstall dependencies: `pip install -r requirements.txt`
  3. Install missing packages: `pip install streamlit keyring opensearch-py`

**Port Already in Use:**
- Error: "Address already in use"
- Solution:
  1. Check if another instance is running: `streamlit run core/web_ui.py --server.port 8502`
  2. Kill existing process on the port
  3. Change port in Docker run command if needed

**Path or Import Errors:**
- Error: "ModuleNotFoundError" or "File not found"
- Solution:
  1. Ensure you're running from the project root directory
  2. Verify all files are in their correct locations (core/run_all.py, core/web_ui.py)
  3. Check that PYTHONPATH includes the project root
  4. Re-run setup: `python setup_env.py` and `python data/setup_local_qdrant.py`

**Embedding Generation Errors:**
- Error: "Error generating embedding"
- Solution:
  1. Verify OpenAI API key is valid and has credits
  2. Check API rate limits
  3. Ensure internet connection is stable
  4. Retry the setup script

### Performance Optimization

**Slow Query Performance:**
- Ensure Qdrant has sufficient resources allocated in Docker
- Consider reducing batch size in setup script
- Check network latency to Qdrant container

**Memory Issues:**
- Increase Docker memory allocation in Docker Desktop settings
- Consider using smaller embedding models
- Close other applications to free system resources

## Project Structure

```
Threat-Intel-Agent/
├── core/                    # Core functionality modules
│   ├── embeddings.py       # Embedding generation
│   ├── hybrid_search.py    # Hybrid search engine
│   ├── llm.py             # LLM provider interface
│   ├── model_manager.py   # Local model management
│   ├── reranker.py        # Document reranking
│   ├── risk_scorer.py     # Risk scoring engine
│   ├── sbom_processor.py  # SBOM processing
│   ├── secrets_manager.py # API key management
│   ├── run_all.py         # Main application runner
│   └── web_ui.py          # Streamlit web interface
├── client/                 # MCP client components
├── data/                   # Data collection scripts
│   ├── osv_collector.py   # OSV data collection
│   └── setup_local_qdrant.py # Database setup
├── server/                 # MCP server
├── tools/                   # Tool implementations
│   ├── rag_tool.py        # RAG tool for vulnerabilities
│   └── web_search.py      # Web search tool
├── utils/                  # Utility modules
│   └── config.py          # Configuration management
├── osv_data/              # Vulnerability data files
├── qdrant_storage/        # Qdrant persistent storage
├── setup_env.py           # Environment setup script
├── requirements.txt       # Python dependencies
└── .env                   # Environment configuration (create this)
```

## Configuration Reference

### Environment Variables

All configuration is done through the `.env` file:

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `OPENAI_API_KEY` | Yes | None | OpenAI API key for embeddings and LLM |
| `OPENAI_MODEL` | No | `gpt-4o-mini` | OpenAI model to use |
| `SERPER_API_KEY` | No | None | Serper API key for web search |
| `MCP_API_KEY` | No | `demo123` | MCP server authentication key |
| `LOG_LEVEL` | No | `INFO` | Logging level (DEBUG, INFO, WARNING, ERROR) |
| `PREFER_LOCAL_MODELS` | No | `false` | Prefer local models over OpenAI |
| `PREFERRED_LOCAL_MODEL` | No | `llama-3.1-70b` | Preferred local model name |

### Docker Services

The application uses Docker containers for:

- **Qdrant**: Vector database on port 6333 (HTTP) and 6334 (gRPC)
- **OpenSearch**: Optional search engine on port 9200 (HTTP)

Both services store data in the `qdrant_storage/` directory for persistence.

## Security Considerations

- **API Keys**: Never commit `.env` file to version control. It contains sensitive credentials.
- **Docker**: Ensure Docker containers are properly secured and not exposed to public networks.
- **Local Models**: When using local models, ensure models are downloaded from trusted sources.
- **Network**: The application runs on localhost by default. For production deployment, implement proper authentication and network security.

## Support and Maintenance

### Logs

Application logs are displayed in the terminal/console where the application is running. Set `LOG_LEVEL=DEBUG` in `.env` for detailed debugging information.

### Data Updates

To update vulnerability data:
1. Run the OSV data collector: `python data/osv_collector.py`
2. Re-run the setup script: `python data/setup_local_qdrant.py`

### Upgrading Dependencies

To update Python packages:

```bash
pip install --upgrade -r requirements.txt
```

To update Docker images:

```bash
docker pull qdrant/qdrant:latest
docker pull opensearchproject/opensearch:2.11.0
```

## License

See LICENSE file for license information.

